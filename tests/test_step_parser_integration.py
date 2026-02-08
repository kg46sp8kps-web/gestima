"""
Integration tests for OCCT and regex parser compatibility.

Tests the hybrid fallback mechanism and consistency between parsers.

ADR-039: OCCT Integration
"""

import pytest
from pathlib import Path
import time

from app.services.step_parser import StepParser


class TestParserIntegration:
    """Test OCCT/regex parser integration."""

    def test_pdm_249322_both_parsers(self):
        """Parse PDM-249322 with both OCCT (fallback) and regex for comparison."""
        step_path = "drawings/PDM-249322_03.stp"

        if not Path(step_path).exists():
            pytest.skip(f"Test file not found: {step_path}")

        # Parse with fallback (tries OCCT, uses regex)
        parser_fallback = StepParser(use_occt=True)
        result_fallback = parser_fallback.parse_file(step_path)

        # Parse with regex only
        parser_regex = StepParser(use_occt=False)
        result_regex = parser_regex.parse_file(step_path)

        # Both should succeed
        assert result_fallback.get('success') is True, f"Fallback failed: {result_fallback.get('error')}"
        assert result_regex.get('success') is True, f"Regex failed: {result_regex.get('error')}"

        # Fallback should use regex (since OCCT not installed)
        assert result_fallback.get('source') == 'step_regex', "Should fallback to regex"

        # Same top-level structure
        assert set(result_fallback.keys()) == set(result_regex.keys())

        # Features should be similar (allow ±1 difference)
        feat_fallback = len(result_fallback.get('features', []))
        feat_regex = len(result_regex.get('features', []))
        assert abs(feat_fallback - feat_regex) <= 1, \
            f"Feature count differs: fallback={feat_fallback}, regex={feat_regex}"

    def test_occt_fallback_graceful(self):
        """Test that parser gracefully falls back to regex on OCCT failure."""
        step_path = "drawings/PDM-249322_03.stp"

        if not Path(step_path).exists():
            pytest.skip(f"Test file not found: {step_path}")

        # Parser with OCCT enabled should fallback gracefully
        parser = StepParser(use_occt=True)

        # Measure fallback behavior
        result = parser.parse_file(step_path)

        # Should always succeed (fallback works)
        assert result.get('success') is True
        assert result.get('source') in ('occt', 'step_regex')

        # Features should be present
        features = result.get('features', [])
        assert len(features) > 0, "Parser should detect features"

        # Metadata structure present
        metadata = result.get('metadata', {})
        assert isinstance(metadata, dict)

    def test_hybrid_mode_performance(self):
        """Test parser performance (fallback should be < 1s for PDM file)."""
        step_path = "drawings/PDM-249322_03.stp"

        if not Path(step_path).exists():
            pytest.skip(f"Test file not found: {step_path}")

        parser = StepParser(use_occt=True)

        start = time.time()
        result = parser.parse_file(step_path)
        elapsed = time.time() - start

        # Should be reasonably fast (regex parser is fast)
        assert elapsed < 1.0, f"Parser took {elapsed:.2f}s, should be < 1.0s"

        # Result should be valid
        assert result.get('success') is True

    def test_three_stp_files(self):
        """Test parser on multiple STEP files for consistency."""
        step_files = [
            "drawings/PDM-249322_03.stp",
            "drawings/10700212_20260204_205737_A.stp",
            "drawings/10316500_20260205_210328_A.stp",
        ]

        parser = StepParser(use_occt=True)

        for step_path in step_files:
            if not Path(step_path).exists():
                pytest.skip(f"Test file not found: {step_path}")

            result = parser.parse_file(step_path)

            # All should parse successfully
            assert result.get('success') is True, \
                f"{step_path}: {result.get('error')}"

            # All should return consistent structure
            assert result.get('format') == 'step'
            assert 'features' in result
            assert 'metadata' in result
            assert 'confidence' in result

            # All should identify source
            assert result.get('source') in ('occt', 'step_regex')

    def test_feature_compatibility(self):
        """Test that features from both parsers are compatible format."""
        step_path = "drawings/PDM-249322_03.stp"

        if not Path(step_path).exists():
            pytest.skip(f"Test file not found: {step_path}")

        parser = StepParser(use_occt=True)
        result = parser.parse_file(step_path)

        features = result.get('features', [])
        assert len(features) > 0

        # Check each feature has required fields
        for feature in features:
            assert 'type' in feature, f"Feature missing 'type': {feature}"
            assert 'confidence' in feature, f"Feature missing 'confidence': {feature}"

            feature_type = feature.get('type')

            # Type-specific validation
            if feature_type == 'cylindrical':
                assert 'diameter' in feature or 'radius' in feature
                if 'diameter' in feature:
                    assert feature['diameter'] > 0
                if 'radius' in feature:
                    assert feature['radius'] > 0

            elif feature_type == 'cone':
                assert 'angle' in feature
                angle = feature.get('angle')
                # Angle in degrees (0-90)
                assert 0 < angle < 90, f"Cone angle out of range: {angle}"

            elif feature_type == 'radius':
                assert 'radius' in feature or 'minor_radius' in feature
                if 'radius' in feature:
                    assert feature['radius'] > 0

    def test_metadata_consistency(self):
        """Test that metadata is consistent across parsers."""
        step_path = "drawings/PDM-249322_03.stp"

        if not Path(step_path).exists():
            pytest.skip(f"Test file not found: {step_path}")

        parser_fallback = StepParser(use_occt=True)
        parser_regex = StepParser(use_occt=False)

        result_fallback = parser_fallback.parse_file(step_path)
        result_regex = parser_regex.parse_file(step_path)

        metadata_fallback = result_fallback.get('metadata', {})
        metadata_regex = result_regex.get('metadata', {})

        # Both should have metadata dict
        assert isinstance(metadata_fallback, dict)
        assert isinstance(metadata_regex, dict)

        # If bounding box present, should have required fields
        if 'bounding_box' in metadata_fallback:
            bbox = metadata_fallback['bounding_box']
            assert 'x_min' in bbox and 'x_max' in bbox
            assert 'y_min' in bbox and 'y_max' in bbox
            assert 'z_min' in bbox and 'z_max' in bbox

        if 'bounding_box' in metadata_regex:
            bbox = metadata_regex['bounding_box']
            assert 'x_min' in bbox and 'x_max' in bbox
            assert 'y_min' in bbox and 'y_max' in bbox
            assert 'z_min' in bbox and 'z_max' in bbox


