"""GESTIMA - Testy řezných podmínek"""

import pytest
from app.services.cutting_conditions import get_conditions, MATERIAL_COEFFICIENTS


@pytest.mark.business
@pytest.mark.critical
def test_reference_material_has_unity_coefficients():
    """KRITICKÝ TEST: Konstrukční ocel = referenční materiál"""
    ref = MATERIAL_COEFFICIENTS["konstrukcni_ocel"]
    assert ref["K_Vc"] == 1.0
    assert ref["K_f"] == 1.0


@pytest.mark.business
@pytest.mark.critical
def test_od_rough_konstrukcni_ocel_mid():
    """KRITICKÝ TEST: Vnější hrubování, konstrukční ocel, MID"""
    result = get_conditions("od_rough", "konstrukcni_ocel", "mid")
    
    assert result["Vc"] == 180
    assert result["f"] == 0.30
    assert result["Ap"] == 3.0
