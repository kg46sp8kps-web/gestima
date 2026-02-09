# Gestima — Session Learning Log

Tento soubor se automaticky plní po každé session (Stop hook s type:agent).
Claude Code ho čte na začátku KAŽDÉ session = persistentní paměť.

---

## 🔥 CRITICAL: Proxy Features ML Architecture — v1.25.0 (2026-02-09)

**MAJOR MILESTONE:** Complete pivot from feature detection to proxy features ML approach!

### ✅ IMPLEMENTOVÁNO (55 souborů, 12,645+ LOC):

#### **Backend (Python/FastAPI):**
1. **`geometry_feature_extractor.py`** (720 LOC) — 56 proxy metrics
   - `internal_cavity_volume_mm3` 🔴 CRITICAL (indirectly captures pockets/holes)
   - `inner_surface_ratio` (REVERSED orientation surfaces → cavities indicator)
   - `max_feature_depth_mm`, `avg_feature_depth`, `depth_variance`
   - `openness_ratio`, `restricted_access_surface_area`
   - `sharp_edge_ratio`, `feature_density_per_cm3`

2. **`pdf_vision_service.py`** (180 LOC) — Universal Vision context
   - Used by Quote + Parts/Technology modules
   - Extracts: `part_number`, `material`, `rot_pri_hint`, `confidence`

3. **`hybrid_part_classifier.py`** (150 LOC) — Confidence-based classifier
   - Logic: OCCT confident (>0.7 or <0.3) → use OCCT
   - OCCT ambiguous (0.3-0.7) → fallback to Vision hint
   - Default: PRI (safer for milling)

4. **`vision_context.py`** schema (80 LOC)
5. **`hybrid_time_estimator.py`** (200 LOC) — Unified estimation service
6. **DB models:** `TurningEstimation`, `MillingEstimation` (4 migrations)

#### **Frontend (Vue 3/TypeScript):**
1. **`StepViewer3D.vue`** — Inner/outer surface visualization
   - Blue: outer surfaces (FORWARD orientation)
   - Red: inner surfaces (REVERSED orientation - cavities!)
   - Toggle: `colorMode='inner-outer'`

2. **`InnerOuterLegend.vue`** — Color legend component
3. **Manual Estimation Module** (8 komponenty):
   - `ManualEstimationListModule.vue`, `ManualEstimationListPanel.vue`
   - `ManualEstimationDetailPanel.vue`, `ManualCorrectionFormWidget.vue`
   - `EstimateFormWidget.vue`, `SimilarPartsWidget.vue`

4. **TypeScript fixes:** 47 errors fixed (optional chaining, nullish coalescing)

#### **Dokumentace:**
- **ADR-042:** Proxy Features ML Architecture (complete spec)
- **MANUAL-ESTIMATION-GUIDE.md:** User workflow
- **Archived:** `deprecated-2026-02-09-feature-detection/` (ADR-041, Phase 1/2 docs)
- **CHANGELOG.md:** v1.25.0 entry

---

## 🎓 LESSONS LEARNED (2026-02-09)

### **L-060: Proxy Features > Feature Detection**
**Problem:** OCCT can't reliably classify manufacturing features (50% accuracy)
- Hole vs boss, pocket vs step → same geometry, different semantics
- OCCT sees surfaces, NOT manufacturing intent
- Even commercial CAM (SolidCAM) only 70-80% accuracy

**Solution:** Measure **complexity metrics** instead of classifying features
- `internal_cavity_volume` → indirectly captures pockets/holes/grooves
- `concave_edge_ratio` → indirectly captures feature complexity
- `inner_surface_ratio` → indirectly captures cavities/holes
- ML learns: "high cavity + high concave → slow" (NO labels needed!)

**Impact:** Tractable problem (OCCT can measure with 100% accuracy)

### **L-061: Confidence-Based Hybrid Classifier**
**Problem:** OCCT `rotational_score=0.55` (ambiguous) → wrong classification

**Solution:** Combine OCCT + Vision with confidence thresholds
```python
if occt_rotational_score > 0.7:
    return "ROT"  # OCCT confident
elif occt_rotational_score < 0.3:
    return "PRI"  # OCCT confident
elif vision_hint in ["ROT", "PRI"] and vision_confidence > 0.6:
    return vision_hint  # Vision fallback
else:
    return "PRI"  # Default (safer)
```

**Impact:** Best of both worlds (geometry + Vision context)

### **L-062: Inner/Outer Surface Visualization**
**Problem:** Can't visually verify cavity detection (inner surfaces)

**Solution:** Color-code 3D model by face orientation
- Blue: `Orientation = FORWARD` (outer surfaces)
- Red: `Orientation = REVERSED` (inner surfaces - cavities!)
- Three.js: `geometry.addGroup()` + materials array

**Implementation:**
```typescript
brepFaces.forEach((face, index) => {
  const isReversed = face.orientation === 'REVERSED'
  geometry.addGroup(startIndex, count, isReversed ? 1 : 0)
})
mesh.material = [outerMaterial, innerMaterial]  // Blue, Red
```

**Impact:** Visual feedback → debug cavity volume calculation

---

## 🗑️ DEPRECATED (2026-02-09)

