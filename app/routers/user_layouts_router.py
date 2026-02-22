"""GESTIMA - User Layouts API router

Per-user named workspace layouts (TileNode trees).
GET /user-layouts seeds 4 factory presets for new users.
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_db
from app.db_helpers import set_audit, safe_commit, soft_delete
from app.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.user_layout import (
    UserLayout,
    UserLayoutCreate,
    UserLayoutUpdate,
    UserLayoutResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# FACTORY PRESETS  (hardcoded TileNode trees for seed)
# ============================================================================

_FACTORY_PRESETS: List[Dict[str, Any]] = [
    {
        "name": "Standardní",
        "is_default": True,
        "show_in_header": True,
        "tree_json": {
            "type": "split", "id": "std-a",
            "direction": "horizontal", "ratio": 0.22,
            "children": [
                {"type": "leaf", "id": "std-b", "module": "parts-list", "ctx": "ca"},
                {"type": "leaf", "id": "std-c", "module": "work-detail", "ctx": "ca"},
            ],
        },
    },
    {
        "name": "Porovnání",
        "is_default": False,
        "show_in_header": True,
        "tree_json": {
            "type": "split", "id": "cmp-a",
            "direction": "horizontal", "ratio": 0.16,
            "children": [
                {"type": "leaf", "id": "cmp-b", "module": "parts-list", "ctx": "ca"},
                {
                    "type": "split", "id": "cmp-c",
                    "direction": "horizontal", "ratio": 0.5,
                    "children": [
                        {"type": "leaf", "id": "cmp-d", "module": "work-detail", "ctx": "ca"},
                        {
                            "type": "split", "id": "cmp-e",
                            "direction": "horizontal", "ratio": 0.5,
                            "children": [
                                {"type": "leaf", "id": "cmp-f", "module": "work-detail", "ctx": "cb"},
                                {"type": "leaf", "id": "cmp-g", "module": "parts-list", "ctx": "cb"},
                            ],
                        },
                    ],
                },
            ],
        },
    },
    {
        "name": "Horizontální",
        "is_default": False,
        "show_in_header": True,
        "tree_json": {
            "type": "split", "id": "hor-a",
            "direction": "horizontal", "ratio": 0.22,
            "children": [
                {"type": "leaf", "id": "hor-b", "module": "parts-list", "ctx": "ca"},
                {
                    "type": "split", "id": "hor-c",
                    "direction": "vertical", "ratio": 0.5,
                    "children": [
                        {"type": "leaf", "id": "hor-d", "module": "work-detail", "ctx": "ca"},
                        {"type": "leaf", "id": "hor-e", "module": "work-ops", "ctx": "ca"},
                    ],
                },
            ],
        },
    },
    {
        "name": "Kompletní",
        "is_default": False,
        "show_in_header": True,
        "tree_json": {
            "type": "split", "id": "qd-a",
            "direction": "horizontal", "ratio": 0.18,
            "children": [
                {"type": "leaf", "id": "qd-b", "module": "parts-list", "ctx": "ca"},
                {
                    "type": "split", "id": "qd-c",
                    "direction": "horizontal", "ratio": 0.5,
                    "children": [
                        {
                            "type": "split", "id": "qd-d",
                            "direction": "vertical", "ratio": 0.5,
                            "children": [
                                {"type": "leaf", "id": "qd-e", "module": "work-detail", "ctx": "ca"},
                                {"type": "leaf", "id": "qd-f", "module": "work-ops", "ctx": "ca"},
                            ],
                        },
                        {
                            "type": "split", "id": "qd-g",
                            "direction": "vertical", "ratio": 0.5,
                            "children": [
                                {"type": "leaf", "id": "qd-h", "module": "work-pricing", "ctx": "ca"},
                                {"type": "leaf", "id": "qd-i", "module": "work-drawing", "ctx": "ca"},
                            ],
                        },
                    ],
                },
            ],
        },
    },
]


async def _seed_factory_presets(db: AsyncSession, user_id: int, username: str) -> List[UserLayout]:
    """Create the 4 factory presets for a new user. Returns created layouts."""
    created: List[UserLayout] = []
    for preset in _FACTORY_PRESETS:
        layout = UserLayout(
            user_id=user_id,
            name=preset["name"],
            tree_json=preset["tree_json"],
            is_default=preset["is_default"],
            show_in_header=preset["show_in_header"],
        )
        set_audit(layout, username)
        db.add(layout)
        created.append(layout)
    await safe_commit(db, action="seed factory presets")
    # Refresh to get IDs and timestamps
    for layout in created:
        await db.refresh(layout)
    return created


# ============================================================================
# LIST
# ============================================================================

@router.get("/user-layouts", response_model=List[UserLayoutResponse])
async def list_user_layouts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all layouts for the authenticated user.
    If none exist yet, seeds 4 factory presets automatically.
    """
    try:
        result = await db.execute(
            select(UserLayout)
            .where(
                UserLayout.user_id == current_user.id,
                UserLayout.deleted_at.is_(None),
            )
            .order_by(UserLayout.is_default.desc(), UserLayout.created_at.asc())
        )
        layouts = list(result.scalars().all())

        if not layouts:
            layouts = await _seed_factory_presets(db, current_user.id, current_user.username)

        return layouts

    except SQLAlchemyError as e:
        logger.error(f"DB error in list_user_layouts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Interní chyba serveru")


