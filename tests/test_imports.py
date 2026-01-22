"""GESTIMA - Testy importů"""

import pytest


@pytest.mark.system
@pytest.mark.critical
def test_import_app():
    """Import hlavní aplikace"""
    from app.gestima_app import app
    assert app is not None


@pytest.mark.system
@pytest.mark.critical
def test_import_all_models():
    """Import všech modelů"""
    from app.models import (
        Part, PartCreate,
        Operation, OperationCreate,
        Feature, FeatureCreate,
        Batch, BatchCreate,
    )
    assert Part is not None


@pytest.mark.system
@pytest.mark.critical
def test_import_services():
    """Import services"""
    from app.services.time_calculator import FeatureCalculator
    from app.services.cutting_conditions import get_conditions
    from app.services.price_calculator import calculate_batch_prices
    
    assert FeatureCalculator is not None
