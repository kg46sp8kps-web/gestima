"""
Tests for contour_validator.py

Validates that the contour validator correctly fixes common Claude errors:
- Scale mismatch between STEP and contour
- Missing start/end points on axis
- Negative r or z values
- Wrong max_diameter
"""
import pytest
from app.services.contour_validator import validate_and_fix_contour


class TestContourValidatorRotational:
    """Test rotational part contour validation."""

    def test_scale_correction_r_values(self):
        """Test scaling of r-values when contour max_r doesn't match STEP."""
        # STEP says max Ø55 (r=27.5)
        # Claude returned contour with max r=50 (wrong!)
        step_features = [
            {"type": "cylindrical", "diameter": 55.0},
            {"type": "cylindrical", "diameter": 30.0},
        ]
        profile_geo = {
            "type": "rotational",
            "outer_contour": [
                {"r": 0, "z": 0},
                {"r": 50, "z": 0},  # Wrong! Should be 27.5
                {"r": 50, "z": 80},
                {"r": 0, "z": 80},
            ],
            "max_diameter": 100,  # Wrong! Should be 55
            "total_length": 80,
        }

        result = validate_and_fix_contour(profile_geo, step_features)

        # Check max_diameter was corrected
        assert result["max_diameter"] == 55.0

        # Check r-values were scaled
        assert result["outer_contour"][1]["r"] == pytest.approx(27.5, abs=0.1)
        assert result["outer_contour"][2]["r"] == pytest.approx(27.5, abs=0.1)

        # Check report
        report = result["validation_report"]
        assert len(report["fixes"]) > 0
        assert any("scaled by" in fix for fix in report["fixes"])

    def test_missing_start_end_points(self):
        """Test adding start/end points if contour doesn't start/end on axis."""
        step_features = [{"type": "cylindrical", "diameter": 30.0}]
        profile_geo = {
            "type": "rotational",
            "outer_contour": [
                {"r": 15, "z": 0},  # Missing (r=0, z=0)
                {"r": 15, "z": 50},
                # Missing (r=0, z=50)
            ],
            "max_diameter": 30,
            "total_length": 50,
        }

        result = validate_and_fix_contour(profile_geo, step_features)

        # Check start/end points added
        assert result["outer_contour"][0] == {"r": 0, "z": 0}
        assert result["outer_contour"][-1]["r"] == 0

        report = result["validation_report"]
        assert any("start point" in fix for fix in report["fixes"])
        assert any("end point" in fix for fix in report["fixes"])

    def test_negative_values_correction(self):
        """Test removal of negative r or z values."""
        step_features = [{"type": "cylindrical", "diameter": 30.0}]
        profile_geo = {
            "type": "rotational",
            "outer_contour": [
                {"r": -5, "z": 0},  # Invalid negative r
                {"r": 15, "z": -2},  # Invalid negative z
                {"r": 15, "z": 50},
            ],
            "max_diameter": 30,
            "total_length": 50,
        }

        result = validate_and_fix_contour(profile_geo, step_features)

        # Check negative values corrected to 0
        assert all(p["r"] >= 0 for p in result["outer_contour"])
        assert all(p["z"] >= 0 for p in result["outer_contour"])

        report = result["validation_report"]
        assert any("Negative" in fix for fix in report["fixes"])

    def test_z_length_scale_correction(self):
        """Test scaling z-values when contour max_z doesn't match total_length."""
        step_features = [{"type": "cylindrical", "diameter": 30.0}]
        profile_geo = {
            "type": "rotational",
            "outer_contour": [
                {"r": 0, "z": 0},
                {"r": 15, "z": 0},
                {"r": 15, "z": 100},  # Wrong! total_length is 50
                {"r": 0, "z": 100},
            ],
            "max_diameter": 30,
            "total_length": 50,  # Correct value
        }

        result = validate_and_fix_contour(profile_geo, step_features)

        # Check z-values were scaled down
        assert result["outer_contour"][2]["z"] == pytest.approx(50, abs=0.5)
        assert result["outer_contour"][3]["z"] == pytest.approx(50, abs=0.5)

        report = result["validation_report"]
        assert any("z-values scaled" in fix for fix in report["fixes"])

    def test_inner_contour_scale_correction(self):
        """Test inner contour scaling for holes."""
        step_features = [
            {"type": "cylindrical", "diameter": 30.0},
            {"type": "hole", "diameter": 19.0},
        ]
        profile_geo = {
            "type": "rotational",
            "outer_contour": [
                {"r": 0, "z": 0},
                {"r": 15, "z": 0},
                {"r": 15, "z": 50},
                {"r": 0, "z": 50},
            ],
            "inner_contour": [
                {"r": 5, "z": 0},  # Wrong! Should be 9.5 for Ø19
                {"r": 5, "z": 50},
            ],
            "max_diameter": 30,
            "total_length": 50,
        }

        result = validate_and_fix_contour(profile_geo, step_features)

        # Check inner contour r scaled to match STEP hole diameter
        assert result["inner_contour"][0]["r"] == pytest.approx(9.5, abs=0.1)
        assert result["inner_contour"][1]["r"] == pytest.approx(9.5, abs=0.1)

        report = result["validation_report"]
        assert any("Inner contour r scaled" in fix for fix in report["fixes"])

    def test_no_fixes_needed(self):
        """Test that correct contour passes validation without changes."""
        step_features = [{"type": "cylindrical", "diameter": 30.0}]
        profile_geo = {
            "type": "rotational",
            "outer_contour": [
                {"r": 0, "z": 0},
                {"r": 15, "z": 0},
                {"r": 15, "z": 50},
                {"r": 0, "z": 50},
            ],
            "max_diameter": 30,
            "total_length": 50,
        }

        result = validate_and_fix_contour(profile_geo, step_features)

        # Original contour should be unchanged
        assert result["outer_contour"] == profile_geo["outer_contour"]

        # No fixes should be reported
        report = result["validation_report"]
        assert len(report["fixes"]) == 0
        assert report["valid"] is True

    def test_missing_step_diameters_warning(self):
        """Test warning when STEP diameter is missing from contour."""
        step_features = [
            {"type": "cylindrical", "diameter": 30.0},
            {"type": "cylindrical", "diameter": 55.0},  # Not in contour
        ]
        profile_geo = {
            "type": "rotational",
            "outer_contour": [
                {"r": 0, "z": 0},
                {"r": 15, "z": 0},  # Only Ø30, missing Ø55
                {"r": 15, "z": 50},
                {"r": 0, "z": 50},
            ],
            "max_diameter": 30,
            "total_length": 50,
        }

        result = validate_and_fix_contour(profile_geo, step_features)

        # Should warn about missing Ø55
        report = result["validation_report"]
        assert any("55" in str(warning) for warning in report["warnings"])


