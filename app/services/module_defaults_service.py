"""GESTIMA - ModuleDefaults service

CRUD for module-wide default settings (ADR-031).
Lookup by module_type (string), not by ID.
"""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.module_defaults import ModuleDefaults, ModuleDefaultsCreate, ModuleDefaultsUpdate
from app.db_helpers import set_audit, safe_commit, soft_delete

logger = logging.getLogger(__name__)


class ModuleDefaultsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_type(self, module_type: str) -> Optional[ModuleDefaults]:
        """Get active defaults by module_type."""
        result = await self.db.execute(
            select(ModuleDefaults).where(
                ModuleDefaults.module_type == module_type,
                ModuleDefaults.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def upsert(self, data: ModuleDefaultsCreate, username: str) -> ModuleDefaults:
        """Create or update defaults (upsert by module_type)."""
        existing = await self.get_by_type(data.module_type)

        if existing:
            existing.default_width = data.default_width
            existing.default_height = data.default_height
            existing.settings = data.settings
            set_audit(existing, username, is_update=True)
            return await safe_commit(self.db, existing, "update module defaults")

        defaults = ModuleDefaults(**data.model_dump())
        set_audit(defaults, username)
        self.db.add(defaults)
        return await safe_commit(self.db, defaults, "create module defaults")

    async def update(self, module_type: str, data: ModuleDefaultsUpdate, username: str) -> ModuleDefaults:
        """Partial update by module_type."""
        defaults = await self.get_by_type(module_type)
        if not defaults:
            raise ValueError(f"Module defaults pro '{module_type}' nenalezeny")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(defaults, field, value)

        set_audit(defaults, username, is_update=True)
        return await safe_commit(self.db, defaults, "update module defaults")

    async def delete(self, module_type: str, username: str) -> bool:
        """Soft-delete defaults by module_type."""
        defaults = await self.get_by_type(module_type)
        if not defaults:
            return False

        await soft_delete(self.db, defaults, deleted_by=username)
        logger.info(f"Soft deleted module defaults for {module_type}")
        return True
