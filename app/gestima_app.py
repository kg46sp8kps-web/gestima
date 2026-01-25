"""GESTIMA 1.0 - Hlavní FastAPI aplikace"""

import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.logging_config import setup_logging, get_logger
from app.rate_limiter import setup_rate_limiting
from app.seed_data import seed_demo_parts
from sqlalchemy import text

from app.routers import (
    auth_router,
    parts_router,
    operations_router,
    features_router,
    batches_router,
    materials_router,
    data_router,
    pages_router,
    misc_router
)
from app.database import async_session, engine, close_db

# Shutdown state for graceful shutdown
_shutdown_in_progress = False

# Inicializace loggingu
setup_logging(debug=settings.DEBUG)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _shutdown_in_progress

    # Startup
    await init_db()
    logger.info(f"🚀 GESTIMA {settings.VERSION} běží na http://localhost:8000")

    # Seed demo data
    async with async_session() as db:
        await seed_demo_parts(db)

    yield

    # Shutdown
    _shutdown_in_progress = True
    logger.info("⏳ Graceful shutdown started...")

    # Close database connections
    await close_db()
    logger.info("✅ Database connections closed")

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
app.include_router(materials_router.router, prefix="/api/materials", tags=["Materials"])
app.include_router(data_router.router, prefix="/api/data", tags=["Data"])
app.include_router(misc_router.router, prefix="/api/misc", tags=["Miscellaneous"])
app.include_router(pages_router.router, tags=["Pages"])


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint pro monitoring a load balancery.
    Vrací stav aplikace a databáze.
    Během shutdown vrací 503 (load balancer přestane posílat requesty).
    """
    # During shutdown, return 503 immediately
    if _shutdown_in_progress:
        return JSONResponse(
            content={"status": "shutting_down", "version": settings.VERSION},
            status_code=503
        )

    db_status = "healthy"
    db_error = None

    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "unhealthy"
        db_error = str(e) if settings.DEBUG else "Database connection failed"

    status = "healthy" if db_status == "healthy" else "unhealthy"
    status_code = 200 if status == "healthy" else 503

    response = {
        "status": status,
        "version": settings.VERSION,
        "database": db_status,
    }

    if db_error:
        response["database_error"] = db_error

    return JSONResponse(content=response, status_code=status_code)


# ============================================================================
# GLOBAL ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handler pro HTTPException - speciálně 401 (Unauthorized)
    Pokud je HTML request a 401 → redirect na /login
    """
    if exc.status_code == 401:
        # Kontrola zda je to HTML request (ne API)
        accept = request.headers.get("accept", "")
        if "text/html" in accept or request.url.path.startswith("/parts"):
            # Redirect na login s query parametrem pro původní URL
            return RedirectResponse(
                url=f"/login?redirect={request.url.path}",
                status_code=302
            )

    # Pro všechny ostatní HTTP výjimky (nebo API requesty) vrátit JSON
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


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
