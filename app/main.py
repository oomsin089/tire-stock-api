import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import locations, movements, products, stock


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()   # สร้างตารางถ้ายังไม่มี
    yield


app = FastAPI(
    title="Tire Stock API",
    description="ระบบสต๊อกยาง: รับเข้า / ขายออก / ย้ายพื้นที่ / ของคงเหลือ",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: ใส่โดเมน frontend จริงของคุณเพิ่มใน env ALLOWED_ORIGINS (คั่นด้วย ,)
default_origins = "http://localhost:3000,http://localhost:5173"
origins = os.environ.get("ALLOWED_ORIGINS", default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router)
app.include_router(locations.router)
app.include_router(movements.router)
app.include_router(stock.router)


@app.get("/", tags=["health"])
def health():
    return {"status": "ok", "service": "tire-stock-api"}
