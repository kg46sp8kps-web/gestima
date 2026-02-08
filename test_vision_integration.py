#!/usr/bin/env python3
"""
Integration test for Vision Hybrid Pipeline - simulates HTTP calls.

Tests:
1. GET /drawing-files (file browser)
2. POST /refine-annotations-files (start job)
3. GET /progress/{job_id} (SSE stream)
"""

import asyncio
import httpx
import json
from pathlib import Path


BASE_URL = "http://localhost:8000/api/vision-debug"


async def test_file_browser():
    """Test GET /drawing-files endpoint."""
    print("\n" + "="*60)
    print("TEST 1: File Browser")
    print("="*60)

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/drawing-files")
        assert response.status_code == 200, f"Status: {response.status_code}"

        data = response.json()
        assert isinstance(data, list), "Response must be list"
        assert len(data) > 0, "No drawing pairs found"

        print(f"✅ File browser OK")
        print(f"   Found {len(data)} drawing pairs")

        # Find JR 810857
        jr_810857 = next((p for p in data if "810857" in p["baseName"]), None)
        assert jr_810857 is not None, "JR 810857 not found"

        print(f"   Test part: {jr_810857['baseName']}")
        print(f"   PDF: {jr_810857['pdfFile']}")
        print(f"   STEP: {jr_810857['stepFile']}")

        return jr_810857


async def test_start_analysis(part):
    """Test POST /refine-annotations-files endpoint."""
    print("\n" + "="*60)
    print("TEST 2: Start Analysis")
    print("="*60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/refine-annotations-files",
            params={
                "pdf_filename": part["pdfFile"],
                "step_filename": part["stepFile"]
            }
        )

        assert response.status_code == 200, f"Status: {response.status_code}, Body: {response.text}"

        data = response.json()
        assert "job_id" in data, "Missing job_id"
        assert "base_name" in data, "Missing base_name"

        print(f"✅ Analysis started")
        print(f"   Job ID: {data['job_id']}")
        print(f"   Part: {data['base_name']}")

        return data["job_id"]


async def test_sse_stream(job_id: str):
    """Test GET /progress/{job_id} SSE endpoint."""
    print("\n" + "="*60)
    print("TEST 3: SSE Progress Stream")
    print("="*60)

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("GET", f"{BASE_URL}/progress/{job_id}") as response:
            assert response.status_code == 200, f"Status: {response.status_code}"

            iteration_count = 0
            last_status = None

            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue

                try:
                    data_str = line.replace("data: ", "")
                    data = json.loads(data_str)

                    if "iteration" in data:
                        iteration_count = data["iteration"]
                        error_val = data.get('error', 'N/A')
                        error_str = f"{error_val:.4f}" if isinstance(error_val, (int, float)) else str(error_val)
                        print(f"   Iteration {data['iteration']}: error={error_str}")

                    if "status" in data:
                        last_status = data["status"]
                        print(f"   Status: {data['status']}")

                        if data["status"] == "completed":
                            print(f"✅ Analysis completed")
                            print(f"   Total iterations: {iteration_count}")
                            print(f"   Features: {len(data.get('features', []))}")
                            return True

                        if data["status"] == "failed":
                            print(f"❌ Analysis failed: {data.get('error_message', 'Unknown error')}")
                            return False

                except json.JSONDecodeError as e:
                    print(f"⚠️  Invalid JSON: {data_str}")
                    continue

            print(f"⚠️  Stream ended without completion status (last status: {last_status})")
            return False


async def main():
    """Run integration tests."""
    print("\n" + "🧪 "*30)
    print("VISION HYBRID PIPELINE - INTEGRATION TESTS")
    print("🧪 "*30)

    try:
        # Test 1: File browser
        part = await test_file_browser()

        # Test 2: Start analysis
        job_id = await test_start_analysis(part)

        # Test 3: SSE stream
        success = await test_sse_stream(job_id)

        if success:
            print("\n" + "="*60)
            print("✅ ALL INTEGRATION TESTS PASSED")
            print("="*60)
            return 0
        else:
            print("\n" + "="*60)
            print("⚠️  TESTS COMPLETED WITH WARNINGS")
            print("="*60)
            return 1

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
    exit(asyncio.run(main()))
