"""
นำเข้าข้อมูลเดิมจากไฟล์ Excel ของน้อง เข้าฐานข้อมูล

วิธีใช้:
    export DATABASE_URL="postgresql://...neon...?sslmode=require"
    python -m scripts.import_excel "รายการยางว_ออโต_ไทร_.xlsx"

อ่านชีต 'บัญชีรับเข้า' และ 'บัญชีขายออก' แล้วสร้าง product / location / movement ให้อัตโนมัติ
(ชีตย้ายพื้นที่ 'ชีต 1' ยังไม่ import เพราะข้อมูลตัวอย่างว่างอยู่ — เพิ่มทีหลังได้)
"""
import sys
from datetime import date, datetime

from openpyxl import load_workbook
from sqlmodel import Session, select

# ให้รันจาก root ของโปรเจกต์: python -m scripts.import_excel <file>
from app.database import engine, init_db
from app.models import Location, Movement, MovementType, Product


def get_or_create_product(session, cache, brand, model, size):
    key = (brand, model, size)
    if key in cache:
        return cache[key]
    p = session.exec(
        select(Product).where(
            Product.brand == brand, Product.model == model, Product.size == size
        )
    ).first()
    if not p:
        p = Product(brand=brand, model=model, size=size)
        session.add(p)
        session.commit()
        session.refresh(p)
    cache[key] = p
    return p


def get_or_create_location(session, cache, name):
    if name in cache:
        return cache[name]
    loc = session.exec(select(Location).where(Location.name == name)).first()
    if not loc:
        loc = Location(name=name)
        session.add(loc)
        session.commit()
        session.refresh(loc)
    cache[name] = loc
    return loc


def parse_date(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    # Excel serial number
    if isinstance(v, (int, float)):
        return date(1899, 12, 30) + __import__("datetime").timedelta(days=int(v))
    return date.today()


def import_sheet(session, ws, sign, movement_type, pcache, lcache):
    count = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        # คอลัมน์: วันที่, SKU, Brand, Model, Size, Lot, จำนวน, ราคา/หน่วย, ราคาสุทธิ, หมายเหตุ, พื้นที่
        if not row or not row[2]:  # ไม่มี brand = ข้าม
            continue
        brand, model, size, lot = row[2], row[3], str(row[4]), str(row[5])
        qty = row[6]
        if not qty:
            continue
        location_name = row[10] or "ไม่ได้ระบุ"
        note = row[9]
        unit_price = row[7] if isinstance(row[7], (int, float)) else None

        product = get_or_create_product(session, pcache, brand, model, size)
        location = get_or_create_location(session, lcache, location_name)

        mv = Movement(
            moved_on=parse_date(row[0]),
            product_id=product.id,
            lot_no=lot,
            location_id=location.id,
            movement_type=movement_type,
            quantity=sign * abs(int(qty)),
            unit_price=unit_price,
            note=note,
        )
        session.add(mv)
        count += 1
    session.commit()
    return count


def main(path):
    init_db()
    wb = load_workbook(path, read_only=True, data_only=True)
    pcache, lcache = {}, {}
    with Session(engine) as session:
        n_in = import_sheet(
            session, wb["บัญชีรับเข้า"], +1, MovementType.IN, pcache, lcache
        )
        n_out = import_sheet(
            session, wb["บัญชีขายออก"], -1, MovementType.OUT, pcache, lcache
        )
    print(f"เสร็จ: รับเข้า {n_in} รายการ, ขายออก {n_out} รายการ")
    print(f"สินค้า {len(pcache)} รายการ, พื้นที่ {len(lcache)} แห่ง")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("ใช้: python -m scripts.import_excel <ไฟล์.xlsx>")
        sys.exit(1)
    main(sys.argv[1])
