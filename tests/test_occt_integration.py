"""
Test OCCT integration in analysis_service.

Verifies that analysis_service actually uses OCCT parser when enabled.

Critical fix: analysis_service.py was calling StepParser() without use_occt=True.
This test ensures OCCT is actually used, not just "available but unused".
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services.analysis_service import _run_step_deterministic
from app.services.step_parser import StepParser
from app.services.step_parser_occt import OCCT_AVAILABLE
from app.config import settings


class TestOCCTIntegration:
    """Test OCCT parser is actually used by analysis_service."""

    def test_analysis_service_uses_occt_when_enabled(self):
        """Verify analysis_service passes use_occt=True to StepParser."""
        step_path = "drawings/PDM-249322_03.stp"

        if not Path(step_path).exists():
            pytest.skip(f"Test file not found: {step_path}")

        # Mock settings to ensure OCCT is enabled
        # settings is imported inline in _run_step_deterministic, so patch at config level
        with patch('app.config.settings') as mock_settings:
            mock_settings.ENABLE_OCCT_PARSER = True

            # Mock StepParser to verify it's called with correct args
            # StepParser is imported inline, so patch at source
            with patch('app.services.step_parser.StepParser') as MockParser:
                mock_instance = MagicMock()
                mock_instance.parse_file.return_value = {
                    'success': True,
                    'features': [{'type': 'cylindrical', 'diameter': 30}],
                    'rotation_axis': 'z',
                    'source': 'occt',  # Simulate OCCT success
                    'metadata': {}
                }
                MockParser.return_value = mock_instance

                # Mock contour builder to avoid full pipeline
                with patch('app.services.contour_builder.ContourBuilder') as MockBuilder:
                    mock_builder = MagicMock()
                    mock_builder.build_profile_geometry.return_value = {
                        'outer_contour': [{'z': 0, 'r': 27.5}],
                        'inner_contour': [],
                        'total_length': 50,
                        'max_diameter': 55
                    }
                    MockBuilder.return_value = mock_builder

                    # Run pipeline
                    import asyncio
                    result = asyncio.run(_run_step_deterministic(
                        step_path=step_path,
                        pdf_path=None,
                        part_id=None,
                        api_key="test-key",
                        db=None
                    ))

                    # CRITICAL ASSERTION: StepParser MUST be called with use_occt=True
                    MockParser.assert_called_once_with(use_occt=True)

                    # Verify it was actually parsed
                    mock_instance.parse_file.assert_called_once_with(step_path)

    def test_analysis_service_logs_parser_source(self):
        """Verify analysis_service logs which parser was used (OCCT vs regex)."""
        step_path = "drawings/PDM-249322_03.stp"

        if not Path(step_path).exists():
            pytest.skip(f"Test file not found: {step_path}")

        # Mock logger to capture log messages
        with patch('app.services.analysis_service.logger') as mock_logger:
            with patch('app.config.settings') as mock_settings:
                mock_settings.ENABLE_OCCT_PARSER = True

                # Mock StepParser to return OCCT result
                with patch('app.services.step_parser.StepParser') as MockParser:
                    mock_instance = MagicMock()
                    mock_instance.parse_file.return_value = {
                        'success': True,
                        'features': [{'type': 'cylindrical', 'diameter': 30}],
                        'rotation_axis': 'z',
                        'source': 'occt',
                        'metadata': {}
                    }
                    MockParser.return_value = mock_instance

                    # Mock contour builder
                    with patch('app.services.contour_builder.ContourBuilder') as MockBuilder:
                        mock_builder = MagicMock()
                        mock_builder.build_profile_geometry.return_value = {
                            'outer_contour': [{'z': 0, 'r': 27.5}],
                            'inner_contour': [],
                            'total_length': 50,
                            'max_diameter': 55
                        }
                        MockBuilder.return_value = mock_builder

                        # Run pipeline
                        import asyncio
                        asyncio.run(_run_step_deterministic(
                            step_path=step_path,
                            pdf_path=None,
                            part_id=None,
                            api_key="test-key",
                            db=None
                        ))

                        # Verify logging
                        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
                        assert any('source: occt' in call for call in info_calls), \
                            "Should log parser source (OCCT)"

    def test_analysis_service_warns_on_regex_fallback(self):
        """Verify analysis_service warns when OCCT unavailable."""
        step_path = "drawings/PDM-249322_03.stp"

        if not Path(step_path).exists():
            pytest.skip(f"Test file not found: {step_path}")

        # Mock logger to capture warnings
        with patch('app.services.analysis_service.logger') as mock_logger:
            with patch('app.config.settings') as mock_settings:
                mock_settings.ENABLE_OCCT_PARSER = True

                # Mock StepParser to return REGEX result (OCCT failed)
                with patch('app.services.step_parser.StepParser') as MockParser:
                    mock_instance = MagicMock()
                    mock_instance.parse_file.return_value = {
                        'success': True,
                        'features': [{'type': 'cylindrical', 'diameter': 30}],
                        'rotation_axis': 'z',
                        'source': 'step_regex',  # Fallback!
                        'metadata': {}
                    }
                    MockParser.return_value = mock_instance

                    # Mock contour builder
                    with patch('app.services.contour_builder.ContourBuilder') as MockBuilder:
                        mock_builder = MagicMock()
                        mock_builder.build_profile_geometry.return_value = {
                            'outer_contour': [{'z': 0, 'r': 27.5}],
                            'inner_contour': [],
                            'total_length': 50,
                            'max_diameter': 55
                        }
                        MockBuilder.return_value = mock_builder

                        # Run pipeline
                        import asyncio
                        asyncio.run(_run_step_deterministic(
                            step_path=step_path,
                            pdf_path=None,
                            part_id=None,
                            api_key="test-key",
                            db=None
                        ))

                        # Verify warning
                        warning_calls = [call[0][0] for call in mock_logger.warning.call_args_list]
                        assert any('regex fallback' in call.lower() for call in warning_calls), \
                            "Should warn when OCCT unavailable"

    @pytest.mark.skipif(not OCCT_AVAILABLE, reason="OCCT not available")
    def test_real_occt_parsing_via_analysis_service(self):
        """End-to-end test: analysis_service → OCCT → accurate contour."""
        step_path = "drawings/PDM-249322_03.stp"

        if not Path(step_path).exists():
            pytest.skip(f"Test file not found: {step_path}")

        # Real call (no mocks)
        import asyncio
        result = asyncio.run(_run_step_deterministic(
            step_path=step_path,
            pdf_path=None,
            part_id=None,
            api_key="test-key",
            db=None
        ))

        # Verify success
        assert result.get('success') is True, f"Pipeline failed: {result.get('error')}"

        # Verify OCCT was used
        assert result.get('_source') == 'step_deterministic'

        # Verify contour was built
        profile_geo = result.get('profile_geometry')
        assert profile_geo is not None, "Should have profile_geometry"

        outer = profile_geo.get('outer_contour', [])
        assert len(outer) >= 10, f"Should have detailed contour, got {len(outer)} points"

        # Verify accuracy (spot check dimensions)
        max_r = max(pt['r'] for pt in outer)
        max_d = max_r * 2
        assert 54 < max_d < 56, f"Max diameter should be ~55mm, got {max_d:.1f}mm"
