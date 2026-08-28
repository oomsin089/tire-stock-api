import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, func, select

from ..database import get_session
from ..models import Movement, MovementType, Product, Location
from ..schemas import StockInCreate, StockOutCreate, TransferCreate

router = APIRouter(prefix="/movements", tags=["movements"])


def _current_qty(session: Session, product_id: int, lot_no: str, location_id: int) -> int:
    """ของคงเหลือ ณ จุดหนึ่ง = ผลรวม quantity ของ product+lot+location นั้น"""
    total = session.exec(
        select(func.coalesce(func.sum(Movement.quantity), 0)).where(
            Movement.product_id == product_id,
            Movement.lot_no == lot_no,
            Movement.location_id == location_id,
        )
    ).one()
    return int(total)


def _require(session: Session, model, id_, label: str):
    obj = session.get(model, id_)
    if not obj:
        raise HTTPException(status_code=404, detail=f"ไม่พบ{label}")
    return obj


@router.get("", response_model=list[Movement])
def list_movements(
    product_id: int | None = None,
    location_id: int | None = None,
    movement_type: MovementType | None = None,
    limit: int = Query(default=100, le=1000),
    session: Session = Depends(get_session),
):
    stmt = select(Movement)
    if product_id:
        stmt = stmt.where(Movement.product_id == product_id)
    if location_id:
        stmt = stmt.where(Movement.location_id == location_id)
    if movement_type:
        stmt = stmt.where(Movement.movement_type == movement_type)
    stmt = stmt.order_by(Movement.moved_on.desc(), Movement.id.desc()).limit(limit)
    return session.exec(stmt).all()


@router.post("/stock-in", response_model=Movement, status_code=201)
def stock_in(payload: StockInCreate, session: Session = Depends(get_session)):
    _require(session, Product, payload.product_id, "สินค้า")
    _require(session, Location, payload.location_id, "พื้นที่เก็บ")
    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="จำนวนต้องมากกว่า 0")

    mv = Movement(
        moved_on=payload.moved_on,
        product_id=payload.product_id,
        lot_no=payload.lot_no,
        location_id=payload.location_id,
        movement_type=MovementType.IN,
        quantity=abs(payload.quantity),   # รับเข้า = บวก
        unit_price=payload.unit_price,
        note=payload.note,
    )
    session.add(mv)
    session.commit()
    session.refresh(mv)
    return mv


@router.post("/stock-out", response_model=Movement, status_code=201)
def stock_out(payload: StockOutCreate, session: Session = Depends(get_session)):
    _require(session, Product, payload.product_id, "สินค้า")
    _require(session, Location, payload.location_id, "พื้นที่เก็บ")
    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="จำนวนต้องมากกว่า 0")

    # กันขายเกินสต๊อก
    have = _current_qty(session, payload.product_id, payload.lot_no, payload.location_id)
    if have < payload.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"ของไม่พอ: คงเหลือ {have} แต่จะตัด {payload.quantity}",
        )

    mv = Movement(
        moved_on=payload.moved_on,
        product_id=payload.product_id,
        lot_no=payload.lot_no,
        location_id=payload.location_id,
        movement_type=MovementType.OUT,
        quantity=-abs(payload.quantity),  # ขายออก = ลบ
        unit_price=payload.unit_price,
        note=payload.note,
    )
    session.add(mv)
    session.commit()
    session.refresh(mv)
    return mv


@router.post("/transfer", response_model=list[Movement], status_code=201)
def transfer(payload: TransferCreate, session: Session = Depends(get_session)):
    """ย้ายของข้ามพื้นที่ = สร้าง 2 รายการ (ออกจากต้นทาง + เข้าปลายทาง) ผูกด้วย transfer_group"""
    _require(session, Product, payload.product_id, "สินค้า")
    _require(session, Location, payload.from_location_id, "พื้นที่ต้นทาง")
    _require(session, Location, payload.to_location_id, "พื้นที่ปลายทาง")

    if payload.from_location_id == payload.to_location_id:
        raise HTTPException(status_code=400, detail="ต้นทางกับปลายทางต้องคนละที่")
    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="จำนวนต้องมากกว่า 0")

    have = _current_qty(session, payload.product_id, payload.lot_no, payload.from_location_id)
    if have < payload.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"ของต้นทางไม่พอ: คงเหลือ {have} แต่จะย้าย {payload.quantity}",
        )

    group = uuid.uuid4().hex
    out_mv = Movement(
        moved_on=payload.moved_on,
        product_id=payload.product_id,
        lot_no=payload.lot_no,
        location_id=payload.from_location_id,
        movement_type=MovementType.TRANSFER_OUT,
        quantity=-abs(payload.quantity),
        note=payload.note,
        transfer_group=group,
    )
    in_mv = Movement(
        moved_on=payload.moved_on,
        product_id=payload.product_id,
        lot_no=payload.lot_no,
        location_id=payload.to_location_id,
        movement_type=MovementType.TRANSFER_IN,
        quantity=abs(payload.quantity),
        note=payload.note,
        transfer_group=group,
    )
    session.add(out_mv)
    session.add(in_mv)
    session.commit()
    session.refresh(out_mv)
    session.refresh(in_mv)
    return [out_mv, in_mv]
