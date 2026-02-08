"""
GESTIMA - Geometry Extraction Accuracy Test

Testuje přesnost AI extrakce geometrie na všech STEP+PDF souborech.

Usage:
    python scripts/test_geometry_extraction_accuracy.py

Output:
    - docs/testing/extraction_results.json (detailed results)
    - docs/testing/accuracy_report.md (summary report)
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.geometry_extractor import GeometryExtractorService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_ground_truth() -> Dict[str, Any]:
    """Load ground truth dataset for comparison."""
    gt_path = Path("docs/testing/ground_truth_template.json")
    if not gt_path.exists():
        logger.warning("Ground truth file not found, creating empty dict")
        return {}

    with open(gt_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Index by filename for easy lookup
    return {item["filename"]: item for item in data.get("ground_truth_dataset", [])}


def find_step_pdf_pairs(directory: str = "uploads/drawings") -> List[Dict[str, str]]:
    """Find all STEP+PDF pairs in directory."""
    drawings_dir = Path(directory)
    step_files = list(drawings_dir.glob("*.stp")) + list(drawings_dir.glob("*.step"))

    pairs = []
    for step_file in step_files:
        # Look for matching PDF
        base_name = step_file.stem
        pdf_candidates = [
            drawings_dir / f"{base_name}.pdf",
            drawings_dir / f"{base_name}_Gelso.pdf",
            # Handle cases like "0304663_D00043519_000.1_3D.stp" → "0304663_D00043519_000.3_2D_Gelso.pdf"
            drawings_dir / f"{base_name.replace('_3D', '_2D')}_Gelso.pdf",
            drawings_dir / f"{base_name.replace('.1', '.3')}_2D_Gelso.pdf"
        ]

        pdf_file = None
        for candidate in pdf_candidates:
            if candidate.exists():
                pdf_file = candidate
                break

        if pdf_file:
            pairs.append({
                "step": str(step_file),
                "pdf": str(pdf_file),
                "filename": step_file.name
            })
        else:
            logger.warning(f"No PDF found for {step_file.name}")

    return pairs


def calculate_contour_accuracy(extracted: List[Dict], ground_truth: List[Dict]) -> float:
    """
    Calculate accuracy of contour extraction.

    Compares number of points and critical dimensions.
    Returns accuracy percentage (0-100).
    """
    if not ground_truth:
        return 0.0  # No ground truth to compare

    if not extracted:
        return 0.0  # Extraction failed

    # Compare number of points (should be within 20%)
    gt_count = len(ground_truth)
    ex_count = len(extracted)
    count_ratio = min(ex_count, gt_count) / max(ex_count, gt_count)

    # Compare critical r values (max, min)
    gt_max_r = max(pt.get("r", 0) for pt in ground_truth)
    ex_max_r = max(pt.get("r", 0) for pt in extracted)

    if gt_max_r > 0:
        r_accuracy = 1.0 - abs(ex_max_r - gt_max_r) / gt_max_r
        r_accuracy = max(0, min(1, r_accuracy))  # Clamp to [0, 1]
    else:
        r_accuracy = 0.0

    # Weighted average
    accuracy = (count_ratio * 0.3 + r_accuracy * 0.7) * 100
    return accuracy


def calculate_features_accuracy(extracted: List[Dict], ground_truth: List[Dict]) -> float:
    """
    Calculate accuracy of feature extraction.

    Checks if critical features are present with correct parameters.
    """
    if not ground_truth:
        return 0.0

    if not extracted:
        return 0.0

    # Count matching features by type
    gt_features = {f["type"]: f for f in ground_truth}
    ex_features = {f["type"]: f for f in extracted}

    matched = 0
    for ftype, gt_feat in gt_features.items():
        if ftype in ex_features:
            ex_feat = ex_features[ftype]

            # Check critical parameters
            param_match = True
            for key in ["diameter", "depth", "width", "pitch"]:
                if key in gt_feat:
                    gt_val = gt_feat[key]
                    ex_val = ex_feat.get(key)

                    if ex_val is None:
                        param_match = False
                        break

                    # Allow 5% tolerance on numeric values
                    if abs(ex_val - gt_val) / gt_val > 0.05:
                        param_match = False
                        break

            if param_match:
                matched += 1

    accuracy = (matched / len(gt_features)) * 100 if gt_features else 0.0
    return accuracy


async def test_single_file(
    step_file: str,
    pdf_file: str,
    filename: str,
    ground_truth: Optional[Dict] = None
) -> Dict[str, Any]:
    """Test geometry extraction on a single STEP+PDF pair."""
    logger.info(f"Testing: {filename}")

    service = GeometryExtractorService()

    try:
        result = await service.extract_geometry(step_file, pdf_file)

        # Extract key metrics
        profile = result.get("profile_geometry", {})
        outer_contour = profile.get("outer_contour", [])
        inner_contour = profile.get("inner_contour", [])
        features = profile.get("features", [])

        # Calculate accuracy if ground truth available
        outer_accuracy = 0.0
        inner_accuracy = 0.0
        features_accuracy = 0.0

        if ground_truth and ground_truth.get("verified_by") != "TODO":
            gt_outer = ground_truth.get("outer_contour", [])
            gt_inner = ground_truth.get("inner_contour", [])
            gt_features = ground_truth.get("features", [])

            if gt_outer:
                outer_accuracy = calculate_contour_accuracy(outer_contour, gt_outer)
            if gt_inner:
                inner_accuracy = calculate_contour_accuracy(inner_contour, gt_inner)
            if gt_features:
                features_accuracy = calculate_features_accuracy(features, gt_features)

        return {
            "filename": filename,
            "status": "success",
            "part_type": result.get("part_type"),
            "material": result.get("material_spec"),
            "outer_contour_points": len(outer_contour),
            "inner_contour_points": len(inner_contour),
            "features_count": len(features),
            "confidence": result.get("confidence", 0.0),
            "accuracy": {
                "outer_contour": outer_accuracy,
                "inner_contour": inner_accuracy,
                "features": features_accuracy,
                "overall": (outer_accuracy + inner_accuracy + features_accuracy) / 3
            },
            "extracted_data": result
        }

    except Exception as e:
        logger.error(f"Error testing {filename}: {e}", exc_info=True)
        return {
            "filename": filename,
            "status": "error",
            "error": str(e),
            "accuracy": {
                "outer_contour": 0.0,
                "inner_contour": 0.0,
                "features": 0.0,
                "overall": 0.0
            }
        }


async def run_batch_test():
    """Run batch test on all STEP+PDF pairs."""
    logger.info("=" * 80)
    logger.info("GEOMETRY EXTRACTION ACCURACY TEST")
    logger.info("=" * 80)

    # Load ground truth
    ground_truth = load_ground_truth()
    logger.info(f"Loaded ground truth for {len(ground_truth)} files")

    # Find all STEP+PDF pairs
    pairs = find_step_pdf_pairs()
    logger.info(f"Found {len(pairs)} STEP+PDF pairs")

    if not pairs:
        logger.error("No STEP+PDF pairs found in uploads/drawings/")
        return

    # Test each pair
    results = []
    for i, pair in enumerate(pairs, 1):
        logger.info(f"[{i}/{len(pairs)}] Testing {pair['filename']}...")

        gt = ground_truth.get(pair['filename'])
        result = await test_single_file(
            pair['step'],
            pair['pdf'],
            pair['filename'],
            gt
        )
        results.append(result)

        # Show accuracy if available
        if result["accuracy"]["overall"] > 0:
            logger.info(f"  → Accuracy: {result['accuracy']['overall']:.1f}%")

    # Save detailed results
    output_file = Path("docs/testing/extraction_results.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"\nDetailed results saved to: {output_file}")

    # Generate summary report
    generate_summary_report(results)

    return results


def generate_summary_report(results: List[Dict[str, Any]]):
    """Generate markdown summary report."""
    report_path = Path("docs/testing/accuracy_report.md")

    # Calculate statistics
    total = len(results)
    success = sum(1 for r in results if r["status"] == "success")
    error = total - success

    # Accuracy stats (only for files with ground truth)
    measured = [r for r in results if r["accuracy"]["overall"] > 0]
    avg_accuracy = sum(r["accuracy"]["overall"] for r in measured) / len(measured) if measured else 0

    # Confidence stats
    confidences = [r.get("confidence", 0) for r in results if r["status"] == "success"]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0

    # Generate report
    report = f"""# Geometry Extraction Accuracy Report