### **Archivováno:**
- `docs/archive/deprecated-2026-02-09-feature-detection/`:
  - ADR-041 (ML Time Estimation - feature detection approach)
  - FEATURE-EXTRACTION-DESIGN.md
  - PHASE1-COMPLETION-REPORT.md
  - PHASE2-HANDOFF-PROMPT.md

### **Proč deprecated:**
1. **Feature Recognition je unsolved problem** (even for commercial CAM)
2. **OCCT limitace:** Nemá "material side", "parent feature", "manufacturing intent"
3. **Circular dependency:** Need features for ML → Can't detect features → Can't train ML
4. **Proxy features jsou řešení:** Measure complexity, not classify features

---

## 📊 TECHNICAL DEBT

### **PRIORITY 1: Refactoring fat components (L-036 violations)**
**Problem:** 4 komponenty >300 LOC (110-78% over limit)

**Files to refactor:**
1. `EstimationDetailPanel.vue` (631 LOC → split to 5 components)
2. `ManualCorrectionFormWidget.vue` (522 LOC → split to 3 components)
3. `StepViewer3DReal.vue` (535 LOC → split to 4 components)
4. `ManualEstimationListModule.vue` (245 LOC → split to 2 components)

**Estimated effort:** 2-3 hours (separate session)

### **PRIORITY 2: TypeScript errors v nesouvisejících modulech**
**Remaining:** 17 errors (admin, manufacturing, materials, infor)
- Not introduced by this session (pre-existing)
- Estimation modules: **0 errors** ✅

---

## 🔄 HISTORIE PŘÍSTUPŮ (všechny selhaly)

### 1. **Physics-Based MRR Model** (ADR-040) — ~50% accuracy ❌
- STEP → OCCT → Geometry → MRR → Time
- **Problém:** Edge cases, surface area bug, žádné učení

### 2. **Feature Recognition Pipeline** (ADR-035/036) — garbage-in ❌
- Claude Vision API → features → time
- **Problém:** ±30% geometry errors

### 3. **Vision Hybrid Pipeline** (ADR-039) — over-engineering ❌
- PDF Vision → OCCT verifikace
- **Problém:** Komplexita, Vision nepřesné

### 4. **Advanced G-code Toolpath** — over-engineering ❌
- Toolpath + G-code simulátor
- **Problém:** Potřebujeme CAM software, ne vlastní engine

**Celkem smazáno:** ~2500 LOC (75% redukce!)

---

## ✅ AKTUÁLNÍ STRATEGIE (v1.25.0)

### **Phase 1: Proxy Feature Extraction** ✅ HOTOVO
- 56 metrics extracted via OCCT (deterministic)
- DB models ready (TurningEstimation, MillingEstimation)
- UI workflow (manual estimation)

### **Phase 2: Ground Truth Collection** (user task)
- Upload 500 STEP files
- Extract proxy features → DB
- User enters actual production times

### **Phase 3: ML Training** (3-4 hours)
- Gradient Boosting (XGBoost)
- Feature importance analysis
- Target: **80-90% accuracy** (±10-15 min for 60 min part)

---

## 🚀 CO DÁL?

### **Option A: Test na 37-part datasetu**
```bash
cd uploads/drawings
python scripts/batch_extract_features_37_parts.py
# Verify: internal_cavity_volume, inner_surface_ratio
```

### **Option B: Start ground truth collection**
- Upload STEP files (500+)
- Enter actual production times
- Build ML training dataset

### **Option C: Refactor fat components**
- Fix L-036 violations (4 komponenty >300 LOC)
- Improve maintainability

---

## 📦 GIT STATUS

**Commit:** `e230cc7` (2026-02-09)
**Tag:** `v1.25.0`
**Files changed:** 55
**Lines added:** 12,645+
**Message:** feat: proxy features ML architecture (ADR-042)

---

## ⚠️ DŮLEŽITÉ PRO DALŠÍ SESSION:

### **NIKDY nepoužívej smazané services:**
- ❌ `time_calculator.py` (feature-based)
- ❌ `ai_feature_mapper.py` (Vision FR)
- ❌ `vision_feature_extractor.py` (Claude Vision)
- ❌ `fr_apply_service.py` (FR apply)
- ❌ `setup_planner.py` (setup optimization)
- ❌ `gcode_generator.py` (G-code gen)

### **VŽDY používej:**
- ✅ `geometry_feature_extractor.py` (proxy metrics)
- ✅ `pdf_vision_service.py` (Vision context)
- ✅ `hybrid_part_classifier.py` (OCCT + Vision)
- ✅ `hybrid_time_estimator.py` (unified estimator)
- ✅ `machining_time_estimation_service.py` (MRR baseline - fallback)

### **Feature Detection pipeline NEEXISTUJE:**
- Smazán (deprecated 2026-02-09)
- Archivováno v `docs/archive/deprecated-2026-02-09-feature-detection/`

---

**Version:** 8.0 (2026-02-09)
**Major milestone:** Proxy Features ML Architecture (v1.25.0)
**Git tag:** v1.25.0
**Detailní pravidla:** [docs/core/RULES.md](docs/core/RULES.md)
