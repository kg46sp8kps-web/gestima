"""
Generate contours from STEP files WITHOUT AI API

Uses deterministic STEP parser (regex-based) to extract geometry.
No API credits needed.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.step_parser import StepParser

TEST_FILES = [
    "JR 810663.ipt.step",
    "JR 810664.ipt.step",
    "JR 810665.ipt.step",
    "JR 810671.ipt.step",
    "JR 810670.ipt.step"
]

def analyze_file(filename):
    step_path = f"uploads/drawings/{filename}"

    print(f"\n{'='*80}")
    print(f"📄 {filename}")
    print(f"{'='*80}")

    try:
        # Parse STEP using regex parser (no OCCT, no API)
        parser = StepParser()
        result = parser.parse_file(step_path)

        if result.get("success"):
            profile = result.get("profile_geometry", {})
            outer = profile.get("outer_contour", [])
            inner = profile.get("inner_contour", [])

            print(f"✅ STEP Parser Success")
            print(f"   Part Type:    {result.get('part_type')}")
            print(f"   Rotation Axis: {result.get('metadata', {}).get('rotation_axis')}")

            if outer:
                max_r = max(pt.get("r", 0) for pt in outer)
                max_z = max(pt.get("z", 0) for pt in outer)
                min_z = min(pt.get("z", 0) for pt in outer)

                print(f"   Max Diameter: Ø{max_r * 2:.1f} mm")
                print(f"   Total Length: {max_z - min_z:.1f} mm")
                print(f"   Outer Points: {len(outer)}")

                # Show contour points
                print(f"\n   Outer Contour:")
                for i, pt in enumerate(outer[:10]):  # First 10 points
                    print(f"   {i+1:2d}. r={pt['r']:6.2f}, z={pt['z']:6.2f}")
                if len(outer) > 10:
                    print(f"   ... ({len(outer) - 10} more points)")

            if inner:
                max_r_inner = max(pt.get("r", 0) for pt in inner)
                print(f"\n   Bore Diameter: Ø{max_r_inner * 2:.1f} mm")
                print(f"   Inner Points: {len(inner)}")

                print(f"\n   Inner Contour:")
                for i, pt in enumerate(inner[:10]):
                    print(f"   {i+1:2d}. r={pt['r']:6.2f}, z={pt['z']:6.2f}")
                if len(inner) > 10:
                    print(f"   ... ({len(inner) - 10} more points)")

            # Features
            features = result.get("features", [])
            if features:
                print(f"\n   Features: {len(features)}")
                for feat in features[:5]:
                    print(f"   - {feat}")

        else:
            print(f"❌ Parse failed: {result.get('error')}")

    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("="*80)
    print("CONTOUR GENERATION - 5 Files (NO API)")
    print("Using STEP regex parser (deterministic)")
    print("="*80)

    for filename in TEST_FILES:
        analyze_file(filename)

    print(f"\n{'='*80}")
    print("✅ Done!")
    print("="*80)
