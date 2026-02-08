# OCCT Parser Accuracy Analysis
**Date:** 2026-02-06
**Context:** User reports ~30% accuracy after OCCT implementation

## Issue Summary
User states: "jediný správně extrahovaný soubor je PDM-249322_03, podle mě parser není genericky"

This suggests OCCT parser works correctly on reference file but fails on production data.

## Test Results

### Files Processed
- **Total:** 37 STEP files
- **With contours:** 36 files (97%)
- **Source:** OCCT (confirmed via backend test)

### Reference File (PDM-249322_03.stp)
**OCCT Output:**
- Max Ø: 55 mm
- Length: 89 mm
- Outer contour: 12 points
- Inner contour: 10 points
- Features: 9 (cylindrical, radius)
- Source: `occt`

**Status:** ✅ User confirms this is CORRECT

### Problem Files
User reports 36/37 files are incorrect. Need to diagnose:

1. **What makes PDM-249322_03 different?**
   - Is it simpler geometry?
   - Specific CAD export format?
   - Specific surface types?

2. **Common failure patterns:**
   - Wrong diameters?
   - Missing features?
   - Inner bore incorrect?
   - Contour shape wrong?

## Root Cause Hypotheses

### H1: Contour Builder Off-Axis Filter
`contour_builder.py` has `_is_off_axis()` check. May be:
- Too strict (filters valid features)
- Too loose (includes cross-holes)
- Wrong tolerance (0.1 radians)

### H2: Z-Bounds Extraction
Recent fix changed from vertices to BoundingBox. May have:
- Coordinate system issues
- Overlapping segments
- Non-sequential Z ordering

### H3: Feature Classification
`occt_feature_extractors.py` classifies surfaces. May misidentify:
- Chamfers as cylinders
- Grooves as separate features
- Thread relief as steps

### H4: Assembly vs Single Part
PDM-249322_03 might be single part, others assemblies. Current code:
```python
if len(parts) > 1:
    # Take largest by volume
```
May select wrong part from assembly.

## Next Steps

### 1. Systematic Comparison (Required)
Pick 5 diverse files, compare OCCT output vs PDF drawings:
- Simple shaft (1 bore, no features)
- Complex shaft (multiple diameters, grooves)
- Flanged part (step changes)
- Threaded part (M10 etc.)
- Assembly (multiple bodies)

### 2. Debug Instrumentation
Add logging to `contour_builder.py`:
- Which features filtered out (off-axis)
- Which segments overlapping (envelope)
- Z-sort order before/after

### 3. Validation Metrics
`contour_validator.py` exists but may need:
- Diameter tolerance check (±0.5mm?)
- Length validation
- Feature count comparison

### 4. Consider Fallback Strategy
If OCCT proves unreliable:
- Hybrid mode: OCCT for simple parts, AI for complex
- Manual override: User marks "trusted" geometry
- Confidence score: Warn user when uncertain

## Blocking Issues
- Cannot read PDF drawings (no poppler installed)
- Need user to provide specific failure examples
- Need ground truth dimensions for comparison

## Recommendation
**CRITICAL:** Before continuing OCCT development, need:
1. User to identify 3-5 specific "wrong" files
2. For each file, what is EXPECTED vs ACTUAL output
3. Access to PDF drawings or CAD screenshots for validation

Without this, we're debugging blind.
