"""
Test OCCT-based STEP parser.

Tests both OCCT parsing and hybrid fallback mechanism.

ADR-039: OCCT Integration
"""

import pytest
from pathlib import Path

from app.services.step_parser import StepParser
from app.services.step_parser_occt import OCCT_AVAILABLE


class TestOCCTParser:
    """Test OCCT parser functionality."""

    @pytest.mark.skipif(not OCCT_AVAILABLE, reason="OCCT not available - install pythonocc-core")
    def test_occt_import_available(self):
        """Verify OCCT is importable."""
        assert OCCT_AVAILABLE, "OCCT should be available (pythonocc-core installed)"

    def test_parse_rotational_part(self):
        """Parse rotational part and verify features."""
        parser = StepParser(use_occt=True)
        step_path = "drawings/PDM-249322_03.stp"

        if not Path(step_path).exists():
            pytest.skip(f"Test file not found: {step_path}")

        result = parser.parse_file(step_path)

        # Basic structure
        assert result.get('success') is True, f"Parsing failed: {result.get('error')}"
        assert result.get('format') == 'step'
        assert result.get('confidence') == 1.0

        # Features
        features = result.get('features', [])
        assert len(features) >= 5, "Should detect at least 5 features"

        # Rotation axis
        assert result.get('rotation_axis') in ('x', 'y', 'z'), "Should detect rotation axis"

        # Source (OCCT or regex fallback)
        assert result.get('source') in ('occt', 'step_regex'), "Should identify parser source"

    def test_volume_calculation(self):
        """Test accurate volume calculation (OCCT feature)."""
        parser = StepParser(use_occt=True)
        step_path = "drawings/PDM-249322_03.stp"

        if not Path(step_path).exists():
            pytest.skip(f"Test file not found: {step_path}")

        result = parser.parse_file(step_path)

        if result.get('source') == 'occt':
            # OCCT should provide volume
            metadata = result.get('metadata', {})
            volume = metadata.get('volume_cm3')

            assert volume is not None, "OCCT should calculate volume"
            assert volume > 0, "Volume should be positive"
            assert 40 < volume < 50, f"Volume should be ~43cm³, got {volume}"

    def test_bounding_box(self):
        """Test bounding box extraction (OCCT feature)."""
        parser = StepParser(use_occt=True)
        step_path = "drawings/PDM-249322_03.stp"

        if not Path(step_path).exists():
            pytest.skip(f"Test file not found: {step_path}")

        result = parser.parse_file(step_path)

        if result.get('source') == 'occt':
            metadata = result.get('metadata', {})
            bbox = metadata.get('bounding_box')

            assert bbox is not None, "OCCT should provide bounding box"
            assert 'height' in bbox
            assert 'width' in bbox
            assert bbox['height'] > 0
            assert bbox['width'] > 0

    def test_fallback_to_regex(self):
        """Test fallback to regex parser on OCCT failure."""
        parser = StepParser(use_occt=True)

        # Corrupt STEP file
        with open('/tmp/test_corrupt.step', 'w') as f:
            f.write("INVALID STEP FILE CONTENT\n")

        result = parser.parse_file('/tmp/test_corrupt.step')

        # Should either succeed with regex or fail gracefully
        if result.get('success'):
            # Regex parser handled it
            assert result.get('source') in ('step_regex', 'occt')
        else:
            # Both parsers failed - should report error
            assert 'error' in result

    def test_occt_disabled(self):
        """Test parser with OCCT explicitly disabled."""
        parser = StepParser(use_occt=False)
        step_path = "drawings/PDM-249322_03.stp"

        if not Path(step_path).exists():
            pytest.skip(f"Test file not found: {step_path}")

        result = parser.parse_file(step_path)

        # Should use regex parser
        assert result.get('success') is True
        assert result.get('source') == 'step_regex'
        assert parser.occt_parser is None

    def test_feature_deduplication(self):
        """Verify features are deduplicated."""
        parser = StepParser(use_occt=True)
        step_path = "drawings/PDM-249322_03.stp"

        if not Path(step_path).exists():
            pytest.skip(f"Test file not found: {step_path}")

        result = parser.parse_file(step_path)
        features = result.get('features', [])

        # Check for duplicates manually
        keys = []
        for f in features:
            key = (
                f.get('type'),
                round(f.get('diameter', 0), 2),
                round(f.get('angle', 0), 1),
                round(f.get('radius', 0), 2)
            )
            keys.append(key)

        assert len(keys) == len(set(keys)), "Features should be deduplicated"

    def test_cylindrical_feature_format(self):
        """Verify cylindrical features match expected format."""
        parser = StepParser(use_occt=True)
        step_path = "drawings/PDM-249322_03.stp"

        if not Path(step_path).exists():
            pytest.skip(f"Test file not found: {step_path}")

        result = parser.parse_file(step_path)
        features = result.get('features', [])

        cylinders = [f for f in features if f.get('type') == 'cylindrical']
        assert len(cylinders) > 0, "Should detect cylindrical surfaces"

        for cyl in cylinders:
            # Required fields
            assert 'diameter' in cyl
            assert 'radius' in cyl
            assert 'confidence' in cyl

            # Consistency
            assert abs(cyl['diameter'] - cyl['radius'] * 2) < 0.01

    def test_conical_feature_format(self):
        """Verify conical features match expected format and angle units."""
        parser = StepParser(use_occt=True)
        step_path = "drawings/PDM-249322_03.stp"

        if not Path(step_path).exists():
            pytest.skip(f"Test file not found: {step_path}")

        result = parser.parse_file(step_path)
        features = result.get('features', [])

        cones = [f for f in features if f.get('type') == 'cone']
        assert len(cones) > 0, "Should detect conical surfaces"

        for cone in cones:
            # Required fields
            assert 'angle' in cone
            assert 'confidence' in cone

            # Angle should be in degrees (not radians!)
            angle = cone['angle']
            assert 0 < angle < 90, f"Cone angle should be in degrees (0-90), got {angle}"

    def test_toroidal_feature_format(self):
        """Verify toroidal features match expected format."""
        parser = StepParser(use_occt=True)
        step_path = "drawings/PDM-249322_03.stp"

        if not Path(step_path).exists():
            pytest.skip(f"Test file not found: {step_path}")

        result = parser.parse_file(step_path)
        features = result.get('features', [])

        toruses = [f for f in features if f.get('type') == 'radius']

        if len(toruses) > 0:
            for torus in toruses:
                # Required fields
                assert 'radius' in torus
                assert 'major_radius' in torus
                assert 'minor_radius' in torus
                assert 'confidence' in torus

                # Consistency
                assert torus['radius'] == torus['minor_radius']


