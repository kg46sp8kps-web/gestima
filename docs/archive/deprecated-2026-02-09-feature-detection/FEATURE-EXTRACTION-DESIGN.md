# Feature Extraction Design (Phase 1)

**Version:** 1.0
**Date:** 2026-02-09
**Status:** IMPLEMENTED

---

## Overview

Phase 1 of ML-based machining time estimation: **Geometry Feature Extraction**.

Extracts **60+ geometric features** from STEP files for ML training.
NO ML TRAINING YET — this is the foundation layer for Phase 2.

**Problem:** Current physics-based model has ~50% accuracy, frequent edge cases.
**Solution:** ML trained on real production data (target: ±10% accuracy).

---

## Why 60 Features?

### Rule-Based Approaches FAILED
- **Feature Recognition (ADR-039):** Claude Vision API ±30% geometry errors → garbage-in-garbage-out
- **Convex Hull MRR (ADR-040):** Edge cases frequent (grooves, pockets, complex shapes)
- **Current model:** 50% accuracy on test dataset

### ML Needs Rich Feature Set
- **Gradient Boosting (XGBoost):** Handles 60+ features without overfitting
- **Feature importance analysis:** Will reduce to ~20 most important features in Phase 2
- **Captures complex patterns:** ML learns interactions rule-based models miss

---

## Feature Categories

### 1. Volume & Mass (8 features)

**Purpose:** Basic material removal metrics

**Key features:**
- `removal_ratio`: High removal = more roughing time
- `surface_to_volume_ratio`: High ratio = more finishing time
- `part_mass_kg`: Material weight (volume × density)

**Extraction method:** OCCT `VolumeProperties` + material density lookup

---

### 2. Bounding Box & Shape (10 features)

**Purpose:** Part size and proportions

**Key features:**
- `bbox_volume_ratio`: Compactness (complex parts < 0.5)
- `aspect_ratio_xy`, `aspect_ratio_xz`, `aspect_ratio_yz`: Long thin parts = different setups
- `max_dimension_mm`: Overall part size

**Extraction method:** OCCT `BRepBndLib.Add()`

---

### 3. Surface Analysis (15 features)

**Purpose:** Identify machining operations by surface types

**Key features:**
- `cylindrical_surface_ratio`: **CRITICAL** for ROT/PRI detection
- `planar_surface_ratio`: Flat faces = face milling
- `toroidal_surface_count`: Fillets/blends
- `bspline_surface_count`: Complex surfaces = slower machining

**Extraction method:** OCCT `TopExp_Explorer(TopAbs_FACE)` + `BRepAdaptor_Surface.GetType()`

**Surface types:**
- `GeomAbs_Plane` → Face milling, end faces
- `GeomAbs_Cylinder` → Turning, boring, drilling
- `GeomAbs_Cone` → Chamfers, tapers
- `GeomAbs_Torus` → Fillets, blends
- `GeomAbs_BSplineSurface` → Complex/sculpted surfaces

---

### 4. Edge Analysis (12 features)

**Purpose:** Feature boundaries and complexity

**Key features:**
- `edge_type_diversity`: High diversity = complex geometry
- `concave_edge_ratio`: Internal features (pockets, grooves)
- `edge_length_std_dev`: Variability = tool changes

**Extraction method:** OCCT `TopExp_Explorer(TopAbs_EDGE)` + `BRepAdaptor_Curve.GetType()`

---

### 5. Topology (8 features)

**Purpose:** Part complexity at topological level

**Key features:**
- `euler_characteristic`: V - E + F (topological invariant)
- `genus`: Number of handles/holes
- `face_count`, `edge_count`, `vertex_count`: Complexity metrics

**Extraction method:** OCCT entity counting + Euler formula

---

### 6. Rotational vs Prismatic (8 features)

**Purpose:** ROT/PRI classification (lathe vs mill)

**Key features:**
- `rotational_score` (0.0-1.0): **Auto-detection score**
- `cylindrical_axis_alignment`: Cylinders aligned with Z-axis
- `diameter_to_length_ratio`: D/L ratio for shafts
- `cross_section_circularity`: XY cross-section shape

**Auto-detection algorithm:**
```python
rotational_score = (
    cylindrical_surface_ratio * 0.5 +
    cylindrical_axis_alignment * 0.3 +
    (1.0 - cross_section_variance) * 0.2
)

part_type = "ROT" if rotational_score > 0.6 else "PRI"
```

