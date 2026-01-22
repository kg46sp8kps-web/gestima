"""GESTIMA - Testy výpočtu časů"""

import pytest
import math
from app.services.time_calculator import FeatureCalculator


@pytest.mark.business
@pytest.mark.critical
def test_rpm_calculation():
    """KRITICKÝ TEST: Výpočet otáček n = 1000×Vc / π×D"""
    calc = FeatureCalculator(max_rpm=4000)
    rpm = calc.calc_rpm(Vc=180, diameter=50)
    expected = (1000 * 180) / (math.pi * 50)
    
    assert abs(rpm - expected) < 1


@pytest.mark.business
@pytest.mark.critical
def test_time_calculation():
    """KRITICKÝ TEST: Výpočet času t = L / (n×f) × 60"""
    calc = FeatureCalculator()
    time_sec = calc.calc_time(length=100, rpm=1000, feed=0.3)
    expected = (100 / (1000 * 0.3)) * 60
    
    assert abs(time_sec - expected) < 0.1
