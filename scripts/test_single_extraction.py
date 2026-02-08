"""Quick test of geometry extraction on single file."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.geometry_extractor import extract_geometry_with_claude


async def test_pdm_249322():
    """Test reference file PDM-249322_03."""
    step_file = "uploads/drawings/PDM-249322_03.stp"
    pdf_file = "uploads/drawings/PDM-249322_03_Gelso.pdf"

    print(f"Testing: {step_file}")
    print(f"PDF: {pdf_file}")

    try:
        result = await extract_geometry_with_claude(step_file, pdf_file)

        # Pretty print result
        print("\n" + "="*80)
        print("EXTRACTION RESULT")
        print("="*80)
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # Extract metrics
        profile = result.get("profile_geometry", {})
        outer = profile.get("outer_contour", [])
        inner = profile.get("inner_contour", [])
        features = profile.get("features", [])

        print("\n" + "="*80)
        print("METRICS")
        print("="*80)
        print(f"Part type: {result.get('part_type')}")
        print(f"Material: {result.get('material_spec')}")
        print(f"Outer contour: {len(outer)} points")
        print(f"Inner contour: {len(inner)} points")
        print(f"Features: {len(features)}")
        print(f"Confidence: {result.get('confidence', 0):.2f}")

        # Compare with known ground truth
        print("\n" + "="*80)
        print("GROUND TRUTH COMPARISON")
        print("="*80)
        print("Expected (from PDF):")
        print("  - Max diameter: 55.0 mm")
        print("  - Total length: 89.0 mm")
        print("  - Bore: Ø19 H7, depth 50 mm")
        print("  - Features: hole, thread M30×2, chamfers")

        if outer:
            max_r = max(pt.get("r", 0) for pt in outer)
            max_z = max(pt.get("z", 0) for pt in outer)
            print(f"\nExtracted:")
            print(f"  - Max diameter: {max_r * 2:.1f} mm (radius {max_r})")
            print(f"  - Total length: {max_z:.1f} mm")

        if inner:
            max_r_inner = max(pt.get("r", 0) for pt in inner)
            print(f"  - Bore diameter: {max_r_inner * 2:.1f} mm (radius {max_r_inner})")

        print(f"  - Features extracted: {len(features)}")
        for feat in features:
            print(f"    - {feat.get('type')}: {feat}")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_pdm_249322())
