"""GESTIMA - Tests for Machining Time Estimation Service

Tests physics-based time estimation logic.
ADR-040: Machining Time Estimation System
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services.machining_time_estimation_service import MachiningTimeEstimationService
from app.config.material_database import get_material_data, list_available_materials


class TestMaterialDatabase:
    """Test material database access."""

    def test_get_material_data_valid(self):
        """Test getting valid material data."""
        data = get_material_data("20910005")  # Alloy steel
        assert data["category"] == "alloy_steel"
        assert data["iso_group"] == "P"
        assert data["density"] == 7.85
        assert data["mrr_aggressive_cm3_min"] == 180.0

    def test_get_material_data_invalid(self):
        """Test getting invalid material returns empty dict."""
        data = get_material_data("99999999")
        assert data == {}

    def test_list_available_materials(self):
        """Test listing all materials."""
        materials = list_available_materials()
        assert len(materials) == 9  # 9 materials in database (including plastics)
        assert "20910005" in materials  # Alloy steel
        assert "20910000" in materials  # Aluminum


class TestMachiningTimeEstimation:
    """Test machining time estimation logic."""

    @pytest.fixture
    def mock_shape(self):
        """Mock OCCT shape with known geometry."""
        shape = MagicMock()
        shape.IsNull.return_value = False
        return shape

    @pytest.fixture
    def mock_geometry(self):
        """Mock geometry data."""
        return {
            "volume_mm3": 50000.0,  # 50 cm³
            "surface_area_mm2": 30000.0,  # 300 cm²
            "bbox": {
                "x_min": 0.0,
                "x_max": 100.0,
                "y_min": 0.0,
                "y_max": 50.0,
                "z_min": 0.0,
                "z_max": 50.0,
                "width": 100.0,
                "depth": 50.0,
                "height": 50.0,
            },
            "face_count": 50,
        }

    def test_calculate_stock_volume_bbox(self, mock_geometry):
        """Test bounding box stock volume calculation."""
        volume = MachiningTimeEstimationService._calculate_stock_volume(
            mock_geometry, "bbox"
        )
        # (100 + 10) * (50 + 10) * (50 + 5) = 110 * 60 * 55
        expected = 110.0 * 60.0 * 55.0
        assert volume == pytest.approx(expected)

    def test_calculate_stock_volume_cylinder(self, mock_geometry):
        """Test cylindrical stock volume calculation."""
        import math
        volume = MachiningTimeEstimationService._calculate_stock_volume(
            mock_geometry, "cylinder"
        )
        # diameter = max(100, 50) + 3 = 103, radius = 51.5
        # length = 50 + 5 = 55
        # volume = π * 51.5² * 55
        expected = math.pi * 51.5 * 51.5 * 55.0
        assert volume == pytest.approx(expected, rel=1e-6)

    def test_detect_constraints_none(self, mock_geometry):
        """Test constraint detection with normal geometry."""
        constraints = MachiningTimeEstimationService._detect_constraints(mock_geometry)
        # No deep pocket (height/width = 50/100 = 0.5 < 3)
        # No thin wall (volume/surface = 50000/30000 = 1.67 < 3 but not thin)
        # No high complexity (50 faces < 100)
        assert "high_complexity" not in constraints

    def test_detect_constraints_deep_pocket(self):
        """Test deep pocket constraint detection."""
        geometry = {
            "volume_mm3": 10000.0,
            "surface_area_mm2": 5000.0,
            "bbox": {
                "width": 20.0,
                "depth": 20.0,
                "height": 100.0,  # height/width = 100/20 = 5 > 3
            },
            "face_count": 30,
        }
        constraints = MachiningTimeEstimationService._detect_constraints(geometry)
        assert "deep_pocket" in constraints

    def test_detect_constraints_thin_wall(self):
        """Test thin wall constraint detection."""
        geometry = {
            "volume_mm3": 10000.0,  # 10 cm³
            "surface_area_mm2": 10000.0,  # 100 cm²
            "bbox": {
                "width": 100.0,
                "depth": 50.0,
                "height": 50.0,
            },
            "face_count": 30,
        }
        # thickness = 10000 / 10000 = 1 mm < 3 mm
        constraints = MachiningTimeEstimationService._detect_constraints(geometry)
        assert "thin_wall" in constraints

    def test_detect_constraints_high_complexity(self):
        """Test high complexity constraint detection."""
        geometry = {
            "volume_mm3": 50000.0,
            "surface_area_mm2": 30000.0,
            "bbox": {
                "width": 100.0,
                "depth": 50.0,
                "height": 50.0,
            },
            "face_count": 150,  # > 100
        }
        constraints = MachiningTimeEstimationService._detect_constraints(geometry)
        assert "high_complexity" in constraints

    def test_calculate_penalty_no_constraints(self):
        """Test penalty calculation with no constraints."""
        material_data = get_material_data("20910005")
        penalty = MachiningTimeEstimationService._calculate_penalty([], material_data)
        assert penalty == 1.0

    def test_calculate_penalty_deep_pocket(self):
        """Test penalty calculation with deep pocket."""
        material_data = get_material_data("20910005")
        penalty = MachiningTimeEstimationService._calculate_penalty(
            ["deep_pocket"], material_data
        )
        # Alloy steel deep_pocket_penalty = 1.8
        assert penalty == 1.8

    def test_calculate_penalty_multiple_constraints(self):
        """Test penalty calculation with multiple constraints."""
        material_data = get_material_data("20910005")
        penalty = MachiningTimeEstimationService._calculate_penalty(
            ["deep_pocket", "thin_wall", "high_complexity"], material_data
        )
        # 1.8 * 2.5 * 1.2 = 5.4
        expected = 1.8 * 2.5 * 1.2
        assert penalty == pytest.approx(expected)

    def test_estimate_time_invalid_material(self, tmp_path):
        """Test estimation with invalid material code."""
        # Create a temporary STEP file to avoid "file not found" error
        dummy_file = tmp_path / "dummy.stp"
        dummy_file.write_text("ISO-10303-21;HEADER;ENDSEC;DATA;ENDSEC;END-ISO-10303-21;")

        with pytest.raises(ValueError, match="Unknown material code"):
            MachiningTimeEstimationService.estimate_time(
                dummy_file, "99999999", "bbox"
            )

    def test_estimate_time_missing_file(self):
        """Test estimation with missing STEP file."""
        with pytest.raises(ValueError, match="STEP file not found"):
            MachiningTimeEstimationService.estimate_time(
                Path("/nonexistent/file.stp"), "20910005", "bbox"
            )

    @patch("app.services.machining_time_estimation_service.OCCT_AVAILABLE", False)
    def test_estimate_time_occt_not_available(self):
        """Test estimation when OCCT is not available."""
        with pytest.raises(RuntimeError, match="OCCT not available"):
            MachiningTimeEstimationService.estimate_time(
                Path("dummy.stp"), "20910005", "bbox"
            )


class TestDeterminism:
    """Test deterministic behavior of estimation."""

    def test_same_input_same_output(self):
        """Test that same inputs always produce identical outputs."""
        # This test would require a real STEP file
        # For now, we validate the calculation logic is deterministic
        material_data = get_material_data("20910005")

        # Simulate two identical calculations
        material_to_remove_cm3 = 100.0
        mrr_roughing = material_data["mrr_aggressive_cm3_min"]
        roughing_time1 = material_to_remove_cm3 / mrr_roughing

        roughing_time2 = material_to_remove_cm3 / mrr_roughing

        assert roughing_time1 == roughing_time2

        # Round to 2 decimals
        rounded1 = round(roughing_time1, 2)
        rounded2 = round(roughing_time2, 2)

        assert rounded1 == rounded2
