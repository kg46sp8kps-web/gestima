#!/usr/bin/env python3
"""
Quick test: Vision API contour extraction on JR 810857
"""

import asyncio
from pathlib import Path
from app.services.vision_feature_extractor import VisionFeatureExtractor
from app.services.occt_waterline_extractor import WaterlineExtractor
from app.services.svg_contour_exporter import export_contour_to_svg
from app.services.pdf_contour_annotator import annotate_pdf_with_contour
from app.config import get_settings

settings = get_settings()

pdf_path = Path('uploads/drawings/JR 810857.pdf')
step_path = Path('uploads/drawings/JR810857.ipt.step')

print(f'Testing Vision API on: {pdf_path.name}')
print(f'STEP file: {step_path.name}')
print()

# Extract STEP geometry
extractor = WaterlineExtractor()
step_geometry = extractor.extract_waterline(step_path)
print(f'STEP waterline: {len(step_geometry.get("r_values", []))} points')
print(f'Segments: {len(step_geometry.get("segments", []))}')
print()

# Call Vision API
async def test_vision():
    vision = VisionFeatureExtractor(api_key=settings.ANTHROPIC_API_KEY)
    result = await vision.extract_features(pdf_path, step_geometry)

    if not result:
        print('❌ Vision API FAILED')
        return

    print(f'✅ Vision API SUCCESS')
    print(f'   Contour points: {len(result.get("contour", []))}')
    print(f'   Confidence: {result.get("confidence", 0)}')
    print(f'   Notes: {result.get("notes", "")}')
    print()

    contour = result['contour']

    print('First 5 contour points:')
    for i, pt in enumerate(contour[:5]):
        print(f'   Point {i}: z={pt["z"]:.2f}mm, r={pt["r"]:.2f}mm')
    print()

    # Export SVG
    svg_path = Path('uploads/contours/JR810857_contour.svg')
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    export_contour_to_svg(contour, step_geometry, svg_path)
    print(f'✅ SVG exported: {svg_path}')

    # Annotate PDF
    annotated_pdf = annotate_pdf_with_contour(pdf_path, contour, step_geometry)
    if annotated_pdf:
        print(f'✅ Annotated PDF: {annotated_pdf}')
    else:
        print('⚠️  PDF annotation failed')

asyncio.run(test_vision())
