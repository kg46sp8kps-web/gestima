## [2.0.0] - Major Cleanup & Architecture Consolidation (2026-02-16)

### Breaking Changes
- **ADR-024 MaterialInput:** Part model no longer has `material_item_id`, `stock_diameter`, `stock_length`, `price_category_id`. Material data moved to `MaterialInput` table (1:N relationship)
- **332 files deleted:** Removed all blind-alley experiments (OCCT/pythonocc, feature detection ML, vision hybrid pipeline, machining time estimation v1, legacy AlpineJS UI)
- **Version unified:** All version references synchronized to 2.0.0 (was inconsistent: 1.12.0 in config, 1.32.1 in docs)

### Removed
- `app/services/`: 30+ experimental services (geometry_extractor, contour_builder, occt_*, pdf_vision_*, hybrid_*, machining_time_*, step_parser, etc.)
- `app/routers/`: estimation_router, machining_time_router, pages_router
- `app/models/`: turning_estimation, milling_estimation, material_database
- `frontend/src/components/modules/estimation/`: Entire estimation UI module (15+ components)
- `frontend/src/components/modules/vision/`: Vision debug module
- `archive/legacy-alpinejs-v1.6.1/`: Legacy AlpineJS frontend
- `docs/archive/`: 60+ obsolete documentation files
- `scripts/`: 20+ obsolete batch/analysis scripts
- OCCT/pythonocc/conda dependencies removed from requirements.txt

### Fixed
- **Test suite:** 32 test failures fixed (ADR-024 Part model migration — 58 → 26 remaining)
- **Test fixtures:** Updated all Part() constructors to use MaterialInput pattern
- **Seed script references:** `seed_machines` → `seed_work_centers` (file was renamed)

### Security (audit findings — not yet fixed)
- SQL injection risk in `infor_router.py:350` (f-string in query)
- Missing auth on 8 TimeVision read endpoints
- Path traversal in `step_router.py:39` and `file_service._ensure_directory()`

---

## [1.32.1] - ADR-044 Phase 2a: FileManager ↔ TimeVision (2026-02-15)

### Added
- **TimeVisionEstimation.file_id** FK → `file_records.id` (nullable, SET NULL on delete)
- **Alembic migration:** `y8z9a0b1c2d3` — add file_id to time_vision_estimations
- **Data migration script:** `scripts/migrate_timevision_files.py` (68 FileRecords, 79 estimations linked)
- **Preview endpoint:** `GET /api/files/{id}/preview` — no auth, PDF only, Content-Disposition: inline
- **Frontend:** `filesApi.getPreviewUrl()`, `FilePreviewPanel.vue` uses `#view=Fit` for PDF fit-to-page