class TestContourValidatorPrismatic:
    """Test prismatic part contour validation."""

    def test_hole_diameter_correction(self):
        """Test hole diameter correction for prismatic parts."""
        step_features = [
            {"type": "hole", "diameter": 8.0},
        ]
        profile_geo = {
            "type": "prismatic",
            "bounding_box": {"length": 100, "width": 50, "height": 20},
            "holes": [
                {"x": 25, "y": 25, "diameter": 7.3, "depth": 20},  # Off by ~9% (0.7mm)
            ],
        }

        result = validate_and_fix_contour(profile_geo, step_features)

        # Hole diameter should be corrected to STEP value (diff > 0.5mm and < 20%)
        assert result["holes"][0]["diameter"] == 8.0

        report = result["validation_report"]
        assert any("Hole" in fix for fix in report["fixes"])


class TestContourValidatorEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_profile_geometry(self):
        """Test that None/empty profile_geometry is handled gracefully."""
        step_features = [{"type": "cylindrical", "diameter": 30.0}]

        result = validate_and_fix_contour(None, step_features)
        assert result is None

        result = validate_and_fix_contour({}, step_features)
        assert result == {}

    def test_no_step_features(self):
        """Test behavior when STEP features are empty."""
        profile_geo = {
            "type": "rotational",
            "outer_contour": [
                {"r": 0, "z": 0},
                {"r": 15, "z": 50},
                {"r": 0, "z": 50},
            ],
        }

        result = validate_and_fix_contour(profile_geo, [])

        # Should return with warning about no STEP data
        report = result["validation_report"]
        assert any("No STEP diameters" in warning for warning in report["warnings"])

    def test_empty_outer_contour(self):
        """Test handling of missing/empty outer_contour."""
        step_features = [{"type": "cylindrical", "diameter": 30.0}]
        profile_geo = {
            "type": "rotational",
            "outer_contour": [],
            "max_diameter": 30,
        }

        result = validate_and_fix_contour(profile_geo, step_features)

        # Should flag as invalid
        report = result["validation_report"]
        assert report["valid"] is False
        assert any("No outer_contour" in warning for warning in report["warnings"])
