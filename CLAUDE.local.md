# Gestima — Session Learning Log

Tento soubor se automaticky plní po každé session (Stop hook s type:agent).
Claude Code ho čte na začátku KAŽDÉ session = persistentní paměť.

---

## 🔥 CRITICAL: Time Calculation System Cleanup (2026-02-08)

**DŮLEŽITÉ:** Projekt má nyní **POUZE 1 systém** počítání strojních časů!

### ✅ JEDINÝ AKTIVNÍ SYSTÉM:
**Physics-Based MRR Model (ADR-040)**
- Service: `app/services/machining_time_estimation_service.py`
- Router: `app/routers/machining_time_router.py`
- Dokumentace: `docs/ADR/040-machining-time-estimation.md`

**Princip:** STEP → OCCT → Geometry → MRR → Time (100% deterministický)

### ❌ SMAZANÉ SYSTÉMY (již NEEXISTUJÍ):
1. `time_calculator.py` - Feature-based calculator
2. `cutting_conditions.py` - Cutting speeds lookup
3. `batch_estimation_service.py` - Starší batch systém
4. `ai_feature_mapper.py` - AI bridge pro FR
5. `vision_feature_extractor.py` - Claude Vision API
6. `fr_apply_service.py` - Feature Recognition apply
7. `setup_planner.py` - Setup optimization
8. `gcode_generator.py` - G-code generator
9. `toolpath_generator.py` - Toolpath generator
10. `vision_debug_router.py` - Debug router
11. `feature_recognition_router.py` - FR API

**Celkem smazáno:** ~2500 LOC (75% redukcí!)

### 📁 ARCHIVOVANÁ DOKUMENTACE:
Přesunuto do `docs/archive/deprecated-2026-02-08/`:
- ADR-039 (Vision Hybrid Pipeline)
- FEATURE-RECOGNITION-GUIDE.md
- CONSTRAINT-DETECTION-GUIDE.md
- FR-HIERARCHICAL-OPERATIONS.md
- FUTURE_VISION_STEP_HYBRID.md

### ⚠️ DŮLEŽITÉ PRO DALŠÍ SESSION:
- **NIKDY** nepoužívej smazané services!
- **NIKDY** neimportuj `time_calculator`, `ai_feature_mapper`, atd.
- Všechny time calculations = pouze `machining_time_estimation_service.py`
- Feature Recognition pipeline **NEEXISTUJE** (smazán)
- Vision API integration **NEEXISTUJE** (smazán)

---

## 🔧 CRITICAL: Material Seed Scripts (CANONICAL)

**JEDINÉ PLATNÉ seed skripty pro materiály:**

1. **`scripts/seed_material_groups.py`** (9 MaterialGroups)
   - 8-digit kódy: `20910000-20910008`
   - Ocel automatová, Ocel konstrukční, Ocel legovaná, Ocel nástrojová, Nerez, Hliník, Měď, Mosaz, Plasty

2. **`scripts/seed_price_categories.py`** (43 MaterialPriceCategories)
   - 8-digit kódy: `20900000-20900042`
   - Kombinace 9 materiálů × tvary (ROUND_BAR, FLAT_BAR, SQUARE_BAR, PLATE, TUBE, HEXAGONAL_BAR)
   - Příklady: "Ocel konstrukční - tyč kruhová" (20900026), "Ocel automatová - tyč plochá" (20900023)

3. **`scripts/seed_material_norms_complete.py`** (83 MaterialNorms)
   - Převodní tabulka W.Nr/EN/CSN/AISI → MaterialGroup

**POZNÁMKA:** Všechny ostatní seed skripty v `scripts/archive/seed_material_*` jsou **DEPRECATED** a nepoužívají se!

**Model:** `app/models/material.py` - String(8) kódy dle ADR-017 (Migration b9c0d1e2f3g4 z 2026-02-03)

**Dokumentace:** `docs/guides/MATERIAL-GUIDE.md` (verze 2.0, 2026-02-08)

---

## Session 2026-02-07 (3D Mfg Feature Coloring — Edge Convexity)

### Co bylo vytvořeno
- **Batch analýza** 37 STEP souborů: waterline polar map + edge convexity (16 ROT, 21 PRI)
- **Backend endpoint** `GET /api/feature-recognition-batch/step-face-features/{filename}` — OCCT edge convexity analýza, per-face mfg_feature klasifikace
- **Backend endpoint** `GET /api/feature-recognition-batch/step-raw/{filename}` — raw STEP binary download
- **StepViewer3D.vue** — rozšířen o `faceFeatures` + `showFeatureColors` props, per-face coloring přes `geometry.addGroup()` + materials array, legenda
- **StepFeatureViewer.vue** (~160 LOC) — standalone wrapper, parallel fetch STEP + features
- **Standalone test** `app/static/test_3d_features.html` — Three.js ESM + occt-import-js WASM, 37 souborů klikací

