# Phase A-B Delivery Summary: ML Estimation Validation Workflow + 3D Viewer

**Date:** 2026-02-09
**Status:** ✅ DELIVERED (Phases A-B Complete)
**Next Steps:** AI Vision Integration + Manual Override UI (separate planning session required)

---

## Executive Summary

Delivered foundational infrastructure for ML-based machining time estimation system:

- **Phase A (Backend):** Validation workflow with 12 new columns, 3 API endpoints, Alembic migration
- **Phase B (3D Viewer):** Three.js STEP viewer with feature visualization, stock/part/removal toggles

**CRITICAL DISCOVERY:** Automatic ROT/PRI classification is ~10% accurate on real-world parts. Examples:
- JR 810663: Simple rotational part → classified as MILLING (wrong)
- Some PRI parts → cylindrical stock (wrong)
- BBox calculations unreliable

**User Decision:** Requires AI Vision integration to extract ground truth from PDF drawings before proceeding with ML training.

---

## Phase A: Backend Validation Workflow

### Database Models (Modified)

**Files:**
- `app/models/turning_estimation.py`
- `app/models/milling_estimation.py`

**Added 12 columns to both tables:**

```python
# ========== VALIDATION WORKFLOW ==========
validation_status: str = "pending"  # pending → validated → estimated → trained

# Corrected features (user-validated data)
corrected_material_code: str | None
corrected_bbox_x_mm: float | None
corrected_bbox_y_mm: float | None
corrected_bbox_z_mm: float | None
corrected_part_type: str | None  # "ROT" or "PRI" override
correction_notes: str | None
validated_by_user_id: int | None
validation_date: datetime | None

# ========== AUTO ESTIMATION (physics-based MRR) ==========
auto_estimated_time_min: float | None
auto_estimate_date: datetime | None

# ========== MANUAL ESTIMATION (user correction) ==========
estimated_time_min: float | None  # User's final estimate
correction_reason: str | None  # Why different from auto?
```

**Migration:** `alembic/versions/933da2e09e7a_add_validation_workflow.py`

**SQLite Fix Applied:**
```python
batch_op.add_column(sa.Column('validation_status', sa.String(length=20),
                               nullable=False, server_default='pending'))
```
SQLite requires `server_default` for NOT NULL columns on existing tables.

### API Endpoints (3 New)

**File:** `app/routers/estimation_router.py`

#### 1. `PATCH /api/estimation/validate/{record_id}`
**Purpose:** Validate extracted features with user corrections

**Request Body:**
```json
{
  "corrected_material_code": "20910000",
  "corrected_bbox_x_mm": 50.0,
  "corrected_bbox_y_mm": 50.0,
  "corrected_bbox_z_mm": 120.0,
  "corrected_part_type": "ROT",
  "correction_notes": "Changed from PRI to ROT - part is cylindrical shaft"
}
```

**Response:** Updated `EstimationRecordResponse` with `validation_status = "validated"`

**L-008 Compliance:** ✅ try/except/rollback

#### 2. `POST /api/estimation/auto-estimate/{record_id}`
**Purpose:** Calculate auto-estimated time using physics-based MRR model (ADR-040)

**Query Params:** `part_type: "ROT" | "PRI"`

**Response:**
```json
{
  "record_id": 1,
  "part_type": "ROT",
  "auto_estimated_time_min": 12.5,
  "breakdown": {
    "roughing_main_min": 8.2,
    "roughing_aux_min": 1.6,
    "finishing_main_min": 2.1,
    "finishing_aux_min": 0.3
  }
}
```

**Implementation:** Calls `MachiningTimeEstimationService.estimate_from_step()` with corrected features (if available), falls back to extracted features.

#### 3. `PATCH /api/estimation/finalize-estimate/{record_id}`
**Purpose:** Finalize time estimate with user's corrected value

**Request Body:**
```json
{
  "estimated_time_min": 15.0,
  "correction_reason": "Added 2.5 min for deburring + inspection"
}
```

**Response:** Updated record with `validation_status = "estimated"`

**Workflow State Machine:**
```
pending → [validate] → validated → [finalize-estimate] → estimated → [ML training] → trained
```

---

## Phase B: 3D STEP Viewer with Feature Visualization

### Component Architecture

**Created:**
- `frontend/src/components/modules/estimation/StepViewer3DReal.vue` (535 LOC)

**Modified:**
- `frontend/src/components/modules/estimation/ManualEstimationDetailPanel.vue` (integrated 3D viewer)
- `frontend/src/components/modules/MasterAdminModule.vue` (added "ML Estimation" tab)

### Features Implemented

