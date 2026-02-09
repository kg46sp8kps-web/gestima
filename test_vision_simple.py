"""Test simplified Vision-primary architecture

Vision = PRIMARY (always correct classification)
OCCT = SECONDARY (exact dimensions for validation)
"""

import asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from app.services.geometry_feature_extractor import GeometryFeatureExtractor
from app.services.pdf_vision_parser import PDFVisionParser

STEP_FILE = "uploads/drawings/JR 810663.ipt.step"
PDF_FILE = "uploads/drawings/JR 810663.idw_Gelso.pdf"


async def main():
    print("=" * 80)
    print("VISION-PRIMARY ARCHITECTURE TEST")
    print("=" * 80)
    print()

    # 1. VISION PARSING (PRIMARY - always correct!)
    print("[1/3] AI VISION PARSING (PRIMARY SOURCE)...")
    pdf_path = Path(PDF_FILE)
    if not pdf_path.exists():
        print(f"❌ PDF not found: {PDF_FILE}")
        return

    parser = PDFVisionParser()
    vision_data = parser.parse_drawing(pdf_path)

    if "error" in vision_data:
        print(f"❌ Vision failed: {vision_data['error']}")
        return

    print(f"✅ Vision parsing complete")
    print(f"   - Part type: {vision_data.get('part_type')} (ALWAYS CORRECT)")
    print(f"   - Confidence: {vision_data.get('confidence', 0):.0%}")
    print(f"   - Material: {vision_data.get('material', {}).get('code')} ({vision_data.get('material', {}).get('name')})")
    stock = vision_data.get('stock', {})
    print(f"   - Stock: {stock.get('type')} Ø{stock.get('diameter')}×{stock.get('length')} mm")
    print()

    # 2. OCCT EXTRACTION (for exact dimensions only)
    print("[2/3] OCCT EXTRACTION (exact dimensions)...")
    step_path = Path(STEP_FILE)
    if not step_path.exists():
        print(f"❌ STEP not found: {STEP_FILE}")
        return

    extractor = GeometryFeatureExtractor()
    occt_features = extractor.extract_features(step_path, "20910000")

    print(f"✅ OCCT extraction complete")
    print(f"   - Part bbox: {occt_features.bbox_x_mm:.1f} × {occt_features.bbox_y_mm:.1f} × {occt_features.bbox_z_mm:.1f} mm")
    print(f"   - Part volume: {occt_features.part_volume_mm3:.0f} mm³")
    print(f"   - Surface area: {occt_features.surface_area_mm2:.0f} mm²")
    print()

    # 3. VALIDATION (compare Vision stock vs OCCT bbox)
    print("[3/3] DIMENSION VALIDATION...")
    occt_max_dim = max(occt_features.bbox_x_mm, occt_features.bbox_y_mm)
    vision_stock_dim = stock.get("diameter", 0)
    dimension_diff_mm = abs(occt_max_dim - vision_stock_dim)
    dimension_diff_pct = dimension_diff_mm / vision_stock_dim * 100 if vision_stock_dim > 0 else 0

    print(f"   Vision stock Ø: {vision_stock_dim:.1f} mm")
    print(f"   OCCT part max:  {occt_max_dim:.1f} mm")
    print(f"   Difference:     {dimension_diff_mm:.1f} mm ({dimension_diff_pct:.1f}%)")

    if dimension_diff_pct > 20:
        print(f"   ⚠️  WARNING: >20% mismatch - needs manual review!")
    else:
        print(f"   ✅ Good match - stock fits part")
    print()

    # SUMMARY
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Classification: {vision_data.get('part_type')} (from Vision - ALWAYS CORRECT)")
    print(f"Material: {vision_data.get('material', {}).get('code')}")
    print(f"Stock: {stock.get('type')} Ø{stock.get('diameter')}×{stock.get('length')} mm")
    print(f"Part dimensions: {occt_features.bbox_x_mm:.1f}×{occt_features.bbox_y_mm:.1f}×{occt_features.bbox_z_mm:.1f} mm (from OCCT)")
    print(f"Needs review: {'YES' if dimension_diff_pct > 20 or vision_data.get('confidence', 0) < 0.7 else 'NO'}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
