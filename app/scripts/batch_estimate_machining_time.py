#!/usr/bin/env python3
"""
Batch Machining Time Estimation Script

Processes all STEP files in uploads/drawings and exports results to JSON + CSV.

Usage:
    python app/scripts/batch_estimate_machining_time.py

Output:
    - batch_estimation_results.json
    - batch_estimation_results.csv
    - batch_estimation_consistency_log.txt (3-run determinism test)

Consistency Testing:
    Each file is processed 3 times to verify 100% deterministic results.
"""

import json
import csv
import sys
import logging
from pathlib import Path
from statistics import stdev

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.machining_time_estimation_service import MachiningTimeEstimationService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def test_determinism(
    step_file: Path,
    material: str = "20910003",
    runs: int = 3
) -> tuple[bool, list[float]]:
    """
    Test if estimation is 100% deterministic across multiple runs.

    Args:
        step_file: Path to STEP file
        material: Material group code (default: "20910003" = Ocel automatová)
        runs: Number of runs (default 3)

    Returns:
        (is_deterministic, times_list)
    """
    times = []

    for run_idx in range(runs):
        try:
            result = MachiningTimeEstimationService.estimate_time(
                step_path=step_file,
                material=material,
                stock_type="bbox"
            )
            times.append(result["total_time_min"])
        except Exception as e:
            logger.warning(f"Determinism test run {run_idx + 1} failed: {e}")
            return False, []

    # Check if all values are identical
    is_deterministic = len(set(times)) == 1

    return is_deterministic, times