class TestHybridIntegration:
    """Test hybrid OCCT/regex integration."""

    def test_config_flag_respected(self):
        """Verify ENABLE_OCCT_PARSER config flag is respected."""
        from app.config import settings

        # Test with config value
        parser = StepParser(use_occt=settings.ENABLE_OCCT_PARSER)

        if settings.ENABLE_OCCT_PARSER:
            # Should try to load OCCT
            # (may fail if not installed, that's OK - fallback works)
            pass
        else:
            # Should NOT load OCCT
            assert parser.occt_parser is None

    def test_parser_compatibility(self):
        """Verify OCCT and regex parsers return compatible formats."""
        step_path = "drawings/PDM-249322_03.stp"

        if not Path(step_path).exists():
            pytest.skip(f"Test file not found: {step_path}")

        # Parse with both
        parser_occt = StepParser(use_occt=True)
        parser_regex = StepParser(use_occt=False)

        result_occt = parser_occt.parse_file(step_path)
        result_regex = parser_regex.parse_file(step_path)

        # Both should succeed
        assert result_occt.get('success') is True
        assert result_regex.get('success') is True

        # Same top-level keys
        assert set(result_occt.keys()) == set(result_regex.keys())

        # Features should be similar (allow ±2 difference)
        feat_occt = len(result_occt.get('features', []))
        feat_regex = len(result_regex.get('features', []))
        assert abs(feat_occt - feat_regex) <= 2, \
            f"Feature count should be similar: OCCT={feat_occt}, regex={feat_regex}"
