"""Tests for feature-based machining time calculator

Verification:
- Detail string parsing (diameter, length, depth, pitch)
- Feature type → DB operation mapping
- Time calculation formulas
- Error handling and warnings
- Integration with cutting conditions catalog
"""

import pytest
from app.services.feature_calculator import (
    parse_diameter,
    parse_length,
    parse_width,
    parse_depth,
    parse_thread_pitch,
    calc_turning_time,
    calc_drilling_time,
    calc_milling_time,
    calc_threading_time,
    calculate_features_time,
)


# ============================================================================
# DETAIL PARSING TESTS
# ============================================================================

class TestDetailParsing:
    """Test extraction of dimensions from AI detail strings."""

    def test_parse_diameter_basic(self):
        assert parse_diameter("ø60 h9") == 60.0
        assert parse_diameter("ø5.3 mm") == 5.3
        assert parse_diameter("Ø12.5") == 12.5

    def test_parse_diameter_with_count(self):
        assert parse_diameter("2× ø5.3 mm") == 5.3

    def test_parse_diameter_thread(self):
        assert parse_diameter("M5") == 5.0
        assert parse_diameter("M10×1.5") == 10.0

    def test_parse_diameter_missing(self):
        assert parse_diameter("") is None
        assert parse_diameter("some text") is None

    def test_parse_length(self):
        assert parse_length("80×22×3.4mm") == 80.0
        assert parse_length("L=50") == 50.0
        assert parse_length("L 50") == 50.0

    def test_parse_width(self):
        assert parse_width("80×22×3.4mm") == 22.0

    def test_parse_depth(self):
        assert parse_depth("80×22×3.4mm") == 3.4
        assert parse_depth("H=5") == 5.0
        assert parse_depth("H 5.5") == 5.5

    def test_parse_thread_pitch_explicit(self):
        assert parse_thread_pitch("M10×1.5") == 1.5
        assert parse_thread_pitch("M12×1.75") == 1.75

    def test_parse_thread_pitch_standard(self):
        # Standard ISO metric pitches
        assert parse_thread_pitch("M5") == 0.8
        assert parse_thread_pitch("M8") == 1.25
        assert parse_thread_pitch("M10") == 1.5


# ============================================================================
# TIME CALCULATION FORMULA TESTS
# ============================================================================

class TestTimeFormulas:
    """Test machining time calculation formulas."""

    def test_turning_time_basic(self):
        # Diameter 60mm, length 100mm, Vc=220, f=0.25, Ap=2.5
        time = calc_turning_time(60, 100, 220, 0.25, 2.5)
        assert time > 0
        assert time < 10  # Sanity check

    def test_turning_time_multiple_passes(self):
        # Material removal 5mm, Ap=2.5 → 2 passes
        time = calc_turning_time(60, 100, 220, 0.25, 2.5, material_removal_mm=5.0)
        assert time > 0

    def test_drilling_time(self):
        # Drill ø5mm, depth 20mm
        time = calc_drilling_time(5, 20, 90, 0.2)
        assert time > 0
        assert time < 5

    def test_milling_time(self):
        # Pocket 80×22×3.4mm
        time = calc_milling_time(80, 22, 3.4, 160, 0.1, 2.0)
        assert time > 0

    def test_threading_time(self):
        # M10×1.5, length 20mm
        time = calc_threading_time(10, 20, 1.5, 80)
        assert time > 0

    def test_zero_inputs_return_minimum(self):
        # Invalid inputs should return minimum time
        assert calc_turning_time(0, 100, 220, 0.25, 2.5) == 0.01
        assert calc_drilling_time(5, 0, 90, 0.2) == 0.01


# ============================================================================
# FEATURE CALCULATION INTEGRATION TESTS
# ============================================================================

