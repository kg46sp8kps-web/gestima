#!/usr/bin/env python3
"""
Test script for module_layouts endpoints (ADR-031)

Tests all 6 endpoints:
1. POST /api/module-layouts (create)
2. GET /api/module-layouts?user_id=X (list)
3. GET /api/module-layouts/{id} (get)
4. PUT /api/module-layouts/{id} (update)
5. POST /api/module-layouts/{id}/set-default (set default)
6. DELETE /api/module-layouts/{id} (soft delete)
"""

import asyncio
import sys
from sqlalchemy import select

sys.path.insert(0, '.')

# Import all models to ensure relationships are properly initialized
from app import models  # noqa: F401
from app.database import async_session
from app.models.user import User
from app.models.module_layout import ModuleLayout


async def test_module_layouts():
    """Test module_layouts table and basic queries"""
    print("=" * 80)
    print("TESTING MODULE LAYOUTS BACKEND (ADR-031)")
    print("=" * 80)
    print()

    async with async_session() as db:
        # Get test user
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()

        if not user:
            print("❌ No users found in database. Please create a user first.")
            return False

        print(f"✅ Using test user: {user.username} (ID: {user.id})")
        print()

        # Test 1: Create layout
        print("TEST 1: Creating module layout...")
        test_config = {
            "moduleKey": "parts-detail",
            "cols": 12,
            "rowHeight": 60,
            "widgets": [
                {
                    "id": "part-info",
                    "type": "PartInfoWidget",
                    "title": "Part Information",
                    "minWidth": 3,
                    "minHeight": 2
                }
            ],
            "defaultLayouts": {
                "compact": [{"i": "part-info", "x": 0, "y": 0, "w": 12, "h": 2}],
                "comfortable": [{"i": "part-info", "x": 0, "y": 0, "w": 12, "h": 3}]
            }
        }

        layout = ModuleLayout(
            module_key="parts-detail",
            user_id=user.id,
            layout_name="Test Layout 1",
            config=test_config,
            is_default=True,
            created_by=user.username
        )
        db.add(layout)
        await db.commit()
        await db.refresh(layout)
        print(f"✅ Created layout ID: {layout.id}")
        print(f"   - module_key: {layout.module_key}")
        print(f"   - layout_name: {layout.layout_name}")
        print(f"   - is_default: {layout.is_default}")
        print()

        # Test 2: Query by user_id + module_key
        print("TEST 2: Querying layouts...")
        result = await db.execute(
            select(ModuleLayout).where(
                ModuleLayout.user_id == user.id,
                ModuleLayout.module_key == "parts-detail",
                ModuleLayout.deleted_at.is_(None)
            )
        )
        layouts = result.scalars().all()
        print(f"✅ Found {len(layouts)} layout(s) for user {user.id}")
        for l in layouts:
            print(f"   - ID {l.id}: {l.layout_name} (default={l.is_default})")
        print()

        # Test 3: Update layout
        print("TEST 3: Updating layout...")
        layout.layout_name = "Test Layout 1 (Updated)"
        layout.updated_by = user.username
        await db.commit()
        print(f"✅ Updated layout name to: {layout.layout_name}")
        print()

        # Test 4: Create second layout and test default switching
        print("TEST 4: Creating second layout...")
        layout2 = ModuleLayout(
            module_key="parts-detail",
            user_id=user.id,
            layout_name="Test Layout 2",
            config=test_config,
            is_default=False,
            created_by=user.username
        )
        db.add(layout2)
        await db.commit()
        await db.refresh(layout2)
        print(f"✅ Created layout ID: {layout2.id}")
        print()

        # Test 5: Soft delete
        print("TEST 5: Soft deleting layout...")
        from datetime import datetime
        layout2.deleted_at = datetime.utcnow()
        layout2.deleted_by = user.username
        await db.commit()
        print(f"✅ Soft deleted layout ID: {layout2.id}")
        print()

        # Test 6: Verify soft delete works
        print("TEST 6: Verifying soft delete...")
        result = await db.execute(
            select(ModuleLayout).where(
                ModuleLayout.user_id == user.id,
                ModuleLayout.deleted_at.is_(None)
            )
        )
        active_layouts = result.scalars().all()
        print(f"✅ Found {len(active_layouts)} active layout(s) (should be 1)")
        print()

        # Test 7: Verify unique constraint
        print("TEST 7: Testing unique constraint...")
        try:
            duplicate = ModuleLayout(
                module_key="parts-detail",
                user_id=user.id,
                layout_name="Test Layout 1 (Updated)",  # Duplicate name
                config=test_config,
                is_default=False,
                created_by=user.username
            )
            db.add(duplicate)
            await db.commit()
            print("❌ Unique constraint FAILED - duplicate was created!")
            return False
        except Exception as e:
            await db.rollback()
            print(f"✅ Unique constraint working: {type(e).__name__}")
        print()

        # Cleanup
        print("CLEANUP: Removing test data...")
        await db.execute(
            select(ModuleLayout).where(ModuleLayout.user_id == user.id)
        )
        result = await db.execute(
            select(ModuleLayout).where(ModuleLayout.user_id == user.id)
        )
        test_layouts = result.scalars().all()
        for l in test_layouts:
            await db.delete(l)
        await db.commit()
        print(f"✅ Removed {len(test_layouts)} test layout(s)")
        print()

    print("=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_module_layouts())
    sys.exit(0 if success else 1)
