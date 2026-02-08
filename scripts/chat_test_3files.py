"""
Chat Test - Process 3 files and show results inline
"""

import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.services.analysis_service import run_analysis
from app.services.profile_svg_renderer import render_profile_svg
from app.config import settings
import base64

TEST_FILES = [
    ("PDM-249322_03.stp", "PDM-249322_03_Gelso.pdf"),
    ("PDM-280739_03.stp", "PDM-280739_03_Gelso.pdf"),
    ("3DM_90057637_000_00.stp", "DRM_90057637_DE0_00.pdf"),
]

async def test_file(step_name, pdf_name):
    step_path = f"uploads/drawings/{step_name}"
    pdf_path = f"uploads/drawings/{pdf_name}"

    print(f"\n{'='*80}")
    print(f"📄 {step_name}")
    print(f"{'='*80}")

    try:
        # Read files
        with open(step_path, 'r', errors='ignore') as f:
            step_text = f.read()[:50000]

        with open(pdf_path, 'rb') as f:
            pdf_base64 = base64.b64encode(f.read()).decode('utf-8')

        # Run analysis
        result = await run_analysis(
            step_text=step_text,
            pdf_base64=pdf_base64,
            step_features=[],
            anthropic_api_key=settings.ANTHROPIC_API_KEY,
            pipeline_mode="deterministic",
            has_step=True,
            has_pdf=True,
            step_path=step_path,
            pdf_path=pdf_path
        )

        if result.get("success"):
            profile = result.get("profile_geometry", {})
            outer = profile.get("outer_contour", [])
            inner = profile.get("inner_contour", [])
            features = profile.get("features", [])

            max_d = max((pt.get("r", 0) * 2 for pt in outer), default=0)
            length = max((pt.get("z", 0) for pt in outer), default=0)
            bore = max((pt.get("r", 0) * 2 for pt in inner), default=0) if inner else 0

            print(f"✅ Part Type:     {result.get('part_type')}")
            print(f"   Material:      {result.get('material_spec')}")
            print(f"   Max Diameter:  Ø{max_d:.1f} mm")
            print(f"   Total Length:  {length:.1f} mm")
            print(f"   Bore Diameter: {'Ø' + f'{bore:.1f} mm' if bore > 0 else 'N/A'}")
            print(f"   Contour:       {len(outer)} outer + {len(inner)} inner points")
            print(f"   Features:      {len(features)}")
            print(f"   Confidence:    {result.get('confidence', 0):.2f}")

            # Show features
            if features:
                print(f"\n   Extracted Features:")
                for feat in features[:5]:  # First 5
                    print(f"   - {feat.get('type')}: {feat}")

            # Generate SVG
            try:
                svg = render_profile_svg(profile)
                svg_file = f"chat_test_{step_name.replace('.stp', '')}.svg.txt"
                with open(svg_file, 'w') as f:
                    f.write(svg)
                print(f"\n   💾 SVG saved: {svg_file} ({len(svg)} bytes)")
            except Exception as e:
                print(f"\n   ⚠️  SVG generation failed: {e}")

        else:
            print(f"❌ Error: {result.get('error')}")

    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

async def main():
    print("="*80)
    print("CHAT TEST - 3 Files with Claude Vision API")
    print("="*80)

    for step, pdf in TEST_FILES:
        await test_file(step, pdf)

    print(f"\n{'='*80}")
    print("✅ Chat test complete!")
    print(f"{'='*80}")

if __name__ == "__main__":
    asyncio.run(main())
