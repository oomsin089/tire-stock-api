from datetime import date, datetime
from enum import Enum

from sqlmodel import Field, SQLModel, UniqueConstraint


class MovementType(str, Enum):
    """ชนิดการเคลื่อนไหวสต๊อก"""
    IN = "IN"                    # รับเข้า
    OUT = "OUT"                  # ขายออก
    TRANSFER_IN = "TRANSFER_IN"  # ย้ายเข้า (ปลายทาง)
    TRANSFER_OUT = "TRANSFER_OUT"  # ย้ายออก (ต้นทาง)
    ADJUST = "ADJUST"            # ปรับยอด (นับสต๊อก/แก้ error)


class Product(SQLModel, table=True):
    """สินค้า 1 รุ่น 1 ขนาด = 1 product. Lot ไม่อยู่ตรงนี้ (เก็บที่ movement)
    เพราะสินค้าเดียวกันมีได้หลาย lot"""
    __tablename__ = "product"
    __table_args__ = (
        UniqueConstraint("brand", "model", "size", name="uq_product_bms"),
    )

    id: int | None = Field(default=None, primary_key=True)
    brand: str = Field(index=True)          # GITI, OTANI, Michelin ...
    model: str = Field(index=True)          # P10, KN1000, SA1000 ...
    size: str = Field(index=True)           # 255/45/19, 195R14 ...
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Location(SQLModel, table=True):
    """พื้นที่เก็บ: ตู้1-4, โรง1-3, สั่งด่วน ฯลฯ"""
    __tablename__ = "location"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)  # ตู้1, โรง2 ...
    note: str | None = None


class Movement(SQLModel, table=True):
    """สมุดรายการเคลื่อนไหว (ledger).
    quantity เก็บเป็นค่า +/- : รับเข้า/ย้ายเข้า = บวก, ขายออก/ย้ายออก = ลบ
    ของคงเหลือ = SUM(quantity) group by product_id, lot_no, location_id
    """
    __tablename__ = "movement"

    id: int | None = Field(default=None, primary_key=True)
    moved_on: date = Field(index=True)
    product_id: int = Field(foreign_key="product.id", index=True)
    lot_no: str = Field(index=True)                 # เลข lot เช่น 1326
    location_id: int = Field(foreign_key="location.id", index=True)
    movement_type: MovementType = Field(index=True)
    quantity: int                                    # +/- (มีเครื่องหมายแล้ว)
    unit_price: float | None = None                  # ราคา/หน่วย (ถ้ามี)
    note: str | None = None
    # จับคู่ 2 ขาของการย้าย (TRANSFER_OUT + TRANSFER_IN ใช้ค่าเดียวกัน)
    transfer_group: str | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
