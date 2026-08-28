from datetime import date

from pydantic import BaseModel


# ---------- Product ----------
class ProductCreate(BaseModel):
    brand: str
    model: str
    size: str


# ---------- Location ----------
class LocationCreate(BaseModel):
    name: str
    note: str | None = None


# ---------- Movement: รับเข้า / ขายออก ----------
class StockInCreate(BaseModel):
    moved_on: date
    product_id: int
    lot_no: str
    location_id: int
    quantity: int          # จำนวนบวก (ระบบจะเก็บเป็น +)
    unit_price: float | None = None
    note: str | None = None


class StockOutCreate(BaseModel):
    moved_on: date
    product_id: int
    lot_no: str
    location_id: int
    quantity: int          # จำนวนบวก (ระบบจะแปลงเป็น -)
    unit_price: float | None = None
    note: str | None = None


# ---------- Movement: ย้ายพื้นที่ ----------
class TransferCreate(BaseModel):
    moved_on: date
    product_id: int
    lot_no: str
    from_location_id: int
    to_location_id: int
    quantity: int          # จำนวนบวก
    note: str | None = None


# ---------- Stock (ผลลัพธ์คำนวณ) ----------
class StockLine(BaseModel):
    product_id: int
    brand: str
    model: str
    size: str
    lot_no: str
    location_id: int
    location_name: str
    quantity: int
