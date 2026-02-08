"""Quick test - Generate SVG for ONE file to verify it works."""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.services.analysis_service import run_analysis
from app.services.profile_svg_renderer import render_profile_svg
from app.config import settings
import base64

async def test_one_file():
    # Test PDM-249322_03 (known good file)
    step_path = "uploads/drawings/PDM-249322_03.stp"
    pdf_path = "uploads/drawings/PDM-249322_03_Gelso.pdf"

    print(f"Testing: {step_path}")

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
        print(f"\n✓ Profile extracted: {len(profile.get('outer_contour', []))} outer points")

        # Generate SVG
        svg = render_profile_svg(profile)
        print(f"✓ SVG generated: {len(svg)} bytes")

        # Save to file
        with open("test_svg_output.html", "w") as f:
            f.write(f"""<!DOCTYPE html>
<html>
<head><title>SVG Test</title></head>
<body>
<h1>PDM-249322_03 - SVG Contour Test</h1>
<img src="data:image/svg+xml;base64,{svg}" style="border: 1px solid #ccc; background: white;" />
</body>
</html>""")

        print(f"\n✅ HTML saved: test_svg_output.html")
        print(f"Open: file://{Path('test_svg_output.html').absolute()}")
    else:
        print(f"\n❌ Error: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(test_one_file())
