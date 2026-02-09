"""Tests for estimation router endpoints (Phase 5 validation)

These tests verify the estimation router API functionality using database queries.
"""

import pytest
from sqlalchemy import select, func
from app.database import async_session
from app.models.turning_estimation import TurningEstimation
from app.models.milling_estimation import MillingEstimation


@pytest.mark.asyncio
async def test_pending_estimates_rot_exist():
    """Verify that ROT parts (turning_estimations) exist without manual estimates"""
    async with async_session() as session:
        result = await session.execute(
            select(func.count(TurningEstimation.id)).where(
                TurningEstimation.estimated_time_min.is_(None)
            )
        )
        count = result.scalar()
        assert count > 0, "Should have ROT parts without manual time estimates"


@pytest.mark.asyncio
async def test_pending_estimates_pri_exist():
    """Verify that PRI parts (milling_estimations) exist without manual estimates"""
    async with async_session() as session:
        result = await session.execute(
            select(func.count(MillingEstimation.id)).where(
                MillingEstimation.estimated_time_min.is_(None)
            )
        )
        count = result.scalar()
        assert count > 0, "Should have PRI parts without manual time estimates"


@pytest.mark.asyncio
async def test_total_seeded_parts_count():
    """Verify that all 37 parts are seeded in DB"""
    async with async_session() as session:
        turning_result = await session.execute(select(func.count(TurningEstimation.id)))
        milling_result = await session.execute(select(func.count(MillingEstimation.id)))
        
        turning_count = turning_result.scalar()
        milling_count = milling_result.scalar()
        total = turning_count + milling_count
        
        assert total == 37, f"Expected 37 total parts, got {total} ({turning_count} ROT + {milling_count} PRI)"


@pytest.mark.asyncio
async def test_rot_pri_classification_consistency():
    """Verify ROT/PRI classification is consistent with rotational_score threshold"""
    async with async_session() as session:
        # Check turning parts have rotational_score distribution
        turning = await session.execute(
            select(TurningEstimation.rotational_score).order_by(TurningEstimation.rotational_score)
        )
        turning_scores = [row[0] for row in turning]
        
        # Check milling parts have rotational_score distribution
        milling = await session.execute(
            select(MillingEstimation.rotational_score).order_by(MillingEstimation.rotational_score)
        )
        milling_scores = [row[0] for row in milling]
        
        # Verify turning parts have higher average rotational_score
        avg_turning = sum(turning_scores) / len(turning_scores) if turning_scores else 0
        avg_milling = sum(milling_scores) / len(milling_scores) if milling_scores else 0
        
        assert avg_turning > avg_milling, "Turning parts should have higher rotational_score on average"


@pytest.mark.asyncio
async def test_volume_conservation_all_parts():
    """Verify volume conservation for all 37 parts (< 1% error)"""
    async with async_session() as session:
        # Get turning parts
        turning_parts = await session.execute(
            select(
                TurningEstimation.filename,
                TurningEstimation.part_volume_mm3,
                TurningEstimation.stock_volume_mm3,
                TurningEstimation.removal_volume_mm3,
            )
        )
        
        # Get milling parts
        milling_parts = await session.execute(
            select(
                MillingEstimation.filename,
                MillingEstimation.part_volume_mm3,
                MillingEstimation.stock_volume_mm3,
                MillingEstimation.removal_volume_mm3,
            )
        )
        
        all_parts = list(turning_parts) + list(milling_parts)
        
        max_error = 0.0
        for fname, part_vol, stock_vol, removal_vol in all_parts:
            if stock_vol > 0:
                error = abs(part_vol + removal_vol - stock_vol) / stock_vol * 100
                max_error = max(max_error, error)
                assert error < 1.0, f"{fname}: Volume conservation error {error:.3f}% exceeds 1%"
        
        assert max_error < 1.0, f"Max volume error {max_error:.3f}% should be < 1%"


@pytest.mark.asyncio
async def test_feature_completeness_sample():
    """Verify feature completeness on random sample parts"""
    async with async_session() as session:
        # Get one turning and one milling part
        turning = await session.execute(select(TurningEstimation).limit(1))
        milling = await session.execute(select(MillingEstimation).limit(1))
        
        turning_record = turning.scalars().first()
        milling_record = milling.scalars().first()
        
        mandatory_fields = [
            'part_volume_mm3', 'stock_volume_mm3', 'removal_volume_mm3',
            'surface_area_mm2', 'bbox_x_mm', 'bbox_y_mm', 'bbox_z_mm',
            'rotational_score', 'face_count', 'edge_count', 'vertex_count'
        ]
        
        for record in [turning_record, milling_record]:
            if record:
                for field in mandatory_fields:
                    val = getattr(record, field)
                    assert val is not None, f"Field {field} should not be None"
                    assert val > 0, f"Field {field} should be > 0, got {val}"


@pytest.mark.asyncio
async def test_rotational_score_ranges():
    """Verify rotational_score is in valid range [0, 1]"""
    async with async_session() as session:
        turning = await session.execute(select(TurningEstimation.rotational_score))
        milling = await session.execute(select(MillingEstimation.rotational_score))
        
        for score, in list(turning) + list(milling):
            assert 0.0 <= score <= 1.0, f"rotational_score {score} not in [0, 1]"


@pytest.mark.asyncio
async def test_no_null_mandatory_fields():
    """Verify no critical fields are NULL in any part"""
    async with async_session() as session:
        turning = await session.execute(
            select(TurningEstimation).where(
                (TurningEstimation.part_volume_mm3.is_(None)) |
                (TurningEstimation.stock_volume_mm3.is_(None)) |
                (TurningEstimation.surface_area_mm2.is_(None)) |
                (TurningEstimation.rotational_score.is_(None))
            )
        )
        turning_nulls = len(turning.scalars().all())
        
        milling = await session.execute(
            select(MillingEstimation).where(
                (MillingEstimation.part_volume_mm3.is_(None)) |
                (MillingEstimation.stock_volume_mm3.is_(None)) |
                (MillingEstimation.surface_area_mm2.is_(None)) |
                (MillingEstimation.rotational_score.is_(None))
            )
        )
        milling_nulls = len(milling.scalars().all())
        
        assert turning_nulls == 0, f"{turning_nulls} turning parts with NULL mandatory fields"
        assert milling_nulls == 0, f"{milling_nulls} milling parts with NULL mandatory fields"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
