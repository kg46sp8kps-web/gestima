"""GESTIMA 1.0 - Hlavní FastAPI aplikace"""

import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.logging_config import setup_logging, get_logger
from app.rate_limiter import setup_rate_limiting
from app.routers import (
    auth_router,
    parts_router,
    operations_router,
    features_router,
    batches_router,
    data_router,
    pages_router
)

# Inicializace loggingu
setup_logging(debug=settings.DEBUG)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info(f"🚀 GESTIMA {settings.VERSION} běží na http://localhost:8000")
    yield
    logger.info("👋 GESTIMA ukončena")


app = FastAPI(
    title="GESTIMA",
    description="Kalkulátor nákladů CNC obrábění",
    version=settings.VERSION,
    lifespan=lifespan,
)

# Rate limiting
setup_rate_limiting(app)
if settings.RATE_LIMIT_ENABLED:
    logger.info(f"Rate limiting enabled: {settings.RATE_LIMIT_DEFAULT}")

# CORS middleware - pouze pokud jsou definovány CORS_ORIGINS
if settings.CORS_ORIGINS:
    origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
            allow_headers=["*"],
        )
        logger.info(f"CORS enabled for origins: {origins}")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

app.include_router(auth_router.router, prefix="/api/auth", tags=["Auth"])
app.include_router(parts_router.router, prefix="/api/parts", tags=["Parts"])
app.include_router(operations_router.router, prefix="/api/operations", tags=["Operations"])
app.include_router(features_router.router, prefix="/api/features", tags=["Features"])
app.include_router(batches_router.router, prefix="/api/batches", tags=["Batches"])
app.include_router(data_router.router, prefix="/api/data", tags=["Data"])
app.include_router(pages_router.router, tags=["Pages"])


# ============================================================================
# GLOBAL ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Globální handler pro všechny neošetřené výjimky
    Loguje chybu a vrací generickou odpověď (bez exposure detailů)
    """
    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
            "client": request.client.host if request.client else None,
        }
    )

    # V DEBUG módu vraťme detail, v produkci ne
    if settings.DEBUG:
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error": str(exc),
                "type": type(exc).__name__,
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
