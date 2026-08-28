# Tire Stock API

ระบบสต๊อกยาง (backend) — รับเข้า / ขายออก / ย้ายพื้นที่ / คำนวณของคงเหลือ
สร้างด้วย **FastAPI + SQLModel + PostgreSQL** พร้อม deploy ขึ้น Render + Neon

---

## แนวคิดของระบบ (สำคัญ อ่านก่อน)

ทุกการเคลื่อนไหวเก็บเป็นรายการเดียวกันในตาราง `movement` (แบบ **ledger**)
โดย `quantity` มีเครื่องหมาย + / - :

| การกระทำ | เก็บเป็น |
|---|---|
| รับเข้า | `+จำนวน` |
| ขายออก | `-จำนวน` |
| ย้ายพื้นที่ | 2 รายการ: ต้นทาง `-`, ปลายทาง `+` (ผูกด้วย `transfer_group`) |

**ของคงเหลือ = ผลรวม `quantity`** แยกตาม `product + lot + location`
วิธีนี้ยอดจะ balance เสมอ และแก้ย้อนหลังได้โดยไม่ต้องคำนวณสต๊อกใหม่ทั้งระบบ

### ตาราง
- `product` — ยี่ห้อ + รุ่น + ขนาด (1 แถว = 1 สินค้า)
- `location` — พื้นที่เก็บ (ตู้1-4, โรง1-3, สั่งด่วน ...)
- `movement` — สมุดรายการเคลื่อนไหวทั้งหมด (lot อยู่ตรงนี้ เพราะสินค้าเดียวมีได้หลาย lot)

---

## รันในเครื่อง (local)

```bash
# 1. สร้าง virtual env
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. ติดตั้ง
pip install -r requirements.txt

# 3. ตั้ง connection string (สมัคร Neon แล้วก๊อป pooled URL มา)
export DATABASE_URL="postgresql://user:pass@ep-xxx-pooler.xxx.neon.tech/db?sslmode=require"
# ไม่ตั้งค่าก็ได้ จะใช้ SQLite (ไฟล์ dev.db) ให้ทดสอบเร็ว ๆ

# 4. รัน
uvicorn app.main:app --reload
```

เปิด **http://localhost:8000/docs** จะเจอหน้า Swagger กดยิง API เล่นได้ทุกตัว

---

## นำเข้าข้อมูลเดิมจาก Excel

```bash
python -m scripts.import_excel "รายการยางว_ออโต_ไทร_.xlsx"
```

อ่านชีต `บัญชีรับเข้า` และ `บัญชีขายออก` แล้วสร้าง product / location / movement ให้อัตโนมัติ
(รันครั้งเดียวพอ — รันซ้ำจะเพิ่มข้อมูลซ้ำ)

---

## Endpoints หลัก

| Method | Path | ทำอะไร |
|---|---|---|
| GET | `/products` | รายการสินค้า (กรอง `?brand=` `?q=`) |
| POST | `/products` | เพิ่มสินค้า |
| GET | `/locations` | รายการพื้นที่เก็บ |
| POST | `/locations` | เพิ่มพื้นที่ |
| POST | `/movements/stock-in` | รับเข้า |
| POST | `/movements/stock-out` | ขายออก (กันขายเกินสต๊อก) |
| POST | `/movements/transfer` | ย้ายพื้นที่ (สร้าง 2 ขาให้เอง) |
| GET | `/movements` | ประวัติการเคลื่อนไหว (กรองได้) |
| GET | `/stock` | ของคงเหลือ แยก lot + พื้นที่ |
| GET | `/stock/by-location` | รายงานรวมต่อพื้นที่ (pivot) |
| GET | `/stock/summary` | ภาพรวม (จำนวน SKU, ยางคงเหลือรวม) |

---

## Deploy ขึ้น Render

1. push repo นี้ขึ้น GitHub
2. Render → **New → Blueprint** → ชี้มาที่ repo (มันจะอ่าน `render.yaml` เอง)
   หรือทำมือ: **New → Web Service** แล้วตั้ง
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. แท็บ **Environment** ใส่:
   - `DATABASE_URL` = pooled connection string ของ Neon
   - `ALLOWED_ORIGINS` = โดเมน frontend เช่น `https://your-app.vercel.app`

เสร็จแล้วได้ URL แบบ `https://tire-stock-api.onrender.com`

> Render free tier จะ "หลับ" หลังไม่มีคนเข้า 15 นาที คำขอแรกหลังหลับรอ ~30-60 วิ เป็นเรื่องปกติ

---

## สิ่งที่ยังไม่รวม (เผื่อทำต่อ)

- **ระบบ login / สิทธิ์ผู้ใช้** — ยังไม่มี (ตอนนี้ API เปิดหมด) ควรใส่ก่อนใช้จริง
- **Migration (Alembic)** — ตอนนี้ใช้ `create_all` พอสำหรับเริ่มต้น พอต้องแก้ schema ควรเปลี่ยนไปใช้ Alembic
- **import ชีตย้ายพื้นที่** — สคริปต์ยัง import แค่รับเข้า/ขายออก
- **แก้ไข/ลบ movement** — ตอนนี้มีแค่เพิ่ม (ตาม best practice ของ ledger ควรใช้รายการปรับยอด `ADJUST` แทนการลบ)
