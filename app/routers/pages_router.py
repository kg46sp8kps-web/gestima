"""GESTIMA - HTML Pages router (HTMX)"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.part import Part
from app.models import User
from app.dependencies import get_current_user

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


@router.get("/parts/{part_id}/edit", response_class=HTMLResponse)
async def part_edit(
    part_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Edit part (protected)"""
    result = await db.execute(select(Part).where(Part.id == part_id))
    part = result.scalar_one_or_none()

    if not part:
        return HTMLResponse(content="<h1>Díl nenalezen</h1>", status_code=404)

    return templates.TemplateResponse("parts/edit.html", {
        "request": request,
        "part": part,
        "user": current_user
    })
