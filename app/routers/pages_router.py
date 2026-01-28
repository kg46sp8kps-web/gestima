"""GESTIMA - HTML Pages router (HTMX)"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.models.part import Part
# Machine model removed - replaced by WorkCenter (ADR-021)
from app.models.config import SystemConfig
from app.models import User
from app.models.enums import UserRole
from app.dependencies import get_current_user, require_role
from app.db_helpers import set_audit, safe_commit

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page (public)"""
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Dashboard (protected)"""
    result = await db.execute(select(Part).order_by(Part.updated_at.desc()).limit(20))
    parts = result.scalars().all()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "parts": parts,
        "user": current_user
    })


@router.get("/parts", response_class=HTMLResponse)
async def parts_list(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Parts list with filtering (protected)"""
    return templates.TemplateResponse("parts_list.html", {
        "request": request,
        "user": current_user
    })


@router.get("/parts/new", response_class=HTMLResponse)
async def part_new(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Create new part (protected)"""
    return templates.TemplateResponse("parts/new.html", {
        "request": request,
        "user": current_user
    })


@router.get("/parts/{part_number}/edit", response_class=HTMLResponse)
async def part_edit(
    part_number: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Edit part (protected)"""
    result = await db.execute(select(Part).where(Part.part_number == part_number))
    part = result.scalar_one_or_none()

    if not part:
        return HTMLResponse(content="<h1>Díl nenalezen</h1>", status_code=404)

    return templates.TemplateResponse("parts/edit.html", {
        "request": request,
        "part": part,
        "user": current_user
    })


@router.get("/parts/{part_number}/pricing", response_class=HTMLResponse)
async def part_pricing(
    part_number: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Part pricing breakdown page (protected)"""
    result = await db.execute(select(Part).where(Part.part_number == part_number))
    part = result.scalar_one_or_none()

    if not part:
        return HTMLResponse(content="<h1>Díl nenalezen</h1>", status_code=404)

    return templates.TemplateResponse("parts/pricing.html", {
        "request": request,
        "part": part,
        "user": current_user
    })


# ============================================================================
# MACHINES PAGES
# ============================================================================

# ============================================================================
# MACHINES ROUTES - DEPRECATED (replaced by WorkCenters, ADR-021)
# ============================================================================
# All /machines routes removed. See work_centers_router.py for replacement.


# ============================================================================
# SETTINGS / ADMIN PAGES
# ============================================================================

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """System settings page (admin only)"""
    result = await db.execute(select(SystemConfig).order_by(SystemConfig.key))
    configs = result.scalars().all()

    return templates.TemplateResponse("settings.html", {
        "request": request,
        "configs": configs,
        "user": current_user
    })
