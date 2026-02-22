# GESTIMA - Current Status

**Last Updated:** 2026-02-22
**Version:** 2.0.0
**Branch:** main (3 commits ahead of origin)

---

## Frontend v3 Rewrite — IN PROGRESS (2026-02-22)

Complete frontend rewrite from scratch. New architecture: tiling workspace (panels), design system v2 (51 tokens), TypeScript strict, Vue 3 Composition API.

**Reference:** `frontend/tiling-preview-v3.html` — visual source of truth for all patterns.

### Architecture

```
TilingWorkspace
└── TileNode (recursive)
    ├── TilePanel (leaf)
    │   ├── TilePanelHeader  (drag, maximize, close)
    │   ├── <AsyncModule>    (lazy-loaded)
    │   └── TileDropZones    (drag & drop overlay)
    └── TileSplitDivider     (resize handle)
```

### Module Status

| ModuleId | Component | Status | Notes |
|----------|-----------|--------|-------|
| `parts-list` | TilePartsList.vue | ✅ Done | Search, filters, create modal |
| `work-detail` | TileWorkDetail.vue | ✅ Done | Info bar, tabs (ops/pricing/materials/drawing), draggable tabs |
| `work-ops` | TileWorkOps.vue | ✅ Done | Operations table, summary ribbon |
| `work-pricing` | — | ❌ Placeholder | Batches, kalkulace |
| `work-materials` | — | ❌ Placeholder | MaterialInputs pro vybraný díl |
| `work-drawing` | — | ❌ Placeholder | Drawing/file preview |
| `time-vision` | — | ❌ Placeholder | AI time estimation |
| `batch-sets` | — | ❌ Placeholder | Dávkové sady |
| `partners` | — | ❌ Placeholder | Partneři |
| `quotes` | — | ❌ Placeholder | Nabídky |
| `production` | — | ❌ Placeholder | Výroba |
| `accounting` | — | ❌ Placeholder | Účetnictví |
| `files` | — | ❌ Placeholder | Soubory |
| `admin` | — | ❌ Placeholder | Administrace |

### Infrastructure (done)

| Co | Stav |
|----|------|
| Design system v2 (51 tokenů) | ✅ `assets/css/design-system.css` |
| Auth (HttpOnly cookie) | ✅ `api/auth.ts`, `stores/auth.ts` |
| API client (axios + withCredentials) | ✅ `api/client.ts` |
| Types: Part, Operation, Batch, Workspace | ✅ `types/` |
| API modules: parts, operations, batches | ✅ `api/` |
| Stores: parts, operations, ui, workspace, auth | ✅ `stores/` |
| UI components: Button, Input, Select, Modal, DataTable, Spinner, Tooltip, ConfirmDialog, ToastContainer | ✅ `components/ui/` |
| Composables: useDialog, useKeyboardShortcuts, useResizeHandle | ✅ `composables/` |
| Drag & drop (panel move + tab spawn) | ✅ workspace.ts |
| Center-drop = swap modules | ✅ workspace.ts |
| Pre-commit hooks (validate-frontend-v2, validate-backend, validate-wiring) | ✅ `.claude/hooks/` |
| CI (GitHub Actions) | ✅ `.github/workflows/ci.yml` |

### Next — Sub-modules (priorita)

1. `work-materials` — MaterialInput list pro vybraný díl (API: `/api/material-inputs?part_id=X`)
2. `work-pricing` — Batch list + kalkulace (API: `/api/batches?part_id=X`)
3. `work-drawing` — File preview (API: `/api/files?part_id=X` + iframe preview)

### Next — Standalone moduly (po sub-modulech)

4. `partners` — list partnerů (jednoduchý DataTable)
5. `quotes` — list nabídek
6. `admin` — správa uživatelů, pracovišť, materiálů
7. ostatní dle priority

---

## Backend — Stable (2.0.0)

Žádné aktivní změny. Bezpečnostní nálezy z auditu (neblokující):
- SQL injection risk: `infor_router.py:350` (f-string)
- Missing auth: 8 TimeVision read endpointů
- Path traversal: `step_router.py:39`, `file_service._ensure_directory()`

---

_Historie před 2026-02-22 dostupná v git logu._
