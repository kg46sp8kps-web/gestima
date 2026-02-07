# OCCT Feature Recognition Experiments (Feb 2026)

**Period:** 2026-02-04 to 2026-02-07  
**Status:** ARCHIVED — Experiments failed, replaced by Vision API + STEP hybrid  
**See:** `docs/future/FUTURE_VISION_STEP_HYBRID.md` for future direction

---

## Summary

We attempted automatic machining time calculation using OCCT 3D B-rep feature recognition. After implementing four system variants (hybrid, deterministic, step_deterministic, auto), testing on 37 STEP files revealed:

**Result:** 50% false positive rate, unreliable heuristic classification → **Abandoned**

---

## What Was Tried

### 1. Edge Convexity Classification (ADR-035, ADR-039, ADR-040)

**Approach:** Classify manufacturing features by analyzing convex/concave edges connecting B-rep faces.

**Implementation:** `occt_edge_classifier.py` (364 LOC)
- Port of AAGNet + Autodesk occwl edge convexity algorithm
- Build edge→face adjacency map using OCCT `TopExp.MapShapesAndAncestors`
- For each manifold edge: sample points, compute dihedral angle between adjacent face normals
- Classify edge as CONCAVE/CONVEX/SMOOTH based on angle sign
- Aggregate edge types per face → decision tree → mfg_feature label

**Face Classification Decision Tree:**
```
Cylindrical:
  inner + concave_ratio > 0.7 → groove_wall
  inner + other → bore
  outer + concave_ratio > 0.7 → groove_wall
  outer + concave_ratio > 0.3 → step_transition
  outer + other → shaft_segment

Planar:
  concave_ratio > 0.7 + inner → pocket_bottom
  concave_ratio > 0.7 + outer → groove_bottom
  concave_ratio > 0.3 → step_face
  other → end_face

Cone:
  concave_ratio > 0.5 → chamfer
  other → taper

Toroidal:
  concave_ratio > 0.5 → fillet_inner
  other → fillet_outer
```

**Result:** ❌ Failed
- **False positives:** 50% overall
- **Inner cylindrical faces → bore (wrong):** Actually fillets/radii
- **Outer cylindrical on PRI parts → shaft_segment (wrong):** Actually corner radii
- **Workaround required:** 9 parts needed hardcoded FORCE_TYPE corrections (3DM_90057637, 0347039, JR808404, JR810686, JR810695, JR811181, JR811183, JR811187, PDM-280739)

**Root cause:** Heuristics cannot distinguish between:
- Shaft outer diameter
- Corner fillet radius
- Bearing seat
- Thread undercut
- Through-hole

All look like "cylindrical + outer/inner" in B-rep geometry.

---

### 2. Toolpath Generation from Faces (ADR-036)

**Approach:** Generate CNC toolpaths directly from B-rep geometry.

**Implementation:** `toolpath_from_faces.py` (639 LOC for milling, 655 LOC for turning)
- OD turning, boring, drilling, facing paths
- 2.5D milling: pocket spiral, slot, contour, face

**Result:** ❌ Not feasible
- We're not CAM software
- No collision detection → potential spindle/part crashes
- No adaptive clearing strategies → inefficient machining
- Missing tool offset management
- No proper tool selection logic
- Impossible to verify without real machine

---

### 3. Waterline 2D Visualization (ADR-037)

**Approach:** Extract r(z) polar map, visualize as SVG profile.

**Implementation:** `Waterline2DViewer.vue` + batch analysis
- Extract cylindrical surface polar coordinates
- Render as 2D contour diagram
- Batch analysis on 37 STEP files → `batch_combined_results.json`

