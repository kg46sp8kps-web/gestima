"""GESTIMA - Module Layouts API router

ADR-031: Visual Editor System
Backend endpoints for managing user-specific module layout configurations.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database import get_db
from app.db_helpers import set_audit, safe_commit
from app.dependencies import get_current_user
from app.models.user import User
from app.models.module_layout import (
    ModuleLayout,
    ModuleLayoutCreate,
    ModuleLayoutUpdate,
    ModuleLayoutResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# LIST & GET
# ============================================================================

@router.get("/module-layouts", response_model=List[ModuleLayoutResponse])
async def list_module_layouts(
    user_id: int = Query(..., description="Filter by user ID"),
    module_key: Optional[str] = Query(None, description="Filter by module key"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List module layouts for a user.

    Filters:
    - user_id (required)
    - module_key (optional)

    Returns active (non-deleted) layouts only.
    """
    try:
        # Build query
        filters = [
            ModuleLayout.user_id == user_id,
            ModuleLayout.deleted_at.is_(None)
        ]

        if module_key:
            filters.append(ModuleLayout.module_key == module_key)

        result = await db.execute(
            select(ModuleLayout)
            .where(and_(*filters))
            .order_by(ModuleLayout.is_default.desc(), ModuleLayout.created_at.desc())
        )
        layouts = result.scalars().all()

        logger.info(f"Listed {len(layouts)} layouts for user_id={user_id}, module_key={module_key}")
        return layouts

    except SQLAlchemyError as e:
        logger.error(f"Database error in list_module_layouts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")


