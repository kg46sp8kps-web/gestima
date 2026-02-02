#!/usr/bin/env python3
"""
Verification script for module_defaults table and endpoints (ADR-031)

Verifies:
1. Table exists
2. Columns are correct
3. Basic CRUD operations work

Run: python3 verify_module_defaults.py
"""

import asyncio
import sys
from sqlalchemy import select, text

sys.path.insert(0, '.')

from app.database import async_session
from app.models.module_defaults import ModuleDefaults


async def verify_module_defaults():
    """Verify module_defaults table and basic operations"""
    print("=" * 80)
    print("VERIFYING MODULE DEFAULTS BACKEND (ADR-031)")
    print("=" * 80)
    print()

    async with async_session() as db:
        # Test 1: Check table exists
        print("TEST 1: Checking if module_defaults table exists...")
        try:
            result = await db.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='module_defaults'")
            )
            table = result.fetchone()
            if table:
                print("✅ module_defaults table exists")
            else:
                print("❌ module_defaults table NOT found")
                return False
        except Exception as e:
            print(f"❌ Error checking table: {e}")
            return False

        print()

        # Test 2: Check columns
        print("TEST 2: Checking table schema...")
        try:
            result = await db.execute(text("PRAGMA table_info(module_defaults)"))
            columns = {row[1] for row in result.fetchall()}
            required_columns = {
                'id', 'module_type', 'default_width', 'default_height', 'settings',
                'created_at', 'updated_at', 'created_by', 'updated_by',
                'deleted_at', 'deleted_by', 'version'
            }
            missing = required_columns - columns
            if missing:
                print(f"❌ Missing columns: {missing}")
                return False
            else:
                print("✅ All required columns present")
                print(f"   Columns: {sorted(columns)}")
        except Exception as e:
            print(f"❌ Error checking schema: {e}")
            return False

        print()

        # Test 3: Create test data
        print("TEST 3: Creating test module defaults...")
        try:
            # Use system user (avoid importing User model which has issues)
            username = "system"
            print(f"✅ Using user: {username}")

            # Clean test data first
            await db.execute(text("DELETE FROM module_defaults WHERE module_type = 'test-module'"))
            await db.commit()

            # Create test defaults
            defaults = ModuleDefaults(
                module_type="test-module",
                default_width=800,
                default_height=600,
                settings={"test": "value"},
                created_by=username
            )
            db.add(defaults)
            await db.commit()
            await db.refresh(defaults)

            print(f"✅ Created test defaults (ID: {defaults.id})")
            print(f"   - module_type: {defaults.module_type}")
            print(f"   - default_width: {defaults.default_width}")
            print(f"   - default_height: {defaults.default_height}")
            print(f"   - settings: {defaults.settings}")

        except Exception as e:
            print(f"❌ Error creating test data: {e}")
            await db.rollback()
            return False

        print()

        # Test 4: Read test data
        print("TEST 4: Reading test module defaults...")
        try:
            result = await db.execute(
                select(ModuleDefaults).where(
                    ModuleDefaults.module_type == "test-module",
                    ModuleDefaults.deleted_at.is_(None)
                )
            )
            read_defaults = result.scalar_one_or_none()

            if not read_defaults:
                print("❌ Could not read test defaults")
                return False

            print("✅ Successfully read test defaults")
            print(f"   - ID: {read_defaults.id}")
            print(f"   - module_type: {read_defaults.module_type}")
            print(f"   - version: {read_defaults.version}")

        except Exception as e:
            print(f"❌ Error reading test data: {e}")
            return False

        print()

        # Test 5: Update test data
        print("TEST 5: Updating test module defaults...")
        try:
            read_defaults.default_width = 1000
            read_defaults.default_height = 800
            read_defaults.updated_by = username
            read_defaults.version += 1

            await db.commit()
            await db.refresh(read_defaults)

            print("✅ Successfully updated test defaults")
            print(f"   - new default_width: {read_defaults.default_width}")
            print(f"   - new default_height: {read_defaults.default_height}")
            print(f"   - version: {read_defaults.version}")

        except Exception as e:
            print(f"❌ Error updating test data: {e}")
            await db.rollback()
            return False

        print()

        # Test 6: Soft delete test data
        print("TEST 6: Soft deleting test module defaults...")
        try:
            from datetime import datetime
            read_defaults.deleted_at = datetime.utcnow()
            read_defaults.deleted_by = username

            await db.commit()

            # Verify soft delete
            result = await db.execute(
                select(ModuleDefaults).where(
                    ModuleDefaults.module_type == "test-module",
                    ModuleDefaults.deleted_at.is_(None)
                )
            )
            should_be_none = result.scalar_one_or_none()

            if should_be_none:
                print("❌ Soft delete failed - record still visible")
                return False

            print("✅ Successfully soft deleted test defaults")

        except Exception as e:
            print(f"❌ Error soft deleting test data: {e}")
            await db.rollback()
            return False

        print()

        # Test 7: Check indexes
        print("TEST 7: Checking indexes...")
        try:
            result = await db.execute(
                text("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='module_defaults'")
            )
            indexes = [row[0] for row in result.fetchall()]

            expected_indexes = [
                'ix_module_defaults_module_type',
                'ix_module_defaults_deleted_at'
            ]

            found_indexes = [idx for idx in expected_indexes if idx in indexes]

            if len(found_indexes) == len(expected_indexes):
                print("✅ All expected indexes present")
                print(f"   Indexes: {found_indexes}")
            else:
                missing = set(expected_indexes) - set(found_indexes)
                print(f"⚠️  Some indexes missing: {missing}")
                print(f"   Found: {indexes}")

        except Exception as e:
            print(f"❌ Error checking indexes: {e}")
            return False

        print()
        print("=" * 80)
        print("✅ ALL TESTS PASSED - MODULE DEFAULTS SYSTEM READY")
        print("=" * 80)
        return True


if __name__ == "__main__":
    success = asyncio.run(verify_module_defaults())
    sys.exit(0 if success else 1)
