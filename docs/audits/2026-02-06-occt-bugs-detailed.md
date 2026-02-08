# OCCT Parser - Detailed Bug Analysis
**Date:** 2026-02-06
**Analyzed:** 5 files with PDF comparison
**Critical bugs found:** 4

---

## ✅ Reference File (CORRECT)

### PDM-249322_03.stp
**PDF dimensions:**
- Max Ø: 55 mm
- Length: 89 mm
- Inner bore: Ø19 mm
- Main body: Ø27 mm
- Flange: Ø55 mm

**OCCT output:**
- Max Ø: 55 mm ✅
- Length: 89 mm ✅
- 12 outer + 10 inner points

**Status:** ✅ CORRECT - This is the ONLY correct file

---

## ❌ BUG #1: Inner/Outer Mis-Classification

### JR 810665.ipt.step (Wippenlager)
**PDF dimensions:**
- **Inner bore: Ø6.9 mm** (H8 tolerance)
- **Outer small diameter: Ø8.9 mm**
- Main body: Ø12 H8
- Length: 87.8 mm
- Chamfers: 0.5×45° both ends

**OCCT output:**
- Inner bore diameter: **Ø8.90 mm** ❌
- Max diameter: 12.0 mm ✅
- Length: 84.5 mm (close enough)

**Root cause:**
OCCT classified **outer Ø8.9 feature as inner bore**. The real Ø6.9 inner bore was missed or filtered out.

**Hypothesis:**
- `occt_feature_extractors.py` sets `is_inner` flag based on surface normal direction
- Small outer diameters (Ø8.9) may have normals pointing inward
- Or: `contour_builder.py` misinterprets nested cylindrical surfaces

**Impact:** CRITICAL - Wrong bore size = wrong tooling

---

## ❌ BUG #2: Duplicate Points (Zigzag Contour)

### JR 810663.ipt.step (Lagersupport)
**PDF dimensions:**
- Max Ø: 59 mm (with 2×45° chamfers)
- Chamfer: 2×45° on outer diameter

**OCCT output:**
```
Outer contour: 8 points
  Point 0: Z=-29.50, R=0.00
  Point 1: Z=-29.50, R=29.50
  Point 2: Z=29.50, R=29.50
  Point 3: Z=-29.50, R=29.50  ← DUPLICATE of Point 1
  Point 4: Z=29.50, R=29.50   ← DUPLICATE of Point 2
```

**Root cause:**
`contour_builder.py` creates duplicate points at same (Z, R) coordinates. This creates zigzag lines in SVG instead of clean chamfer representation.

**Hypothesis:**
- Chamfer faces generate multiple features with same Z-bounds
- `_build_outer_contour()` doesn't deduplicate sequential identical points
- Or: Envelope algorithm adds overlapping segment endpoints

**Impact:** HIGH - Visual artifacts, user confusion

---

## ❌ BUG #3: Dramatically Wrong Length

### JR 810671.ipt.step (Čep Ø12)
**PDF dimensions:**
- Pin diameter: Ø12 mm
- **Pin length: 43.2 mm** (critical dimension)

**OCCT output:**
- Max Ø: 87.1 mm ❌ (completely wrong!)
- **Length: 6.0 mm** ❌ (86% error!)

**Root cause:**
OCCT extracted completely wrong geometry. Either:
1. Selected wrong part from assembly
2. Z-bounds extraction catastrophically failed
3. Read wrong solid from multi-body STEP file

**Hypothesis:**
- `step_parser_occt.py` takes "largest by volume" when `len(parts) > 1`
- JR 810671 may be assembly where largest part ≠ main part
- Or: Bounding box extraction failed for thin pin geometry

**Impact:** CRITICAL - 86% error makes data completely useless

---

## ❌ BUG #4: Prismatic Parts Detected as Rotational

### 0304663_D00043519_000.1_3D.stp
**PDF dimensions:**
- **Prismatic housing** (boxy shape ~66×20.5×33 mm)
- Pockets, holes, step changes
- **NO rotation axis**

**OCCT output:**
- **Rotation axis: z** ❌
- Max diameter: 341.28 mm ❌
- Length: 202.31 mm ❌

**Root cause:**
`occt_metadata.py` `detect_rotation_axis()` incorrectly identified Z axis on prismatic part.

### JR 810686 (User reported)
- User: "prizmatický díl s válcovým nákružkem - identifikován jako soutružnický díl"
- Same issue: Part with cylindrical feature misclassified as fully rotational

**Hypothesis:**
- Rotation axis detection too permissive - finds Z axis if ANY cylindrical feature present
- Should require: majority of volume is rotationally symmetric
- Or: Check if outer envelope is cylindrical vs prismatic

**Impact:** CRITICAL - Sends prismatic parts to lathe pipeline, completely wrong operations

---

## Root Cause Summary

### Primary Issues

