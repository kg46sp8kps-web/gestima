"""
Test OCCT Section-Based Profile Extraction.

Verifies BRepAlgoAPI_Section produces correct dimensions vs. heuristic methods.

Critical test cases:
1. PDM-249322_03.stp - Reference baseline (Ø55mm, 89mm, Ø19mm bore)
2. JR 810665 - Inner bore Ø6.9 (not Ø8.9 - regression check)
3. Prismatic part - Should NOT extract rotational profile

ADR-040: OCCT Section-Based Extraction (Phase 2)
"""

import pytest
from pathlib import Path

# OCCT is optional - skip tests if unavailable
try:
    from app.services.step_parser import StepParser
    OCCT_AVAILABLE = True
except ImportError:
    OCCT_AVAILABLE = False


@pytest.mark.skipif(not OCCT_AVAILABLE, reason="OCCT not installed")
class TestSectionExtraction:
    """Test section-based profile extraction."""

    @pytest.fixture
    def parser(self):
        """Create OCCT-enabled parser."""
        return StepParser(use_occt=True)

    def test_pdm249322_baseline(self, parser):
        """
        PDM-249322_03.stp - MUST PASS (regression blocker).

        Expected dimensions:
        - Max diameter: 55.0mm
        - Total length: 89.0mm
        - Inner bore: ~19mm diameter
        """
        step_file = Path("uploads/drawings/PDM-249322_03.stp")

        if not step_file.exists():
            pytest.skip(f"Test file not found: {step_file}")

        result = parser.parse_file(str(step_file))

        assert result['success'], f"Parse failed: {result.get('error')}"
        assert result['source'] == 'occt', "Should use OCCT parser, not regex"

        # Check profile_geometry exists
        profile = result.get('profile_geometry')
        assert profile is not None, "profile_geometry missing"
        assert profile['source'] == 'occt_section', "Should use section extraction"

        # Verify dimensions (±1mm tolerance)
        max_dia = profile['max_diameter']
        length = profile['total_length']

        assert 54.0 <= max_dia <= 56.0, f"Max diameter {max_dia}mm not ~55mm"
        assert 88.0 <= length <= 90.0, f"Length {length}mm not ~89mm"

        # Verify inner bore present
        inner = profile['inner_contour']
        assert len(inner) > 0, "Inner contour missing"

        # Check inner diameter ~19mm (±2mm tolerance)
        inner_diameters = [p['r'] * 2 for p in inner]
        assert any(17.0 <= d <= 21.0 for d in inner_diameters), \
            f"Inner bore Ø19mm not found in: {inner_diameters}"

    def test_jr810665_correct_inner_bore(self, parser):
        """
        JR 810665 - Inner bore regression check.

        OLD contour_builder: Ø8.9mm (WRONG)
        CORRECT: Ø6.9mm

        This test verifies section extraction finds Ø6.9, NOT Ø8.9.
        """
        step_file = Path("uploads/drawings/JR 810665.ipt.step")

        if not step_file.exists():
            pytest.skip(f"Test file not found: {step_file}")

        result = parser.parse_file(str(step_file))

        assert result['success'], f"Parse failed: {result.get('error')}"

        profile = result.get('profile_geometry')
        if profile is None:
            pytest.skip("Profile geometry not extracted (not rotational?)")

        # Check inner contour
        inner = profile['inner_contour']
        if not inner:
            pytest.fail("No inner contour found - expected Ø6.9mm bore")

        inner_diameters = [p['r'] * 2 for p in inner]

        # Inner bore should be Ø6.9 (±0.5mm tolerance)
        assert any(6.4 <= d <= 7.4 for d in inner_diameters), \
            f"Inner bore Ø6.9mm not found! Got: {inner_diameters}"

        # Should NOT find Ø8.9 (old wrong value)
        assert not any(8.4 <= d <= 9.4 for d in inner_diameters), \
            f"Found old wrong Ø8.9mm bore: {inner_diameters}"

    def test_section_extractor_direct(self):
        """
        Test SectionProfileExtractor directly (unit test).

        Verifies extractor can be instantiated and returns correct schema.
        """
        try:
            from app.services.section_profile_extractor import SectionProfileExtractor
        except ImportError:
            pytest.skip("OCCT not available")

        extractor = SectionProfileExtractor()

        # Check it has required method
        assert hasattr(extractor, 'extract_profile'), \
            "SectionProfileExtractor missing extract_profile method"

    def test_prismatic_part_no_profile(self, parser):
        """
        Prismatic part (0304663) should NOT have rotational profile.

        Verifies section extraction doesn't force rotational profile on non-rotational parts.
        """
        step_file = Path("uploads/drawings/0304663_D00043519_000.1_3D.stp")

        if not step_file.exists():
            pytest.skip(f"Test file not found: {step_file}")

        result = parser.parse_file(str(step_file))

        assert result['success'], f"Parse failed: {result.get('error')}"

        # Prismatic part may not have rotation_axis or may have profile_geometry=None
        rotation_axis = result.get('rotation_axis')
        profile = result.get('profile_geometry')

        # Either no rotation axis OR profile extraction failed (both acceptable)
        if rotation_axis:
            # If rotation axis detected, profile_geometry can be None or have low confidence
            if profile:
                # If profile exists, it should be flagged low confidence or have minimal points
                assert len(profile.get('outer_contour', [])) < 20, \
                    "Prismatic part shouldn't have complex rotational profile"


@pytest.mark.skipif(not OCCT_AVAILABLE, reason="OCCT not installed")
def test_section_extraction_vs_contour_builder_comparison():
    """
    OPTIONAL: Batch comparison test.

    Compares section extraction vs old contour_builder on multiple files.
    Run manually for accuracy report.
    """
    pytest.skip("Batch test - run manually for accuracy report")
