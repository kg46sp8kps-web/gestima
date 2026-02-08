#!/usr/bin/env python3
"""
Test ALL STEP files in drawings/ for rotation_axis detection.
"""

import sys
import glob
sys.path.insert(0, '.')

from app.services.step_parser import StepParser

print("="*80)
print("BATCH TEST - All STEP Files Rotation Axis Detection")
print("="*80)

# Find all STEP files
step_files = sorted(glob.glob('drawings/*.stp') + glob.glob('uploads/drawings/*.stp'))

if not step_files:
    print("\n❌ No STEP files found!")
    sys.exit(1)

print(f"\nFound {len(step_files)} STEP files")
print("="*80)

# Test with regex parser (NO OCCT dependency)
parser = StepParser(use_occt=False)

results = []

for filepath in step_files:
    filename = filepath.split('/')[-1]

    try:
        result = parser.parse_file(filepath)

        if result.get('success'):
            features = result.get('features', [])
            rotation_axis = result.get('rotation_axis')

            # Classify
            if rotation_axis:
                classification = f"ROTATIONAL ({rotation_axis}-axis)"
                symbol = "🔄"
            else:
                classification = "PRISMATIC"
                symbol = "📦"

            results.append({
                'file': filename,
                'rotation_axis': rotation_axis,
                'classification': classification,
                'features': len(features),
                'symbol': symbol
            })

            print(f"{symbol} {filename:40s} → {classification:20s} ({len(features)} features)")
        else:
            print(f"❌ {filename:40s} → PARSE FAILED: {result.get('error')}")

    except Exception as e:
        print(f"💥 {filename:40s} → EXCEPTION: {e}")

print("="*80)
print(f"\nSUMMARY:")
print(f"  Total files: {len(step_files)}")

rotational = [r for r in results if r['rotation_axis']]
prismatic = [r for r in results if not r['rotation_axis']]

print(f"  Rotational: {len(rotational)}")
print(f"  Prismatic: {len(prismatic)}")

if rotational:
    print(f"\n  Rotational parts:")
    for r in rotational:
        print(f"    - {r['file']} ({r['rotation_axis']}-axis)")

if prismatic:
    print(f"\n  Prismatic parts:")
    for r in prismatic:
        print(f"    - {r['file']}")

print("="*80)
