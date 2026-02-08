"""
Visual Inspection Batch Test - Direct Service Call

Directly calls analysis_service without HTTP API (no auth needed).

Usage:
    python scripts/visual_inspection_batch_direct.py
"""

import asyncio
import json
import logging
import os
import base64
from pathlib import Path
from typing import List, Dict, Any
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env for API key
from dotenv import load_dotenv
load_dotenv()

from app.services.analysis_service import run_analysis
from app.services.profile_svg_renderer import render_profile_svg
from app.config import settings
# Note: We don't need STEP features for AI Vision pipeline (deterministic mode)

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

DRAWINGS_DIR = Path("uploads/drawings")
# Get API key from app config (loads from .env)
ANTHROPIC_API_KEY = settings.ANTHROPIC_API_KEY


def find_step_pdf_pairs() -> List[Dict[str, str]]:
    """Find all STEP+PDF pairs."""
    step_files = sorted(list(DRAWINGS_DIR.glob("*.stp")) + list(DRAWINGS_DIR.glob("*.step")))

    pairs = []
    for step_file in step_files:
        base_name = step_file.stem

        # Handle .ipt.step → .idw_Gelso.pdf pattern
        base_for_pdf = base_name.replace(".ipt", "").replace(".IPT", "")

        pdf_candidates = [
            DRAWINGS_DIR / f"{base_name}.pdf",
            DRAWINGS_DIR / f"{base_name}_Gelso.pdf",
            DRAWINGS_DIR / f"{base_for_pdf}.idw_Gelso.pdf",  # JR 810663.ipt → JR 810663.idw_Gelso.pdf
            DRAWINGS_DIR / f"{base_name.replace('_3D', '_2D')}_Gelso.pdf",
            DRAWINGS_DIR / f"{base_name.replace('.1', '.3')}_2D_Gelso.pdf",
        ]

        # Special mappings
        special_mappings = {
            "10138363-01_21.03.2024": "10138363_01 Kunde_Gelso.pdf",
            "3DM_90057637_000_00": "DRM_90057637_DE0_00.pdf",
        }
        if base_name in special_mappings:
            pdf_candidates.insert(0, DRAWINGS_DIR / special_mappings[base_name])

        pdf_file = next((c for c in pdf_candidates if c.exists()), None)

        if pdf_file:
            pairs.append({
                "step": step_file.name,
                "pdf": pdf_file.name,
                "step_path": str(step_file),
                "pdf_path": str(pdf_file)
            })
        else:
            logger.warning(f"⚠️  No PDF for {step_file.name}")

    return pairs


async def test_single_pair(pair: Dict[str, str], index: int, total: int) -> Dict[str, Any]:
    """Test single STEP+PDF pair."""
    logger.info(f"[{index}/{total}] {pair['step']}")

    try:
        # Read STEP file
        with open(pair['step_path'], 'r', errors='ignore') as f:
            step_text = f.read()[:50000]  # First 50KB

        # Parse STEP features (empty for AI Vision - not needed)
        step_features = []  # AI Vision doesn't need pre-parsed STEP features

        # Read PDF
        with open(pair['pdf_path'], 'rb') as f:
            pdf_bytes = f.read()
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

        # Call analysis service directly
        result = await run_analysis(
            step_text=step_text,
            pdf_base64=pdf_base64,
            step_features=step_features,
            anthropic_api_key=ANTHROPIC_API_KEY,
            pipeline_mode="deterministic",  # AI Vision pipeline
            has_step=True,
            has_pdf=True,
            step_path=pair['step_path'],
            pdf_path=pair['pdf_path']
        )

        if result.get("success"):
            # Extract metrics
            profile = result.get("profile_geometry", {})
            outer = profile.get("outer_contour", [])
            inner = profile.get("inner_contour", [])
            features = profile.get("features", [])

            max_diameter = max((pt.get("r", 0) * 2 for pt in outer), default=0)
            total_length = max((pt.get("z", 0) for pt in outer), default=0)
            bore_diameter = max((pt.get("r", 0) * 2 for pt in inner), default=0) if inner else 0

            # Generate SVG visualization
            svg_data = ""
            try:
                svg_data = render_profile_svg(profile)
            except Exception as svg_err:
                logger.warning(f"  ⚠️  SVG generation failed: {svg_err}")

            logger.info(
                f"  ✓ Ø{max_diameter:.0f}mm × {total_length:.0f}mm, "
                f"{len(outer)}+{len(inner)} pts, {len(features)} feat, "
                f"conf={result.get('confidence', 0):.2f}"
            )

            return {
                "index": index,
                "filename": pair['step'],
                "pdf": pair['pdf'],
                "status": "success",
                "part_type": result.get("part_type"),
                "material": result.get("material_spec"),
                "confidence": result.get("confidence", 0),
                "metrics": {
                    "max_diameter": round(max_diameter, 1),
                    "total_length": round(total_length, 1),
                    "bore_diameter": round(bore_diameter, 1),
                    "outer_points": len(outer),
                    "inner_points": len(inner),
                    "features_count": len(features)
                },
                "features": features[:10],  # Limit to 10 features for HTML size
                "profile_geometry": profile,
                "svg_data": svg_data,  # Base64 encoded SVG
                "raw_result": result
            }
        else:
            error = result.get("error", "Unknown error")
            logger.info(f"  ✗ {error[:80]}")
            return {
                "index": index,
                "filename": pair['step'],
                "pdf": pair['pdf'],
                "status": "error",
                "error": error
            }

    except Exception as e:
        logger.error(f"  ✗ Exception: {e}")
        return {
            "index": index,
            "filename": pair['step'],
            "pdf": pair['pdf'],
            "status": "error",
            "error": str(e)
        }


async def run_batch_test():
    """Run batch test."""
    logger.info("="*80)
    logger.info("VISUAL INSPECTION BATCH TEST - All 37 Files")
    logger.info("="*80)

    if not ANTHROPIC_API_KEY:
        logger.error("❌ ANTHROPIC_API_KEY not set!")
        return

    pairs = find_step_pdf_pairs()
    logger.info(f"Found {len(pairs)} STEP+PDF pairs\n")

    results = []
    for i, pair in enumerate(pairs, 1):
        result = await test_single_pair(pair, i, len(pairs))
        results.append(result)

    # Save results
    output_file = Path("docs/testing/visual_inspection_results.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    success_count = sum(1 for r in results if r["status"] == "success")

    logger.info(f"\n{'='*80}")
    logger.info(f"✅ Success: {success_count}/{len(results)}")
    logger.info(f"💾 Results: {output_file}")
    logger.info(f"{'='*80}")

    # Generate HTML report
    from scripts.visual_inspection_batch import generate_html_report
    generate_html_report(results)

    return results


if __name__ == "__main__":
    asyncio.run(run_batch_test())
