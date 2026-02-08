"""Tests for batch reprocessing results endpoint"""
import pytest
from pathlib import Path


@pytest.mark.asyncio
async def test_batch_results_endpoint_returns_cached_data(client, admin_headers):
    """Test GET /api/feature-recognition/batch-results returns cached JSON"""
    response = await client.get("/api/feature-recognition/batch-results", headers=admin_headers)

    # Should return cached results if file exists, or 404 if not
    if response.status_code == 404:
        # File doesn't exist yet - acceptable
        assert "not found" in response.json()["detail"].lower()
    else:
        # File exists - should return valid array
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        if len(data) > 0:
            # Verify structure of first result
            first = data[0]
            assert "filename" in first
            assert "part_type" in first
            assert "source" in first
            assert "features" in first
            assert "status" in first


@pytest.mark.asyncio
async def test_batch_results_structure_validation(client, admin_headers):
    """Test batch results have expected structure"""
    # Skip if file doesn't exist
    results_path = Path("uploads/drawings/reprocessed_results.json")
    if not results_path.exists():
        pytest.skip("Batch results file not found")

    response = await client.get("/api/feature-recognition/batch-results", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    assert len(data) > 0, "Batch results should contain at least one file"

    # Check each result has required fields
    for result in data:
        assert "filename" in result
        assert "filepath" in result
        assert "part_type" in result
        assert "source" in result
        assert "features" in result
        assert "operations" in result
        assert "outer_contour" in result
        assert "inner_contour" in result
        assert "status" in result

        # Validate values
        assert result["part_type"] in ["rotational", "prismatic", "ERROR"]
        assert result["source"] in ["step_regex", "step_occt", "error"]
        assert result["status"] in ["✅", "❌"]
        assert isinstance(result["features"], int)
        assert result["features"] >= 0


@pytest.mark.asyncio
async def test_batch_results_counts(client, admin_headers):
    """Test batch results summary statistics"""
    # Skip if file doesn't exist
    results_path = Path("uploads/drawings/reprocessed_results.json")
    if not results_path.exists():
        pytest.skip("Batch results file not found")

    response = await client.get("/api/feature-recognition/batch-results", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()

    # Count results by status
    success_count = sum(1 for r in data if r["status"] == "✅")
    error_count = sum(1 for r in data if r["status"] == "❌")

    assert success_count + error_count == len(data)
    assert success_count > 0, "At least some files should parse successfully"

    # Log summary for debugging
    print(f"\nBatch results summary: {success_count} success, {error_count} errors (total: {len(data)})")