#### 1. Three.js Scene Setup
```typescript
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

// Scene with dark background
scene.background = new THREE.Color(0x1a1a1a)

// PerspectiveCamera (FOV 50°)
camera.position.set(bboxX * 1.5, bboxY * 1.5, bboxZ * 2)

// OrbitControls with damping
controls.enableDamping = true
controls.dampingFactor = 0.05

// Lighting: ambient (0.6) + 2 directional (0.8, 0.4)
// Grid helper (20x20)
// Axes helper (XYZ)
```

#### 2. Stock Mesh Visualization
**Adaptive stock geometry based on `rotational_score`:**

```typescript
if (rotational_score > 0.6) {
  // ROT part → Cylindrical stock
  const diameter = Math.max(bboxX, bboxY)
  const length = bboxZ
  geometry = new THREE.CylinderGeometry(diameter / 2, diameter / 2, length, 32)
  geometry.rotateX(Math.PI / 2)  // Align with Z-axis
} else {
  // PRI part → Box stock
  geometry = new THREE.BoxGeometry(bboxX, bboxY, bboxZ)
}

// Wireframe rendering (gray edges)
stockMesh = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0x666666 }))
```

**KNOWN ISSUE:** Stock detection is unreliable (~10% accuracy). User reported:
- JR 810663: Rotational part → box stock (should be cylinder)
- Some PRI parts → cylinder stock (should be box)

#### 3. Part Mesh (Placeholder)
**Current implementation:**
```typescript
// TODO: Replace with real OCCT mesh from backend
const scale = 0.8
const geometry = new THREE.BoxGeometry(
  bboxX * scale,
  bboxY * scale,
  bboxZ * scale
)

partMesh = new THREE.Mesh(geometry, new THREE.MeshPhongMaterial({ color: 0x2196F3 }))
```

**Next steps:**
- Backend endpoint: `GET /api/step/mesh/{filename}` → triangulated mesh (OCCT)
- Frontend: Load mesh via `THREE.BufferGeometry` from vertex/index arrays

#### 4. Feature Color Mapping
**13 manufacturing feature types:**

```typescript
const FEATURE_COLORS: Record<string, string> = {
  // Cylindrical
  shaft_segment: '#4CAF50',    // green
  bore: '#2196F3',              // blue
  groove_wall: '#FF9800',       // orange
  step_transition: '#9C27B0',   // purple

  // Planar
  end_face: '#FFEB3B',          // yellow
  step_face: '#00BCD4',         // cyan
  pocket_bottom: '#E91E63',     // pink
  groove_bottom: '#FF5722',     // deep orange

  // Conical
  chamfer: '#8BC34A',           // light green
  taper: '#FFC107',             // amber

  // Toroidal
  fillet_inner: '#9E9E9E',      // gray
  fillet_outer: '#607D8B',      // blue-gray

  // Unknown
  unknown: '#CCCCCC'            // light gray
}
```

**Feature data structure:**
```typescript
features = [
  { type: 'shaft_segment', color: '#4CAF50', faceIndices: [0, 1] },
  { type: 'end_face', color: '#FFEB3B', faceIndices: [2, 3] },
  { type: 'chamfer', color: '#8BC34A', faceIndices: [4] }
]
```

**Implementation status:** Mock data only (backend endpoint TODO: `/api/step/face-features/{filename}`)

#### 5. Interactive Controls
**5 toggle buttons:**

| Button | Action | Visual Effect |
|--------|--------|---------------|
| 📦 Stock | `toggleStock()` | Show/hide stock wireframe |
| 🔧 Part | `togglePart()` | Show/hide part mesh |
| 🔴 Removal | `toggleRemoval()` | Show/hide removal material (boolean subtraction) |
| 🎨 Features | `toggleFeatures()` | Switch part material to multi-material per-face coloring |
| 🎯 Reset | `resetCamera()` | Reset camera to initial position |

**Feature Legend:**
```vue
<div v-if="showFeatures && features.length > 0" class="feature-legend">
  <h5>Identified Features:</h5>
  <div class="legend-items">
    <div v-for="(feature, idx) in uniqueFeatures" :key="idx" class="legend-item">
      <span class="color-box" :style="{ background: feature.color }"></span>
      <span class="feature-name">{{ feature.label }} ({{ feature.count }})</span>
    </div>
  </div>
</div>
```

#### 6. Info Bar
**Displays key metrics:**
```
📐 BBox: 50 × 50 × 120 mm
📊 Part: 235619 mm³
🔄 Removal: 35%
🎨 Features: 12
```

### UI Integration