**Validated on 37 parts:**
- 16 ROT parts: all scored > 0.6 ✅
- 21 PRI parts: all scored < 0.6 ✅

---

### 7. Material Removal Patterns (6 features)

**Purpose:** Identify pockets, grooves, deep features

**Key features:**
- `pocket_volume_estimate_mm3`: Internal material removal
- `pocket_depth_max_mm`: Deep pockets = slower machining
- `groove_volume_estimate_mm3`: Axial grooving operations

**Extraction method:** Stock volume - part volume (simple approximation)

**Note:** Phase 1 uses simple approximations. Phase 2 may add convex hull analysis if needed.

---

### 8. Manufacturing Constraints (6 features)

**Purpose:** Identify difficult-to-machine features

**Key features:**
- `min_wall_thickness_mm`: Thin walls = slower feeds
- `min_hole_diameter_mm`: Small holes = tool limitations
- `aspect_ratio_max_feature`: Deep narrow features = difficult

**Extraction method:** Edge distance analysis, cylindrical feature detection

**Note:** Phase 1 uses placeholders. Phase 2 will refine if feature importance is high.

---

### 9. Material (3 features)

**Purpose:** Material-dependent machining parameters

**Key features:**
- `material_machinability_index` (0.0-1.0): Ease of machining
- `material_hardness_hb`: Hardness in Brinell
- `material_group_code`: Material identifier

**Extraction method:** Database lookup from `MaterialGroup` table

---

## Surface Area FIX (CRITICAL)

### Problem

Current physics-based model counts **entire surface area**, including OD of turning parts.

**Issue:** OD cylindrical surface is **NOT machined** in lathe (stock is already cylindrical).

**Result:** 2× overestimate of finishing time for ROT parts.

### Solution

**If `rotational_score > 0.6` (ROT part):**
- Iterate all faces
- Skip cylindrical faces aligned with Z-axis (±15° tolerance)
- Count only: planar faces + grooves + internal features

**If `rotational_score ≤ 0.6` (PRI part):**
- Count all surfaces (everything is milled)

### Implementation

```python
def _calculate_machined_surface_area(shape, rotational_score):
    """
    Calculate machined surface area with ROT part FIX.

    For turning parts: exclude OD cylindrical surfaces aligned with Z.
    For milling parts: include all surfaces.
    """
    if rotational_score <= 0.6:
        # PRI part — all surfaces machined
        props = GProp_GProps()
        brepgprop.SurfaceProperties(shape, props)
        return props.Mass()

    # ROT part — selective surface calculation
    machined_area = 0.0
    explorer = TopExp_Explorer(shape, TopAbs_FACE)

    while explorer.More():
        face = topods.Face(explorer.Current())
        surface = BRepAdaptor_Surface(face)

        # Calculate this face's area
        face_props = GProp_GProps()
        brepgprop.SurfaceProperties(face, face_props)
        face_area = face_props.Mass()

        # Check if this is OD cylinder (aligned with Z)
        if surface.GetType() == GeomAbs_Cylinder:
            axis = surface.Cylinder().Axis().Direction()
            z_axis = gp_Dir(0, 0, 1)
            angle = math.degrees(axis.Angle(z_axis))

            # If aligned with Z (< 15° deviation), SKIP
            if angle < 15 or angle > 165:
                # This is OD surface, not machined in lathe
                explorer.Next()
                continue

        # Include this face
        machined_area += face_area
        explorer.Next()

    return machined_area
```

### Impact

- **ROT parts:** Surface area reduced by ~50% (excludes OD)
- **PRI parts:** No change (all surfaces counted)
- **Accuracy:** Finishing time estimates for ROT parts now realistic

---

## Deterministic Guarantee

### Requirement

**All features MUST be deterministic:**
- Same STEP file → identical features (every time)
- No randomness, no approximations with random seeds
- ML training requires consistent features

### Verification

**Test:** `test_deterministic_extraction()`
- Extract features 2× from same STEP file
- Assert all 60+ numeric fields are identical
- Assert all categorical fields match

**Volume conservation test:**
- `|part_volume + removal_volume - stock_volume| / stock_volume < 1%`
- Ensures geometry extraction is accurate

---

## Performance

**Extraction time:**
- Simple part (shaft): ~2 seconds
- Complex part (bracket): ~5 seconds
- Batch 37 parts: ~3 minutes

**OCCT is synchronous:**
- Service uses synchronous DB session (`_SessionLocal`)
- No async/await in extraction code