1. **Assembly Handling** (BUG #3)
   - `step_parser_occt.py` line ~89: `parts.sort(key=lambda p: compute_volume(p), reverse=True)`
   - Takes largest part, but largest ≠ always main part
   - Need smarter heuristic or user selection

2. **Inner/Outer Classification** (BUG #1)
   - `occt_feature_extractors.py` line ~245: `is_inner = dot_product < 0`
   - Surface normal approach unreliable for nested geometries
   - Need topology-based classification (is surface enclosed?)

3. **Contour Deduplication** (BUG #2)
   - `contour_builder.py` line ~182: `_build_outer_contour()`
   - No deduplication of sequential identical (Z, R) points
   - Chamfer/fillet features create overlapping segments

4. **Part Type Detection** (BUG #4)
   - `occt_metadata.py` line ~128: `detect_rotation_axis()`
   - Finds rotation axis if ANY cylindrical surfaces exist
   - Should require: dominant axis + rotationally symmetric envelope

### Secondary Issues

- **Z-bounds extraction** may still have edge cases (BUG #3)
- **Envelope algorithm** may create duplicates (BUG #2)
- **Off-axis filtering** may filter valid inner features (BUG #1)

---

## Recommended Fixes (Priority Order)

### 1. Fix Part Type Detection (BUG #4) - BLOCKING
**File:** `app/services/occt_metadata.py`

Current logic:
```python
def detect_rotation_axis(shape):
    # Returns Z if ANY cylindrical faces found
    if cylindrical_faces_count > 0:
        return dominant_axis
```

Proposed fix:
```python
def detect_rotation_axis(shape):
    # Require: majority of surface area is rotationally symmetric
    total_area = compute_total_surface_area(shape)
    rotational_area = sum(compute_face_area(f) for f in cylindrical_faces)

    if rotational_area / total_area < 0.7:  # 70% threshold
        return None  # Prismatic part

    # Check outer envelope is cylindrical
    bbox = get_bounding_box(shape)
    if abs(bbox.x_size - bbox.y_size) / max(bbox.x_size, bbox.y_size) > 0.2:
        return None  # Not cylindrical envelope

    return dominant_axis
```

### 2. Fix Assembly Part Selection (BUG #3) - CRITICAL
**File:** `app/services/step_parser_occt.py`

Current logic:
```python
parts.sort(key=lambda p: compute_volume(p), reverse=True)
main_part = parts[0]
```

Proposed fix:
```python
# Option A: Take part with most cylindrical faces (for rotational)
def score_part(part):
    volume = compute_volume(part)
    cyl_faces = count_cylindrical_faces(part)
    return volume * (1 + cyl_faces * 0.5)  # Prefer parts with cylinders

parts.sort(key=score_part, reverse=True)
main_part = parts[0]

# Option B: Let user select from list (UI change needed)
# Option C: Take part closest to origin (0,0,0)
```

### 3. Fix Inner/Outer Classification (BUG #1) - CRITICAL
**File:** `app/services/occt_feature_extractors.py`

Current logic:
```python
is_inner = dot_product < 0  # Normal points inward
```

Proposed fix:
```python
from OCC.Core.BRepClass3d import BRepClass3d_SolidClassifier

def is_inner_surface(face, shape):
    # Get point on surface
    u_mid, v_mid = get_surface_mid_params(face)
    point = evaluate_surface(face, u_mid, v_mid)

    # Get normal direction
    normal = compute_normal(face, u_mid, v_mid)

    # Move point slightly inward along normal
    test_point = point + normal * -0.01  # Negative = inward

    # Check if test point is INSIDE solid
    classifier = BRepClass3d_SolidClassifier(shape, test_point, 1e-6)
    state = classifier.State()

    # TopAbs_IN = inside solid = inner surface
    # TopAbs_OUT = outside solid = outer surface
    return state == TopAbs_IN
```

### 4. Fix Contour Deduplication (BUG #2) - HIGH
**File:** `app/services/contour_builder.py`

Add deduplication after contour building:
```python
def _deduplicate_contour(contour, tolerance=0.01):
    """Remove sequential duplicate points"""
    if not contour:
        return contour

    result = [contour[0]]
    for point in contour[1:]:
        prev = result[-1]
        dz = abs(point['z'] - prev['z'])
        dr = abs(point['r'] - prev['r'])

        if dz > tolerance or dr > tolerance:
            result.append(point)

    return result

# Apply after building outer/inner contours
outer_contour = _deduplicate_contour(outer_contour)
inner_contour = _deduplicate_contour(inner_contour)
```

---

## Testing Plan

1. **Create test suite** with 5 reference files:
   - PDM-249322_03 (simple rotational - WORKING)
   - JR 810665 (nested cylinders - BUG #1)
   - JR 810663 (chamfers - BUG #2)
   - JR 810671 (assembly/thin pin - BUG #3)
   - 0304663 (prismatic - BUG #4)

2. **Ground truth JSON** for each file:
```json
{
  "filename": "JR 810665.ipt.step",
  "part_type": "rotational",
  "max_diameter": 12.0,
  "total_length": 87.8,
  "inner_bore_diameter": 6.9,
  "tolerance_mm": 0.5
}
```

3. **Automated regression test** comparing OCCT output vs ground truth

---

## Impact Assessment

**Without fixes:**
- **70% of files have critical errors** (26/37 based on user feedback)
- Parts sent to wrong machining pipeline (prismatic → lathe)
- Wrong tool sizes selected (Ø8.9 drill instead of Ø6.9)
- Wrong stock lengths ordered (6mm vs 43mm - 700% error)

**With fixes:**
- Target: **90%+ accuracy** on rotational parts
- Prismatic parts correctly rejected (sent to separate pipeline)
- Assembly parts handled correctly
- Clean contours without artifacts

---

## Next Steps

1. ✅ Detailed bug analysis complete
2. ⏳ Implement Fix #1 (Part Type Detection) - BLOCKING for prismatic parts
3. ⏳ Implement Fix #3 (Assembly Selection) - CRITICAL for length accuracy
4. ⏳ Implement Fix #2 (Inner/Outer) - CRITICAL for bore sizing
5. ⏳ Implement Fix #4 (Deduplication) - HIGH for visual quality
6. ⏳ Create automated test suite with ground truth
7. ⏳ Re-test all 37 files and measure accuracy improvement
