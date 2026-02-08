# Constraint Detection Guide

## Overview

The Constraint Detection Service analyzes STEP geometry to detect machining constraints that increase manufacturing complexity and time.

**ADR-TBD:** Machining Constraints Detection System

## Detected Constraints

### 1. Deep Pockets (depth/width > 3.0)

**Detection Method:** Analyzes internal cylindrical faces (bores/holes)
- **Moderate:** depth/width ratio 3.0-4.0 → 1.5x penalty
- **Severe:** depth/width ratio > 4.0 → 1.8x penalty

**Examples:**
- 10mm diameter, 40mm deep hole → ratio 4.0 (severe)
- 20mm diameter, 70mm deep hole → ratio 3.5 (moderate)

### 2. Thin Walls (thickness < 3.0mm)

**Detection Method:** Face-to-face distance measurement for parallel planar faces
- **Moderate:** 2.0-3.0mm thickness → 2.5x penalty
- **Critical:** < 2.0mm thickness → 2.5x penalty + critical flag

**Examples:**
- 2.5mm wall → moderate
- 1.5mm wall → critical

### 3. Long Overhangs (NOT YET IMPLEMENTED)

Planned for future implementation.

## Usage

### Basic Usage

```python
from pathlib import Path
from app.services.constraint_detection_service import ConstraintDetectionService

# Analyze STEP file
step_path = Path("uploads/drawings/part.stp")
analysis = ConstraintDetectionService.analyze_constraints(step_path)

if analysis:
    print(f"Deep pockets: {len(analysis.deep_pockets)}")
    print(f"Thin walls: {len(analysis.thin_walls)}")
    print(f"Critical constraints: {analysis.has_critical_constraints}")
    print(f"Penalty multiplier: {analysis.recommended_penalty_multiplier}x")
```

### Integration with Time Calculator

```python
from app.services.time_calculator import FeatureCalculator
from app.services.constraint_detection_service import ConstraintDetectionService

# Calculate base time
calculator = FeatureCalculator()
result = await calculator.calculate(
    feature_type="drill",
    material_group="11xxx",
    cutting_mode="rough",
    geometry={"diameter": 10, "depth": 40}
)

base_time = result.total_time_sec

# Apply constraint penalties
step_path = Path("part.stp")
constraints = ConstraintDetectionService.analyze_constraints(step_path)

if constraints:
    adjusted_time = base_time * constraints.recommended_penalty_multiplier
    print(f"Base time: {base_time:.1f}s")
    print(f"Adjusted time: {adjusted_time:.1f}s ({constraints.recommended_penalty_multiplier}x)")
```

## Algorithm Details

### Deep Pocket Detection

**Method:** Face-based analysis (not slicing)

1. Iterate all faces in STEP geometry
2. Identify cylindrical faces with REVERSED orientation (internal)
3. Measure face bounding box for depth (Z extent)
4. Calculate diameter from cylinder radius
5. Flag if depth/diameter > 3.0

**Why not slicing?** Z-slicing with `BRepAlgoAPI_Section` often fails on simple geometries due to tolerance issues. Face-based analysis is more robust.

**Limitations:**
- Only detects cylindrical pockets (holes/bores)
- Does not detect rectangular or complex-shaped pockets
- Assumes Z-aligned features

### Thin Wall Detection

**Method:** Face-to-face distance measurement

1. Extract all planar faces
2. For each pair, check if normals are parallel (dot product ~±1)
3. Measure minimum distance using `BRepExtrema_DistShapeShape`
4. Flag if distance < 3.0mm

**Deduplication:**
- Constraints within 5mm of each other are merged
- Keeps the thinnest wall measurement

## Penalty Multiplier Calculation

Penalties are **multiplicative** for multiple constraints:

```python
penalty = 1.0

for pocket in deep_pockets:
    if pocket.severity == "severe":
        penalty *= 1.8
    else:
        penalty *= 1.5

for wall in thin_walls:
    penalty *= 2.5
```

**Examples:**
- 1 moderate deep pocket: 1.5x
- 1 severe deep pocket: 1.8x
- 1 thin wall: 2.5x
- 1 moderate pocket + 1 thin wall: 1.5 × 2.5 = 3.75x
- 2 severe pockets: 1.8 × 1.8 = 3.24x

## Testing

```bash
pytest tests/test_constraint_detection.py -v
```

**Determinism verified:** 10 runs produce identical results.

## Future Enhancements

1. **Rectangular pockets:** Detect non-cylindrical pockets using edge loop analysis
2. **Long overhangs:** Detect cantilever features requiring support
3. **Material-specific penalties:** Different penalty factors per material (aluminum vs. steel)
4. **Tool accessibility:** Detect features requiring special tooling (e.g., deep hole drills)

## References

- OCCT Documentation: https://dev.opencascade.org/
- `BRepAdaptor_Surface`: Surface type detection
- `BRepExtrema_DistShapeShape`: Shape-to-shape distance measurement
- `TopAbs_Orientation`: Face orientation (FORWARD=outer, REVERSED=inner)