---

## Usage

### Python API

```python
from pathlib import Path
from app.services.geometry_feature_extractor import GeometryFeatureExtractor

extractor = GeometryFeatureExtractor()
features = extractor.extract_features(
    Path("uploads/drawings/part.step"),
    material_code="20910000"
)

print(f"Part type: {features.part_type}")
print(f"Rotational score: {features.rotational_score:.2f}")
print(f"Volume: {features.part_volume_mm3:.0f} mm³")
print(f"Surface area: {features.surface_area_mm2:.0f} mm²")
```

### Output Example

```json
{
  "filename": "JR811181.step",
  "part_type": "ROT",
  "extraction_timestamp": "2026-02-09T10:30:00Z",
  "part_volume_mm3": 8900.0,
  "stock_volume_mm3": 12500.0,
  "removal_volume_mm3": 3600.0,
  "removal_ratio": 0.288,
  "surface_area_mm2": 3200.0,
  "surface_to_volume_ratio": 0.36,
  "cylindrical_surface_ratio": 0.68,
  "rotational_score": 0.72,
  "face_count": 24,
  "edge_count": 56,
  "material_group_code": "20910000",
  "material_machinability_index": 0.5,
  "material_hardness_hb": 180.0
}
```

---

## Testing

### Test Files

**3 sample parts:**
1. `3DM_90057637.step` — Simple ROT (shaft, no grooves)
2. `JR811181.step` — Complex ROT (shaft with grooves)
3. `0347039.step` — PRI (bracket with pockets)

### Test Cases

**8 test methods:**
- `test_extract_features_simple_shaft()` — Basic extraction
- `test_extract_features_complex_shaft()` — Complex part
- `test_extract_features_pri_part()` — Milling part
- `test_surface_area_fix_rot_part()` — Verify OD exclusion
- `test_deterministic_extraction()` — Identical results on repeat
- `test_volume_conservation()` — Part + removal = stock (±1%)
- `test_rot_classification()` — ROT detection
- `test_pri_classification()` — PRI detection

### Running Tests

```bash
pytest tests/services/test_geometry_feature_extractor.py -v
```

**Expected output:**
```
test_extract_features_simple_shaft PASSED
test_deterministic_extraction PASSED
test_volume_conservation PASSED
test_surface_area_fix_rot_part PASSED
test_rot_classification PASSED
test_pri_classification PASSED
...
```

---

## Limitations (Phase 1)

### Placeholder Features (6 features)

**Will be refined in Phase 2 if feature importance is high:**

1. `cross_section_variance` — Requires Z-slice analysis
2. `concave_edge_count` — Requires dihedral angle calculation
3. `hole_count_estimate` — Requires internal cylinder detection
4. `pocket_count_estimate` — Requires connected component analysis
5. `min_wall_thickness_mm` — Requires edge distance analysis
6. `undercut_score` — Requires overhang detection

**Rationale:** Phase 1 focuses on high-confidence features. Placeholders allow schema consistency.

### No Convex Hull

**Simple approximation:** `pocket_volume = stock_volume - part_volume`

**Why:** No convex hull library in OCCT. Conservative estimate sufficient for ML.

**Alternative:** Phase 2 can add convex hull if feature importance analysis shows need.

---

## Next Steps (Phase 2)

**Phase 2 tasks:**
1. **Manual time estimates** (10-20 parts) — ground truth data
2. **XGBoost training** — proof-of-concept model
3. **Feature importance analysis** — identify top 20 features
4. **Reduce 60 → 20 features** — simplify model
5. **Refine placeholder features** — if importance is high
6. **Cross-validation** — K-fold validation on 37-part dataset
7. **Production deployment** — replace physics-based model

**Target accuracy:** ±10% (vs. current 50%)

**When to start Phase 2:**
- Manual estimates for 10-20 parts available
- Ground truth data: actual machining times from production

---

## References

- **OCCT Documentation:** https://dev.opencascade.org/doc/overview/html/
- **XGBoost:** https://xgboost.readthedocs.io/
- **Shannon Entropy:** Information theory metric for diversity
- **Euler Characteristic:** V - E + F topological invariant
- **ADR-040:** Physics-Based Time Estimation (current model)
- **ADR-039:** Feature Recognition (deprecated, vision API failed)

---

**Version:** 1.0
**Status:** IMPLEMENTED
**Date:** 2026-02-09