**ManualEstimationDetailPanel.vue structure:**
```vue
<template>
  <div class="estimation-detail-panel">
    <!-- KEY FEATURES -->
    <section class="features-section">
      <dl class="features-grid">
        <div class="feature-item">Volume: 235619 mm³</div>
        <div class="feature-item">Removal: 35% (82467 mm³)</div>
        <div class="feature-item">Surface Area: 47124 mm²</div>
        <div class="feature-item">BBox: 50 × 50 × 120 mm</div>
        <div class="feature-item">Material: 20910000</div>
        <div class="feature-item">Machinability: 100%</div>
        <div class="feature-item">Rotational Score: 85%</div>
        <div class="feature-item">Cylindrical Surface: 73%</div>
        <div class="feature-item">Planar Surface: 21%</div>
      </dl>
    </section>

    <!-- SIMILAR PARTS -->
    <SimilarPartsWidget v-if="similarParts.length > 0" />

    <!-- ESTIMATE FORM -->
    <EstimateFormWidget @submit="$emit('submit-estimate', $event)" />

    <!-- 3D VIEWER -->
    <StepViewer3DReal
      :filename="record.filename"
      :bbox-x="record.bbox_x_mm"
      :bbox-y="record.bbox_y_mm"
      :bbox-z="record.bbox_z_mm"
      :part-volume="record.part_volume_mm3"
      :removal-ratio="record.removal_ratio"
      :rotational-score="record.rotational_score"
    />
  </div>
</template>
```

---

## Critical Issues Discovered

### 1. Classification Accuracy: ~10% (BLOCKING)

**Examples of failures:**

**JR 810663:**
- Reality: Simple rotational shaft (external turning)
- Classified as: MILLING (PRI)
- Stock: Box (should be cylinder)
- Root cause: `rotational_score` heuristic broken

**Unknown PRI parts:**
- Reality: Prismatic milled parts
- Classified as: TURNING (ROT)
- Stock: Cylinder (should be box)

**Impact:** Cannot proceed with ML training - garbage input = garbage model

### 2. Feature Extraction Limitations

**From Phase 1 implementation:**
- BBox calculations unreliable (some parts)
- Stock detection wrong (cylinder vs box confusion)
- Material group code not extracted (needs PDF)
- Actual stock dimensions not known (PDF required)

### 3. User Feedback

**Direct quote (2026-02-09):**
> "takhle to nepujde, protože budeme korigovat casy, které mají nepřesné vstupní informace jako třeba materiáal atd...také je naprosto špatné identifikace mill/rot dílů a tvorba polotovaru...jak navrhuješ debugging?"

> "budeme číst z ai vision z pdf informace o dílu..nepomohlo by to pro prvotní kvalifikaci dílu a zparsování co jak vypadá? protože toto je naprosto zoufalé a odpovídá to na 10% zhruba"

---

## User Requirements for Phase C (Next Session)

### Option A: Manual Override UI (1 hour)
**User can manually correct:**
- Part type (ROT/PRI radio buttons)
- Stock type (Cylinder/Box/Tube dropdown)
- Stock dimensions (editable fields)
- Material code (dropdown from MaterialGroups)
- BBox dimensions (editable fields)

**UI Layout:** Split pane with PDF viewer on left, editable form on right

### Option B: AI Vision Integration (2-3 hours)
**Extract from PDF drawings:**
- Part type (ROT/PRI) - read title block or infer from views
- Stock type + dimensions - read from material spec or infer from envelope
- Material code - read from title block material field
- Manufacturing features - read from GD&T symbols, notes, dimensions
- Tolerances - read from dimension annotations

**Integration requirement:**
> "ok chci A i B ale připrav nejdříve plán..at integrujeme AI promt společně s tím co máme v modulu QUOTE at v"vxtáhneme z pdf všechny data!"

**Existing infrastructure to leverage:**
- `app/services/quote_request_parser.py` - likely has Claude API integration
- `app/services/pdf_context_extractor.py` - PDF parsing logic
- `app/services/step_pdf_parser.py` - STEP-PDF mapping
- `app/services/drawing_parser.py` - pattern matching (no ML)

---

## Technical Debt / TODO

### Backend
- [ ] Real OCCT mesh endpoint: `GET /api/step/mesh/{filename}`
- [ ] Face feature detection endpoint: `GET /api/step/face-features/{filename}`
- [ ] Boolean subtraction for removal volume visualization
- [ ] Batch re-run feature extraction with corrected classification

