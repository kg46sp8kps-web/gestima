"""
Tests for Batch Cost Percentages (P0-006: Static Bar Charts Fix)

Verifies that cost percentages are calculated in Python (ADR-016: Rule #1),
not in JavaScript on the frontend.

CRITICAL-003 FIX: Percentages now computed ONLY in Pydantic BatchResponse
computed fields, not in BatchPrices dataclass (Single Source of Truth - L-002).
"""

import pytest
from app.services.price_calculator import BatchPrices, calculate_batch_prices
from app.models.batch import BatchResponse


def test_calculate_batch_prices_basic():
    """Test that calculate_batch_prices() computes costs correctly"""
    # Setup test data
    quantity = 10
    material_cost = 150.0
    operations = [
        {
            "is_coop": False,
            "machine_id": 1,
            "operation_time_min": 10.0,  # 10 min per piece
            "setup_time_min": 30.0,  # 30 min setup
        }
    ]
    machines = {
        1: {"hourly_rate": 1200}  # 1200 Kč/hod = 20 Kč/min
    }

    # Calculate
    result = calculate_batch_prices(quantity, material_cost, operations, machines)

    # Expected values:
    # machining_cost = 10 min × (1200/60) = 10 × 20 = 200 Kč
    # setup_cost = 30 min × (1200/60) / 10 = 30 × 20 / 10 = 60 Kč
    # unit_cost = 150 + 200 + 60 = 410 Kč

    assert result.material_cost == 150.0
    assert result.machining_cost == 200.0
    assert result.setup_cost == 60.0
    assert result.coop_cost == 0.0
    assert result.unit_cost == 410.0
    assert result.total_cost == 4100.0  # 410 × 10

    # BatchPrices no longer has percentage fields (CRITICAL-003 fix)
    # Percentages are computed in BatchResponse computed fields


def test_calculate_batch_prices_zero_cost():
    """Test calculate_batch_prices with zero cost (edge case)"""
    result = calculate_batch_prices(
        quantity=1,
        material_cost=0.0,
        operations=[],
        machines={}
    )

    assert result.material_cost == 0.0
    assert result.machining_cost == 0.0
    assert result.setup_cost == 0.0
    assert result.coop_cost == 0.0
    assert result.unit_cost == 0.0
    assert result.total_cost == 0.0


def test_batch_response_computed_percentages():
    """Test that BatchResponse computes percentages via @computed_field"""
    # Create mock batch data
    batch_data = {
        "id": 1,
        "part_id": 1,
        "quantity": 10,
        "is_default": False,
        "unit_time_min": 15.0,
        "material_cost": 100.0,
        "machining_cost": 150.0,
        "setup_cost": 50.0,
        "coop_cost": 0.0,
        "unit_cost": 300.0,
        "total_cost": 3000.0,
        "version": 1,
        "created_at": "2026-01-26T12:00:00",
        "updated_at": "2026-01-26T12:00:00",
        "is_frozen": False,
        "frozen_at": None,
        "frozen_by_id": None,
        "snapshot_data": None,
        "unit_price_frozen": None,
        "total_price_frozen": None,
    }

    # Create BatchResponse (Pydantic will compute percentages)
    response = BatchResponse(**batch_data)

    # Verify computed percentages
    assert response.material_percent == round((100.0 / 300.0) * 100, 1)  # 33.3%
    assert response.machining_percent == 50.0  # 150/300 = 50%
    assert response.setup_percent == round((50.0 / 300.0) * 100, 1)  # 16.7%
    assert response.coop_percent == 0.0

    # Verify sum is 100%
    total = response.material_percent + response.machining_percent + response.setup_percent + response.coop_percent
    assert total == 100.0


def test_batch_response_percentages_zero_cost():
    """Test BatchResponse computed percentages with zero unit_cost"""
    batch_data = {
        "id": 1,
        "part_id": 1,
        "quantity": 1,
        "is_default": False,
        "unit_time_min": 0.0,
        "material_cost": 0.0,
        "machining_cost": 0.0,
        "setup_cost": 0.0,
        "coop_cost": 0.0,
        "unit_cost": 0.0,
        "total_cost": 0.0,
        "version": 1,
        "created_at": "2026-01-26T12:00:00",
        "updated_at": "2026-01-26T12:00:00",
        "is_frozen": False,
    }

    response = BatchResponse(**batch_data)

    # All percentages should be 0 (no division by zero)
    assert response.material_percent == 0.0
    assert response.machining_percent == 0.0
    assert response.setup_percent == 0.0
    assert response.coop_percent == 0.0
