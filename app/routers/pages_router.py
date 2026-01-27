"""GESTIMA - HTML Pages router (HTMX)"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.models.part import Part
from app.models.machine import MachineDB, MachineCreate, MachineUpdate
from app.models.config import SystemConfig
from app.models import User
from app.models.enums import UserRole
from app.dependencies import get_current_user, require_role
from app.db_helpers import set_audit

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

@router.get("/machines", response_class=HTMLResponse)
async def machines_list(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Machines list (protected)"""
    return templates.TemplateResponse("machines_list.html", {
        "request": request,
        "user": current_user
    })


@router.get("/machines/new", response_class=HTMLResponse)
async def machine_new(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Create new machine (protected)"""
    return templates.TemplateResponse("machines/edit.html", {
        "request": request,
        "machine": None,
        "user": current_user
    })


@router.get("/machines/{machine_id}/edit", response_class=HTMLResponse)
async def machine_edit(
    machine_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Edit machine (protected)"""
    result = await db.execute(select(MachineDB).where(MachineDB.id == machine_id))
    machine = result.scalar_one_or_none()

    if not machine:
        return HTMLResponse(content="<h1>Stroj nenalezen</h1>", status_code=404)

    return templates.TemplateResponse("machines/edit.html", {
        "request": request,
        "machine": machine,
        "user": current_user
    })


@router.post("/machines")
async def machine_create_post(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    type: str = Form(...),
    subtype: Optional[str] = Form(None),
    max_bar_dia: Optional[float] = Form(None),
    max_cut_diameter: Optional[float] = Form(None),
    max_workpiece_dia: Optional[float] = Form(None),
    max_workpiece_length: Optional[float] = Form(None),
    min_workpiece_dia: Optional[float] = Form(None),
    bar_feed_max_length: Optional[float] = Form(None),
    has_bar_feeder: bool = Form(False),
    has_milling: bool = Form(False),
    max_milling_tools: Optional[int] = Form(None),
    has_sub_spindle: bool = Form(False),
    axes: Optional[int] = Form(None),
    suitable_for_series: bool = Form(True),
    suitable_for_single: bool = Form(True),
    hourly_rate_amortization: float = Form(400.0),
    hourly_rate_labor: float = Form(300.0),
    hourly_rate_tools: float = Form(200.0),
    hourly_rate_overhead: float = Form(300.0),
    setup_base_min: float = Form(30.0),
    setup_per_tool_min: float = Form(3.0),
    priority: int = Form(99),
    active: bool = Form(True),
    notes: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create machine via form POST"""
    # Build data dict
    data = MachineCreate(
        code=code,
        name=name,
        type=type,
        subtype=subtype,
        max_bar_dia=max_bar_dia,
        max_cut_diameter=max_cut_diameter,
        max_workpiece_dia=max_workpiece_dia,
        max_workpiece_length=max_workpiece_length,
        min_workpiece_dia=min_workpiece_dia,
        bar_feed_max_length=bar_feed_max_length,
        has_bar_feeder=has_bar_feeder,
        has_milling=has_milling,
        max_milling_tools=max_milling_tools,
        has_sub_spindle=has_sub_spindle,
        axes=axes,
        suitable_for_series=suitable_for_series,
        suitable_for_single=suitable_for_single,
        hourly_rate_amortization=hourly_rate_amortization,
        hourly_rate_labor=hourly_rate_labor,
        hourly_rate_tools=hourly_rate_tools,
        hourly_rate_overhead=hourly_rate_overhead,
        setup_base_min=setup_base_min,
        setup_per_tool_min=setup_per_tool_min,
        priority=priority,
        active=active,
        notes=notes
    )

    machine = MachineDB(**data.model_dump())
    set_audit(machine, current_user.username)
    db.add(machine)

    try:
        await db.commit()
        await db.refresh(machine)
        return RedirectResponse(url="/machines", status_code=303)
    except Exception as e:
        await db.rollback()
        return HTMLResponse(content=f"<h1>Chyba při vytváření stroje</h1><p>{str(e)}</p>", status_code=500)


@router.post("/machines/{machine_id}")
async def machine_update_post(
    machine_id: int,
    request: Request,
    version: int = Form(...),
    code: str = Form(...),
    name: str = Form(...),
    type: str = Form(...),
    subtype: Optional[str] = Form(None),
    max_bar_dia: Optional[float] = Form(None),
    max_cut_diameter: Optional[float] = Form(None),
    max_workpiece_dia: Optional[float] = Form(None),
    max_workpiece_length: Optional[float] = Form(None),
    min_workpiece_dia: Optional[float] = Form(None),
    bar_feed_max_length: Optional[float] = Form(None),
    has_bar_feeder: bool = Form(False),
    has_milling: bool = Form(False),
    max_milling_tools: Optional[int] = Form(None),
    has_sub_spindle: bool = Form(False),
    axes: Optional[int] = Form(None),
    suitable_for_series: bool = Form(True),
    suitable_for_single: bool = Form(True),
    hourly_rate_amortization: float = Form(400.0),
    hourly_rate_labor: float = Form(300.0),
    hourly_rate_tools: float = Form(200.0),
    hourly_rate_overhead: float = Form(300.0),
    setup_base_min: float = Form(30.0),
    setup_per_tool_min: float = Form(3.0),
    priority: int = Form(99),
    active: bool = Form(True),
    notes: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update machine via form POST"""
    result = await db.execute(select(MachineDB).where(MachineDB.id == machine_id))
    machine = result.scalar_one_or_none()
    if not machine:
        return HTMLResponse(content="<h1>Stroj nenalezen</h1>", status_code=404)

    # Optimistic locking
    if machine.version != version:
        return HTMLResponse(
            content="<h1>Konflikt verzí</h1><p>Data byla změněna jiným uživatelem. Obnovte stránku a zkuste znovu.</p>",
            status_code=409
        )

    # Update fields
    machine.code = code
    machine.name = name
    machine.type = type
    machine.subtype = subtype
    machine.max_bar_dia = max_bar_dia
    machine.max_cut_diameter = max_cut_diameter
    machine.max_workpiece_dia = max_workpiece_dia
    machine.max_workpiece_length = max_workpiece_length
    machine.min_workpiece_dia = min_workpiece_dia
    machine.bar_feed_max_length = bar_feed_max_length
    machine.has_bar_feeder = has_bar_feeder
    machine.has_milling = has_milling
    machine.max_milling_tools = max_milling_tools
    machine.has_sub_spindle = has_sub_spindle
    machine.axes = axes
    machine.suitable_for_series = suitable_for_series
    machine.suitable_for_single = suitable_for_single
    machine.hourly_rate_amortization = hourly_rate_amortization
    machine.hourly_rate_labor = hourly_rate_labor
    machine.hourly_rate_tools = hourly_rate_tools
    machine.hourly_rate_overhead = hourly_rate_overhead
    machine.setup_base_min = setup_base_min
    machine.setup_per_tool_min = setup_per_tool_min
    machine.priority = priority
    machine.active = active
    machine.notes = notes
    set_audit(machine, current_user.username, is_update=True)

    try:
        await db.commit()
        return RedirectResponse(url="/machines", status_code=303)
    except Exception as e:
        await db.rollback()
        return HTMLResponse(content=f"<h1>Chyba při aktualizaci stroje</h1><p>{str(e)}</p>", status_code=500)


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