**Date:** {Path(__file__).stat().st_mtime}
**Total Files:** {total}
**Success Rate:** {success}/{total} ({success/total*100:.1f}%)

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| **Total files tested** | {total} |
| **Successful extractions** | {success} ({success/total*100:.1f}%) |
| **Failed extractions** | {error} ({error/total*100:.1f}%) |
| **Average confidence** | {avg_confidence:.2f} |
| **Files with ground truth** | {len(measured)} |
| **Average accuracy (measured)** | {avg_accuracy:.1f}% |

---

## Detailed Results

### Files with Accuracy Measurement

| Filename | Overall | Outer Contour | Inner Contour | Features | Confidence |
|----------|---------|---------------|---------------|----------|------------|
"""

    # Add measured files
    for r in sorted(measured, key=lambda x: x["accuracy"]["overall"], reverse=True):
        acc = r["accuracy"]
        conf = r.get("confidence", 0)
        report += f"| {r['filename']} | {acc['overall']:.1f}% | {acc['outer_contour']:.1f}% | {acc['inner_contour']:.1f}% | {acc['features']:.1f}% | {conf:.2f} |\n"

    report += "\n### Files without Ground Truth\n\n"
    report += "| Filename | Part Type | Points (Outer/Inner) | Features | Confidence |\n"
    report += "|----------|-----------|---------------------|----------|------------|\n"

    unmeasured = [r for r in results if r["status"] == "success" and r["accuracy"]["overall"] == 0]
    for r in unmeasured:
        outer_pts = r.get("outer_contour_points", 0)
        inner_pts = r.get("inner_contour_points", 0)
        feat_count = r.get("features_count", 0)
        conf = r.get("confidence", 0)
        part_type = r.get("part_type", "unknown")
        report += f"| {r['filename']} | {part_type} | {outer_pts}/{inner_pts} | {feat_count} | {conf:.2f} |\n"

    if error > 0:
        report += "\n### Failed Extractions\n\n"
        report += "| Filename | Error |\n"
        report += "|----------|-------|\n"

        failed = [r for r in results if r["status"] == "error"]
        for r in failed:
            report += f"| {r['filename']} | {r.get('error', 'Unknown error')} |\n"

    report += f"""
---

## Next Steps

### If accuracy < 95%:
1. Analyze failing files (lowest accuracy)
2. Identify common error patterns
3. Improve prompt in `geometry_extractor.py`
4. Re-run this test
5. Repeat until accuracy ≥ 95%

### If accuracy ≥ 95%:
1. Freeze prompt
2. Move to Phase 2: Time calculation calibration
3. Collect shop floor data (actual times)
4. Implement calibration layer

---

## Files

- **Detailed results:** `docs/testing/extraction_results.json`
- **Ground truth:** `docs/testing/ground_truth_template.json`
- **Test script:** `scripts/test_geometry_extraction_accuracy.py`
"""

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    logger.info(f"Summary report saved to: {report_path}")
    logger.info(f"\n{'='*80}")
    logger.info(f"OVERALL ACCURACY: {avg_accuracy:.1f}% (based on {len(measured)} measured files)")
    logger.info(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(run_batch_test())
