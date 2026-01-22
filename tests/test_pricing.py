"""GESTIMA - Testy cenové kalkulace"""

import pytest
import math
from app.services.price_calculator import calculate_material_cost, calculate_machining_cost


@pytest.mark.business
@pytest.mark.critical
@pytest.mark.asyncio
async def test_material_cost_rod_steel():
    """KRITICKÝ TEST: Materiálové náklady pro tyč ø50 × 100mm"""
    result = await calculate_material_cost(
        stock_diameter=50.0,
        stock_length=100.0,
        material_group="konstrukcni_ocel",
    )
    
    expected_volume = math.pi * (25**2) * 100
    expected_weight = (expected_volume / 1_000_000) * 7.85
    expected_cost = expected_weight * 28
    
    assert abs(result.volume_mm3 - expected_volume) < 1
    assert abs(result.weight_kg - expected_weight) < 0.01
    assert abs(result.cost - expected_cost) < 0.5


@pytest.mark.business
@pytest.mark.critical
def test_machining_cost_basic():
    """KRITICKÝ TEST: Strojní náklady"""
    result = calculate_machining_cost(operation_time_min=5.0, hourly_rate=1200.0)
    expected = (5.0 / 60) * 1200
    assert result == expected