class TestParserErrorHandling:
    """Test parser error handling and edge cases."""

    def test_nonexistent_file(self):
        """Test parser gracefully handles missing files."""
        parser = StepParser(use_occt=True)
        result = parser.parse_file("drawings/nonexistent_file_12345.stp")

        # Should fail gracefully
        assert result.get('success') is False
        assert 'error' in result

    def test_corrupt_step_file(self):
        """Test parser gracefully handles corrupt STEP files."""
        parser = StepParser(use_occt=True)

        # Create corrupt file
        corrupt_path = '/tmp/test_corrupt_parser.step'
        with open(corrupt_path, 'w') as f:
            f.write("INVALID STEP FILE\n")
            f.write("NOT A VALID STEP FORMAT\n")

        result = parser.parse_file(corrupt_path)

        # Should either fail gracefully or fallback to regex
        # (regex may partially parse even corrupt files)
        assert 'success' in result
        assert 'error' in result or result.get('success') is True

    def test_empty_step_file(self):
        """Test parser handles empty STEP files."""
        parser = StepParser(use_occt=True)

        # Create empty file
        empty_path = '/tmp/test_empty_parser.step'
        with open(empty_path, 'w') as f:
            pass

        result = parser.parse_file(empty_path)

        # Should handle gracefully
        assert 'success' in result
        if result.get('success'):
            features = result.get('features', [])
            assert isinstance(features, list)
        else:
            assert 'error' in result

    def test_parser_state_isolation(self):
        """Test that parser instances don't interfere with each other."""
        step_path = "drawings/PDM-249322_03.stp"

        if not Path(step_path).exists():
            pytest.skip(f"Test file not found: {step_path}")

        # Create two parsers and use them alternately
        parser1 = StepParser(use_occt=True)
        parser2 = StepParser(use_occt=False)

        result1a = parser1.parse_file(step_path)
        result2a = parser2.parse_file(step_path)
        result1b = parser1.parse_file(step_path)

        # Results should be consistent
        feat_1a = len(result1a.get('features', []))
        feat_2a = len(result2a.get('features', []))
        feat_1b = len(result1b.get('features', []))

        assert feat_1a == feat_1b, "Parser1 results should be consistent"
        assert abs(feat_1a - feat_2a) <= 1, "Parsers should return similar results"
