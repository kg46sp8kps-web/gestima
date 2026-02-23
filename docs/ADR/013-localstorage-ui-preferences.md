# ADR-013: localStorage for UI Preferences [ACCEPTED]
> Archive: docs/ADR/archive/013-localstorage-ui-preferences.md — Claude může požádat o přečtení

## Rozhodnutí
UI preferences (viditelnost sloupců, layout velikosti) se ukládají do localStorage per-browser, ne do DB.

## Pattern
- `frontend/src/composables/` — localStorage composables, klíče ve formátu `gestima-{feature}-prefs`

## Nesmíš
- Ukládat UI preferences do DB (zbytečné API calls)
- Používat globální Pinia state pro UI layout
