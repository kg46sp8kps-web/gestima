# Gestima — Session Learning Log

Tento soubor se automaticky plní po každé session (Stop hook s type:agent).
Claude Code ho čte na začátku KAŽDÉ session = persistentní paměť.

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