### Klíčový poznatek: Face ordering
OCCT `TopExp_Explorer` face traversal order = shodné pořadí s `occt-import-js` `brep_faces[]` v browseru. Per-face coloring mapuje 1:1 bez nutnosti matchingu.

### OCC 7.9 API rozdíly (pythonocc-core)
- `.Size()` místo `.Extent()` (přejmenováno)
- `TopTools_IndexedMapOfShape` + `FindIndex()` pro stabilní face/edge ID (ne `.HashCode()`)
- `face_list.First()` / `face_list.Last()` pro 2-face manifold edges (ne SWIG iterator)

### Klasifikační logika (`occt_edge_classifier.py`)
Rozhodovací strom na základě `concave_ratio = concave_edges / total_edges`:

**Cylindrical:**
- outer + concave ≤ 0.3 → `shaft_segment`
- outer + concave 0.3–0.7 → `step_transition`
- outer + concave > 0.7 → `groove_wall`
- inner + concave ≤ 0.7 → `bore`
- inner + concave > 0.7 → `groove_wall`

**Planar:**
- concave > 0.7 + inner → `pocket_bottom`
- concave > 0.7 + outer → `groove_bottom`
- concave 0.3–0.7 → `step_face`
- concave ≤ 0.3 → `end_face`

**Conical:** concave > 0.5 → `chamfer`, else → `taper`
**Toroidal:** concave > 0.5 → `fillet_inner`, else → `fillet_outer`

### KNOWN LIMITATIONS klasifikace (neopraveno, dokumentováno)

**1. Vnější rohové zaoblení na PRI dílech → `shaft_segment` (špatně)**
- Cylindrická plocha (outer, convex edges) na prizmatickém dílu = rohový radius, ne hřídel
- Root cause: klasifikátor nerozlišuje fillet vs shaft — oba jsou cylindrical + outer + convex
- Řešení potřebuje: arc sweep angle (fillet ~90°, shaft ~360°), nebo radius vs. bbox poměr

**2. Vnitřní radiusy → `bore` (špatně)**
- Malé vnitřní cylindrické plochy (inner, Orientation=REVERSED) = fillet přechod, ne vrtaná díra
- Root cause: OCCT klasifikuje fillet face jako REVERSED orientation → is_inner=True → bore
- Řešení potřebuje: sweep angle detekci nebo sousední-plochy analýzu

**3. Dno drážky vs. pocket_bottom záměna**
- Záleží na is_inner flag, ale kontext (kapsa vs drážka) vyžaduje sousední plochy

**4. Part type klasifikace špatná pro PRI díly s mnoha dírami**
- Threshold >40% cylindrických ploch → ROT, ale PRI díly s 20+ bory překročí threshold
- FORCE_TYPE dict s 9 hardcoded korekcemi (3DM_90057637, 0347039, JR808404, JR810686, JR810695, JR811181, JR811183, JR811187, PDM-280739)

### Architektonické rozhodnutí: 2D kontura vs 3D model pro strojní časy
**OTEVŘENÁ OTÁZKA** — viz konec session. Dvě cesty:
- **2D kontura (waterline r(z)):** Jednodušší, funguje pro ROT díly, generuje operace z profilové geometrie
- **3D B-rep analýza:** Přesnější, ale komplexnější, umožňuje pocket/slot/hole detekci na PRI dílech
- Edge convexity klasifikace je MEZIKROK — identifikuje CO se obrábí, ale ne JAK a JAK DLOUHO

### Environment
- conda env: `gestima-prod` (pythonocc-core OCC 7.9.0)
- Backend: `app.gestima_app:app` port 8000
- Frontend: port 5173 (Vite dev)
- Three.js ESM importmap: lokální kopie v `app/static/` (CDN jsdelivr byl 503)
- occt-import-js WASM: `frontend/public/` + kopie v `app/static/`

