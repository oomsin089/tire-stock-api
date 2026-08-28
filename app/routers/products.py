from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..database import get_session
from ..models import Product
from ..schemas import ProductCreate

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[Product])
def list_products(
    brand: str | None = Query(default=None),
    q: str | None = Query(default=None, description="ค้นหาใน model/size"),
    session: Session = Depends(get_session),
):
    stmt = select(Product)
    if brand:
        stmt = stmt.where(Product.brand == brand)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Product.model.ilike(like)) | (Product.size.ilike(like)))
    return session.exec(stmt.order_by(Product.brand, Product.model, Product.size)).all()


@router.post("", response_model=Product, status_code=201)
def create_product(payload: ProductCreate, session: Session = Depends(get_session)):
    # กันสินค้าซ้ำ (brand+model+size)
    exists = session.exec(
        select(Product).where(
            Product.brand == payload.brand,
            Product.model == payload.model,
            Product.size == payload.size,
        )
    ).first()
    if exists:
        return exists  # มีอยู่แล้ว คืนตัวเดิม (idempotent)

    product = Product(**payload.model_dump())
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


@router.get("/{product_id}", response_model=Product)
def get_product(product_id: int, session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")
    return product
