"""GESTIMA - Module Defaults API router

ADR-031: Visual Editor System
Backend endpoints for managing module-wide default settings.

Difference from ModuleLayout:
- ModuleDefaults: Global defaults per module type (one per module type)
- ModuleLayout: User-specific saved layouts (many per user per module)
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database import get_db
from app.db_helpers import set_audit, safe_commit
from app.dependencies import get_current_user
from app.models.user import User
from app.models.module_defaults import (
    ModuleDefaults,
    ModuleDefaultsCreate,
    ModuleDefaultsUpdate,
    ModuleDefaultsResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# GET
# ============================================================================

@router.get("/module-defaults/{module_type}", response_model=ModuleDefaultsResponse)
async def get_module_defaults(
    module_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get default settings for a specific module type.

    Args:
        module_type: Module identifier (e.g., 'part-main', 'part-pricing')

    Returns:
        ModuleDefaultsResponse: Default settings

    Raises:
        404: Module defaults not found for this type
    """
    try:
        result = await db.execute(
            select(ModuleDefaults).where(
                ModuleDefaults.module_type == module_type,
                ModuleDefaults.deleted_at.is_(None)
            )
        )
        defaults = result.scalar_one_or_none()

        if not defaults:
            raise HTTPException(
                status_code=404,
                detail=f"Module defaults not found for type: {module_type}"
            )

        return defaults

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_module_defaults: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")


# ============================================================================
# CREATE/UPDATE (UPSERT)
# ============================================================================

@router.post("/module-defaults", response_model=ModuleDefaultsResponse, status_code=201)
async def create_or_update_module_defaults(
    data: ModuleDefaultsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create or update module defaults (upsert by module_type).

    Validation:
    - module_type: UNIQUE constraint
    - default_width: 200-3000 (enforced by Pydantic)
    - default_height: 200-3000 (enforced by Pydantic)
    - settings: Must be valid JSON dict (if provided)

    Logic:
    - If module_type exists → UPDATE
    - If module_type doesn't exist → CREATE

    Returns:
        201: Created new defaults
        201: Updated existing defaults (same code for simplicity)
    """
    try:
        # Validate settings is dict (if provided)
        if data.settings is not None and not isinstance(data.settings, dict):
            raise HTTPException(
                status_code=400,
                detail="settings must be a valid JSON object"
            )

        # Check if defaults exist for this module_type
        result = await db.execute(
            select(ModuleDefaults).where(
                ModuleDefaults.module_type == data.module_type,
                ModuleDefaults.deleted_at.is_(None)
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # UPDATE existing
            existing.default_width = data.default_width
            existing.default_height = data.default_height
            existing.settings = data.settings
            set_audit(existing, current_user.username, is_update=True)

            await safe_commit(
                db,
                entity=existing,
                action="update module defaults",
                integrity_error_msg=f"Conflict updating module defaults for {data.module_type}"
            )

            logger.info(f"Updated module defaults for {data.module_type}")
            return existing

        else:
            # CREATE new
            defaults = ModuleDefaults(**data.model_dump())
            set_audit(defaults, current_user.username)

            db.add(defaults)

            await safe_commit(
                db,
                entity=defaults,
                action="create module defaults",
                integrity_error_msg=f"Module defaults already exist for {data.module_type}"
            )

            logger.info(f"Created module defaults for {data.module_type}")
            return defaults

    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.warning(f"IntegrityError in create_or_update_module_defaults: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Conflict with module_type: {data.module_type}"
        )
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error in create_or_update_module_defaults: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")


# ============================================================================
# UPDATE (PATCH)
# ============================================================================

@router.put("/module-defaults/{module_type}", response_model=ModuleDefaultsResponse)
async def update_module_defaults(
    module_type: str,
    data: ModuleDefaultsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update module defaults (PATCH - partial update).

    Updates:
    - default_width (optional)
    - default_height (optional)
    - settings (optional)

    Raises:
        404: Module defaults not found for this type
    """
    try:
        # Get existing defaults
        result = await db.execute(
            select(ModuleDefaults).where(
                ModuleDefaults.module_type == module_type,
                ModuleDefaults.deleted_at.is_(None)
            )
        )
        defaults = result.scalar_one_or_none()

        if not defaults:
            raise HTTPException(
                status_code=404,
                detail=f"Module defaults not found for type: {module_type}"
            )

        # Apply updates
        update_data = data.model_dump(exclude_unset=True)

        # Validate settings if provided
        if "settings" in update_data and update_data["settings"] is not None:
            if not isinstance(update_data["settings"], dict):
                raise HTTPException(
                    status_code=400,
                    detail="settings must be a valid JSON object"
                )

        # Update fields
        for field, value in update_data.items():
            setattr(defaults, field, value)

        set_audit(defaults, current_user.username, is_update=True)

        await safe_commit(
            db,
            entity=defaults,
            action="update module defaults",
            integrity_error_msg=f"Conflict updating module defaults for {module_type}"
        )

        logger.info(f"Updated module defaults for {module_type}")
        return defaults

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error in update_module_defaults: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")


# ============================================================================
# DELETE (SOFT DELETE)
# ============================================================================

@router.delete("/module-defaults/{module_type}", status_code=204)
async def delete_module_defaults(
    module_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soft delete module defaults.

    Sets deleted_at timestamp instead of removing from database.

    Raises:
        404: Module defaults not found for this type
    """
    try:
        # Get existing defaults
        result = await db.execute(
            select(ModuleDefaults).where(
                ModuleDefaults.module_type == module_type,
                ModuleDefaults.deleted_at.is_(None)
            )
        )
        defaults = result.scalar_one_or_none()

        if not defaults:
            raise HTTPException(
                status_code=404,
                detail=f"Module defaults not found for type: {module_type}"
            )

        # Soft delete
        from datetime import datetime
        defaults.deleted_at = datetime.utcnow()
        defaults.deleted_by = current_user.username

        await db.commit()

        logger.info(f"Soft deleted module defaults for {module_type}")
        return None

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error in delete_module_defaults: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")
