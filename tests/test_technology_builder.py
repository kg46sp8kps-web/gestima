"""GESTIMA - Technology Builder Tests

Tests for Technology Builder service (Phase 1):
- Cut height calculations for different stock shapes
- Sawing time calculations (height / feed_rate)
- Technology plan generation
"""

import pytest
from app.models.enums import StockShape
from app.services.technology_builder import (
    calculate_cut_height_mm,
    TechnologyPlan,
)


class TestCutHeightCalculations:
    """Test cut height calculations for different stock shapes."""

    def test_round_bar(self):
        """Round bar: cut height = diameter."""
        height = calculate_cut_height_mm(
            stock_shape=StockShape.ROUND_BAR,
            stock_diameter=50.0,
        )
        assert height == 50.0

    def test_square_bar(self):
        """Square bar: cut height = side (width)."""
        height = calculate_cut_height_mm(
            stock_shape=StockShape.SQUARE_BAR,
            stock_width=40.0,
        )
        assert height == 40.0

    def test_flat_bar(self):
        """Flat bar: cut height = shorter dimension (min of w, h)."""
        height = calculate_cut_height_mm(
            stock_shape=StockShape.FLAT_BAR,
            stock_width=60.0,
            stock_height=20.0,
        )
        assert height == 20.0

    def test_flat_bar_reversed(self):
        """Flat bar: same result regardless of which is larger."""
        height = calculate_cut_height_mm(
            stock_shape=StockShape.FLAT_BAR,
            stock_width=20.0,
            stock_height=60.0,
        )
        assert height == 20.0

    def test_hexagonal_bar(self):
        """Hexagonal bar: cut height = across-flats dimension."""
        height = calculate_cut_height_mm(
            stock_shape=StockShape.HEXAGONAL_BAR,
            stock_diameter=50.0,
        )
        assert height == 50.0

    def test_tube(self):
        """Tube: cut height = outer diameter."""
        height = calculate_cut_height_mm(
            stock_shape=StockShape.TUBE,
            stock_diameter=50.0,
            stock_wall_thickness=5.0,
        )
        assert height == 50.0

    def test_plate(self):
        """Plate: cut height = thickness (height)."""
        height = calculate_cut_height_mm(
            stock_shape=StockShape.PLATE,
            stock_width=100.0,
            stock_height=10.0,
        )
        assert height == 10.0

    def test_zero_dimensions(self):
        """Missing or zero dimensions return 0."""
        height = calculate_cut_height_mm(
            stock_shape=StockShape.ROUND_BAR,
            stock_diameter=None,
        )
        assert height == 0.0


class TestSawingTimeCalculation:
    """Test sawing time = cut_height_mm / feed_rate_mm_min."""

    def test_ocel_konstrukcni_d50(self):
        """
        C45 (ocel konstrukční), round bar D=50mm:
        - Cut height = 50mm
        - Feed rate = 71 mm/min (mid mode, sk. II)
        - Time = 50 / 71 ≈ 0.7 min
        """
        height = calculate_cut_height_mm(
            stock_shape=StockShape.ROUND_BAR,
            stock_diameter=50.0,
        )
        feed_rate_mid = 71  # From _sawing_base["20910004"]
        time = height / feed_rate_mid
        assert abs(time - 0.7) < 0.05

    def test_ocel_konstrukcni_d40(self):
        """
        C45, round bar D=40mm:
        - Cut height = 40mm
        - Feed rate = 71 mm/min
        - Time = 40 / 71 ≈ 0.56 min
        """
        height = calculate_cut_height_mm(
            stock_shape=StockShape.ROUND_BAR,
            stock_diameter=40.0,
        )
        feed_rate_mid = 71
        time = height / feed_rate_mid
        assert abs(time - 0.56) < 0.05

    def test_hlinik_d50(self):
        """
        Hliník, round bar D=50mm:
        - Cut height = 50mm
        - Feed rate = 96 mm/min (mid, sk. I)
        - Time = 50 / 96 ≈ 0.52 min
        """
        height = calculate_cut_height_mm(
            stock_shape=StockShape.ROUND_BAR,
            stock_diameter=50.0,
        )
        feed_rate_mid = 96  # From _sawing_base["20910000"]
        time = height / feed_rate_mid
        assert abs(time - 0.52) < 0.05

    def test_nerez_d50(self):
        """
        Nerez, round bar D=50mm:
        - Cut height = 50mm
        - Feed rate = 23 mm/min (mid, sk. VI)
        - Time = 50 / 23 ≈ 2.17 min
        """
        height = calculate_cut_height_mm(
            stock_shape=StockShape.ROUND_BAR,
            stock_diameter=50.0,
        )
        feed_rate_mid = 23  # From _sawing_base["20910007"]
        time = height / feed_rate_mid
        assert abs(time - 2.17) < 0.05

    def test_flat_bar_ocel(self):
        """
        C45 flat bar 60×20mm:
        - Cut height = 20mm (shorter side)
        - Feed rate = 71 mm/min
        - Time = 20 / 71 ≈ 0.28 min
        """
        height = calculate_cut_height_mm(
            stock_shape=StockShape.FLAT_BAR,
            stock_width=60.0,
            stock_height=20.0,
        )
        feed_rate_mid = 71
        time = height / feed_rate_mid
        assert abs(time - 0.28) < 0.05


class TestTechnologyPlan:
    """Test TechnologyPlan dataclass."""

    def test_empty_plan(self):
        """Test empty technology plan."""
        plan = TechnologyPlan()
        assert plan.operations == []
        assert plan.warnings == []

    def test_plan_with_warnings(self):
        """Test technology plan with warnings."""
        plan = TechnologyPlan(
            operations=[],
            warnings=["Materiál nezadán", "Pracoviště nenalezeno"]
        )
        assert len(plan.warnings) == 2
        assert "Materiál nezadán" in plan.warnings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