### Frontend
- [ ] Replace placeholder part geometry with real OCCT mesh
- [ ] Implement per-face material coloring (multi-material)
- [ ] Implement removal material visualization (boolean subtraction)
- [ ] Add PDF viewer side-by-side with 3D viewer
- [ ] Implement manual override form (Option A)
- [ ] Integrate AI Vision extraction (Option B)

### Testing
- [ ] Pytest: 3 new endpoints (`validate`, `auto-estimate`, `finalize-estimate`)
- [ ] Vitest: StepViewer3DReal.vue component tests
- [ ] Manual validation: Test JR 810663 classification with AI Vision

### Documentation
- [ ] ADR-041: ML Time Estimation System Architecture
- [ ] MANUAL-ESTIMATION-GUIDE.md: User workflow documentation
- [ ] AI-VISION-INTEGRATION-PLAN.md: Phase C design (REQUIRED before implementation)

---

## Deliverables Summary

### Files Created (2)
1. `alembic/versions/933da2e09e7a_add_validation_workflow.py` (150 LOC)
2. `frontend/src/components/modules/estimation/StepViewer3DReal.vue` (535 LOC)

### Files Modified (5)
1. `app/models/turning_estimation.py` (+12 columns)
2. `app/models/milling_estimation.py` (+12 columns)
3. `app/routers/estimation_router.py` (+3 endpoints, ~180 LOC)
4. `frontend/src/components/modules/estimation/ManualEstimationDetailPanel.vue` (+10 LOC)
5. `frontend/src/components/modules/MasterAdminModule.vue` (+1 tab)

### Total LOC: ~900 (Phase A: 350, Phase B: 550)

### Git Status
- Migration applied: ✅ `933da2e09e7a`
- Database schema: ✅ 12 new columns in 2 tables
- Backend build: ✅ No errors
- Frontend build: ✅ No errors
- Pytest: ⏸️ Not run (no new backend tests written yet - technical debt)
- Vitest: ⏸️ Not run (no frontend tests written yet - technical debt)

---

## Next Steps (Phase C - Separate Planning Session)

**BLOCKING REQUIREMENT:** AI Vision integration plan document

**User requested:**
1. Research existing Quote module PDF parsing infrastructure
2. Create unified AI Vision prompt design (leverage existing Claude API patterns)
3. Define data extraction schema (part_type, stock_type, dimensions, material, features)
4. Design Manual Override UI (Option A) - mockup/wireframe
5. Design AI Vision Integration flow (Option B) - sequence diagram
6. Show how to fix JR 810663 example with PDF ground truth

**Estimated effort:**
- Planning document: 1 hour
- Option A implementation: 1 hour
- Option B implementation: 2-3 hours
- Testing + validation: 1 hour
- **Total: 5-6 hours**

**Document to create:** `docs/phase1/AI-VISION-INTEGRATION-PLAN.md`

---

## Lessons Learned

**L-060: Classification Heuristics Fail on Real Data**
- **Problem:** `rotational_score > 0.6` threshold works on synthetic data, fails on production parts
- **Root cause:** Real parts have mixed features (ROT parts with pockets, PRI parts with bores)
- **Solution:** Ground truth from PDF drawings (title block, drawing views) > geometric heuristics
- **Impact:** Cannot train ML model without reliable classification

**L-061: Stock Detection Requires Domain Knowledge**
- **Problem:** BBox != actual stock dimensions (material allowances, standard sizes)
- **Example:** Part BBox 48mm diameter → actual stock 50mm (standard bar size)
- **Solution:** Extract from PDF material specification or quote database
- **Impact:** 20-30% error in removal volume calculation

**L-062: Three.js Z-up Convention**
- **Implementation:** OCCT uses Z-up (ISO 841 standard for CNC), Three.js default is Y-up
- **Solution:** Rotate cylindrical stock `geometry.rotateX(Math.PI / 2)` to align with Z-axis
- **Impact:** Correct visualization of turning parts (spindle axis = Z)

**L-063: SQLite Server Default Requirement**
- **Problem:** `ALTER TABLE ADD COLUMN x NOT NULL` fails on SQLite without default value
- **Solution:** Use `server_default='pending'` in Alembic migration
- **Impact:** Enables backward-compatible schema migrations

**L-064: Floating Window Module Architecture**
- **Problem:** Initially edited `MasterDataView.vue` (deprecated), tab not visible
- **Solution:** Floating windows use `*Module.vue` components (e.g., `MasterAdminModule.vue`)
- **Impact:** Consistent UI pattern across all admin features

---

**Phase A-B Status:** ✅ COMPLETE
**Handoff to Phase C:** AI Vision Integration Planning Session Required
**Blocking Issue:** Classification accuracy 10% → PDF ground truth extraction needed
