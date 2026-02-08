#!/usr/bin/env python3
"""
Test regex parser rotation_axis detection WITHOUT OCCT dependency.
"""

import sys
sys.path.insert(0, '.')

print("="*80)
print("REGEX PARSER ROTATION AXIS TEST")
print("="*80)

# Test with regex parser explicitly (NO OCCT)
from app.services.step_parser import StepParser

print("\n[1] Testing regex parser (use_occt=False):")
parser = StepParser(use_occt=False)

test_file = 'drawings/PDM-249322_03.stp'
print(f"   Parsing: {test_file}")

result = parser.parse_file(test_file)

print(f"\n[2] Parser Result:")
print(f"   Success: {result.get('success')}")
print(f"   Source: {result.get('source')}")
print(f"   Features: {len(result.get('features', []))}")
print(f"   Rotation axis: {result.get('rotation_axis')}")  # ← KEY!

features = result.get('features', [])
if features:
    print(f"\n[3] First 5 features:")
    for i, f in enumerate(features[:5]):
        print(f"   [{i}] type={f.get('type'):15s} radius={f.get('radius', 0):6.2f}")

# Test analysis service with regex
print(f"\n[4] Analysis Service (deterministic pipeline):")
from app.services.analysis_service import AnalysisService

service = AnalysisService()

# Force OCCT off by testing step_parser directly
from app.services import step_parser
original_available = getattr(step_parser, 'OCCT_AVAILABLE', None)
step_parser.OCCT_AVAILABLE = False  # Force regex

try:
    analysis_result = service.run_deterministic_pipeline(test_file)

    geometry = analysis_result.get('geometry', {})
    part_type = geometry.get('part_type')

    print(f"   part_type: {part_type}")  # ← MUST be "rotational"!
    print(f"   operations: {len(analysis_result.get('operations', []))}")

    if part_type == 'rotational':
        print(f"\n✅ SUCCESS: Regex parser correctly detects rotational parts!")
    else:
        print(f"\n❌ FAIL: part_type = {part_type} (expected 'rotational')")

finally:
    # Restore
    if original_available is not None:
        step_parser.OCCT_AVAILABLE = original_available

print(f"\n{'='*80}")
