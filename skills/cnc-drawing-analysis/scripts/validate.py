#!/usr/bin/env python3
"""Validate extracted drawing data for consistency.

Checks:
- PRI parts must have null max_diameter_mm
- ROT parts must have non-null max_diameter_mm
- Dimensions must be positive
- Required fields present

Usage:
    python validate.py '{"part_type": "PRI", ...}'
"""
import json
import sys


def validate(data: dict) -> list:
    """Validate extraction data. Returns list of error strings (empty = OK)."""
    errors = []

    # Required fields
    required = ["part_type", "complexity", "material_hint", "operations"]
    for field in required:
        if field not in data or data[field] is None:
            errors.append(f"MISSING: '{field}' is required")

    pt = data.get("part_type", "")

    # Part type consistency
    if pt == "PRI":
        if data.get("max_diameter_mm") is not None:
            errors.append(
                f"INCONSISTENT: PRI part should have max_diameter_mm=null, "
                f"got {data['max_diameter_mm']}. "
                f"Did you confuse a HOLE diameter for the part diameter?"
            )
        if data.get("max_width_mm") is None and data.get("max_height_mm") is None:
            errors.append("WARNING: PRI part should have width and height dimensions")

    elif pt == "ROT":
        if data.get("max_diameter_mm") is None:
            errors.append("INCONSISTENT: ROT part must have max_diameter_mm set")
        if data.get("max_width_mm") is not None:
            errors.append("WARNING: ROT part typically has max_width_mm=null")

    elif pt == "COMBINED":
        if data.get("max_diameter_mm") is None:
            errors.append("INCONSISTENT: COMBINED part must have max_diameter_mm set")

    elif pt:
        errors.append(f"INVALID: part_type must be ROT, PRI, or COMBINED, got '{pt}'")

    # Dimension sanity
    for dim_key in ["max_diameter_mm", "max_length_mm", "max_width_mm", "max_height_mm"]:
        val = data.get(dim_key)
        if val is not None:
            if not isinstance(val, (int, float)):
                errors.append(f"INVALID: {dim_key} must be a number, got {type(val).__name__}")
            elif val <= 0:
                errors.append(f"INVALID: {dim_key} must be positive, got {val}")
            elif val > 5000:
                errors.append(f"WARNING: {dim_key}={val}mm seems very large — double check")

    # Complexity
    if data.get("complexity") not in ("simple", "medium", "complex", None):
        errors.append(f"INVALID: complexity must be simple/medium/complex, got '{data.get('complexity')}'")

    # Operations
    ops = data.get("operations", [])
    valid_ops = {"soustružení", "frézování", "vrtání", "vystružování", "závitování", "broušení"}
    for op in ops:
        if op not in valid_ops:
            errors.append(f"WARNING: unknown operation '{op}' — valid: {sorted(valid_ops)}")

    # Cross-check operations vs part type
    if pt == "PRI" and "soustružení" in ops:
        errors.append("WARNING: PRI part with 'soustružení' — are you sure it's not ROT/COMBINED?")
    if pt == "ROT" and "frézování" in ops and "soustružení" not in ops:
        errors.append("WARNING: ROT part with frézování but no soustružení — should this be COMBINED?")

    return errors


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate.py '<json_string>'", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    errors = validate(data)
    if errors:
        print(f"VALIDATION: {len(errors)} issue(s) found:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1 if any("INVALID" in e or "INCONSISTENT" in e for e in errors) else 0)
    else:
        print("VALIDATION: OK — all checks passed")
