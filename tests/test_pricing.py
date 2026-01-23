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
        stock_type="tyc",
    )
    
    expected_volume = math.pi * (25**2) * 100
    expected_weight = (expected_volume / 1_000_000) * 7.85
    # Cena se načítá z DB, takže počítáme s tím co vrátil
    expected_cost = expected_weight * result.price_per_kg
    
    assert abs(result.volume_mm3 - expected_volume) < 1
    assert abs(result.weight_kg - expected_weight) < 0.01
    assert abs(result.cost - expected_cost) < 0.5
    assert result.price_per_kg > 0  # Cena musí být načtená z DB


@pytest.mark.business
@pytest.mark.critical
@pytest.mark.asyncio
async def test_material_cost_tube():
    """KRITICKÝ TEST: Materiálové náklady pro trubku ø50/40 × 100mm"""
    result = await calculate_material_cost(
        stock_diameter=50.0,
        stock_diameter_inner=40.0,
        stock_length=100.0,
        material_group="konstrukcni_ocel",
        stock_type="trubka",
    )
    
    r_outer = 25
    r_inner = 20
    expected_volume = math.pi * (r_outer**2 - r_inner**2) * 100
    expected_weight = (expected_volume / 1_000_000) * 7.85
    expected_cost = expected_weight * result.price_per_kg
    
    assert abs(result.volume_mm3 - expected_volume) < 1
    assert abs(result.weight_kg - expected_weight) < 0.01
    assert abs(result.cost - expected_cost) < 0.5


@pytest.mark.business
@pytest.mark.critical
@pytest.mark.asyncio
async def test_material_cost_billet():
    """KRITICKÝ TEST: Materiálové náklady pro přířez 100×50×30mm"""
    result = await calculate_material_cost(
        stock_diameter=0,
        stock_length=100.0,
        stock_width=50.0,
        stock_height=30.0,
        material_group="konstrukcni_ocel",
        stock_type="prizez",
    )
    
    expected_volume = 100 * 50 * 30
    expected_weight = (expected_volume / 1_000_000) * 7.85
    expected_cost = expected_weight * result.price_per_kg
    
    assert abs(result.volume_mm3 - expected_volume) < 1
    assert abs(result.weight_kg - expected_weight) < 0.01
    assert abs(result.cost - expected_cost) < 0.5


@pytest.mark.business
@pytest.mark.critical
@pytest.mark.asyncio
async def test_material_cost_sheet():
    """KRITICKÝ TEST: Materiálové náklady pro plech 1000×500×5mm"""
    result = await calculate_material_cost(
        stock_diameter=0,
        stock_length=1000.0,
        stock_width=500.0,
        stock_height=5.0,
        material_group="konstrukcni_ocel",
        stock_type="plech",
    )
    
    expected_volume = 1000 * 500 * 5
    expected_weight = (expected_volume / 1_000_000) * 7.85
    expected_cost = expected_weight * result.price_per_kg
    
    assert abs(result.volume_mm3 - expected_volume) < 1
    assert abs(result.weight_kg - expected_weight) < 0.01
    assert abs(result.cost - expected_cost) < 0.5


@pytest.mark.business
@pytest.mark.critical
@pytest.mark.asyncio
async def test_material_cost_casting():
    """KRITICKÝ TEST: Materiálové náklady pro odlitek ø80 × 150mm"""
    result = await calculate_material_cost(
        stock_diameter=80.0,
        stock_length=150.0,
        material_group="liatina_siva",
        stock_type="odlitek",
    )
    
    expected_volume = math.pi * (40**2) * 150
    # Hustota se načítá z DB, použijeme vrácený výsledek
    expected_cost = result.weight_kg * result.price_per_kg
    
    assert abs(result.volume_mm3 - expected_volume) < 1
    assert result.weight_kg > 0
    assert result.price_per_kg > 0
    assert abs(result.cost - expected_cost) < 0.5


@pytest.mark.business
@pytest.mark.asyncio
async def test_material_cost_stainless():
    """TEST: Materiálové náklady pro nerez tyč ø50 × 100mm"""
    result = await calculate_material_cost(
        stock_diameter=50.0,
        stock_length=100.0,
        material_group="nerez_austeniticka",
        stock_type="tyc",
    )
    
    # Objem je stejný pro všechny materiály
    expected_volume = math.pi * (25**2) * 100
    assert abs(result.volume_mm3 - expected_volume) < 1
    
    # Hmotnost a cena závisí na hustotě a ceně z DB
    # Testujeme jen že výpočet proběhl
    assert result.weight_kg > 0
    assert result.price_per_kg > 0
    assert result.cost > 0
    assert result.cost == pytest.approx(result.weight_kg * result.price_per_kg, rel=0.01)


@pytest.mark.business
@pytest.mark.asyncio
async def test_material_cost_zero_dimensions():
    """TEST: Nulové rozměry vrací nulové náklady"""
    result = await calculate_material_cost(
        stock_diameter=0,
        stock_length=0,
        material_group="konstrukcni_ocel",
        stock_type="tyc",
    )
    
    assert result.volume_mm3 == 0
    assert result.weight_kg == 0
    assert result.cost == 0
    assert result.price_per_kg == 0  # Když není objem, není ani cena


@pytest.mark.business
@pytest.mark.asyncio
async def test_material_cost_invalid_material():
    """TEST: Neexistující materiál používá fallback hodnoty"""
    result = await calculate_material_cost(
        stock_diameter=50.0,
        stock_length=100.0,
        material_group="neexistujici_material",
        stock_type="tyc",
    )
    
    # Fallback: density=7.85, price_per_kg=30
    expected_volume = math.pi * (25**2) * 100
    expected_weight = (expected_volume / 1_000_000) * 7.85
    
    assert abs(result.volume_mm3 - expected_volume) < 1
    assert abs(result.weight_kg - expected_weight) < 0.01
    assert result.price_per_kg == 30  # Fallback cena
    assert result.cost > 0


@pytest.mark.business
@pytest.mark.critical
def test_machining_cost_basic():
    """KRITICKÝ TEST: Strojní náklady"""
    result = calculate_machining_cost(operation_time_min=5.0, hourly_rate=1200.0)
    expected = (5.0 / 60) * 1200
    assert result == expected
