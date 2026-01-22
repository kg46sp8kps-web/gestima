"""GESTIMA - HTML Pages router (HTMX)"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.part import Part

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Part).order_by(Part.updated_at.desc()).limit(20))
    parts = result.scalars().all()
    
    return templates.TemplateResponse("index.html", {"request": request, "parts": parts})


@router.get("/parts", response_class=HTMLResponse)
async def parts_list(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Part).order_by(Part.updated_at.desc()))
    parts = result.scalars().all()
    
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("parts/list_fragment.html", {"request": request, "parts": parts})
    
    return templates.TemplateResponse("parts/list.html", {"request": request, "parts": parts})


@router.get("/parts/{part_id}/edit", response_class=HTMLResponse)
async def part_edit(part_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Part).where(Part.id == part_id))
    part = result.scalar_one_or_none()
    
    if not part:
        return HTMLResponse(content="<h1>Díl nenalezen</h1>", status_code=404)
    
    return templates.TemplateResponse("parts/edit.html", {"request": request, "part": part})
