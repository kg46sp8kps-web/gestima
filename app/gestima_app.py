"""GESTIMA 1.0 - Hlavní FastAPI aplikace"""

import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
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
    pricing_router,
    materials_router,
    material_inputs_router,  # ADR-024
    work_centers_router,
    config_router,
    data_router,
    pages_router,
    misc_router,
    admin_router
)
from app.database import async_session, engine, close_db


# ============================================================================
# SECURITY HEADERS MIDDLEWARE (P0 - Audit fix)
# ============================================================================

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware pro přidání bezpečnostních HTTP hlaviček (H-3, H-4 audit fix).
    Chrání proti: Clickjacking, MIME sniffing, XSS, SSL strip attacks.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Ochrana proti clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Zakázat MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # XSS ochrana (legacy, ale stále užitečné)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Kontrola referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy (omezit features)
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # === H-3: Content Security Policy ===
        # Pragmatic approach: unsafe-inline + unsafe-eval pro Alpine.js + HTMX
        # Note: Alpine.js REQUIRES 'unsafe-eval' for reactivity (new AsyncFunction)
        # CSP nonces (stricter) plánované v v2.0 (ADR-XXX)
        csp_policy = "; ".join([
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Alpine.js eval + HTMX inline
            "style-src 'self' 'unsafe-inline'",   # Inline styles
            "img-src 'self' data:",               # Allow data: URIs for inline images
            "font-src 'self'",
            "connect-src 'self'",                 # HTMX AJAX
            "frame-ancestors 'none'",             # Redundant with X-Frame-Options
            "base-uri 'self'",
            "form-action 'self'",
        ])
        response.headers["Content-Security-Policy"] = csp_policy

        # === H-4: HSTS (HTTPS Strict Transport Security) ===
        # CRITICAL: Only set HSTS on HTTPS connections!
        # Setting HSTS on HTTP causes browser errors.
        # In production (Caddy HTTPS), this enforces HTTPS-only access.
        if request.url.scheme == "https":
            # max-age=1 year, includeSubDomains, preload-ready
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response

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

# Security headers middleware (MUSÍ být před CORS)
app.add_middleware(SecurityHeadersMiddleware)

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

# Favicon route (zabrání 404 chybám)
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Vrátí logo.png jako favicon"""
    from fastapi.responses import FileResponse
    return FileResponse("app/static/img/logo.png")

app.include_router(auth_router.router, prefix="/api/auth", tags=["Auth"])
app.include_router(parts_router.router, prefix="/api/parts", tags=["Parts"])
app.include_router(operations_router.router, prefix="/api/operations", tags=["Operations"])
app.include_router(features_router.router, prefix="/api/features", tags=["Features"])
app.include_router(batches_router.router, prefix="/api/batches", tags=["Batches"])
app.include_router(pricing_router.router, prefix="/api/pricing", tags=["Pricing"])
app.include_router(materials_router.router, prefix="/api/materials", tags=["Materials"])
app.include_router(material_inputs_router.router)  # ADR-024: prefix already in router
# Machines router removed - replaced by WorkCenters (ADR-021)
app.include_router(work_centers_router.router, prefix="/api/work-centers", tags=["Work Centers"])
app.include_router(config_router.router, prefix="/api/config", tags=["Configuration"])
app.include_router(data_router.router, prefix="/api/data", tags=["Data"])
app.include_router(misc_router.router, prefix="/api/misc", tags=["Miscellaneous"])
app.include_router(admin_router.router, prefix="/admin", tags=["Admin"])
app.include_router(pages_router.router, tags=["Pages"])


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Extended health check endpoint pro monitoring a load balancery.

    Kontroluje:
    - Database connectivity
    - Backup folder integrity
    - Disk space
    - Recent backup age

    Stavy:
    - healthy: Vše OK
    - degraded: Warnings, ale ne kritické (status 200)
    - unhealthy: Kritické problémy (status 503)
    - shutting_down: Graceful shutdown (status 503)
    """
    # During shutdown, return 503 immediately
    if _shutdown_in_progress:
        return JSONResponse(
            content={"status": "shutting_down", "version": settings.VERSION},
            status_code=503
        )

    checks = {}

    # 1. Database check
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = {"status": "healthy"}
    except Exception as e:
        checks["database"] = {
            "status": "unhealthy",
            "error": str(e) if settings.DEBUG else "Database connection failed"
        }

    # 2. Backup folder integrity check
    backup_dir = settings.BASE_DIR / "backups"
    try:
        if not backup_dir.exists():
            checks["backup_folder"] = {
                "status": "warning",
                "message": "Backup folder neexistuje"
            }
        elif not os.access(backup_dir, os.W_OK):
            checks["backup_folder"] = {
                "status": "unhealthy",
                "message": "Backup folder není writeable"
            }
        else:
            checks["backup_folder"] = {"status": "healthy"}
    except Exception as e:
        checks["backup_folder"] = {
            "status": "error",
            "error": str(e) if settings.DEBUG else "Backup folder check failed"
        }

    # 3. Disk space warning
    try:
        usage = shutil.disk_usage(settings.BASE_DIR)
        free_gb = usage.free / (1024**3)
        total_gb = usage.total / (1024**3)
        percent_free = (usage.free / usage.total) * 100

        if percent_free < 5:  # < 5% free
            disk_status = "critical"
        elif percent_free < 10:  # < 10% free
            disk_status = "warning"
        else:
            disk_status = "healthy"

        checks["disk_space"] = {
            "status": disk_status,
            "free_gb": round(free_gb, 2),
            "total_gb": round(total_gb, 2),
            "percent_free": round(percent_free, 1)
        }
    except Exception as e:
        checks["disk_space"] = {
            "status": "error",
            "error": str(e) if settings.DEBUG else "Disk space check failed"
        }

    # 4. Recent backup check
    try:
        if backup_dir.exists():
            backups = sorted(
                backup_dir.glob("*.db.backup*"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            if not backups:
                checks["recent_backup"] = {
                    "status": "warning",
                    "message": "Žádné backupy nenalezeny"
                }
            else:
                latest = backups[0]
                age_hours = (
                    datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)
                ).total_seconds() / 3600

                if age_hours > 48:  # Starší než 2 dny
                    backup_status = "warning"
                else:
                    backup_status = "healthy"

                checks["recent_backup"] = {
                    "status": backup_status,
                    "latest_backup": latest.name,
                    "age_hours": round(age_hours, 1)
                }
        else:
            checks["recent_backup"] = {
                "status": "warning",
                "message": "Backup folder neexistuje"
            }
    except Exception as e:
        checks["recent_backup"] = {
            "status": "error",
            "error": str(e) if settings.DEBUG else "Backup check failed"
        }

    # Určit celkový status
    statuses = [check.get("status") for check in checks.values()]
    if "unhealthy" in statuses or "critical" in statuses:
        overall_status = "unhealthy"
        status_code = 503
    elif "warning" in statuses or "error" in statuses:
        overall_status = "degraded"
        status_code = 200  # Load balancer může pokračovat
    else:
        overall_status = "healthy"
        status_code = 200

    return JSONResponse(
        content={
            "status": overall_status,
            "version": settings.VERSION,
            "checks": checks
        },
        status_code=status_code
    )


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
