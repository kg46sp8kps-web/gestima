"""GESTIMA - Infor Sync Router

API endpoints for managing Infor Smart Polling Sync.
All endpoints require ADMIN role.
"""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.db_helpers import safe_commit
from app.dependencies import require_role
from app.models import User, UserRole
from app.models.sync_state import (
    SyncState,
    SyncLog,
    SyncStateRead,
    SyncStateUpdate,
    SyncLogRead,
    SyncStatusResponse,
    SyncTriggerResponse,
)
from app.services.infor_sync_service import infor_sync_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/infor/sync", tags=["infor-sync"])


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Get current sync service status."""
    result = await db.execute(select(SyncState))
    steps = result.scalars().all()

    return SyncStatusResponse(running=infor_sync_service.running, steps=[SyncStateRead.model_validate(s) for s in steps])


@router.get("/logs", response_model=dict)
async def get_sync_logs(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """Get sync execution logs."""
    # Get total count
    count_result = await db.execute(select(func.count(SyncLog.id)))
    total = count_result.scalar() or 0

    # Get logs (ordered by created_at DESC)
    result = await db.execute(select(SyncLog).order_by(SyncLog.created_at.desc()).offset(skip).limit(limit))
    logs = result.scalars().all()

    return {"items": [SyncLogRead.model_validate(log) for log in logs], "total": total}


@router.post("/trigger/{step_name}", response_model=SyncTriggerResponse)
async def trigger_sync_step(
    step_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """Manually trigger sync for one step."""
    # Get step
    result = await db.execute(select(SyncState).where(SyncState.step_name == step_name))
    step = result.scalar_one_or_none()

    if not step:
        raise HTTPException(status_code=404, detail=f"Sync step not found: {step_name}")

    # Execute step directly (bypasses enabled check)
    start_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    try:
        # Use service's internal executor
        async with infor_sync_service._lock:
            await infor_sync_service._execute_step(step, db)

        end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        duration_ms = end_ms - start_ms

        return SyncTriggerResponse(
            status="success",
            step_name=step_name,
            fetched=0,  # Not tracked in trigger
            created=step.created_count,
            updated=step.updated_count,
            errors=step.error_count,
            duration_ms=duration_ms,
        )

    except Exception as e:
        logger.error(f"Manual trigger failed for {step_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.put("/steps/{step_name}", response_model=SyncStateRead)
async def update_sync_step(
    step_name: str,
    data: SyncStateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """Update sync step configuration."""
    result = await db.execute(select(SyncState).where(SyncState.step_name == step_name))
    step = result.scalar_one_or_none()

    if not step:
        raise HTTPException(status_code=404, detail=f"Sync step not found: {step_name}")

    # Update fields
    if data.enabled is not None:
        step.enabled = data.enabled
    if data.interval_seconds is not None:
        step.interval_seconds = data.interval_seconds

    step.updated_at = datetime.now(timezone.utc)

    try:
        await safe_commit(db, action="aktualizace konfigurace sync kroku")
        await db.refresh(step)
    except Exception:
        await db.rollback()
        raise

    return SyncStateRead.model_validate(step)


@router.post("/start")
async def start_sync_service(current_user: User = Depends(require_role([UserRole.ADMIN]))):
    """Start sync scheduler."""
    if infor_sync_service.running:
        return {"status": "already_running"}

    await infor_sync_service.start()
    return {"status": "started"}


@router.post("/stop")
async def stop_sync_service(current_user: User = Depends(require_role([UserRole.ADMIN]))):
    """Stop sync scheduler."""
    if not infor_sync_service.running:
        return {"status": "not_running"}

    await infor_sync_service.stop()
    return {"status": "stopped"}
