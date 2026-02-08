#!/usr/bin/env python3
"""
Emergency diagnostic for rotational part classification bug.

Tests entire pipeline from STEP → OCCT → rotation_axis → part_type.
Run standalone: python3 test_rotation_axis_diagnostic.py
"""

import sys
import os

# Minimal imports to avoid dependency hell
sys.path.insert(0, os.path.dirname(__file__))

print("="*80)
print("EMERGENCY DIAGNOSTIC - Rotation Axis Detection")
print("="*80)

# Step 1: Check if OCCT is available
print("\n[1] OCCT Availability Check:")
try:
    from OCC.Core.STEPControl import STEPControl_Reader
    print("  ✅ pythonocc-core is installed")
    OCCT_OK = True
except ImportError as e:
    print(f"  ❌ pythonocc-core NOT available: {e}")
    OCCT_OK = False

if not OCCT_OK:
    print("\n🛑 OCCT not available - cannot proceed with diagnostic")
    sys.exit(1)

# Step 2: Test OCCT parser directly
print("\n[2] OCCT Parser Test:")
try:
    from app.services.step_parser_occt import StepParserOCCT

    parser = StepParserOCCT()
    test_file = 'drawings/PDM-249322_03.stp'

    if not os.path.exists(test_file):
        print(f"  ⚠️  Test file not found: {test_file}")
        print("  Searching for any .stp files...")
        import glob
        step_files = glob.glob('drawings/*.stp') + glob.glob('uploads/drawings/*.stp')
        if step_files:
            test_file = step_files[0]
            print(f"  Using: {test_file}")
        else:
            print("  ❌ No STEP files found!")
            sys.exit(1)

    print(f"  Parsing: {test_file}")
    result = parser.parse_file(test_file)

    print(f"  Success: {result.get('success')}")
    print(f"  Source: {result.get('source')}")
    print(f"  Features: {len(result.get('features', []))}")
    print(f"  Rotation axis: {result.get('rotation_axis')}")  # ← CRITICAL!

    features = result.get('features', [])

    if features:
        print(f"\n  First 3 features:")
        for i, f in enumerate(features[:3]):
            axis_dir = f.get('axis_direction')
            print(f"    [{i}] type={f.get('type'):12s} radius={f.get('radius', 0):6.2f} axis_direction={axis_dir}")

    # Manual rotation axis detection test
    print(f"\n[3] Manual Rotation Axis Detection:")
    from app.services.occt_metadata import detect_rotation_axis

    manual_axis = detect_rotation_axis(features)
    print(f"  detect_rotation_axis() returned: {manual_axis}")

    # Step 4: Compare with analysis_service
    print(f"\n[4] Analysis Service Integration Test:")
    from app.services.analysis_service import AnalysisService

    service = AnalysisService()
    analysis_result = service.run_deterministic_pipeline(test_file)

    geometry = analysis_result.get('geometry', {})
    part_type = geometry.get('part_type')

    print(f"  Geometry part_type: {part_type}")  # ← MUST be "rotational"!
    print(f"  Operations count: {len(analysis_result.get('operations', []))}")

    ops = analysis_result.get('operations', [])
    if ops:
        first_op = ops[0].get('operation_type')
        print(f"  First operation: {first_op}")

    # Step 5: Verdict
    print(f"\n{'='*80}")
    print("DIAGNOSTIC SUMMARY:")
    print(f"{'='*80}")

    print(f"\n  OCCT parser rotation_axis: {result.get('rotation_axis')}")
    print(f"  detect_rotation_axis():     {manual_axis}")
    print(f"  Analysis part_type:         {part_type}")

    if result.get('rotation_axis') and part_type == 'rotational':
        print(f"\n  ✅ VERDICT: Pipeline is WORKING correctly!")
        print(f"  ✅ Rotational parts are classified as 'rotational'")
    elif result.get('rotation_axis') and part_type != 'rotational':
        print(f"\n  ❌ VERDICT: BUG in analysis_service.py!")
        print(f"  ❌ rotation_axis detected but part_type = {part_type}")
        print(f"  ❌ Check line ~335 in app/services/analysis_service.py")
    elif not result.get('rotation_axis'):
        print(f"\n  ❌ VERDICT: BUG in rotation axis detection!")
        print(f"  ❌ OCCT parser returned rotation_axis = None")
        print(f"  ❌ Check axis_direction in feature dicts")

        if features:
            has_axis_dir = any(f.get('axis_direction') for f in features)
            print(f"  ❌ Features have axis_direction: {has_axis_dir}")
            if not has_axis_dir:
                print(f"  ❌ CRITICAL: OCCT extractors not returning axis_direction!")

    print(f"\n{'='*80}")

except Exception as e:
    print(f"  ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
