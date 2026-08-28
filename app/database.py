import os

from sqlmodel import Session, SQLModel, create_engine

# อ่าน connection string จาก environment variable เท่านั้น
# ตอน dev ให้ตั้งใน .env แล้วรัน; ตอน deploy ตั้งใน Render dashboard
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./dev.db")

# psycopg (v3) ต้องใช้ prefix นี้ — แปลงให้อัตโนมัติ
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# Neon เป็น serverless (scale-to-zero) -> pool_pre_ping กัน connection ตายตอน DB เพิ่งตื่น
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args=connect_args,
)


def init_db() -> None:
    """สร้างตารางทั้งหมดถ้ายังไม่มี (เรียกตอนแอปเปิด)"""
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