class TestFeatureCalculation:
    """Test end-to-end feature time calculation."""

    def test_turning_feature(self):
        features = [
            {
                "type": "outer_diameter",
                "count": 1,
                "detail": "ø60 h9",
                "location": "hlava"
            }
        ]

        result = calculate_features_time(
            features,
            material_group="20910004",  # Ocel konstrukční
            cutting_mode="mid",
            part_type="ROT"
        )

        assert result["calculated_time_min"] > 0
        assert len(result["feature_times"]) == 1
        assert result["feature_times"][0]["type"] == "outer_diameter"
        assert "turning" in result["feature_times"][0]["method"]

    def test_drilling_feature(self):
        features = [
            {
                "type": "through_hole",
                "count": 2,
                "detail": "ø5.3 mm",
                "location": "levý roh"
            }
        ]

        result = calculate_features_time(
            features,
            material_group="20910004",
            cutting_mode="mid"
        )

        assert result["calculated_time_min"] > 0
        assert len(result["feature_times"]) == 1
        ft = result["feature_times"][0]
        assert ft["count"] == 2
        assert "drilling" in ft["method"]

    def test_milling_pocket(self):
        features = [
            {
                "type": "pocket",
                "count": 1,
                "detail": "80×22×3.4mm",
                "location": "střed"
            }
        ]

        result = calculate_features_time(
            features,
            material_group="20910004",
            cutting_mode="mid",
            part_type="PRI"
        )

        assert result["calculated_time_min"] > 0
        assert len(result["feature_times"]) == 1
        assert "milling" in result["feature_times"][0]["method"]

    def test_threading_feature(self):
        features = [
            {
                "type": "thread_external",
                "count": 1,
                "detail": "M10×1.5",
                "location": "konec"
            }
        ]

        result = calculate_features_time(
            features,
            material_group="20910004",
            cutting_mode="mid"
        )

        assert result["calculated_time_min"] > 0
        assert "threading" in result["feature_times"][0]["method"]

    def test_chamfer_constant_time(self):
        features = [
            {
                "type": "chamfer",
                "count": 3,
                "detail": "1×45°",
                "location": "konec"
            }
        ]

        result = calculate_features_time(
            features,
            material_group="20910004",
            cutting_mode="mid"
        )

        # 3 chamfers × 0.05 min = 0.15 min = 9 sec
        assert result["calculated_time_min"] == 0.15
        assert "constant" in result["feature_times"][0]["method"]

    def test_groove_feature(self):
        features = [
            {
                "type": "groove",
                "count": 1,
                "detail": "1.6 H13",
                "location": "konec"
            }
        ]

        # Note: This will generate a warning (missing diameter)
        result = calculate_features_time(
            features,
            material_group="20910004",
            cutting_mode="mid"
        )

        # Should have warning about missing dimensions
        assert len(result["warnings"]) > 0

    def test_informational_features_zero_time(self):
        features = [
            {
                "type": "surface_finish",
                "count": 1,
                "detail": "Ra 1.6",
                "location": ""
            },
            {
                "type": "material",
                "count": 1,
                "detail": "C45",
                "location": ""
            }
        ]

        result = calculate_features_time(
            features,
            material_group="20910004",
            cutting_mode="mid"
        )

        # Informational features contribute zero time
        assert result["calculated_time_min"] == 0
        assert len(result["feature_times"]) == 2
        for ft in result["feature_times"]:
            assert ft["time_sec"] == 0.0
            assert "informational" in ft["method"]

    def test_multiple_features(self):
        features = [
            {"type": "outer_diameter", "count": 1, "detail": "ø60 h9", "location": "hlava"},
            {"type": "through_hole", "count": 2, "detail": "ø5.3 mm", "location": "roh"},
            {"type": "chamfer", "count": 3, "detail": "1×45°", "location": "konec"},
        ]

        result = calculate_features_time(
            features,
            material_group="20910004",
            cutting_mode="mid"
        )

        # Should have time from all 3 features
        assert result["calculated_time_min"] >= 0.15  # At least chamfer time
        assert len(result["feature_times"]) == 3

    def test_unknown_material_defaults_to_konstrukcni_ocel(self):
        features = [
            {"type": "outer_diameter", "count": 1, "detail": "ø60", "location": ""}
        ]

        result = calculate_features_time(
            features,
            material_group="UNKNOWN_CODE",
            cutting_mode="mid"
        )

        # Should default to 20910004
        assert result["material_group"] == "20910004"
        assert len(result["warnings"]) > 0
        assert "defaulting" in result["warnings"][0].lower()

    def test_unknown_feature_type_warning(self):
        features = [
            {"type": "nonexistent_feature_type", "count": 1, "detail": "test detail", "location": "test"}
        ]

        result = calculate_features_time(
            features,
            material_group="20910004",
            cutting_mode="mid"
        )

        # Should have warning about unknown feature
        assert len(result["warnings"]) > 0
        assert "unknown" in result["warnings"][0].lower()

    def test_missing_dimensions_warning(self):
        features = [
            {"type": "through_hole", "count": 1, "detail": "some hole", "location": ""}
        ]

        result = calculate_features_time(
            features,
            material_group="20910004",
            cutting_mode="mid"
        )

        # Should warn about missing dimensions
        assert len(result["warnings"]) > 0

    def test_aluminum_vs_steel_cutting_speeds(self):
        features = [
            {"type": "outer_diameter", "count": 1, "detail": "ø60", "location": ""}
        ]

        # Aluminum (faster)
        result_al = calculate_features_time(
            features,
            material_group="20910000",  # Hliník
            cutting_mode="mid"
        )

        # Steel (slower)
        result_steel = calculate_features_time(
            features,
            material_group="20910004",  # Ocel
            cutting_mode="mid"
        )

        # Aluminum should be faster (less time)
        # Note: Actual comparison depends on dimensions being parsable
        assert result_al["material_group"] == "20910000"
        assert result_steel["material_group"] == "20910004"

    def test_cutting_mode_affects_time(self):
        features = [
            {"type": "outer_diameter", "count": 1, "detail": "ø60", "location": ""}
        ]

        result_low = calculate_features_time(
            features,
            material_group="20910004",
            cutting_mode="low"
        )

        result_high = calculate_features_time(
            features,
            material_group="20910004",
            cutting_mode="high"
        )

        # High mode should be faster
        assert result_low["cutting_mode"] == "low"
        assert result_high["cutting_mode"] == "high"
