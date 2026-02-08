#!/usr/bin/env python3
"""Update batch_estimation_results.json to use material group codes instead of hardcoded 16MnCr5.

This script updates the existing batch results file to replace "16MnCr5" with "OCEL-AUTO"
(the default material code from MaterialGroup table).

Usage:
    python app/scripts/update_batch_results_material.py
"""

import json
import sys
from pathlib import Path


def main():
    """Update batch results with correct material code."""

    results_file = Path("batch_estimation_results.json")
    backup_file = Path("batch_estimation_results.json.backup")

    if not results_file.exists():
        print(f"ERROR: {results_file} not found")
        sys.exit(1)

    # Load existing results
    with open(results_file, "r", encoding="utf-8") as f:
        results = json.load(f)

    print(f"Loaded {len(results)} results from {results_file}")

    # Create backup
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Created backup at {backup_file}")

    # Update material codes
    updated_count = 0
    for result in results:
        if result.get("material") == "16MnCr5":
            result["material"] = "OCEL-AUTO"
            updated_count += 1

        # Also update in breakdown
        if result.get("breakdown", {}).get("material") == "16MnCr5":
            result["breakdown"]["material"] = "OCEL-AUTO"

    print(f"Updated {updated_count} records: 16MnCr5 → OCEL-AUTO")

    # Save updated results
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Saved updated results to {results_file}")
    print("\nDone! Material codes updated successfully.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
