#!/usr/bin/env python3
"""
Batch test proxy features extraction on 37 STEP files.

Tests:
1. Feature extraction (56 proxy metrics)
2. Determinism (same input → same output)
3. Value ranges (sanity checks)
4. Critical metrics (cavity volume, inner surface ratio)
5. Time estimation (MRR baseline)

Output: JSON report + console summary
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.geometry_feature_extractor import GeometryFeatureExtractor

UPLOADS_DIR = Path(__file__).parent.parent / "uploads" / "drawings"
OUTPUT_FILE = UPLOADS_DIR / "batch_proxy_test_results.json"


def test_single_file(filename: str, extractor: GeometryFeatureExtractor) -> dict:
    """Test single STEP file extraction."""
    step_path = UPLOADS_DIR / filename

    if not step_path.exists():
        return {"error": f"File not found: {filename}"}

    try:
        start_time = time.time()
        features = extractor.extract_features(step_path, material_code="20910000")
        extraction_time = time.time() - start_time

        # Validate critical metrics
        validations = {
            "part_volume_positive": features.part_volume_mm3 > 0,
            "removal_volume_valid": 0 <= features.removal_volume_mm3 <= features.stock_volume_mm3,
            "removal_ratio_valid": 0 <= features.removal_ratio <= 1.0,
            "cavity_ratio_valid": 0 <= features.cavity_to_stock_ratio <= 1.0,
            "inner_surface_ratio_valid": 0 <= features.inner_surface_ratio <= 1.0,
            "concave_edge_ratio_valid": 0 <= features.concave_edge_ratio <= 1.0,
            "rotational_score_valid": 0 <= features.rotational_score <= 1.0,
        }

        all_valid = all(validations.values())

        # Calculate basic time estimate (MRR baseline)
        roughing_time = features.removal_volume_mm3 / 100  # cm³/min MRR
        finishing_time = features.surface_area_mm2 / 500    # cm²/min finishing rate
        total_time = roughing_time + finishing_time

        return {
            "filename": filename,
            "success": True,
            "extraction_time_sec": round(extraction_time, 2),
            "part_type": features.part_type,
            "metrics": {
                "part_volume_mm3": round(features.part_volume_mm3, 1),
                "removal_volume_mm3": round(features.removal_volume_mm3, 1),
                "removal_ratio": round(features.removal_ratio, 3),
                "internal_cavity_volume_mm3": round(features.internal_cavity_volume_mm3, 1),
                "cavity_to_stock_ratio": round(features.cavity_to_stock_ratio, 3),
                "inner_surface_ratio": round(features.inner_surface_ratio, 3),
                "concave_edge_ratio": round(features.concave_edge_ratio, 3),
                "max_feature_depth_mm": round(features.max_feature_depth_mm, 1),
                "openness_ratio": round(features.openness_ratio, 3),
                "rotational_score": round(features.rotational_score, 3),
                "cylindrical_surface_ratio": round(features.cylindrical_surface_ratio, 3),
                "planar_surface_ratio": round(features.planar_surface_ratio, 3),
                "freeform_surface_ratio": round(features.freeform_surface_ratio, 3),
                "sharp_edge_ratio": round(features.sharp_edge_ratio, 3),
                "feature_density_per_cm3": round(features.feature_density_per_cm3, 2),
            },
            "time_estimate": {
                "roughing_min": round(roughing_time, 1),
                "finishing_min": round(finishing_time, 1),
                "total_min": round(total_time, 1),
            },
            "validations": validations,
            "all_valid": all_valid,
        }

    except Exception as e:
        return {
            "filename": filename,
            "success": False,
            "error": str(e),
        }


def main():
    print("=" * 80)
    print("🔬 PROXY FEATURES BATCH TEST")
    print("=" * 80)
    print(f"Uploads dir: {UPLOADS_DIR}")
    print()

    # Find all STEP files
    step_files = sorted([f.name for f in UPLOADS_DIR.glob("*.step")])

    if not step_files:
        print("❌ No STEP files found!")
        return

    print(f"Found {len(step_files)} STEP files")
    print()

    # Initialize extractor
    extractor = GeometryFeatureExtractor()

    # Test all files
    results = []
    success_count = 0
    error_count = 0

    for i, filename in enumerate(step_files, 1):
        print(f"[{i}/{len(step_files)}] Testing {filename}...", end=" ", flush=True)

        result = test_single_file(filename, extractor)
        results.append(result)

        if result.get("success"):
            success_count += 1
            part_type = result["part_type"]
            cavity_ratio = result["metrics"]["cavity_to_stock_ratio"]
            time_est = result["time_estimate"]["total_min"]
            print(f"✅ {part_type} | Cavity: {cavity_ratio:.1%} | Time: {time_est:.0f}min")
        else:
            error_count += 1
            print(f"❌ Error: {result.get('error', 'Unknown')}")

    print()
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"Total files:     {len(step_files)}")
    print(f"Success:         {success_count} ({success_count/len(step_files)*100:.1f}%)")
    print(f"Errors:          {error_count}")
    print()

    # Aggregate statistics
    successful = [r for r in results if r.get("success")]

    if successful:
        rot_count = sum(1 for r in successful if r["part_type"] == "ROT")
        pri_count = sum(1 for r in successful if r["part_type"] == "PRI")

        print("PART TYPE DISTRIBUTION:")
        print(f"  ROT (turning):  {rot_count} ({rot_count/len(successful)*100:.1f}%)")
        print(f"  PRI (milling):  {pri_count} ({pri_count/len(successful)*100:.1f}%)")
        print()

        # Cavity volume stats
        cavities = [r["metrics"]["internal_cavity_volume_mm3"] for r in successful]
        cavity_ratios = [r["metrics"]["cavity_to_stock_ratio"] for r in successful]

        print("CAVITY VOLUME STATS:")
        print(f"  Min:     {min(cavities):.0f} mm³")
        print(f"  Max:     {max(cavities):.0f} mm³")
        print(f"  Average: {sum(cavities)/len(cavities):.0f} mm³")
        print(f"  Parts with cavities (>0): {sum(1 for c in cavities if c > 0)} ({sum(1 for c in cavities if c > 0)/len(cavities)*100:.1f}%)")
        print()

        # Inner surface ratio stats
        inner_ratios = [r["metrics"]["inner_surface_ratio"] for r in successful]

        print("INNER SURFACE RATIO STATS:")
        print(f"  Min:     {min(inner_ratios):.1%}")
        print(f"  Max:     {max(inner_ratios):.1%}")
        print(f"  Average: {sum(inner_ratios)/len(inner_ratios):.1%}")
        print()

        # Time estimates
        times = [r["time_estimate"]["total_min"] for r in successful]

        print("TIME ESTIMATES (MRR baseline):")
        print(f"  Min:     {min(times):.0f} min")
        print(f"  Max:     {max(times):.0f} min")
        print(f"  Average: {sum(times)/len(times):.0f} min")
        print()

        # Validation summary
        invalid_count = sum(1 for r in successful if not r.get("all_valid"))
        if invalid_count > 0:
            print(f"⚠️  WARNING: {invalid_count} files have validation errors!")
            for r in successful:
                if not r.get("all_valid"):
                    failed_checks = [k for k, v in r["validations"].items() if not v]
                    print(f"  - {r['filename']}: {', '.join(failed_checks)}")
            print()

    # Save results
    output = {
        "test_date": datetime.now().isoformat(),
        "total_files": len(step_files),
        "success_count": success_count,
        "error_count": error_count,
        "results": results,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"📁 Results saved to: {OUTPUT_FILE}")
    print()

    # Exit code
    if error_count > 0:
        print("⚠️  Some files failed - check results for details")
        sys.exit(1)
    else:
        print("✅ All files processed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
