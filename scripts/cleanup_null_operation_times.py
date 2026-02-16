#!/usr/bin/env python3
"""
GESTIMA - Cleanup NULL operation times

Problem: Operations with NULL setup_time_min/operation_time_min cause ResponseValidationError
Fix: Set NULL values to defaults (setup_time_min=30.0, operation_time_min=0.0)

Created: 2026-01-26
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import engine


async def cleanup_null_times():
    """Set NULL operation times to default values"""
    async with engine.begin() as conn:
        # Check how many NULLs exist
        result = await conn.execute(text("""
            SELECT COUNT(*) as count FROM operations
            WHERE setup_time_min IS NULL OR operation_time_min IS NULL
        """))
        null_count = result.scalar()

        if null_count == 0:
            print("✅ No NULL values found in operation times")
            return

        print(f"🔧 Found {null_count} operations with NULL times")

        # Fix setup_time_min
        result = await conn.execute(text("""
            UPDATE operations
            SET setup_time_min = 30.0
            WHERE setup_time_min IS NULL
        """))
        setup_fixed = result.rowcount
        print(f"✅ Fixed {setup_fixed} NULL setup_time_min values → 30.0")

        # Fix operation_time_min
        result = await conn.execute(text("""
            UPDATE operations
            SET operation_time_min = 0.0
            WHERE operation_time_min IS NULL
        """))
        op_fixed = result.rowcount
        print(f"✅ Fixed {op_fixed} NULL operation_time_min values → 0.0")

        # Fix coop_price (also has default 0.0)
        result = await conn.execute(text("""
            UPDATE operations
            SET coop_price = 0.0
            WHERE coop_price IS NULL
        """))
        coop_fixed = result.rowcount
        if coop_fixed > 0:
            print(f"✅ Fixed {coop_fixed} NULL coop_price values → 0.0")

        print(f"\n✅ Cleanup complete! Total operations fixed: {null_count}")


async def main():
    print("GESTIMA - Cleanup NULL Operation Times")
    print("=" * 50)
    try:
        await cleanup_null_times()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
