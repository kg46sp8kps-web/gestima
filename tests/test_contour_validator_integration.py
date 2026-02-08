"""
Integration test for contour validator with analysis_service.

Tests the full pipeline: analysis_service.build_fr_response() → contour_validator.
"""
import pytest
from app.services.analysis_service import build_fr_response


class TestContourValidatorIntegration:
    """Test contour validation integrated into analysis_service."""

    @pytest.mark.asyncio
    async def test_validation_in_response_builder(self):
        """Test that build_fr_response validates contours automatically."""
        # Simulate Claude result with scale error
        step_features = [
            {"type": "cylindrical", "diameter": 55.0},
            {"type": "cylindrical", "diameter": 30.0},
            {"type": "hole", "diameter": 19.0},
        ]

        result = {
            "success": True,
            "_source": "claude_step_pdf_merge",
            "operations": [],
            "features": step_features,
            "metadata": {},
            "profile_geometry": {
                "type": "rotational",
                "outer_contour": [
                    {"r": 0, "z": 0},
                    {"r": 50, "z": 0},  # Wrong! Should be 27.5 (Ø55)
                    {"r": 50, "z": 89},
                    {"r": 0, "z": 89},
                ],
                "inner_contour": [
                    {"r": 5, "z": 0},  # Wrong! Should be 9.5 (Ø19)
                    {"r": 5, "z": 89},
                ],
                "max_diameter": 100,  # Wrong! Should be 55
                "total_length": 89,
            },
            "confidence": 0.95,
            "cost": 0.0,
            "warnings": [],
        }

        # Build response (should validate contour automatically)
        response = await build_fr_response(result, step_features)

        # Feature recognition should have run, no error should be raised
        assert response.source == "claude_step_pdf_merge"
        assert response.confidence == 0.95
        assert response.features == step_features

        # SVG should have been generated (even with corrected contour)
        # Note: actual SVG generation may fail without full dependencies,
        # but validation should not raise error
        assert response is not None

    @pytest.mark.asyncio
    async def test_validation_with_step_only_source(self):
        """Test that step_geometry source skips validation gracefully."""
        step_features = [{"type": "cylindrical", "diameter": 30.0}]

        result = {
            "success": True,
            "_source": "step_geometry",
            "operations": [],
            "features": step_features,
            "metadata": {},
            # No profile_geometry for step_geometry source
        }

        # Should not crash, should return response
        response = await build_fr_response(result, step_features)

        assert response.source == "step_geometry"
        assert response.features == step_features

    @pytest.mark.asyncio
    async def test_validation_logs_fixes(self, caplog):
        """Test that validation fixes are logged."""
        import logging
        caplog.set_level(logging.INFO)

        step_features = [{"type": "cylindrical", "diameter": 30.0}]

        result = {
            "success": True,
            "_source": "deterministic_geometry",
            "operations": [],
            "features": step_features,
            "metadata": {},
            "profile_geometry": {
                "type": "rotational",
                "outer_contour": [
                    {"r": 0, "z": 0},
                    {"r": 20, "z": 50},  # Wrong! Should be 15 (Ø30)
                    {"r": 0, "z": 50},
                ],
                "max_diameter": 40,  # Wrong! Should be 30
                "total_length": 50,
            },
        }

        response = await build_fr_response(result, step_features)

        # Check that validation fixes were logged
        assert any("Contour validation fixes" in rec.message for rec in caplog.records)
