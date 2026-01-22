"""GESTIMA 1.0 - Hlavní FastAPI aplikace"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.routers import parts_router, operations_router, features_router, batches_router, data_router, pages_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print(f"🚀 GESTIMA {settings.VERSION} běží na http://localhost:8000")
    yield
    print("👋 GESTIMA ukončena")


app = FastAPI(
    title="GESTIMA",
    description="Kalkulátor nákladů CNC obrábění",
    version=settings.VERSION,
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

app.include_router(parts_router.router, prefix="/api/parts", tags=["Parts"])
app.include_router(operations_router.router, prefix="/api/operations", tags=["Operations"])
app.include_router(features_router.router, prefix="/api/features", tags=["Features"])
app.include_router(batches_router.router, prefix="/api/batches", tags=["Batches"])
app.include_router(data_router.router, prefix="/api/data", tags=["Data"])
app.include_router(pages_router.router, tags=["Pages"])