### Changed
- **time_vision_router.py:** file_id resolution in process-openai, process-features, list_drawings; UPSERT prefers file_id
- **file_service.py:** `serve_file()` uses `content_disposition_type="inline"`
- **FilePreviewPanel.vue:** iframe uses `/api/files/{id}/preview` (no auth) instead of `/download` (auth)
- **getDrawingPdfUrl():** Always uses filename-based endpoint (pdf.js can't send auth headers)

### Fixed
- **PDF preview broken:** iframe/pdf.js couldn't authenticate to `/api/files/{id}/download` → 401 → download instead of preview
- **Multiple FileLinks per file:** Migration script now only links newest estimation per type, soft-deleted 98 old links (73 active remain)

---

## [1.31.0] - TimeVision Integration into Technology Module (2026-02-14)

### Added
- **ADR-043:** TimeVision → Technology module integration
- **AIEstimatePanel.vue:** Collapsible right panel for AI time estimation from PDF drawings (~270 LOC)
- **ai_estimation_id:** FK on operations → time_vision_estimations (persists after unlock)
- **Technology → TimeVision sync:** Changing operation time on AI-created operation writes `human_estimate_min` for fine-tuning
- **Visual indicators:** Purple border + Lock icon on AI-locked times, "AI časy" badge in header
- **Alembic migration:** `cf31cd62fcfc` — add ai_estimation_id to operations

### Changed
- **time_vision_router.py:** UPSERT pattern (max 1 estimation per filename), ADMIN auth on calibrate endpoint
- **OperationsDetailPanel.vue:** Added Sparkles button, part prop, sync logic
- **OperationsRightPanel.vue:** AI panel slot, hasAILockedTime computed
- **OperationRow.vue:** Lock/unlock button, purple AI styling
- **OperationsHeader.vue:** AI časy badge with Sparkles icon

### Security
- `PUT /estimations/{id}/calibrate` now requires ADMIN role

---

## [1.26.0] - Proxy Features ML Architecture (2026-02-09)

### Added
- **ADR-042:** Proxy Features ML Architecture (replaces feature detection approach)
- **GeometryFeatureExtractor:** `app/services/geometry_feature_extractor.py` (720 LOC)
- **PdfVisionService:** `app/services/pdf_vision_service.py` (180 LOC)
- **HybridPartClassifier:** `app/services/hybrid_part_classifier.py` (150 LOC)
- **VisionContext Schema:** `app/schemas/vision_context.py` (80 LOC)

### Changed
- **GeometryFeaturesSchema:** Removed feature counts, added proxy metrics (cavity_volume, inner_surface_ratio, etc.)
- **Philosophy:** "classify features" → "measure complexity" (proxy metrics for ML)

### Deprecated
- **ADR-041:** Feature Detection ML approach → replaced by proxy metrics

---

## [1.25.0] - ML-Based Time Estimation Foundation (2026-02-09)

### Added
- Phase 1-6 complete: Feature extraction, DB models, API (6 endpoints), Frontend UI, Validation
- 60+ geometric features from STEP files, TurningEstimation + MillingEstimation models
- ManualEstimationListModule (split-pane), ~3,500 LOC across 26 new files
- 607+ backend tests passing

---

## [1.24.0] - Major Cleanup: Machining Time Consolidation (2026-02-08)

### Changed
- **REMOVED:** Feature Recognition pipeline (~2500 LOC deleted)
- **UNIFIED:** 1 machining time method (ADR-040 Physics-Based MRR)
- **Added:** Audit Framework, Material System seeds, Frontend split components

---

## [1.23.2] - Frontend Bug Fixes (2026-02-06)

### Fixed
- 3D Viewer loading (StepViewerWrapper.vue with `:key` forcing)
- Duplicate uploads in STEP Contours (deduplication logic)

---

## [1.23.1] - OCCT Parser Integration Fix (2026-02-06)

### Fixed
- `analysis_service.py` was NOT passing `use_occt=True` → 40% accuracy instead of 90%+

---

## [1.23.0] - OCCT Backend Parser (2026-02-06)

### Added
- Native OCCT STEP parser (pythonocc-core), ±0.1% volume accuracy
- Hybrid fallback: OCCT → regex → Claude, 31 automated tests

---

## [1.22.0] - STEP Contour Inner Surface Fixes (2026-02-06)

### Fixed
- 3 critical inner contour bugs (zigzag, cone misclassification, cross-holes)

---

## [1.21.0] - 3D STEP Viewer + 2D Geometry Fix (2026-02-05)

### Added
- 3D STEP Viewer (ADR-038): occt-import-js WASM + Three.js, cutting plane, view presets
- `contour_validator.py` — auto-scales Claude's contour to match STEP dimensions

---

## [1.20.0] - Interactive SVG Feature Visualization (2026-02-05)

### Added
- Interactive SVG (ADR-037): feature zones, bidirectional hover, multi-view prismatic
- 5 new backend services (~1812 LOC), 2 frontend components (~307 LOC)

---

## [1.19.0] - Manufacturing Planning Services (2026-02-05)

### Added
- Tool Selection Catalog (ADR-036): 33 entries, diameter-based, ISO groups
- Setup Planner: multi-setup analysis (turning/milling/hybrid)
- Machine Selector: cost-based 3ax/4ax/5ax recommendation
- 70 unit tests total

---

_History before v1.19.0 (v1.0–v1.18) removed in project cleanup 2026-02-16. Available in git history._
