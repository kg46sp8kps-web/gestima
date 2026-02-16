# ADR-043: TimeVision Integration into Technology Module

**Status:** Accepted (v2 — refactored)
**Date:** 2026-02-14
**Author:** AI + User

## Context

TimeVision (AI time estimation from PDF drawings) was a standalone module. User needs the same AI estimation directly in the Technology module (PartOperationsModule) to:
1. Estimate machining time from drawing without leaving Technology
2. Create operations with AI-estimated times (freely editable)
3. Provide explicit calibration (human estimate + actual time) via dedicated Model Learning ribbon

**v2 change (2026-02-14):** Locking approach abandoned. Technologist has full freedom to edit times. Calibration is explicit, not auto-synced.

## Decision

### 1. AI Estimate Panel (Collapsible Right Panel)

`AIEstimatePanel.vue` component in Technology module:
- Loads primary drawing from part via `listDrawings(part_number)`
- Reuses existing estimation if found (`fetchOpenAIEstimation(filename)`)
- Creates new estimation via SSE only if none exists (UPSERT backend)
- Shows: time, part type, complexity, confidence, operation breakdown
- **UPSERT operations:** Re-running AI on same part UPDATES existing AI operation (no duplicates)

### 2. One Operation = Total Time

AI creates **1 operation** with total estimated time (not N operations per breakdown).
Reason: soustružení + vrtání typically run on one CNC machine in one setup.

- Operation type: `turning` (ROT) or `milling` (PRI) based on `part_type`
- Work center: auto-selected by type + priority
- Breakdown shown as info only (not separate operations)

### 3. No Locking — Free Edit + Visual Indicators

- ~~`operation_time_locked = true` on AI-created operations~~ **REMOVED**
- Operation time inputs are ALWAYS editable (no disabled state)
- **Visual indicators:**
  - `AlertTriangle` icon next to seq number when `ai_estimation_id != null`
  - "Existuje AI čas" label next to "Operace" header (normal color → RED when user modifies AI time)
  - `RotateCcw` restore button next to operation_time input (visible only after modification)
- `operation_time_locked` field remains in DB schema (backward compat) but is IGNORED everywhere

### 4. ai_estimation_id (FK)

Column `operations.ai_estimation_id` → FK to `time_vision_estimations.id`:
- Set on operation creation/update from AI panel
- Sole indicator of AI origin (replaces `operation_time_locked` for detection)
- Used by ML ribbon to fetch full estimation data

### 5. Model Learning Ribbon (Explicit Calibration)

**No auto-sync.** Calibration is done explicitly via dedicated ribbon below operations table:

```
OperationsRightPanel
  ├── OperationsHeader (+ "AI odhad" badge)
  ├── MaterialInputSelectorV2
  ├── .operations-split
  │     ├── OperationsDetailPanel (+ "Existuje AI čas" warning)
  │     └── AIEstimatePanel (collapsible)
  └── Model Learning ribbon (visible when hasAIEstimation)
```

**Ribbon contains:**
| AI odhad (teal, readonly) | Můj odhad (blue, input) | Skutečný čas (amber, input) | Na operaci (grey, readonly) |
| `estimated_time_min` | `human_estimate_min` | `actual_time_min` | `operation_time_min` |

Plus: status badge (estimated/calibrated/verified), deviations (%), complexity, part_type, notes, Save button.

**Data flow:** `firstAIEstimationId` watch → `fetchEstimationById(id)` → form refs → `calibrateEstimation(id, payload)`.

### 6. Restore AI Time

When user modifies an AI operation's time:
1. Warning turns red, `RotateCcw` button appears next to input
2. Click restore → `fetchEstimationById(ai_estimation_id)` → update operation back to `estimated_time_min`
3. Warning resets to normal color

### 7. TimeVision UPSERT (Deduplication)

Backend `process-openai` endpoint uses UPSERT pattern:
- Query existing estimation by `pdf_filename` (newest, not deleted)
- If exists: UPDATE AI fields, preserve calibration (`actual_time_min`, `human_estimate_min`)
- If not exists: INSERT new record
- Result: max 1 estimation per filename

### 8. Calibrate Endpoint Security

`PUT /estimations/{id}/calibrate` requires ADMIN role (`require_role([UserRole.ADMIN])`).

## Visual Indicators

| Element | Indicator |
|---------|-----------|
| Seq cell (OperationRow) | `AlertTriangle` icon (teal, 12px) when `ai_estimation_id` present |
| Operations header (DetailPanel) | "Existuje AI čas" label (secondary → danger on modification) |
| Operation time input | Normal style (no coloring), `RotateCcw` button beside input on modification |
| Operations header (OperationsHeader) | "AI odhad" badge (purple, Sparkles icon) |
| Model Learning ribbon | Teal header, 4 time columns, status badge, deviation grid |

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/api/time-vision.ts` | `fetchEstimationById(id)` helper |
| `frontend/src/components/modules/operations/AIEstimatePanel.vue` | UPSERT operations, no lock step |
| `frontend/src/components/modules/operations/OperationsDetailPanel.vue` | AI warning label, restore function, no sync logic |
| `frontend/src/components/modules/operations/OperationsRightPanel.vue` | Model Learning ribbon + state |
| `frontend/src/components/modules/operations/OperationRow.vue` | AlertTriangle, restore button, no lock UI |
| `frontend/src/components/modules/operations/OperationsHeader.vue` | "AI odhad" badge |
| `frontend/src/types/operation.ts` | ai_estimation_id on all interfaces |
| `app/models/operation.py` | ai_estimation_id column + schemas |
| `app/routers/operations_router.py` | Removed locked field validation |
| `app/routers/time_vision_router.py` | UPSERT pattern, ADMIN auth on calibrate |

## Fine-Tuning Data Flow

```
AI estimation (estimated_time_min)
    ↓
User freely edits operation time in Technology
    ↓
User enters human_estimate_min + actual_time_min
    in Model Learning ribbon (explicit calibration)
    ↓
calibrateEstimation() → TimeVision status → calibrated/verified
    ↓
Export JSONL: ground_truth = actual_time_min || human_estimate_min
    ↓
GPT-4o Vision fine-tuning
```

## Known Limitations

1. **Single AI estimation display:** ML ribbon shows only first AI operation's estimation. Multiple AI operations per part not fully supported.
2. ~~**Silent 409 on version conflict:**~~ **FIXED** — Re-fetches fresh data + shows warning toast on 409.
3. ~~**Null reset not detected:**~~ **FIXED** — Uses `!==` comparison instead of truthy guard. Note: null → `undefined` in payload = field not sent (backend unchanged). Full null reset would need backend schema change.
4. **Legacy `operation_time_locked` field:** Exists in DB, types, and parts_router clone logic but is never set/checked by UI.

## Future (Not Implemented)

- Pila (saw) as first operation (OP10) — time from stock dimensions
- Kontrola (quality) as last operation (OP90) — fixed time
- Material selection from AI-detected material
- Machining aggressiveness selector in AI panel
- Multi-estimation support in ML ribbon (tab/dropdown)
- Phase 2: Quote module integration (parse RFQ PDF → create items + estimate)
