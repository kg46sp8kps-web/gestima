"""migrate_actual_to_human_estimate

Move data from actual_time_min → human_estimate_min.
The existing actual_time_min values are human estimates (before manufacturing),
not real production times. After this migration:
- human_estimate_min = user's estimate (moved from actual_time_min)
- actual_time_min = empty (reserved for real production times)
- status reverts from 'verified' to 'estimated' (no production data yet)

Revision ID: b6c7d8e9f0a1
Revises: ae265e925f90
Create Date: 2026-02-13 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6c7d8e9f0a1'
down_revision: Union[str, Sequence[str], None] = 'ae265e925f90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Move actual_time_min data to human_estimate_min, clear actual columns."""
    # Step 1: Copy actual_time_min → human_estimate_min (where human is still NULL)
    op.execute(
        "UPDATE time_vision_estimations "
        "SET human_estimate_min = actual_time_min "
        "WHERE actual_time_min IS NOT NULL AND human_estimate_min IS NULL"
    )

    # Step 2: Clear actual_time_min and actual_entered_at (these were human estimates, not production)
    op.execute(
        "UPDATE time_vision_estimations "
        "SET actual_time_min = NULL, actual_entered_at = NULL "
        "WHERE actual_time_min IS NOT NULL"
    )

    # Step 3: Revert status from 'verified' to 'estimated' (no real production data yet)
    op.execute(
        "UPDATE time_vision_estimations "
        "SET status = 'estimated' "
        "WHERE status = 'verified'"
    )


def downgrade() -> None:
    """Move human_estimate_min back to actual_time_min."""
    # Reverse: copy human_estimate_min → actual_time_min
    op.execute(
        "UPDATE time_vision_estimations "
        "SET actual_time_min = human_estimate_min "
        "WHERE human_estimate_min IS NOT NULL AND actual_time_min IS NULL"
    )

    # Clear human_estimate_min
    op.execute(
        "UPDATE time_vision_estimations "
        "SET human_estimate_min = NULL "
        "WHERE human_estimate_min IS NOT NULL"
    )

    # Restore verified status for records with actual_time_min
    op.execute(
        "UPDATE time_vision_estimations "
        "SET status = 'verified' "
        "WHERE actual_time_min IS NOT NULL"
    )
