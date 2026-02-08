#!/usr/bin/env python3
"""
Test live API endpoint for feature recognition part_type classification.
"""

import requests
import json
from pathlib import Path

API_BASE = "http://localhost:8000"

print("="*80)
print("LIVE API TEST - Feature Recognition Part Type")
print("="*80)

# Test file
test_file = Path("drawings/PDM-249322_03.stp")

if not test_file.exists():
    print(f"\n❌ Test file not found: {test_file}")
    exit(1)

print(f"\n[1] Testing file: {test_file.name}")
print(f"    Expected: part_type = 'rotational'")

# Call feature recognition API
print(f"\n[2] Calling POST /api/feature-recognition/analyze-step...")

with open(test_file, 'rb') as f:
    files = {'step_file': (test_file.name, f, 'application/stp')}

    try:
        response = requests.post(
            f"{API_BASE}/api/feature-recognition/analyze-step",
            files=files,
            timeout=60
        )

        print(f"    Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            print(f"\n[3] Response:")
            geometry = data.get('geometry', {})
            part_type = geometry.get('part_type')

            print(f"    source: {data.get('source')}")
            print(f"    confidence: {data.get('confidence')}")
            print(f"    part_type: {part_type}")  # ← KEY!
            print(f"    features: {len(data.get('features', []))}")
            print(f"    operations: {len(data.get('operations', []))}")

            if data.get('operations'):
                first_op = data['operations'][0]
                print(f"    first_operation: {first_op.get('operation_type')} / {first_op.get('sub_type')}")

            print(f"\n{'='*80}")
            print(f"VERDICT:")
            print(f"{'='*80}")

            if part_type == 'rotational':
                print(f"\n✅ SUCCESS: API correctly returns part_type = 'rotational'!")
                print(f"✅ Backend code is up-to-date and working!")
            else:
                print(f"\n❌ FAIL: API returns part_type = '{part_type}' (expected 'rotational')")
                print(f"❌ Backend server may be running old code!")
                print(f"❌ Try restarting: kill {response.headers.get('server')} && python3 gestima.py run")

                # Debug info
                print(f"\n🔍 DEBUG INFO:")
                print(f"   Profile geometry:")
                pg = geometry.get('profile_geometry', {})
                print(f"     outer_contour: {len(pg.get('outer_contour', []))} points")
                print(f"     inner_contour: {len(pg.get('inner_contour', []))} points")

        else:
            print(f"\n❌ API Error: {response.status_code}")
            print(response.text[:500])

    except requests.exceptions.ConnectionError:
        print(f"\n❌ Backend not running on {API_BASE}!")
        print(f"   Start with: python3 gestima.py run")
    except Exception as e:
        print(f"\n💥 Exception: {e}")

print(f"\n{'='*80}")
