# ADR-025: Workspace Layout — Resizable Panels [ACCEPTED]
> Archive: docs/ADR/archive/025-workspace-layout-system.md — Claude může požádat o přečtení

## Rozhodnutí
Resize panelů přes drag handle, preference uloženy v localStorage per-module-type.

## Pattern
- `frontend/src/composables/useResizeHandle.ts` — resize logika
- localStorage klíče `gestima-layout-*`

## Nesmíš
- pevné rozměry panelů v CSS
- ukládat layout do Pinia (resety při refreshi)
- duplicitní resize implementace mimo useResizeHandle
