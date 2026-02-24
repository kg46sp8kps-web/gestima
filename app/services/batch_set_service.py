"""GESTIMA - BatchSet business logic service."""

import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_helpers import set_audit, safe_commit
from app.models import User
from app.models.batch import Batch
from app.models.batch_set import BatchSet, generate_batch_set_name
from app.services.snapshot_service import create_batch_snapshot
from app.services.batch_service import recalculate_batch_costs
from app.services.number_generator import NumberGenerator

logger = logging.getLogger(__name__)


async def freeze_batch_set_batches(
    batch_set: BatchSet,
    active_batches: list[Batch],
    user: User,
    db: AsyncSession,
) -> None:
    """
    Snapshot and freeze all active batches, then mark the set as frozen.

    Caller must ensure:
    - batch_set.status != "frozen"
    - len(active_batches) > 0
    - Batches loaded with Part.material_inputs relations (for snapshot)

    Raises:
        SQLAlchemyError: On DB error (safe_commit handles rollback)
    """
    now = datetime.utcnow()

    for batch in active_batches:
        snapshot = await create_batch_snapshot(batch, user.username, db)
        batch.is_frozen = True
        batch.frozen_at = now
        batch.frozen_by_id = user.id
        batch.snapshot_data = snapshot
        batch.unit_price_frozen = batch.unit_cost
        batch.total_price_frozen = batch.total_cost

    batch_set.status = "frozen"
    batch_set.frozen_at = now
    batch_set.frozen_by_id = user.id
    batch_set.updated_by = user.username
    batch_set.updated_at = now

    await safe_commit(db, batch_set, "zmrazení sady")
    logger.info(
        f"Frozen batch set {batch_set.id} with {len(active_batches)} batches",
        extra={"batch_set_id": batch_set.id, "user": user.username}
    )


async def recalculate_all_batches(
    batch_set: BatchSet,
    active_batches: list[Batch],
    user: User,
    db: AsyncSession,
) -> None:
    """
    Recalculate costs for all active batches and update batch_set timestamp.

    Caller must ensure batch_set is not frozen and not deleted.

    Raises:
        ValueError: On invalid batch data
        SQLAlchemyError: On DB error (safe_commit handles rollback)
    """
    for batch in active_batches:
        await recalculate_batch_costs(batch, db)

    batch_set.updated_by = user.username
    batch_set.updated_at = datetime.utcnow()

    await safe_commit(db, batch_set, "přepočet sady")
    logger.info(
        f"Recalculated batch set {batch_set.id} with {len(active_batches)} batches",
        extra={"batch_set_id": batch_set.id, "user": user.username}
    )


async def clone_batch_set(
    original: BatchSet,
    user: User,
    db: AsyncSession,
) -> BatchSet:
    """
    Clone a batch set: new draft set with same batches (costs copied, not frozen).

    Raises:
        NumberGenerationError: If number generation fails
        SQLAlchemyError: On DB error (safe_commit handles rollback)
    """
    set_number = await NumberGenerator.generate_batch_set_number(db)

    new_set = BatchSet(
        set_number=set_number,
        part_id=original.part_id,
        name=generate_batch_set_name(),
        status="draft"
    )
    set_audit(new_set, user.username)
    db.add(new_set)
    await db.flush()

    active_batches = [b for b in original.batches if b.deleted_at is None]
    for batch in active_batches:
        batch_number = await NumberGenerator.generate_batch_number(db)
        new_batch = Batch(
            batch_number=batch_number,
            part_id=batch.part_id,
            batch_set_id=new_set.id,
            quantity=batch.quantity,
            is_default=False,
            unit_time_min=batch.unit_time_min,
            material_cost=batch.material_cost,
            machining_cost=batch.machining_cost,
            setup_cost=batch.setup_cost,
            overhead_cost=batch.overhead_cost,
            margin_cost=batch.margin_cost,
            coop_cost=batch.coop_cost,
            unit_cost=batch.unit_cost,
            total_cost=batch.total_cost,
            material_weight_kg=batch.material_weight_kg,
            material_price_per_kg=batch.material_price_per_kg,
        )
        set_audit(new_batch, user.username)
        db.add(new_batch)

    new_set = await safe_commit(db, new_set, "klonování sady")
    logger.info(
        f"Cloned batch set {original.id} -> {new_set.id} with {len(active_batches)} batches",
        extra={"original_id": original.id, "new_id": new_set.id, "user": user.username}
    )
    return new_set
