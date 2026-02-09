"""GESTIMA - Batch Feature Extraction for 37 STEP Parts (Phase 2)

Extracts 79 geometry features from all STEP files in uploads/drawings/
and populates turning_estimations / milling_estimations tables.

Classification:
- rotational_score > 0.6 → TurningEstimation (ROT)
- rotational_score ≤ 0.6 → MillingEstimation (PRI)

Expected split: 16 turning + 21 milling = 37 total

Usage:
    python scripts/batch_extract_features_37_parts.py
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import async_session
from app.services.geometry_feature_extractor import GeometryFeatureExtractor
from app.models.turning_estimation import TurningEstimation
from app.models.milling_estimation import MillingEstimation

STEP_DIR = Path("uploads/drawings/")
ROT_THRESHOLD = 0.6  # rotational_score > 0.6 = turning
MATERIAL_CODE_DEFAULT = "20910000"  # Ocel automatová


async def process_all_step_files():
    """
    Extract features from all STEP files and populate DB.

    Returns:
        dict: Summary with turning/milling counts and errors
    """
    extractor = GeometryFeatureExtractor()
    step_files = sorted(STEP_DIR.glob("*.st*p"))

    results = {
        "turning": [],
        "milling": [],
        "errors": [],
        "volume_conservation_errors": []
    }

    print(f"Found {len(step_files)} STEP files in {STEP_DIR}")
    print("=" * 80)

    async with async_session() as session:
        for step_file in step_files:
            try:
                # Extract features
                print(f"Processing: {step_file.name}...", end=" ")
                features = extractor.extract_features(step_file, MATERIAL_CODE_DEFAULT)

                # Classify ROT vs PRI
                is_turning = features.rotational_score > ROT_THRESHOLD

                # Volume conservation check (<1% error)
                removal_calc = features.stock_volume_mm3 - features.part_volume_mm3
                removal_measured = features.removal_volume_mm3
                if removal_calc > 0:  # Skip if no stock (unexpected)
                    error_pct = abs(removal_calc - removal_measured) / removal_calc * 100
                    if error_pct > 1.0:
                        results["volume_conservation_errors"].append({
                            "file": step_file.name,
                            "error_pct": error_pct,
                            "removal_calc": removal_calc,
                            "removal_measured": removal_measured
                        })

                # Prepare DB record
                feature_dict = features.model_dump(exclude={"extraction_timestamp"})
                feature_dict["extraction_timestamp"] = datetime.fromisoformat(features.extraction_timestamp)

                # Create record
                if is_turning:
                    record = TurningEstimation(**feature_dict)
                    session.add(record)
                    results["turning"].append(step_file.name)
                    print(f"✓ TURNING (rot={features.rotational_score:.2f})")
                else:
                    record = MillingEstimation(**feature_dict)
                    session.add(record)
                    results["milling"].append(step_file.name)
                    print(f"✓ MILLING (rot={features.rotational_score:.2f})")

                await session.commit()

            except SQLAlchemyError as e:
                await session.rollback()
                results["errors"].append({"file": step_file.name, "error": f"DB error: {str(e)}"})
                print(f"❌ DB ERROR: {e}")

            except Exception as e:
                await session.rollback()
                results["errors"].append({"file": step_file.name, "error": str(e)})
                print(f"❌ EXTRACTION ERROR: {e}")

    # Print summary
    print("\n" + "=" * 80)
    print("BATCH EXTRACTION COMPLETE")
    print("=" * 80)
    print(f"✓ Turning parts:  {len(results['turning'])}")
    print(f"✓ Milling parts:  {len(results['milling'])}")
    print(f"✓ Total success:  {len(results['turning']) + len(results['milling'])}")
    print(f"❌ Errors:         {len(results['errors'])}")
    print(f"⚠️  Volume errors: {len(results['volume_conservation_errors'])} (>1% error)")
    print("=" * 80)

    # Detailed error reports
    if results["errors"]:
        print("\nERROR DETAILS:")
        for err in results["errors"]:
            print(f"  - {err['file']}: {err['error']}")

    if results["volume_conservation_errors"]:
        print("\nVOLUME CONSERVATION WARNINGS (>1% error):")
        for err in results["volume_conservation_errors"]:
            print(f"  - {err['file']}: {err['error_pct']:.2f}% error "
                  f"(calc={err['removal_calc']:.0f}, meas={err['removal_measured']:.0f})")

    # List turning parts
    if results["turning"]:
        print("\nTURNING PARTS (16 expected):")
        for fname in results["turning"]:
            print(f"  - {fname}")

    # List milling parts
    if results["milling"]:
        print("\nMILLING PARTS (21 expected):")
        for fname in results["milling"]:
            print(f"  - {fname}")

    return results


if __name__ == "__main__":
    print("GESTIMA - Batch Feature Extraction (Phase 2)")
    print("Processing 37 STEP files from uploads/drawings/")
    print("Populating turning_estimations + milling_estimations tables\n")

    results = asyncio.run(process_all_step_files())

    # Exit code
    if results["errors"]:
        print("\n⚠️  WARNING: Some files failed to process (see errors above)")
        sys.exit(1)
    else:
        print("\n✅ SUCCESS: All 37 parts processed!")
        sys.exit(0)