**Result:** ⚠️ Mixed
- ✅ Extraction algorithm worked (accurate r(z) measurements)
- ❌ Per-contour scaling bug → visual zigzag artifacts
- ❌ Feature classification from contour unreliable (can't distinguish bore from fillet)

**Why it failed:** Contour alone doesn't encode surface type (cylindrical vs toroidal), orientation (inner vs outer), or manufacturing context.

---

### 4. 3D STEP Viewer with Feature Coloring (ADR-038)

**Approach:** Render 3D STEP model in browser using occt-import-js WASM, color faces by mfg_feature label.

**Implementation:** 
- `StepViewer3D.vue` (901 LOC) — Three.js + occt-import-js rendering
- Per-face coloring via `geometry.addGroup()` + MeshPhongMaterial array
- Backend endpoint: `GET /api/feature-recognition-batch/step-face-features/{filename}`
- 12-color scheme (shaft_segment=blue, bore=red, groove_wall=orange, etc.)

**Technical achievement:** ✅
- OCCT face traversal order matches occt-import-js browser order (1:1)
- Face ID stable across parsing
- Rendering performance good

**Result:** ⚠️ Visualization worked, classification didn't
- Colors were wrong because underlying mfg_feature labels wrong
- Viewer itself useful for geometry inspection
- But feature coloring accuracy depends on flawed classifier

---

### 5. OCCT Integration (ADR-039)

**Approach:** Replace regex STEP parser with native OCCT (pythonocc-core).

**Implementation:** 
- `step_parser_occt.py` (299 LOC) — Main OCCT orchestrator
- `occt_feature_extractors.py` (282 LOC) — Cylinder/cone/torus extraction
- `occt_metadata.py` (147 LOC) — Volume, bbox, rotation axis
- Hybrid coordinator: OCCT primary, regex fallback if OCCT unavailable

**Technical achievement:** ✅
- Accurate geometry extraction (exact, not approximate)
- Fast parsing (~40ms per file)
- Proper handling of assemblies
- OCC 7.9 API quirks documented (.Size() not .Extent(), etc.)

**Result:** ✅ OCCT parser kept for future use
- Core geometry extraction reused in `step_raw_extractor.py`
- Removed classification/interpretation layer
- Useful foundation for Vision API + STEP hybrid approach

---

## Key Learnings

### 1. Heuristic Feature Classification Unreliable for Real-World Parts

- Works for textbook CAD examples
- Fails on actual manufactured parts with fillets, chamfers, complex geometry
- Same geometry = different feature depending on:
  - Part type (rotational vs prismatic)
  - Design intent (is that fillet for strength or accuracy?)
  - Manufacturing context (tolerance symbols, surface finish, material)

### 2. STEP Files Lack Manufacturing Context

Raw STEP provides:
- ✅ **Exact geometry:** dimensions, surface types, orientations
- ❌ **No tolerances:** H7, h6, ISO 2768
- ❌ **No surface finish:** Ra values
- ❌ **No threads:** M5, M30×2 pitch
- ❌ **No material specs:** 1.2379 steel hardness
- ❌ **No design intent:** why is this fillet here?

**This is fundamental.** A fillet and a corner radius have identical B-rep geometry but different manufacturing meanings.

### 3. PDF Drawings Have Context But Are Hard to Parse

Manufacturing drawings contain all context (tolerances, finish, materials) but:
- Multi-view ambiguity (which dimension belongs to which feature?)
- OCR unreliable on complex technical drawings
- Overlapping annotations, small fonts, handwritten notes
- Commercial PDF parsers don't understand engineering drawing conventions

### 4. Volume-Based Time Calculation Too Crude

Deterministic pipeline produced:
- Oversimplified time estimates
- Hole count, groove count matter more than total volume removed
- Setup time, tool changes, inspection time not captured

---

## What Was Kept

✅ **OCCT STEP Loading** (pythonocc-core dependency kept)
```python
from OCC.Core.STEPControl import STEPControl_Reader
```

✅ **Raw Geometry Extraction** (`app/services/step_raw_extractor.py`)
- No classification, no interpretation
- Returns JSON: cylindrical faces with diameter/z_min/z_max/is_inner
- Bounding box, volume (cm³)
- Safe to use for future integrations

✅ **API Endpoint** (`GET /api/step/raw-geometry/{filename}`)
- Supports future Claude Vision API integration
- Returns exact geometry data without interpretation

✅ **3D Visualization Basis** (occt-import-js WASM kept)
- WASM binary in `frontend/public/occt-import-js.wasm`
- Three.js integration working
- Can be repurposed for other visualization tasks

---

## Architecture of Failed System (for reference)

**Total codebase:** ~18,500 LOC across ~47 files

### Backend Layers
```
STEP file → StepParser(use_occt=True)
              ├─ OCCT available → StepParserOCCT
              │   ├─ Feature extraction (cyl/cone/torus)
              │   ├─ Metadata (volume, bbox, rotation axis)
              │   └─ Edge convexity → face classification ❌
              └─ OCCT unavailable → regex parser
                    ↓
              ContourBuilder → profile_geometry
                    ↓
              OperationGenerator → operations ❌ unreliable
                    ↓
              ProfileSvgRenderer → SVG

PDF file → Claude Sonnet 4.5 API
  ├─ geometry_extractor.py (structured geometry)
  └─ step_pdf_parser.py (operations directly) ❌ high cost, unreliable
```

### Frontend Layers
- `FeatureRecognitionModule.vue` (1851 LOC) — split-pane coordinator
- `StepViewer3D.vue` (901 LOC) — 3D viewer with feature coloring
- Various visualization components

---

## Performance Metrics

- OCCT parse: 40ms per file
- Edge convexity analysis: ~100ms per file
- Claude API call: ~38s (bottleneck)
- Memory: +150 MB per worker

---

## Files Deleted (Cleanup 2026-02-07)

### Backend Services Deleted
- `app/services/analysis_service.py` (717 LOC) — pipeline dispatch
- `app/services/toolpath_from_faces.py` (639 LOC) — milling toolpaths
- `app/services/occt_edge_classifier.py` (364 LOC) — edge convexity
- `app/services/feature_recognition_ml_service.py`
- `app/services/feature_recognition_service.py` (360 LOC)

### Router Deleted
- `app/routers/feature_recognition_router.py` (1721 LOC) — 13 API endpoints

### Models/Schemas Deleted
- `app/models/feature_recognition.py` (268 LOC)
- `app/schemas/feature_recognition.py` (358 LOC)

### Frontend Components Deleted
- `FeatureRecognitionModule.vue` (1851 LOC)
- `StepViewer3D.vue` (901 LOC)
- `StepFeatureViewer.vue` (195 LOC)
- `StepViewerWithContour.vue` (210 LOC)
- `StepViewerWrapper.vue` (75 LOC)
- `Waterline2DViewer.vue`
- `ToolpathViewer3D.vue`
- `InteractiveSvgViewer.vue` (275 LOC)
- `useFeatureHighlight.ts` (32 LOC)

### Tests Deleted
- `test_step_parser_occt.py` (259 LOC)
- `test_occt_integration.py` (209 LOC)
- `test_analysis_service.py` (457 LOC)
- `test_contour_builder.py` (297 LOC)
- `test_contour_validator.py` (272 LOC)
- `test_milling_toolpath.py`

### Migrations Deleted
- `r1s2t3u4v5w6_add_feature_recognition_id_to_operations.py`

### Documentation Deleted
- ADR-035 through ADR-042 (consolidated into this archive)

---

## OCC 7.9 API Notes (for future maintainers)

If pythonocc-core needs reinstallation:

```bash
conda install -c conda-forge pythonocc-core
```

Critical API differences from older OCCT versions:
- `.Size()` not `.Extent()` for indexed maps
- `TopTools_IndexedMapOfShape.FindIndex()` for stable face/edge IDs
- `face_list.First()` / `face_list.Last()` for 2-element lists (no iterator)
- `brepgprop.VolumeProperties()` return signature changed
- Face orientation: `face.Orientation() == 1` means REVERSED (inner)

---

## Future Direction: Vision API + STEP Hybrid

**New approach (accepted):**
1. OCCT extracts RAW geometry → JSON (no interpretation)
2. Claude Vision API reads PDF drawing + receives STEP JSON as context
3. Vision API matches PDF labels (M5, Bore, Ø27, h6) → STEP face IDs
4. Use STEP exact measurements + PDF engineering context for accurate feature classification

**Why this will work better:**
- STEP = 100% accurate dimensions (not OCR)
- Vision API = interprets PDF context (tolerances, surface finish, what-is-what)
- Human-like reasoning: "this fillet connects M5 thread undercut, so fillet_inner"
- No heuristic classification needed

**See:** `docs/future/FUTURE_VISION_STEP_HYBRID.md`

---

## Lessons for Future Architecture Decisions

1. **Geometry ≠ Intent**
   - Don't try to infer manufacturing intent from pure geometry
   - Engineering drawings are the source of truth
   - CAD models are implementation details

2. **Heuristics Don't Scale**
   - Decision trees work for 10 edge cases
   - Real-world parts have 10,000 edge cases
   - Better: ask the drawing (Vision API) than guess from geometry

3. **Cost-Benefit of Automation**
   - OCCT implementation: 15 days, 18,500 LOC, $200 infra
   - Result: 50% accuracy, needs hardcoded fixes
   - Alternative: 30 second Vision API call, 90% accuracy, $0.04 cost
   - **Lesson:** Sometimes the "wrong" approach (outsource to AI) is correct

4. **Test on Real Data Early**
   - 37 STEP files caught the 50% false positive rate immediately
   - Would have saved 10+ days if tested day 1
   - Real data > textbook examples

---

**End of OCCT Experiments Archive**

**Last updated:** 2026-02-07  
**Status:** Complete cleanup, ready for Vision API integration  
**Next step:** Implement Vision API + STEP hybrid in `docs/future/`
