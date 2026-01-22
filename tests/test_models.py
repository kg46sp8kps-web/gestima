"""GESTIMA - Testy modelů"""

import pytest
from app.models.enums import StockType, PartStatus, FeatureType
from app.models.part import PartCreate


@pytest.mark.system
def test_part_create_minimal():
    """Vytvoření dílu s minimálními daty"""
    part = PartCreate()
    
    assert part.part_number == ""
    assert part.material_group == "konstrukcni_ocel"
    assert part.stock_type == StockType.ROD


@pytest.mark.system
@pytest.mark.critical
def test_feature_types_count():
    """KRITICKÝ TEST: Počet typů kroků"""
    feature_types = list(FeatureType)
    assert len(feature_types) >= 50
