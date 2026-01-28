"""GESTIMA - Testy modelů"""

import pytest
from app.models.enums import StockType, FeatureType
from app.models.part import PartCreate


@pytest.mark.system
def test_part_create_minimal():
    """Vytvoření dílu s minimálními daty (ADR-011: Material Hierarchy)"""
    part = PartCreate(
        part_number="1000001",
        material_item_id=1  # FK na MaterialItem (required)
    )

    assert part.part_number == "1000001"  # ADR-017: 7-digit number
    assert part.material_item_id == 1
    assert part.length == 0.0  # default


@pytest.mark.system
@pytest.mark.critical
def test_feature_types_count():
    """KRITICKÝ TEST: Počet typů kroků"""
    feature_types = list(FeatureType)
    assert len(feature_types) >= 50
