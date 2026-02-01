"""GESTIMA - Testy modelů"""

import pytest
from app.models.enums import StockType, FeatureType
from app.models.part import PartCreate


@pytest.mark.system
def test_part_create_minimal():
    """Vytvoření dílu s minimálními daty (ADR-024: article_number REQUIRED)"""
    part = PartCreate(
        article_number="ART-TEST-001",  # REQUIRED field
        name="Test díl"  # REQUIRED field
    )

    assert part.article_number == "ART-TEST-001"
    assert part.name == "Test díl"


@pytest.mark.system
@pytest.mark.critical
def test_feature_types_count():
    """KRITICKÝ TEST: Počet typů kroků"""
    feature_types = list(FeatureType)
    assert len(feature_types) >= 50
