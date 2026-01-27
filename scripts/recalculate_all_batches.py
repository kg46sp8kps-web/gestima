"""
GESTIMA - Recalculate All Batches
Přepočítá všechny batches s novou kalkulací (ADR-016)
"""

import asyncio
import sys
from pathlib import Path

# Přidat root do path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import async_session
from app.models.batch import Batch
from app.services.batch_service import recalculate_batch_costs
from sqlalchemy import select


async def recalculate_all():
    """Recalculate all batches with new pricing (ADR-016)"""
    async with async_session() as session:
        # Načíst všechny batches
        result = await session.execute(
            select(Batch).where(Batch.deleted_at.is_(None))
        )
        batches = result.scalars().all()

        print(f"📊 Nalezeno {len(batches)} batchů k přepočítání\n")

        success = 0
        failed = 0

        for i, batch in enumerate(batches, 1):
            try:
                print(f"[{i}/{len(batches)}] Batch ID {batch.id} (Part {batch.part_id}, {batch.quantity} ks)...", end=" ")

                # Recalculate (caller musí commitnout!)
                await recalculate_batch_costs(batch, session)
                await session.commit()

                print(f"✅ {batch.unit_cost:.0f} Kč/ks")
                success += 1

            except Exception as e:
                await session.rollback()
                print(f"❌ CHYBA: {e}")
                failed += 1

        print(f"\n📊 Recalculation dokončen:")
        print(f"   ✅ Úspěšných: {success}")
        print(f"   ❌ Selhání: {failed}")
        print(f"   📦 Celkem: {len(batches)}")


if __name__ == "__main__":
    print("🚀 Recalculation všech batchů (ADR-016)\n")
    asyncio.run(recalculate_all())
