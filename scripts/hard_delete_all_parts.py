#!/usr/bin/env python3
"""
Hard-delete ALL parts and related data from Gestima database.

WARNING: This is destructive! All parts and related data will be permanently removed.

Usage:
    python scripts/hard_delete_all_parts.py

Tables affected (in FK order):
1. time_vision_estimations (part_id SET NULL)
2. quote_items (part_id SET NULL)
3. production_records (cascade from parts)
4. drawings (cascade from parts)
5. batches (cascade from parts) -> batch_sets orphaned
6. operations (cascade from parts)
7. material_inputs (cascade from parts)
8. batch_sets (back_populates only, must delete manually)
9. parts (main table)

Version: 1.0.0
Author: Backend Architect
Date: 2026-02-16
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session
from app.models import (
    Part,
    MaterialInput,
    Operation,
    Batch,
    BatchSet,
    Drawing,
    ProductionRecord,
    QuoteItem,
    TimeVisionEstimation,
)


async def hard_delete_all_parts():
    """
    Hard-delete all parts and related data.

    Transaction handling (L-008):
    - Single transaction with try/except/rollback
    - Rollback on any error
    """
    async with async_session() as db:
        try:
            print("=" * 80)
            print("HARD DELETE ALL PARTS - DESTRUCTIVE OPERATION")
            print("=" * 80)

            # Count before deletion
            print("\n📊 Counting records before deletion...")

            counts_before = {}
            for model_name, model in [
                ("TimeVisionEstimation", TimeVisionEstimation),
                ("QuoteItem", QuoteItem),
                ("ProductionRecord", ProductionRecord),
                ("Drawing", Drawing),
                ("BatchSet", BatchSet),
                ("Batch", Batch),
                ("Operation", Operation),
                ("MaterialInput", MaterialInput),
                ("Part", Part),
            ]:
                result = await db.execute(select(func.count()).select_from(model))
                count = result.scalar() or 0
                counts_before[model_name] = count
                print(f"  {model_name:25} {count:6} rows")

            # === DELETE PHASE ===
            print("\n🗑️  Deleting records (FK order: children first)...")

            # 1. TimeVisionEstimation - SET NULL on part_id (no cascade)
            stmt = delete(TimeVisionEstimation).where(TimeVisionEstimation.part_id.isnot(None))
            result = await db.execute(stmt)
            deleted_tv = result.rowcount
            print(f"  ✅ TimeVisionEstimation: {deleted_tv} deleted (part_id FK cleared)")

            # 2. QuoteItem - SET NULL on part_id (no cascade)
            stmt = delete(QuoteItem).where(QuoteItem.part_id.isnot(None))
            result = await db.execute(stmt)
            deleted_qi = result.rowcount
            print(f"  ✅ QuoteItem: {deleted_qi} deleted (part_id FK cleared)")

            # 3. BatchSet - must delete manually (no cascade delete-orphan)
            # Find all batch_sets referencing parts before we delete parts
            stmt = select(BatchSet).join(Part, BatchSet.part_id == Part.id)
            result = await db.execute(stmt)
            batch_sets_to_delete = result.scalars().all()

            for bs in batch_sets_to_delete:
                await db.delete(bs)
            deleted_bs = len(batch_sets_to_delete)
            print(f"  ✅ BatchSet: {deleted_bs} deleted (manual cleanup before part cascade)")

            # 4-8. Parts + cascaded children (ProductionRecord, Drawing, Batch, Operation, MaterialInput)
            # Get all parts first
            stmt = select(Part)
            result = await db.execute(stmt)
            parts_to_delete = result.scalars().all()

            parts_count = len(parts_to_delete)
            print(f"  ℹ️  Found {parts_count} parts to delete...")

            # Delete all parts (cascades to children)
            for part in parts_to_delete:
                await db.delete(part)

            # Commit transaction
            await db.commit()
            print(f"\n✅ Transaction committed successfully")

            # Count after deletion
            print("\n📊 Counting records after deletion...")

            counts_after = {}
            for model_name, model in [
                ("TimeVisionEstimation", TimeVisionEstimation),
                ("QuoteItem", QuoteItem),
                ("ProductionRecord", ProductionRecord),
                ("Drawing", Drawing),
                ("BatchSet", BatchSet),
                ("Batch", Batch),
                ("Operation", Operation),
                ("MaterialInput", MaterialInput),
                ("Part", Part),
            ]:
                result = await db.execute(select(func.count()).select_from(model))
                count = result.scalar() or 0
                counts_after[model_name] = count
                deleted = counts_before[model_name] - count
                print(f"  {model_name:25} {count:6} rows ({deleted:+6} deleted)")

            print("\n" + "=" * 80)
            print("✅ DELETION COMPLETE")
            print("=" * 80)

            total_deleted = sum(counts_before.values()) - sum(counts_after.values())
            print(f"\nTotal records deleted: {total_deleted}")

        except Exception as e:
            await db.rollback()
            print(f"\n❌ ERROR: {e}")
            print("🔄 Transaction rolled back")
            raise


if __name__ == "__main__":
    print("\n⚠️  WARNING: This will permanently delete ALL parts and related data!")
    print("⚠️  This action CANNOT be undone!")

    response = input("\nType 'DELETE ALL PARTS' to confirm: ")

    if response.strip() == "DELETE ALL PARTS":
        print("\n🚀 Starting deletion...")
        asyncio.run(hard_delete_all_parts())
    else:
        print("\n❌ Deletion cancelled (input did not match)")
        sys.exit(1)
