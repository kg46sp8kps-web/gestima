"""GESTIMA - Drawing Import Router

Import drawings from network share to FileRecord system (ADR-044).
2-step workflow: status/preview -> execute.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import require_role
from app.models.user import UserRole
from app.schemas.drawing_import import (
    ShareStatusResponse,
    DrawingImportPreviewResponse,
    DrawingImportExecuteRequest,
    DrawingImportExecuteResponse,
)
from app.services.drawing_import_service import DrawingImportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/drawings/import", tags=["Drawing Import"])


def _get_service() -> DrawingImportService:
    """Create DrawingImportService with configured share path."""
    return DrawingImportService(settings.DRAWINGS_SHARE_PATH)


@router.get(
    "/status",
    response_model=ShareStatusResponse,
    summary="Check if drawing share is accessible",
)
async def get_share_status(
    _user=Depends(require_role([UserRole.ADMIN])),
):
    """Check if the network share with drawings is accessible."""
    service = _get_service()

    if not settings.DRAWINGS_SHARE_PATH:
        return ShareStatusResponse(
            share_path="(not configured)",
            is_accessible=False,
            total_folders=0,
            message="DRAWINGS_SHARE_PATH not set in .env",
        )

    return service.check_status()


@router.post(
    "/preview",
    response_model=DrawingImportPreviewResponse,
    summary="Scan share and preview import matches",
)
async def preview_import(
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_role([UserRole.ADMIN])),
):
    """
    Step 1: Scan network share, match folders to Parts, return preview.

    This may take 5-10 seconds for 3000+ folders.
    """
    service = _get_service()

    if not settings.DRAWINGS_SHARE_PATH:
        return DrawingImportPreviewResponse(
            share_path="(not configured)",
            total_folders=0,
            folders=[],
        )

    return await service.preview_import(db)


@router.post(
    "/execute",
    response_model=DrawingImportExecuteResponse,
    summary="Execute drawing import for confirmed folders",
)
async def execute_import(
    request: DrawingImportExecuteRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role([UserRole.ADMIN])),
):
    """
    Step 2: Execute import for user-confirmed folders.

    Copies files from share to uploads/, creates FileRecords + FileLinks,
    sets Part.file_id. May take several minutes for large imports.
    """
    service = _get_service()

    logger.info(
        f"Drawing import started by {user.username}: "
        f"{len(request.folders)} folders to import"
    )

    return await service.execute_import(
        folders=request.folders,
        db=db,
        created_by=user.username,
    )
