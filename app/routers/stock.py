from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, func, select

from ..database import get_session
from ..models import Location, Movement, Product
from ..schemas import StockLine

router = APIRouter(prefix="/stock", tags=["stock"])


@router.get("", response_model=list[StockLine])
def current_stock(
    brand: str | None = Query(default=None),
    location_id: int | None = Query(default=None),
    lot_no: str | None = Query(default=None),
    include_zero: bool = Query(default=False, description="แสดงรายการที่คงเหลือ 0 ด้วยไหม"),
    session: Session = Depends(get_session),
):
    """ของคงเหลือ = SUM(quantity) จาก ledger แยกตาม product + lot + location"""
    qty = func.sum(Movement.quantity).label("qty")
    stmt = (
        select(
            Product.id, Product.brand, Product.model, Product.size,
            Movement.lot_no, Location.id, Location.name, qty,
        )
        .join(Product, Product.id == Movement.product_id)
        .join(Location, Location.id == Movement.location_id)
        .group_by(
            Product.id, Product.brand, Product.model, Product.size,
            Movement.lot_no, Location.id, Location.name,
        )
    )
    if brand:
        stmt = stmt.where(Product.brand == brand)
    if location_id:
        stmt = stmt.where(Movement.location_id == location_id)
    if lot_no:
        stmt = stmt.where(Movement.lot_no == lot_no)
    if not include_zero:
        stmt = stmt.having(func.sum(Movement.quantity) != 0)

    rows = session.exec(stmt.order_by(Product.brand, Product.model)).all()
    return [
        StockLine(
            product_id=r[0], brand=r[1], model=r[2], size=r[3],
            lot_no=r[4], location_id=r[5], location_name=r[6], quantity=int(r[7]),
        )
        for r in rows
    ]


@router.get("/by-location")
def stock_by_location(session: Session = Depends(get_session)):
    """รายงาน pivot: ของคงเหลือรวมต่อพื้นที่เก็บ (แบบชีต 'รายงานพื้นที่เก็บ')"""
    qty = func.sum(Movement.quantity).label("qty")
    rows = session.exec(
        select(Location.name, qty)
        .join(Location, Location.id == Movement.location_id)
        .group_by(Location.name)
        .order_by(Location.name)
    ).all()
    return [{"location": r[0], "quantity": int(r[1])} for r in rows if r[1]]


@router.get("/summary")
def stock_summary(session: Session = Depends(get_session)):
    """ภาพรวม: จำนวน SKU, จำนวนยางคงเหลือรวม"""
    total = session.exec(
        select(func.coalesce(func.sum(Movement.quantity), 0))
    ).one()
    n_products = session.exec(select(func.count(Product.id))).one()
    n_locations = session.exec(select(func.count(Location.id))).one()
    return {
        "total_tires_in_stock": int(total),
        "product_count": int(n_products),
        "location_count": int(n_locations),
    }