def main():
    """Main batch processing function."""

    drawings_dir = Path("uploads/drawings")
    default_material = "20910003"  # Ocel automatová

    if not drawings_dir.exists():
        logger.error(f"Directory not found: {drawings_dir}")
        sys.exit(1)

    logger.info("=" * 70)
    logger.info("GESTIMA BATCH MACHINING TIME ESTIMATION")
    logger.info("=" * 70)
    logger.info(f"Default material: {default_material}")

    # Phase 1: Estimate all files
    logger.info("\n[Phase 1] Estimating machining times...")

    step_files = sorted(
        list(drawings_dir.glob("**/*.step")) + list(drawings_dir.glob("**/*.stp"))
    )

    logger.info(f"Found {len(step_files)} STEP files")

    results = []
    errors = []

    for idx, step_file in enumerate(step_files, 1):
        try:
            logger.info(f"[{idx}/{len(step_files)}] Processing {step_file.name}...")

            result = MachiningTimeEstimationService.estimate_time(
                step_path=step_file,
                material=default_material,
                stock_type="bbox"
            )

            # Convert to format expected by output
            result_dict = {
                "filename": step_file.name,
                "material": default_material,
                "setup_time_min": result["setup_time_min"],
                "roughing_time_min": result["roughing_time_min"],
                "roughing_time_main": result["roughing_time_main"],
                "roughing_time_aux": result["roughing_time_aux"],
                "finishing_time_min": result["finishing_time_min"],
                "finishing_time_main": result["finishing_time_main"],
                "finishing_time_aux": result["finishing_time_aux"],
                "total_time_min": result["total_time_min"],
                "breakdown": result["breakdown"],
                "deterministic": result["deterministic"],
            }

            results.append(result_dict)

            logger.info(f"  ✓ {result['total_time_min']:.2f} min ({default_material})")

        except Exception as e:
            logger.error(f"  ✗ ERROR: {e}")
            errors.append({
                "filename": step_file.name,
                "error": str(e)
            })

    if not results:
        logger.error("No results generated. Check OCCT installation.")
        sys.exit(1)

    logger.info(f"\nProcessed {len(results)} files successfully")
    if errors:
        logger.warning(f"Failed to process {len(errors)} files")
    
    # Phase 2: Determinism testing (sample first 5 files)
    logger.info("\n[Phase 2] Testing determinism (sampling first 5 files, 3 runs each)...")
    
    step_files = sorted(
        list(drawings_dir.glob("**/*.step")) + list(drawings_dir.glob("**/*.stp"))
    )
    sample_files = step_files[:5]
    
    determinism_log = []
    all_deterministic = True
    
    for step_file in sample_files:
        is_det, times = test_determinism(step_file, runs=3)
        status = "PASS" if is_det else "FAIL"
        
        log_entry = {
            "filename": step_file.name,
            "deterministic": is_det,
            "times": times,
            "status": status,
        }
        determinism_log.append(log_entry)
        
        times_str = ", ".join(f"{t:.2f}" for t in times)
        logger.info(f"  {status}: {step_file.name} → [{times_str}] min")
        
        if not is_det:
            all_deterministic = False
    
    # Phase 3: Export JSON
    logger.info("\n[Phase 3] Exporting results...")
    
    output_json = Path("batch_estimation_results.json")
    with open(output_json, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"  JSON: {output_json} ({len(results)} records)")
    
    # Phase 4: Export CSV
    output_csv = Path("batch_estimation_results.csv")
    with open(output_csv, "w", newline="") as f:
        fieldnames = [
            "filename",
            "material",
            "part_volume_mm3",
            "stock_volume_mm3",
            "material_to_remove_mm3",
            "surface_area_mm2",
            "setup_time_min",
            "roughing_time_min",
            "finishing_time_min",
            "total_time_min",
            "constraint_multiplier",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for r in results:
            bd = r["breakdown"]
            writer.writerow({
                "filename": r["filename"],
                "material": bd["material"],
                "part_volume_mm3": bd["part_volume_mm3"],
                "stock_volume_mm3": bd["stock_volume_mm3"],
                "material_to_remove_mm3": bd["material_to_remove_mm3"],
                "surface_area_mm2": bd["surface_area_mm2"],
                "setup_time_min": r["setup_time_min"],
                "roughing_time_min": r["roughing_time_min"],
                "finishing_time_min": r["finishing_time_min"],
                "total_time_min": r["total_time_min"],
                "constraint_multiplier": bd["constraint_multiplier"],
            })
    logger.info(f"  CSV: {output_csv} ({len(results)} records)")
    
    # Phase 5: Export determinism log
    output_log = Path("batch_estimation_consistency_log.txt")
    with open(output_log, "w") as f:
        f.write("GESTIMA BATCH ESTIMATION - DETERMINISM TEST LOG\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Total files processed: {len(results)}\n")
        f.write(f"Determinism tests: {len(determinism_log)} samples\n")
        f.write(f"All deterministic: {'YES' if all_deterministic else 'NO'}\n\n")
        
        for entry in determinism_log:
            f.write(f"File: {entry['filename']}\n")
            f.write(f"Status: {entry['status']}\n")
            times_str = ", ".join(f"{t:.2f}" for t in entry['times'])
            f.write(f"Times: {times_str} min\n")
            if entry['times'] and len(entry['times']) > 1:
                variance = 0.0 if len(set(entry['times'])) == 1 else stdev(entry['times'])
                f.write(f"Variance: {variance:.4f}\n")
            f.write("\n")
    
    logger.info(f"  Log: {output_log}")
    
    # Phase 6: Summary statistics
    logger.info("\n[Phase 6] Summary Statistics")
    logger.info("=" * 70)
    
    times_list = [r["total_time_min"] for r in results]
    
    avg_time = sum(times_list) / len(times_list) if times_list else 0
    min_time = min(times_list) if times_list else 0
    max_time = max(times_list) if times_list else 0
    
    logger.info(f"Files processed: {len(results)}")
    logger.info(f"Average time: {avg_time:.2f} min")
    logger.info(f"Min time: {min_time:.2f} min")
    logger.info(f"Max time: {max_time:.2f} min")
    
    # Material distribution
    materials = {}
    for r in results:
        mat = r["breakdown"]["material"]
        materials[mat] = materials.get(mat, 0) + 1

    logger.info(f"\nMaterial distribution:")
    for mat, count in sorted(materials.items()):
        pct = count/len(results)*100
        logger.info(f"  {mat}: {count} files ({pct:.1f}%)")
    
    # Constraint analysis
    constrained = [r for r in results if r["breakdown"]["constraint_multiplier"] > 1.0]
    pct_constrained = len(constrained)/len(results)*100
    logger.info(f"\nConstrained parts (multiplier > 1.0): {len(constrained)} ({pct_constrained:.1f}%)")
    
    # Determinism result
    det_status = "PASS" if all_deterministic else "FAIL"
    logger.info(f"\nDeterminism test: {det_status}")
    if all_deterministic:
        logger.info("  All sampled files produced identical results across 3 runs")
    else:
        logger.warning("  Some files showed inconsistent results")
    
    logger.info("\n" + "=" * 70)
    logger.info("BATCH PROCESSING COMPLETE")
    logger.info("=" * 70)
    
    return 0 if all_deterministic else 1


if __name__ == "__main__":
    sys.exit(main())
