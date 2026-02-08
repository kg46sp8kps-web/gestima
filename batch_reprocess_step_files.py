#!/usr/bin/env python3
"""
Batch Reprocessing Script for STEP Files
Reprocesses all STEP files in uploads/drawings/ with OCCT parser
"""
import glob
import sys
import os
import json

# Setup path
sys.path.insert(0, '/Users/lofas/Documents/__App_Claude/Gestima')
os.chdir('/Users/lofas/Documents/__App_Claude/Gestima')

from app.services.step_parser import StepParser
from app.services.contour_builder import ContourBuilder
from app.config import settings

print("=" * 80)
print("FULL BATCH REPROCESSING - uploads/drawings/")
print("=" * 80)
print(f"OCCT Parser Enabled: {settings.ENABLE_OCCT_PARSER}")
print("=" * 80)

parser = StepParser(use_occt=settings.ENABLE_OCCT_PARSER)
builder = ContourBuilder()

# Find all STEP files
step_files = sorted(
    glob.glob('uploads/drawings/*.stp') + glob.glob('uploads/drawings/*.step')
)
print(f"\nFound {len(step_files)} STEP files\n")

results = []

for i, filepath in enumerate(step_files, 1):
    filename = os.path.basename(filepath)
    print(f"[{i}/{len(step_files)}] Processing: {filename}...")

    try:
        # Parse STEP file with OCCT/regex parser
        step_result = parser.parse_file(filepath)

        if not step_result.get('success'):
            raise Exception(step_result.get('error', 'STEP parse failed'))

        source = step_result.get('source', 'unknown')
        features_list = step_result.get('features', [])
        rotation_axis = step_result.get('rotation_axis', 'z')

        # Build deterministic contour
        profile_geometry = builder.build_profile_geometry(
            features_list,
            step_result.get('advanced_faces', {}),
            rotation_axis
        )

        if not profile_geometry:
            raise Exception('Contour build failed - insufficient geometry data')

        # Determine part type from profile geometry
        part_type = profile_geometry.get('part_type', 'rotational')
        outer_points = len(profile_geometry.get('outer_contour', []))
        inner_points = len(profile_geometry.get('inner_contour', []))
        max_diameter = profile_geometry.get('max_diameter', 0)
        total_length = profile_geometry.get('total_length', 0)

        results.append({
            'filename': filename,
            'filepath': filepath,
            'part_type': part_type,
            'source': source,
            'features': len(features_list),
            'operations': 0,  # Not generating operations in batch mode
            'outer_contour': outer_points,
            'inner_contour': inner_points,
            'max_diameter': max_diameter,
            'total_length': total_length,
            'status': '✅'
        })

        print(f"  ✓ part_type={part_type}, source={source}, features={len(features_list)}, contour={outer_points}+{inner_points} pts, Ø{max_diameter:.1f}mm × {total_length:.1f}mm")

    except Exception as e:
        results.append({
            'filename': filename,
            'filepath': filepath,
            'part_type': 'ERROR',
            'source': 'error',
            'features': 0,
            'operations': 0,
            'outer_contour': 0,
            'inner_contour': 0,
            'max_diameter': 0,
            'total_length': 0,
            'status': '❌',
            'error': str(e)
        })
        print(f"  ✗ ERROR: {e}")

print("\n" + "=" * 80)
print("REPROCESSING COMPLETE")
print("=" * 80)

# Summary table
print("\n{:<40} {:<12} {:<12} {:<8} {:<8} {:<8}".format(
    "Filename", "Part Type", "Source", "Features", "Ops", "Status"
))
print("-" * 90)
for r in results:
    print("{:<40} {:<12} {:<12} {:<8} {:<8} {:<8}".format(
        r['filename'][:39],
        r['part_type'],
        r['source'],
        str(r['features']),
        str(r['operations']),
        r['status']
    ))

# Count rotational vs prismatic
rotational = sum(1 for r in results if r['part_type'] == 'rotational')
prismatic = sum(1 for r in results if r['part_type'] == 'prismatic')
errors = sum(1 for r in results if r['status'] == '❌')

print("\n" + "=" * 80)
print(f"SUMMARY: {rotational} rotational, {prismatic} prismatic, {errors} errors (out of {len(results)} total)")
print("=" * 80)

# Save results to JSON for frontend
output_path = 'uploads/drawings/reprocessed_results.json'
with open(output_path, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n✅ Results saved to: {output_path}")

# Show any errors
if errors > 0:
    print("\n" + "=" * 80)
    print("ERRORS DETAIL")
    print("=" * 80)
    for r in results:
        if r['status'] == '❌':
            print(f"\n{r['filename']}:")
            print(f"  {r.get('error', 'Unknown error')}")