@router.get("/module-layouts/{id}", response_model=ModuleLayoutResponse)
async def get_module_layout(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get single module layout by ID"""
    try:
        result = await db.execute(
            select(ModuleLayout).where(
                ModuleLayout.id == id,
                ModuleLayout.deleted_at.is_(None)
            )
        )
        layout = result.scalar_one_or_none()

        if not layout:
            raise HTTPException(status_code=404, detail="Module layout not found")

        return layout

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_module_layout: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")


# ============================================================================
# CREATE
# ============================================================================

@router.post("/module-layouts", response_model=ModuleLayoutResponse, status_code=201)
async def create_module_layout(
    data: ModuleLayoutCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create new module layout.

    Validation:
    - config must be valid JSON
    - Unique constraint: (module_key, user_id, layout_name)
    - If is_default=True, unset other defaults for this module+user
    """
    try:
        # Validate config is dict (basic check)
        if not isinstance(data.config, dict):
            raise HTTPException(
                status_code=400,
                detail="config must be a valid JSON object"
            )

        # If is_default=True, unset other defaults
        if data.is_default:
            await db.execute(
                select(ModuleLayout)
                .where(
                    ModuleLayout.user_id == data.user_id,
                    ModuleLayout.module_key == data.module_key,
                    ModuleLayout.deleted_at.is_(None)
                )
            )
            result = await db.execute(
                select(ModuleLayout).where(
                    and_(
                        ModuleLayout.user_id == data.user_id,
                        ModuleLayout.module_key == data.module_key,
                        ModuleLayout.is_default == True,
                        ModuleLayout.deleted_at.is_(None)
                    )
                )
            )
            existing_defaults = result.scalars().all()

            for layout in existing_defaults:
                layout.is_default = False
                set_audit(layout, current_user.username, is_update=True)

        # Create new layout
        layout = ModuleLayout(**data.model_dump())
        set_audit(layout, current_user.username)

        db.add(layout)

        # Commit with transaction handling
        await safe_commit(
            db,
            entity=layout,
            action="create module layout",
            integrity_error_msg="Layout name already exists for this module and user"
        )

        logger.info(f"Created module layout {layout.id} for user {data.user_id}")
        return layout

    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.warning(f"IntegrityError in create_module_layout: {e}")
        raise HTTPException(
            status_code=409,
            detail="Layout name already exists for this module and user"
        )
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error in create_module_layout: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")


# ============================================================================
# UPDATE
# ============================================================================

@router.put("/module-layouts/{id}", response_model=ModuleLayoutResponse)
async def update_module_layout(
    id: int,
    data: ModuleLayoutUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update module layout.

    Updates:
    - layout_name (optional)
    - config (optional)
    - is_default (optional) - if True, unset other defaults
    """
    try:
        # Get existing layout
        result = await db.execute(
            select(ModuleLayout).where(
                ModuleLayout.id == id,
                ModuleLayout.deleted_at.is_(None)
            )
        )
        layout = result.scalar_one_or_none()

        if not layout:
            raise HTTPException(status_code=404, detail="Module layout not found")

        # Apply updates
        update_data = data.model_dump(exclude_unset=True)

        # Validate config if provided
        if "config" in update_data:
            if not isinstance(update_data["config"], dict):
                raise HTTPException(
                    status_code=400,
                    detail="config must be a valid JSON object"
                )

        # If is_default=True, unset other defaults
        if update_data.get("is_default") is True:
            result = await db.execute(
                select(ModuleLayout).where(
                    and_(
                        ModuleLayout.user_id == layout.user_id,
                        ModuleLayout.module_key == layout.module_key,
                        ModuleLayout.is_default == True,
                        ModuleLayout.deleted_at.is_(None),
                        ModuleLayout.id != id
                    )
                )
            )
            existing_defaults = result.scalars().all()

            for other_layout in existing_defaults:
                other_layout.is_default = False
                set_audit(other_layout, current_user.username, is_update=True)

        # Update fields
        for field, value in update_data.items():
            setattr(layout, field, value)

        set_audit(layout, current_user.username, is_update=True)

        # Commit with transaction handling
        await safe_commit(
            db,
            entity=layout,
            action="update module layout",
            integrity_error_msg="Layout name already exists for this module and user"
        )

        logger.info(f"Updated module layout {id}")
        return layout

    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.warning(f"IntegrityError in update_module_layout: {e}")
        raise HTTPException(
            status_code=409,
            detail="Layout name already exists for this module and user"
        )
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error in update_module_layout: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")


# ============================================================================
# DELETE (SOFT DELETE)
# ============================================================================

@router.delete("/module-layouts/{id}", status_code=204)
async def delete_module_layout(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soft delete module layout.

    Sets deleted_at timestamp instead of removing from database.
    """
    try:
        # Get existing layout
        result = await db.execute(
            select(ModuleLayout).where(
                ModuleLayout.id == id,
                ModuleLayout.deleted_at.is_(None)
            )
        )
        layout = result.scalar_one_or_none()

        if not layout:
            raise HTTPException(status_code=404, detail="Module layout not found")

        # Soft delete
        from datetime import datetime
        layout.deleted_at = datetime.utcnow()
        layout.deleted_by = current_user.username

        await safe_commit(db, action="mazání rozložení modulu")

        logger.info(f"Soft deleted module layout {id}")
        return None

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error in delete_module_layout: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")


# ============================================================================
# SET DEFAULT
# ============================================================================

@router.post("/module-layouts/{id}/set-default", response_model=ModuleLayoutResponse)
async def set_default_layout(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Set layout as default for user+module.

    Unsets is_default for all other layouts of the same user+module.
    """
    try:
        # Get target layout
        result = await db.execute(
            select(ModuleLayout).where(
                ModuleLayout.id == id,
                ModuleLayout.deleted_at.is_(None)
            )
        )
        layout = result.scalar_one_or_none()

        if not layout:
            raise HTTPException(status_code=404, detail="Module layout not found")

        # Unset other defaults for same user+module
        result = await db.execute(
            select(ModuleLayout).where(
                and_(
                    ModuleLayout.user_id == layout.user_id,
                    ModuleLayout.module_key == layout.module_key,
                    ModuleLayout.is_default == True,
                    ModuleLayout.deleted_at.is_(None),
                    ModuleLayout.id != id
                )
            )
        )
        existing_defaults = result.scalars().all()

        for other_layout in existing_defaults:
            other_layout.is_default = False
            set_audit(other_layout, current_user.username, is_update=True)

        # Set target as default
        layout.is_default = True
        set_audit(layout, current_user.username, is_update=True)

        await safe_commit(db, action="nastavení výchozího rozložení modulu")
        await db.refresh(layout)

        logger.info(f"Set module layout {id} as default")
        return layout

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error in set_default_layout: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")
