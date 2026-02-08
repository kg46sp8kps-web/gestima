"""
Contour validator and corrector.

Validates Claude's profile_geometry against STEP parser data
and corrects common errors (wrong scale, missing diameters, bounds mismatch).

Rules enforced:
- L-008: Transaction handling (not applicable here - pure dict processing)
- L-009: Pydantic validation (not needed - dict-to-dict transform)

ADR-037: Part of Interactive SVG Visualization system.
"""
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def validate_and_fix_contour(
    profile_geometry: Dict[str, Any],
    step_features: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Validate and fix profile_geometry against STEP data.

    Checks:
    1. max_diameter matches max STEP diameter
    2. All STEP diameters appear in contour
    3. Contour starts at (r=0, z=0) and ends at (r=0, z=total_length)
    4. No negative r or z values
    5. Scale correction if contour is proportionally wrong

    Args:
        profile_geometry: Claude's profile_geometry output
        step_features: Features from STEP parser

    Returns:
        Corrected profile_geometry with validation_report field added
    """
    if not profile_geometry:
        return profile_geometry

    report = {"fixes": [], "warnings": [], "valid": True}
    geo = dict(profile_geometry)  # Don't mutate original

    part_type = geo.get("type", "rotational")

    if part_type == "rotational":
        geo = _validate_rotational(geo, step_features, report)
    elif part_type == "prismatic":
        geo = _validate_prismatic(geo, step_features, report)

    geo["validation_report"] = report
    return geo


def _validate_rotational(
    geo: Dict[str, Any],
    step_features: List[Dict],
    report: Dict,
) -> Dict[str, Any]:
    """Validate rotational part contour."""
    outer = geo.get("outer_contour", [])
    inner = geo.get("inner_contour", [])
    total_length = geo.get("total_length", 0)
    max_diameter = geo.get("max_diameter", 0)

    if not outer:
        report["warnings"].append("No outer_contour in profile_geometry")
        report["valid"] = False
        return geo

    # 1. Extract STEP diameters
    step_diameters = sorted(set(
        f["diameter"] for f in step_features
        if "diameter" in f and f["diameter"] > 0
    ))

    if not step_diameters:
        report["warnings"].append("No STEP diameters for validation")
        return geo

    step_max_dia = max(step_diameters)

    # 2. Check max_diameter field
    if max_diameter > 0 and abs(max_diameter - step_max_dia) > 1.0:
        report["fixes"].append(
            f"max_diameter corrected: {max_diameter} → {step_max_dia}"
        )
        geo["max_diameter"] = step_max_dia
    elif max_diameter <= 0:
        geo["max_diameter"] = step_max_dia
        report["fixes"].append(f"max_diameter set to {step_max_dia}")

    # 3. Check contour max radius vs STEP max diameter
    contour_max_r = max((p.get("r", 0) for p in outer), default=0)
    expected_max_r = step_max_dia / 2

    if contour_max_r > 0 and expected_max_r > 0:
        ratio = expected_max_r / contour_max_r

        if abs(ratio - 1.0) > 0.05:  # More than 5% off
            # Scale all r values to match STEP
            report["fixes"].append(
                f"Contour r-values scaled by {ratio:.3f} "
                f"(contour max r={contour_max_r:.1f}, STEP expects r={expected_max_r:.1f})"
            )
            for pt in outer:
                if "r" in pt:
                    pt["r"] = round(pt["r"] * ratio, 2)
            for pt in inner:
                if "r" in pt:
                    pt["r"] = round(pt["r"] * ratio, 2)

    # 4. Ensure contour starts and ends on axis
    if outer and outer[0].get("r", -1) != 0:
        outer.insert(0, {"r": 0, "z": 0})
        report["fixes"].append("Added start point (r=0, z=0)")

    if outer and outer[-1].get("r", -1) != 0:
        z_end = outer[-1].get("z", total_length)
        outer.append({"r": 0, "z": z_end})
        report["fixes"].append(f"Added end point (r=0, z={z_end})")

    # 5. Fix total_length if contour z-range doesn't match
    contour_max_z = max((p.get("z", 0) for p in outer), default=0)
    if total_length > 0 and contour_max_z > 0:
        z_ratio = total_length / contour_max_z
        if abs(z_ratio - 1.0) > 0.05:
            report["fixes"].append(
                f"Contour z-values scaled by {z_ratio:.3f} to match total_length={total_length}"
            )
            for pt in outer:
                if "z" in pt:
                    pt["z"] = round(pt["z"] * z_ratio, 2)
            for pt in inner:
                if "z" in pt:
                    pt["z"] = round(pt["z"] * z_ratio, 2)

    # 6. Check STEP inner diameters match inner_contour
    step_hole_diameters = sorted(set(
        f["diameter"] for f in step_features
        if f.get("type") == "hole" and "diameter" in f
    ))
    if step_hole_diameters and inner:
        inner_max_r = max((p.get("r", 0) for p in inner), default=0)
        expected_inner_r = max(step_hole_diameters) / 2
        if inner_max_r > 0 and abs(inner_max_r - expected_inner_r) > 0.5:
            inner_ratio = expected_inner_r / inner_max_r
            for pt in inner:
                if "r" in pt:
                    pt["r"] = round(pt["r"] * inner_ratio, 2)
            report["fixes"].append(
                f"Inner contour r scaled: {inner_max_r:.1f} → {expected_inner_r:.1f}"
            )

    # 7. Remove negative values
    for pt in outer:
        if pt.get("r", 0) < 0:
            pt["r"] = 0
            report["fixes"].append("Negative r value corrected to 0")
        if pt.get("z", 0) < 0:
            pt["z"] = 0
            report["fixes"].append("Negative z value corrected to 0")

    # 8. Check monotonic z (should go left to right)
    z_values = [p.get("z", 0) for p in outer]
    if z_values and z_values != sorted(z_values):
        report["warnings"].append("outer_contour z-values not monotonic — may cause rendering issues")

    # 9. Report missing STEP diameters
    contour_diameters = set()
    for i in range(len(outer) - 1):
        r = outer[i].get("r", 0)
        if r > 0:
            contour_diameters.add(round(r * 2, 1))

    for d in step_diameters:
        rounded_d = round(d, 1)
        if rounded_d > 0 and not any(abs(cd - rounded_d) < 1.0 for cd in contour_diameters):
            closest = min(contour_diameters, key=lambda x: abs(x-rounded_d), default='none')
            report["warnings"].append(
                f"STEP Ø{d} not found in outer_contour (closest: {closest})"
            )

    geo["outer_contour"] = outer
    geo["inner_contour"] = inner

    if report["fixes"]:
        logger.info(f"Contour validation: {len(report['fixes'])} fixes applied")
    if report["warnings"]:
        logger.warning(f"Contour validation: {len(report['warnings'])} warnings")

    return geo


def _validate_prismatic(
    geo: Dict[str, Any],
    step_features: List[Dict],
    report: Dict,
) -> Dict[str, Any]:
    """Validate prismatic part geometry."""
    bbox = geo.get("bounding_box", {})

    # Basic validation for prismatic
    if not bbox:
        report["warnings"].append("No bounding_box for prismatic part")
        report["valid"] = False
        return geo

    # Check holes match STEP data
    step_hole_dias = [
        f["diameter"] for f in step_features
        if f.get("type") == "hole" and "diameter" in f
    ]
    geo_holes = geo.get("holes", [])

    for hole in geo_holes:
        dia = hole.get("diameter", 0)
        if dia > 0 and step_hole_dias:
            closest = min(step_hole_dias, key=lambda d: abs(d - dia))
            if abs(closest - dia) > 0.5 and abs(closest - dia) < dia * 0.2:
                report["fixes"].append(f"Hole Ø{dia} corrected to STEP Ø{closest}")
                hole["diameter"] = closest

    return geo