### Soubory vytvořené/modifikované
- `uploads/drawings/batch_combined_analysis.py` — batch skript (waterline + edge convexity)
- `uploads/drawings/contour_SVG/batch_combined_results.json` — výsledky 37 souborů
- `app/routers/feature_recognition_router.py` — 2 nové endpointy (~270 LOC přidáno)
- `frontend/src/components/modules/visualization/StepViewer3D.vue` — feature coloring (+150 LOC)
- `frontend/src/components/modules/visualization/StepFeatureViewer.vue` — nová komponenta (160 LOC)
- `app/static/test_3d_features.html` — standalone 3D test stránka
- `app/static/test_features.html` — tabulková test stránka (bez 3D)

---

## Session 2026-02-08 (Machining Time UI Refactor + PDF Viewer)

### Co bylo hotovo
**1. Backend time calculation refactor** (setup removed, split times):
- Removed `setup_time_min` from calculations (deprecated, defaulted to 0.0)
- Split roughing/finishing times into **main** (actual machining) + **auxiliary** (rapids/tool changes)
- Auxiliary time: 20% of roughing main, 15% of finishing main
- Files: `app/services/machining_time_estimation_service.py`, `app/schemas/machining_time.py`

**2. Frontend time display refactor**:
- Updated `TimeBreakdownWidget.vue` to show 2 sections (Roughing + Finishing), each with main + aux times
- Updated TypeScript types in `frontend/src/types/estimation.ts`
- Files: `frontend/src/components/modules/estimation/TimeBreakdownWidget.vue`, `EstimationDetailPanel.vue`

**3. PDF drawing viewer (floating window)**:
- Created `EstimationPdfWindow.vue` - simple PDF viewer reading URL from window title (format: `"Výkres: filename|url"`)
- Created JSON mapping: `uploads/drawings/step_pdf_mapping.json` (38 STEP → PDF filename mappings)
- Character-by-character matching algorithm (minimum 5 common chars)
- Linked to estimation detail panel: click "📄 Výkres" → opens floating window
- **Auto-update on selection change**: watch on `props.result` updates PDF window title when switching parts in list
- Files: `EstimationPdfWindow.vue`, `EstimationDetailPanel.vue`, `windows.ts` (+`updateWindowTitle`, `findWindowByModule`)

**4. Batch results regenerated**:
- Re-ran `app/scripts/batch_estimate_machining_time.py` with new time structure
- Output: `uploads/drawings/batch_machining_time_results.json` (37 files, all deterministic)

### Key implementation pattern: Window title as data carrier
- PDF URL passed via window title: `"Výkres: filename.step|/uploads/drawings/file.pdf"`
- `EstimationPdfWindow` parses title into `displayFilename` + `pdfUrl` (computed)
- Watch on `props.result` → find open PDF window → update title → component reacts (Vue reactivity)
- No need for complex context store extensions - simple string manipulation

### Files created/modified
- `frontend/src/components/modules/estimation/EstimationPdfWindow.vue` (NEW, 180 LOC)
- `frontend/src/components/modules/estimation/EstimationDetailPanel.vue` (PDF button + auto-update watch)
- `frontend/src/components/modules/estimation/TimeBreakdownWidget.vue` (redesigned display)
- `frontend/src/stores/windows.ts` (+`updateWindowTitle`, `findWindowByModule`)
- `frontend/src/views/windows/WindowsView.vue` (registered EstimationPdfWindow)
- `uploads/drawings/step_pdf_mapping.json` (NEW, 38 mappings)

---

## Starší sessions (archiv)

### 2026-02-04: Agent systém refaktor
- Hooks > dokumentace pro enforcement. YAML frontmatter v `.claude/agents/*.md` s `disallowedTools`.

### 2026-02-04: Feature recognition v3 (point-based contour)
- Block model → point-based kontura. Prompt MUSÍ mít konkrétní příklad. API bez PDF = nesmysly.

### 2026-02-05: Interactive SVG (ADR-037)
- 5 backend services + 2 frontend komponenty. ŠÉFÍK mode pro 12+ souborů.

### 2026-02-05: Deterministic FR Pipeline (ADR-035/036)
- `analysis_service.py` pipeline dispatch. Claude geometry ±30% nepřesná = garbage-in-garbage-out.

### 2026-02-05: 3D STEP viewer (ADR-038)
- occt-import-js WASM + Three.js. `locateFile` pro WASM cestu. Z-up konvence.

### 2026-02-06: STEP contour fixes + OCCT decision
- `surf.radius` pro cones = semi_angle, NE radius. Off-axis filter na VŠECHNY povrchy. OCCT migrace schválena.

### 2026-02-06: 3D viewer + contour overlay
- OCCT (pythonocc-core) MUSÍ být nainstalováno. Backend `app.gestima_app:app`.