# ============================================================================
# CREATE
# ============================================================================

@router.post("/user-layouts", response_model=UserLayoutResponse)
async def create_user_layout(
    data: UserLayoutCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR])),
):
    """Create a new layout for the current user."""
    try:
        if data.is_default:
            await _clear_defaults(db, current_user.id, exclude_id=None, username=current_user.username)

        layout = UserLayout(
            user_id=current_user.id,
            name=data.name,
            tree_json=data.tree_json,
            is_default=data.is_default,
            show_in_header=data.show_in_header,
        )
        set_audit(layout, current_user.username)
        db.add(layout)

        await safe_commit(db, entity=layout, action="create user layout")
        await db.refresh(layout)

        logger.info(f"Created user layout {layout.id} for user {current_user.id}")
        return layout

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"DB error in create_user_layout: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Interní chyba serveru")


# ============================================================================
# UPDATE
# ============================================================================

@router.put("/user-layouts/{layout_id}", response_model=UserLayoutResponse)
async def update_user_layout(
    layout_id: int,
    data: UserLayoutUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR])),
):
    """Update an existing layout (optimistic locking via version)."""
    try:
        result = await db.execute(
            select(UserLayout).where(
                UserLayout.id == layout_id,
                UserLayout.user_id == current_user.id,
                UserLayout.deleted_at.is_(None),
            )
        )
        layout = result.scalar_one_or_none()

        if not layout:
            raise HTTPException(status_code=404, detail="Layout nenalezen")

        # Optimistic lock check
        if layout.version != data.version:
            raise HTTPException(
                status_code=409,
                detail="Verze záznamu se neshoduje. Obnovte stránku.",
            )

        # If setting as default, clear others
        if data.is_default is True:
            await _clear_defaults(db, current_user.id, exclude_id=layout_id, username=current_user.username)

        update_data = data.model_dump(exclude_unset=True, exclude={"version"})
        for field, value in update_data.items():
            setattr(layout, field, value)

        set_audit(layout, current_user.username, is_update=True)
        await safe_commit(db, entity=layout, action="update user layout")
        await db.refresh(layout)

        return layout

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"DB error in update_user_layout: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Interní chyba serveru")


# ============================================================================
# DELETE (SOFT)
# ============================================================================

@router.delete("/user-layouts/{layout_id}", status_code=204)
async def delete_user_layout(
    layout_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR])),
):
    """Soft-delete a layout."""
    try:
        result = await db.execute(
            select(UserLayout).where(
                UserLayout.id == layout_id,
                UserLayout.user_id == current_user.id,
                UserLayout.deleted_at.is_(None),
            )
        )
        layout = result.scalar_one_or_none()

        if not layout:
            raise HTTPException(status_code=404, detail="Layout nenalezen")

        await soft_delete(db, layout, deleted_by=current_user.username)
        logger.info(f"Soft-deleted user layout {layout_id}")
        return None

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"DB error in delete_user_layout: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Interní chyba serveru")


# ============================================================================
# HELPERS
# ============================================================================

async def _clear_defaults(
    db: AsyncSession,
    user_id: int,
    exclude_id: int | None,
    username: str,
) -> None:
    """Unset is_default for all user layouts except exclude_id."""
    filters = [
        UserLayout.user_id == user_id,
        UserLayout.is_default.is_(True),
        UserLayout.deleted_at.is_(None),
    ]
    if exclude_id is not None:
        filters.append(UserLayout.id != exclude_id)

    result = await db.execute(select(UserLayout).where(and_(*filters)))
    for layout in result.scalars().all():
        layout.is_default = False
        set_audit(layout, username, is_update=True)
