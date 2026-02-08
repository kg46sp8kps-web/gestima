# Stop Hook Frontend Violations — 2026-02-06

**Context:** Bug fix session (3D viewer + duplicate uploads)
**Hook:** `validate-frontend.sh` (L-036 enforcement)

---

## Pre-Existing Violations (NOT introduced this session)

| File | LOC | Status | Session |
|------|-----|--------|---------|
| `frontend/src/components/ui/ColumnChooser.vue` | 356 | ⚠️ Pre-existing | N/A |
| `frontend/src/components/ui/DataTable.vue` | 642 | ⚠️ Pre-existing | N/A |
| `frontend/src/components/layout/AppHeader.vue` | 1181 | ⚠️ Pre-existing | N/A |
| `frontend/src/components/modules/visualization/StepViewer3D.vue` | 763 | ⚠️ Pre-existing | 2026-02-05 |
| `frontend/src/components/modules/quotes/QuoteFromRequestPanel.vue` | 1235 | ⚠️ Pre-existing | N/A |
| `frontend/src/components/modules/admin/infor/InforBrowserTab.vue` | 501 | ⚠️ Pre-existing | N/A |

**Total:** 6 files violating L-036 (max 300 LOC)

---

## Files Changed THIS Session (2026-02-06)

| File | LOC | Status | Violation? |
|------|-----|--------|------------|
| `StepContourTestPanel.vue` | 292 | ✅ Compliant | NO |
| `StepViewerWrapper.vue` | 75 | ✅ Compliant | NO |

**Verification:**
```bash
wc -l frontend/src/components/modules/admin/StepContourTestPanel.vue
# 292 lines ✅

wc -l frontend/src/components/modules/visualization/StepViewerWrapper.vue
# 75 lines ✅
```

---

## Root Cause

Stop hook runs **repository-wide** validation, not just on changed files.

Pre-existing violations accumulated over multiple sessions:
- `DataTable.vue` (642 LOC) — complex table component, needs split
- `AppHeader.vue` (1181 LOC) — nav + search + user menu, massive
- `StepViewer3D.vue` (763 LOC) — Three.js + OCCT integration, created 2026-02-05
- `QuoteFromRequestPanel.vue` (1235 LOC) — quote request parsing UI

---

## Action Items

### Immediate (Blocking)
NONE — This session's code is compliant.

### Future Refactoring (Tech Debt)

#### Priority 1: AppHeader.vue (1181 LOC → 4 components)
```
AppHeader.vue (300 LOC) — layout coordinator
├── AppHeaderNav.vue (200 LOC) — main navigation
├── AppHeaderSearch.vue (250 LOC) — global search
├── AppHeaderUser.vue (200 LOC) — user menu + settings
└── AppHeaderNotifications.vue (200 LOC) — notification bell
```

#### Priority 2: QuoteFromRequestPanel.vue (1235 LOC → 5 components)
```
QuoteFromRequestPanel.vue (200 LOC) — coordinator
├── QuoteRequestUpload.vue (250 LOC) — PDF upload zone
├── QuoteRequestMetadata.vue (200 LOC) — customer/date fields
├── QuoteRequestItemsTable.vue (300 LOC) — items list
├── QuoteRequestValidation.vue (150 LOC) — warnings/errors
└── QuoteRequestActions.vue (150 LOC) — save/submit buttons
```

#### Priority 3: StepViewer3D.vue (763 LOC → 3 components)
```
StepViewer3D.vue (250 LOC) — Three.js scene manager
├── StepViewerControls.vue (150 LOC) — orbit/zoom/pan
├── StepViewerToolbar.vue (100 LOC) — view presets
└── StepViewerLoader.vue (200 LOC) — OCCT WASM loading
```

#### Priority 4: DataTable.vue (642 LOC → 3 components)
```
DataTable.vue (250 LOC) — table layout
├── DataTableHeader.vue (150 LOC) — column headers + sorting
├── DataTableBody.vue (150 LOC) — rows + cells
└── DataTablePagination.vue (100 LOC) — pagination controls
```

---

## Enforcement Strategy

### Current (Reactive)
Stop hook warns but doesn't block commit. Developer can bypass.

### Proposed (Proactive)
1. **PreToolUse Edit hook:** Block edits to files >300 LOC (already implemented)
2. **Stop hook:** Fail commit if LOC violations increase
3. **CI/CD:** Run `validate-frontend.sh` in GitHub Actions

### Gradual Cleanup
- New code MUST be <300 LOC (enforced)
- Existing violations: 1 per sprint refactored
- 6 violations → 6 sprints = Q2 2026 clean

---

## Session Summary

**This session:** ✅ COMPLIANT
- Created 2 files, both <300 LOC
- Fixed 2 bugs (3D viewer + duplicates)
- No new violations introduced

**Repo status:** ⚠️ 6 pre-existing violations
- Tech debt from previous sessions
- Documented in this audit
- Cleanup plan defined

---

**Recommendation:** Proceed with commit. Pre-existing violations are tracked and will be addressed in future sprints.
