"""GESTIMA - Testy řezných podmínek"""

import pytest
from app.services.cutting_conditions import get_conditions


@pytest.mark.business
@pytest.mark.critical
@pytest.mark.asyncio
async def test_od_rough_konstrukcni_ocel_mid():
    """KRITICKÝ TEST: Vnější hrubování, konstrukční ocel, MID"""
    result = await get_conditions("od_rough", "konstrukcni_ocel", "mid")
    
    # Values from DB (not hardcoded anymore)
    assert result["Vc"] == 200.0
    assert result["f"] == 0.25
    assert result["Ap"] == 2.5
