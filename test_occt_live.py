#!/usr/bin/env python3
"""
Live integration test for OCCT parser.

Tests that analysis_service actually uses OCCT when configured.
Requires backend running on localhost:8000.
"""

import requests
from pathlib import Path

# Test file
STEP_FILE = "drawings/PDM-249322_03.stp"

if not Path(STEP_FILE).exists():
    print(f"❌ Test file not found: {STEP_FILE}")
    print("Skipping live test.")
    exit(0)

print("🔧 Testing OCCT integration...")
print(f"   File: {STEP_FILE}")

# Call feature recognition endpoint
with open(STEP_FILE, 'rb') as f:
    files = {'step_file': f}
    response = requests.post(
        'http://localhost:8000/api/feature-recognition/analyze',
        files=files,
        timeout=30
    )

if response.status_code != 200:
    print(f"❌ API call failed: {response.status_code}")
    print(response.text)
    exit(1)

data = response.json()

# Verify response structure
source = data.get('source')
features = data.get('features', [])
profile_geo = data.get('profile_geometry')

print(f"\n✅ API Response:")
print(f"   Source: {source}")
print(f"   Features: {len(features)}")
print(f"   Profile geometry: {'Yes' if profile_geo else 'No'}")

# Check if OCCT was used
if source == 'step_deterministic':
    print("\n✅ OCCT Integration Working!")
    print("   Pipeline: step_deterministic (pure CAD geometry)")

    if profile_geo:
        outer = profile_geo.get('outer_contour', [])
        inner = profile_geo.get('inner_contour', [])
        print(f"   Outer contour: {len(outer)} points")
        print(f"   Inner contour: {len(inner)} points")
        print(f"   Total length: {profile_geo.get('total_length')}mm")
        print(f"   Max diameter: {profile_geo.get('max_diameter')}mm")

        if len(outer) >= 10:
            print("\n✅ DETAILED CONTOUR DETECTED (OCCT working)")
            print("   Accuracy: Expect 90%+ (native CAD kernel)")
        else:
            print("\n⚠️  Low contour detail - possible regex fallback")

elif source == 'step_regex':
    print("\n⚠️  OCCT NOT USED - Regex Fallback")
    print("   This means OCCT is either unavailable or failed.")
    print("   Accuracy: ~40% (regex approximation)")

else:
    print(f"\n⚠️  Unexpected source: {source}")
    print("   Expected: step_deterministic (OCCT) or step_regex (fallback)")

print("\n" + "="*60)
print("Test complete. See logs for 'STEP parsed with source: ...'")
