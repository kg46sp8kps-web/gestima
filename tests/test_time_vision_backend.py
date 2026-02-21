"""Tests for TimeVision backend implementation"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.models.time_vision import (
    TimeVisionEstimation,
    VisionExtractionResult,
    TimeEstimationResult,
    OperationBreakdown,
    FeatureItem,
    FeaturesExtractionResult,
    TimeVisionResponse,
    TimeVisionListItem,
)


class TestTimeVisionModels:
    """Test TimeVision Pydantic models validation (L-009 compliance)."""

    def test_vision_extraction_validation(self):
        """Test VisionExtractionResult Field() validation."""
        # Valid data
        data = VisionExtractionResult(
            part_type="ROT",
            complexity="medium",
            max_diameter_mm=80.0,
            max_length_mm=200.0,
            manufacturing_description="Test description with sufficient length",
            operations=["soustružení", "vrtání"],
            requires_grinding=False,
        )
        assert data.part_type == "ROT"
        assert data.complexity == "medium"
        assert len(data.operations) == 2

        # Invalid: manufacturing_description too short
        with pytest.raises(ValueError):
            VisionExtractionResult(
                part_type="ROT",
                complexity="medium",
                manufacturing_description="Short",
                operations=["soustružení"],
                requires_grinding=False,
            )

        # Invalid: operations empty list
        with pytest.raises(ValueError):
            VisionExtractionResult(
                part_type="ROT",
                complexity="medium",
                manufacturing_description="Test description with sufficient length",
                operations=[],
                requires_grinding=False,
            )

        # Invalid: max_diameter negative
        with pytest.raises(ValueError):
            VisionExtractionResult(
                part_type="ROT",
                complexity="medium",
                max_diameter_mm=-10.0,
                manufacturing_description="Test description with sufficient length",
                operations=["soustružení"],
                requires_grinding=False,
            )

    def test_operation_breakdown_validation(self):
        """Test OperationBreakdown Field() validation."""
        # Valid data
        op = OperationBreakdown(
            operation="soustružení",
            time_min=25.0,
            notes="Test notes",
        )
        assert op.operation == "soustružení"
        assert op.time_min == 25.0

        # Invalid: negative time
        with pytest.raises(ValueError):
            OperationBreakdown(
                operation="soustružení",
                time_min=-5.0,
                notes="Test",
            )

        # Invalid: empty operation
        with pytest.raises(ValueError):
            OperationBreakdown(
                operation="",
                time_min=25.0,
            )

    def test_time_estimation_validation(self):
        """Test TimeEstimationResult Field() validation."""
        # Valid data
        estimation = TimeEstimationResult(
            estimated_time_min=45.0,
            confidence="medium",
            reasoning="Test reasoning with sufficient length",
            breakdown=[
                OperationBreakdown(operation="soustružení", time_min=25.0, notes="Test 1"),
                OperationBreakdown(operation="vrtání", time_min=20.0, notes="Test 2"),
            ],
        )
        assert estimation.estimated_time_min == 45.0
        assert estimation.confidence == "medium"
        assert len(estimation.breakdown) == 2

        # Invalid: estimated_time_min zero
        with pytest.raises(ValueError):
            TimeEstimationResult(
                estimated_time_min=0.0,
                confidence="medium",
                reasoning="Test reasoning",
                breakdown=[OperationBreakdown(operation="test", time_min=10.0)],
            )

        # Invalid: breakdown empty
        with pytest.raises(ValueError):
            TimeEstimationResult(
                estimated_time_min=45.0,
                confidence="medium",
                reasoning="Test reasoning",
                breakdown=[],
            )


@pytest.mark.asyncio
class TestTimeVisionIntegration:
    """Integration tests (database required)."""

    async def test_database_model_creation(self, db_session):
        """Test creating TimeVisionEstimation in database (L-008 compliance)."""
        from datetime import datetime

        estimation = TimeVisionEstimation(
            pdf_filename="test.pdf",
            pdf_path="/tmp/test.pdf",
            part_type="ROT",
            complexity="medium",
            status="estimated",
            estimated_time_min=45.0,
            confidence="medium",
        )
        db_session.add(estimation)

        try:
            await db_session.commit()
            await db_session.refresh(estimation)
            assert estimation.id is not None
            assert estimation.created_at is not None
            assert estimation.version == 0
        except Exception:
            await db_session.rollback()
            raise


class TestCalibrationUpdate:
    """Test CalibrationUpdate schema validation."""

    def test_calibration_update_complexity_only(self):
        """Test updating only complexity field."""
        from app.routers.time_vision_router import CalibrationUpdate

        # Valid: only complexity
        data = CalibrationUpdate(
            complexity="complex",
            version=0,
        )
        assert data.complexity == "complex"
        assert data.actual_time_min is None
        assert data.actual_notes is None

    def test_calibration_update_actual_time_only(self):
        """Test updating only actual time field."""
        from app.routers.time_vision_router import CalibrationUpdate

        # Valid: only actual time
        data = CalibrationUpdate(
            actual_time_min=35.5,
            version=0,
        )
        assert data.complexity is None
        assert data.actual_time_min == 35.5
        assert data.actual_notes is None

    def test_calibration_update_all_fields(self):
        """Test updating all fields together."""
        from app.routers.time_vision_router import CalibrationUpdate

        # Valid: all fields
        data = CalibrationUpdate(
            part_type="ROT",
            complexity="simple",
            actual_time_min=20.0,
            actual_notes="Recalibrated after production",
            human_estimate_min=18.5,
            version=0,
        )
        assert data.part_type == "ROT"
        assert data.complexity == "simple"
        assert data.actual_time_min == 20.0
        assert data.actual_notes == "Recalibrated after production"
        assert data.human_estimate_min == 18.5

    def test_calibration_update_invalid_complexity(self):
        """Test invalid complexity value."""
        from app.routers.time_vision_router import CalibrationUpdate

        # Invalid: wrong complexity value
        with pytest.raises(ValueError):
            CalibrationUpdate(
                complexity="invalid",
                version=0,
            )

    def test_calibration_update_invalid_time(self):
        """Test invalid actual time value."""
        from app.routers.time_vision_router import CalibrationUpdate

        # Invalid: negative time
        with pytest.raises(ValueError):
            CalibrationUpdate(
                actual_time_min=-10.0,
                version=0,
            )

        # Invalid: time too large
        with pytest.raises(ValueError):
            CalibrationUpdate(
                actual_time_min=20000.0,
                version=0,
            )

    def test_calibration_update_part_type_validation(self):
        """Test part_type field validation."""
        from app.routers.time_vision_router import CalibrationUpdate

        # Valid: ROT
        data = CalibrationUpdate(
            part_type="ROT",
            version=0,
        )
        assert data.part_type == "ROT"

        # Valid: PRI
        data = CalibrationUpdate(
            part_type="PRI",
            version=0,
        )
        assert data.part_type == "PRI"

        # Valid: COMBINED
        data = CalibrationUpdate(
            part_type="COMBINED",
            version=0,
        )
        assert data.part_type == "COMBINED"

        # Invalid: wrong value
        with pytest.raises(ValueError):
            CalibrationUpdate(
                part_type="INVALID",
                version=0,
            )

    def test_calibration_update_human_estimate_validation(self):
        """Test human_estimate_min field validation."""
        from app.routers.time_vision_router import CalibrationUpdate

        # Valid: positive time
        data = CalibrationUpdate(
            human_estimate_min=45.5,
            version=0,
        )
        assert data.human_estimate_min == 45.5

        # Invalid: negative time
        with pytest.raises(ValueError):
            CalibrationUpdate(
                human_estimate_min=-5.0,
                version=0,
            )

        # Invalid: zero
        with pytest.raises(ValueError):
            CalibrationUpdate(
                human_estimate_min=0.0,
                version=0,
            )

        # Invalid: too large
        with pytest.raises(ValueError):
            CalibrationUpdate(
                human_estimate_min=15000.0,
                version=0,
            )


@pytest.mark.asyncio
class TestOpenAIVisionService:
    """Test OpenAI vision service (single-call estimation)."""

    @pytest.mark.skip(reason="Complex mocking of PyMuPDF - brittle test. Use integration tests instead.")
    async def test_pdf_to_base64_image_success(self):
        """Test PDF to base64 image conversion."""
        from app.services.openai_vision_service import _pdf_to_base64_image
        from pathlib import Path

        # Mock Path.exists() check
        with patch('app.services.openai_vision_service.Path') as mock_path_class:
            mock_path = Mock()
            mock_path.exists.return_value = True
            mock_path_class.return_value = mock_path

            # Mock PyMuPDF
            with patch('app.services.openai_vision_service.fitz') as mock_fitz:
                mock_page = Mock()
                mock_pix = Mock()
                mock_pix.tobytes.return_value = b'fake_png_data'
                mock_page.get_pixmap.return_value = mock_pix

                # Create mock document with proper magic method support
                mock_doc = Mock()
                mock_doc.__len__ = Mock(return_value=1)
                mock_doc.__getitem__ = Mock(return_value=mock_page)
                mock_fitz.open.return_value = mock_doc

                # Test successful conversion
                result = _pdf_to_base64_image("/fake/path.pdf", page_num=0, dpi=200)
                assert isinstance(result, str)
                assert len(result) > 0
                mock_doc.close.assert_called_once()

    async def test_pdf_to_base64_image_file_not_found(self):
        """Test PDF rendering with nonexistent file."""
        from app.services.openai_vision_service import _pdf_to_base64_image

        with pytest.raises(FileNotFoundError):
            _pdf_to_base64_image("/nonexistent/file.pdf")

    async def test_estimate_from_pdf_openai_success(self):
        """Test successful OpenAI estimation."""
        from app.services.openai_vision_service import estimate_from_pdf_openai

        # Mock PDF rendering
        with patch('app.services.openai_vision_service._pdf_to_base64_image') as mock_render:
            mock_render.return_value = "fake_base64_image"

            # Mock OpenAI API
            with patch('app.services.openai_vision_service.OpenAI') as mock_openai_class:
                mock_client = Mock()
                mock_response = Mock()
                mock_choice = Mock()
                mock_message = Mock()
                mock_usage = Mock()

                # Valid JSON response
                mock_message.content = '''{
                    "part_type": "ROT",
                    "complexity": "medium",
                    "material_detected": "C45",
                    "max_diameter_mm": 80.0,
                    "max_length_mm": 200.0,
                    "max_width_mm": null,
                    "max_height_mm": null,
                    "manufacturing_description": "Středně složitá hřídel s několika stupni",
                    "operations": ["soustružení", "vrtání", "závitování"],
                    "estimated_time_min": 35.5,
                    "confidence": "medium",
                    "reasoning": "ROT ø80×200mm ocel, medium. Ref: střední hřídel medium 6-15 min, dolní třetina=9min × 1.00=9.0. Díry: 2×0.3=0.6. Závity: 1×0.5=0.5. Celkem=10.1 min",
                    "breakdown": [
                        {"operation": "soustružení", "time_min": 30.0, "notes": "základ"},
                        {"operation": "vrtání", "time_min": 3.0, "notes": "2 díry"},
                        {"operation": "závitování", "time_min": 2.5, "notes": "M8"}
                    ]
                }'''
                mock_choice.message = mock_message
                mock_response.choices = [mock_choice]
                mock_usage.prompt_tokens = 500
                mock_usage.completion_tokens = 300
                mock_usage.total_tokens = 800
                mock_response.usage = mock_usage

                mock_client.chat.completions.create.return_value = mock_response
                mock_openai_class.return_value = mock_client

                # Create fake PDF
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                    pdf_path = f.name

                try:
                    # Run estimation
                    result = await estimate_from_pdf_openai(
                        pdf_path=pdf_path,
                        similar_parts=None,
                    )

                    # Verify result
                    assert result['part_type'] == 'ROT'
                    assert result['complexity'] == 'medium'
                    assert result['material_detected'] == 'C45'
                    assert result['estimated_time_min'] == 35.5
                    assert result['confidence'] == 'medium'
                    assert len(result['breakdown']) == 3
                    assert len(result['operations']) == 3
                finally:
                    import os
                    os.unlink(pdf_path)

    async def test_estimate_from_pdf_openai_missing_api_key(self):
        """Test estimation fails when API key is missing."""
        from app.services.openai_vision_service import estimate_from_pdf_openai

        # Mock settings to return empty API key
        with patch('app.services.openai_vision_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = ""

            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                pdf_path = f.name

            try:
                with pytest.raises(ValueError, match="OPENAI_API_KEY is not configured"):
                    await estimate_from_pdf_openai(pdf_path=pdf_path)
            finally:
                import os
                os.unlink(pdf_path)

    async def test_estimate_from_pdf_openai_invalid_json(self):
        """Test estimation handles invalid JSON response."""
        from app.services.openai_vision_service import estimate_from_pdf_openai

        # Mock PDF rendering
        with patch('app.services.openai_vision_service._pdf_to_base64_image') as mock_render:
            mock_render.return_value = "fake_base64_image"

            # Mock OpenAI API returning invalid JSON
            with patch('app.services.openai_vision_service.OpenAI') as mock_openai_class:
                mock_client = Mock()
                mock_response = Mock()
                mock_choice = Mock()
                mock_message = Mock()

                # Invalid JSON response
                mock_message.content = 'This is not valid JSON {broken'
                mock_choice.message = mock_message
                mock_response.choices = [mock_choice]
                mock_response.usage = None

                mock_client.chat.completions.create.return_value = mock_response
                mock_openai_class.return_value = mock_client

                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                    pdf_path = f.name

                try:
                    with pytest.raises(RuntimeError, match="invalid JSON"):
                        await estimate_from_pdf_openai(pdf_path=pdf_path)
                finally:
                    import os
                    os.unlink(pdf_path)

    async def test_parse_json_response_with_markdown(self):
        """Test JSON parsing handles markdown code blocks."""
        from app.services.openai_vision_service import _parse_json_response

        # Test with markdown code block
        markdown_response = '''```json
{
    "part_type": "ROT",
    "estimated_time_min": 25.0
}
```'''
        result = _parse_json_response(markdown_response)
        assert result['part_type'] == 'ROT'
        assert result['estimated_time_min'] == 25.0

        # Test with plain JSON
        plain_response = '{"part_type": "PRI", "estimated_time_min": 30.0}'
        result = _parse_json_response(plain_response)
        assert result['part_type'] == 'PRI'
        assert result['estimated_time_min'] == 30.0


class TestFeatureExtraction:
    """Test Feature Extraction v2 models (L-009 compliance)."""

    def test_feature_item_validation(self):
        """Test FeatureItem Field() validation."""
        # Valid feature
        feature = FeatureItem(
            type="hole",
            count=4,
            detail="M6 threaded holes",
            location="top face"
        )
        assert feature.type == "hole"
        assert feature.count == 4
        assert feature.detail == "M6 threaded holes"

        # Valid with defaults
        feature_minimal = FeatureItem(type="slot")
        assert feature_minimal.count == 1
        assert feature_minimal.detail == ""

        # Invalid: empty type
        with pytest.raises(ValueError):
            FeatureItem(type="")

        # Invalid: count must be positive
        with pytest.raises(ValueError):
            FeatureItem(type="hole", count=0)

    def test_features_extraction_result_validation(self):
        """Test FeaturesExtractionResult Field() validation."""
        # Valid result with features
        result = FeaturesExtractionResult(
            drawing_number="TEST-001",
            part_name="Test Part",
            part_type="PRI",
            material={"grade": "C45", "iso": "P"},
            overall_dimensions={"length": 100, "width": 50, "height": 30},
            features=[
                FeatureItem(type="hole", count=4, detail="M6"),
                FeatureItem(type="slot", count=2, detail="10x50mm")
            ],
            general_notes=["Tolerance IT7", "Surface finish Ra 3.2"]
        )
        assert result.drawing_number == "TEST-001"
        assert len(result.features) == 2
        assert len(result.general_notes) == 2

        # Valid minimal result
        minimal_result = FeaturesExtractionResult()
        assert minimal_result.features == []
        assert minimal_result.general_notes == []

    def test_time_vision_response_with_features(self):
        """Test TimeVisionResponse includes feature extraction fields."""
        import json

        # Create response with feature extraction data
        response = TimeVisionResponse(
            id=1,
            pdf_filename="test.pdf",
            status="estimated",
            ai_provider="openai_ft",
            estimation_type="features_v2",
            features_json=json.dumps({
                "features": [
                    {"type": "hole", "count": 4, "detail": "M6"}
                ]
            }),
            calculated_time_min=45.5
        )

        assert response.estimation_type == "features_v2"
        assert response.calculated_time_min == 45.5
        assert response.features_json is not None

        # Parse and validate features JSON
        features_data = json.loads(response.features_json)
        assert len(features_data["features"]) == 1

    def test_time_vision_list_item_with_features(self):
        """Test TimeVisionListItem includes feature extraction fields."""
        # Create list item with feature extraction data
        item = TimeVisionListItem(
            id=1,
            pdf_filename="test.pdf",
            status="estimated",
            estimation_type="features_v2",
            calculated_time_min=45.5
        )

        assert item.estimation_type == "features_v2"
        assert item.calculated_time_min == 45.5

    def test_time_vision_estimation_model_defaults(self):
        """Test TimeVisionEstimation model has correct defaults for new fields."""
        from datetime import datetime

        # Create estimation with minimal data (explicit default for estimation_type)
        estimation = TimeVisionEstimation(
            pdf_filename="test.pdf",
            pdf_path="/uploads/drawings/test.pdf",
            estimation_type="time_v1",  # Explicit default
            created_by="test",
            updated_by="test",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # Check values (estimation_type explicitly set, others should be None)
        assert estimation.estimation_type == "time_v1"
        assert estimation.features_json is None
        assert estimation.features_corrected_json is None
        assert estimation.calculated_time_min is None

    @pytest.mark.asyncio
    async def test_time_vision_estimation_database_defaults(self):
        """Test TimeVisionEstimation database defaults work correctly."""
        from datetime import datetime
        import tempfile
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.database import Base

        # Create in-memory test database
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        try:
            # Create estimation without setting estimation_type
            estimation = TimeVisionEstimation(
                pdf_filename="test_db.pdf",
                pdf_path="/uploads/drawings/test_db.pdf",
                created_by="test",
                updated_by="test",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.add(estimation)
            db.commit()
            db.refresh(estimation)

            # Database default should be applied
            assert estimation.estimation_type == "time_v1"
            assert estimation.features_json is None
            assert estimation.features_corrected_json is None
            assert estimation.calculated_time_min is None

        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()


class TestFeaturesUpdate:
    """Test FeaturesUpdate schema validation."""

    def test_features_update_valid(self):
        """Test valid features update."""
        from app.routers.time_vision_router import FeaturesUpdate

        data = FeaturesUpdate(
            features_corrected_json='{"features": [{"type": "hole", "count": 4}]}',
            version=0,
        )
        assert data.features_corrected_json == '{"features": [{"type": "hole", "count": 4}]}'
        assert data.version == 0

    def test_features_update_invalid_json_too_short(self):
        """Test features update with too short JSON."""
        from app.routers.time_vision_router import FeaturesUpdate

        # Valid: exactly 2 chars (edge case OK)
        data = FeaturesUpdate(
            features_corrected_json="{}",
            version=0,
        )
        assert data.features_corrected_json == "{}"

        # Invalid: less than 2 chars
        with pytest.raises(ValueError):
            FeaturesUpdate(
                features_corrected_json="{",
                version=0,
            )

    def test_features_update_version_validation(self):
        """Test version must be non-negative."""
        from app.routers.time_vision_router import FeaturesUpdate

        # Valid: version 0
        data = FeaturesUpdate(
            features_corrected_json='{"test": "data"}',
            version=0,
        )
        assert data.version == 0

        # Valid: version > 0
        data = FeaturesUpdate(
            features_corrected_json='{"test": "data"}',
            version=5,
        )
        assert data.version == 5

        # Invalid: negative version
        with pytest.raises(ValueError):
            FeaturesUpdate(
                features_corrected_json='{"test": "data"}',
                version=-1,
            )


class TestTimeVisionRouterImports:
    """Test time vision router imports and endpoint definitions."""

    def test_list_estimations_accepts_new_parameters(self):
        """Test that list_estimations endpoint signature includes new params."""
        from app.routers.time_vision_router import list_estimations
        import inspect

        sig = inspect.signature(list_estimations)
        params = list(sig.parameters.keys())

        # Verify all expected parameters are present
        assert 'status' in params
        assert 'estimation_type' in params
        assert 'filename' in params
        assert 'db' in params

    def test_process_features_endpoint_exists(self):
        """Test that process_features endpoint is defined."""
        from app.routers.time_vision_router import process_features
        assert callable(process_features)

    def test_save_corrected_features_endpoint_exists(self):
        """Test that save_corrected_features endpoint is defined."""
        from app.routers.time_vision_router import save_corrected_features
        assert callable(save_corrected_features)

    def test_export_features_training_endpoint_exists(self):
        """Test that export_features_training_data endpoint is defined."""
        from app.routers.time_vision_router import export_features_training_data
        assert callable(export_features_training_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
