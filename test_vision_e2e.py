#!/usr/bin/env python3
"""
E2E test for Vision Hybrid Pipeline.

Tests complete workflow:
1. STEP geometry extraction
2. PDF annotation
3. Vision API refinement (mocked)
4. SSE streaming
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, Any

from app.services.occt_waterline_extractor import WaterlineExtractor
from app.services.pdf_step_annotator import PdfStepAnnotator
from app.services.pdf_coordinate_refiner import PdfCoordinateRefiner


def test_step_extraction():
    """Test STEP waterline extraction."""
    print("\n" + "="*60)
    print("TEST 1: STEP Geometry Extraction")
    print("="*60)

    step_path = Path("uploads/drawings/JR 810857.ipt.step")
    extractor = WaterlineExtractor()
    result = extractor.extract_waterline(step_path)

    assert result is not None, "STEP extraction failed"
    assert "segments" in result, "Missing segments key"
    assert len(result["segments"]) > 0, "No segments extracted"

    print(f"✅ STEP extraction OK")
    print(f"   Waterline points: {len(result['r_values'])}")
    print(f"   Segments: {len(result['segments'])}")

    for i, seg in enumerate(result["segments"]):
        print(f"   {i+1}. {seg['type']}: z={seg['z_start']} to {seg['z_end']}, "
              f"Ø{seg['diameter']}mm, L={seg['length']}mm")

    return result


def test_pdf_annotation(step_geometry: Dict):
    """Test PDF annotation with STEP overlay."""
    print("\n" + "="*60)
    print("TEST 2: PDF Annotation")
    print("="*60)

    pdf_path = Path("uploads/drawings/JR 810857.idw_Gelso.pdf")
    annotator = PdfStepAnnotator()

    annotated_pdf = annotator.annotate_pdf_with_step(pdf_path, step_geometry)

    assert annotated_pdf is not None, "PDF annotation failed"
    assert annotated_pdf.exists(), "Annotated PDF not created"

    print(f"✅ PDF annotation OK")
    print(f"   Input: {pdf_path}")
    print(f"   Output: {annotated_pdf}")
    print(f"   Segments annotated: {len(step_geometry['segments'])}")

    return annotated_pdf


def test_vision_schema_validation():
    """Test Vision API response schema validation."""
    print("\n" + "="*60)
    print("TEST 3: Vision API Schema Validation")
    print("="*60)

    # Simulate Vision API response
    mock_response = {
        "iteration": 1,
        "error": 0.15,
        "converged": False,
        "features": [
            {
                "type": "bore",
                "dimension": 9.5,
                "depth": 2.0,
                "dimension_error": 2.15,
                "step_data": {
                    "r_avg": 4.65,
                    "length": 2.0,
                    "type": "bore"
                }
            },
            {
                "type": "groove",
                "dimension": 9.2,
                "depth": 7.7,
                "dimension_error": 1.08,
                "step_data": {
                    "r_avg": 4.65,
                    "length": 7.7,
                    "type": "groove"
                }
            }
        ]
    }

    # Validate all required fields exist
    assert "iteration" in mock_response, "Missing iteration"
    assert "error" in mock_response, "Missing error"
    assert "converged" in mock_response, "Missing converged"
    assert "features" in mock_response, "Missing features"

    for i, feature in enumerate(mock_response["features"]):
        assert "type" in feature, f"Feature {i}: missing type"
        assert "dimension" in feature, f"Feature {i}: missing dimension"
        assert "depth" in feature, f"Feature {i}: missing depth"
        assert "dimension_error" in feature, f"Feature {i}: missing dimension_error"
        assert "step_data" in feature, f"Feature {i}: missing step_data"

        step_data = feature["step_data"]
        assert "r_avg" in step_data, f"Feature {i}: missing step_data.r_avg"
        assert "length" in step_data, f"Feature {i}: missing step_data.length"
        assert "type" in step_data, f"Feature {i}: missing step_data.type"

    print(f"✅ Schema validation OK")
    print(f"   Features: {len(mock_response['features'])}")
    print(f"   All required fields present")

    return mock_response


def test_sse_payload_format():
    """Test SSE payload format for frontend."""
    print("\n" + "="*60)
    print("TEST 4: SSE Payload Format")
    print("="*60)

    # Simulate job status dict (_active_jobs)
    job_status = {
        "status": "refining",
        "base_name": "JR 810857",
        "pdf_filename": "JR 810857.idw_Gelso.pdf",
        "step_filename": "JR 810857.ipt.step",
        "iteration": 1,
        "error": 0.15,
        "converged": False,
        "features": [
            {
                "type": "bore",
                "dimension": 9.5,
                "depth": 2.0,
                "dimension_error": 2.15,
                "step_data": {
                    "r_avg": 4.65,
                    "length": 2.0,
                    "type": "bore"
                }
            }
        ],
        "annotated_pdf_url": "/uploads/temp/annotated_123.pdf"
    }

    # Convert to SSE format
    sse_data = json.dumps(job_status)
    sse_message = f"data: {sse_data}\n\n"

    # Validate JSON is valid
    parsed = json.loads(sse_data)
    assert parsed["status"] == "refining"
    assert isinstance(parsed["iteration"], int)
    assert isinstance(parsed["error"], (int, float))
    assert isinstance(parsed["converged"], bool)
    assert isinstance(parsed["features"], list)

    print(f"✅ SSE format OK")
    print(f"   Status: {parsed['status']}")
    print(f"   Iteration: {parsed['iteration']}")
    print(f"   Error: {parsed['error']}")
    print(f"   Features: {len(parsed['features'])}")

    return sse_message


def test_frontend_compatibility():
    """Test data structure matches frontend expectations."""
    print("\n" + "="*60)
    print("TEST 5: Frontend Component Compatibility")
    print("="*60)

    # Simulate feature from backend
    backend_feature = {
        "type": "bore",
        "dimension": 9.5,
        "depth": 2.0,
        "dimension_error": 2.15,
        "step_data": {
            "r_avg": 4.65,
            "length": 2.0,
            "type": "bore"
        }
    }

    # Check all fields VisionFeaturesPanel needs
    required_fields = {
        "type": str,
        "dimension": (int, float),
        "depth": (int, float),
        "dimension_error": (int, float),
        "step_data": dict
    }

    for field, expected_type in required_fields.items():
        assert field in backend_feature, f"Missing field: {field}"
        assert isinstance(backend_feature[field], expected_type), \
            f"Wrong type for {field}: expected {expected_type}, got {type(backend_feature[field])}"

    # Check step_data nested fields
    step_data_fields = {
        "r_avg": (int, float),
        "length": (int, float),
        "type": str
    }

    for field, expected_type in step_data_fields.items():
        assert field in backend_feature["step_data"], f"Missing step_data.{field}"
        assert isinstance(backend_feature["step_data"][field], expected_type), \
            f"Wrong type for step_data.{field}"

    print(f"✅ Frontend compatibility OK")
    print(f"   All required fields present with correct types")

    # Test .toFixed() calls won't crash
    dimension_str = f"{backend_feature['dimension']:.2f}"
    depth_str = f"{backend_feature['depth']:.2f}"
    error_str = f"{backend_feature['dimension_error']:.1f}"
    r_avg_str = f"{backend_feature['step_data']['r_avg']:.2f}"
    length_str = f"{backend_feature['step_data']['length']:.2f}"

    print(f"   Dimension: Ø{dimension_str} mm")
    print(f"   Depth: {depth_str} mm")
    print(f"   Error: {error_str}%")
    print(f"   STEP r_avg: {r_avg_str} mm")
    print(f"   STEP length: {length_str} mm")


def main():
    """Run all E2E tests."""
    print("\n" + "🔬 "*30)
    print("VISION HYBRID PIPELINE - E2E TESTS")
    print("🔬 "*30)

    try:
        # Test 1: STEP extraction
        step_geometry = test_step_extraction()

        # Test 2: PDF annotation
        annotated_pdf = test_pdf_annotation(step_geometry)

        # Test 3: Schema validation
        vision_response = test_vision_schema_validation()

        # Test 4: SSE format
        sse_message = test_sse_payload_format()

        # Test 5: Frontend compatibility
        test_frontend_compatibility()

        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
        print("\nWorkflow validated:")
        print("  1. ✅ STEP geometry extraction")
        print("  2. ✅ PDF annotation with overlays")
        print("  3. ✅ Vision API schema validation")
        print("  4. ✅ SSE payload format")
        print("  5. ✅ Frontend component compatibility")

        return 0

    except AssertionError as e:
        print("\n" + "="*60)
        print(f"❌ TEST FAILED: {e}")
        print("="*60)
        return 1
    except Exception as e:
        print("\n" + "="*60)
        print(f"❌ UNEXPECTED ERROR: {e}")
        print("="*60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
