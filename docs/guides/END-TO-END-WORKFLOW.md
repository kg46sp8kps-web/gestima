# End-to-End Workflow — Novy modul

**Verze:** 2.0 (2026-02-17) | Floating Windows only (viz CLAUDE.md — UI PATTERN)

---

## Workflow diagram

```
Mockup → Widgety → Layout Config → Module → Registrace → Test
  5min      10min       3min        2min       2min       8min
                                                         = 30min
```

---

## Kroky

### 1. Mockup (5 min)
Excalidraw — nakresli split-pane layout (seznam | detail), pojmenuj widgety.

### 2. Widgety (10 min)
Uloz do `frontend/src/components/widgets/`:
- Props: `context?: { item?: T | null }`
- Design tokens: `var(--space-3)`, `var(--text-body)` atd.
- Empty state povinny, max 200 LOC (L-036)
- Zadny `any` typ (L-049), zadny `console.log` (L-044)

### 3. Layout Config (3 min)
Soubor `frontend/src/config/layouts/xxx-detail.ts`:
- `ModuleLayoutConfig` s `widgets[]` + `defaultLayouts` (compact / comfortable)
- Kazdy widget: `id`, `component`, `minWidth`, `minHeight`, `defaultWidth`, `defaultHeight`

### 4. Main Module (2 min)
Soubor `frontend/src/components/modules/xxx/XxxModule.vue`:
- Split-pane: ListPanel vlevo, `CustomizableModule` vpravo
- `widgetContext` computed — data pro kazdy widget
- Resize handle + LocalStorage persistence panelSize
- Zadny business logic — jen koordinace panelu a oken

### 5. Registrace (2 min)
Tri mista:
- `frontend/src/stores/windows.ts` — pridat `WindowModule` typ
- `frontend/src/views/WindowsView.vue` — `defineAsyncComponent` + mapping
- `frontend/src/components/layout/AppHeader.vue` — polozka v `availableModules`

### 6. Test & debug (8 min)
```bash
python gestima.py dev    # backend + Vite dev
```
- `Ctrl+Shift+D` — CSS debug overlay
- Klikni na item v seznamu → detail se zobrazi
- Resize window + widgety → container queries reaguje
- Widget action → handler loguje (ne `console.log` — pouzij `logger`)

---

## Souborova struktura

```
frontend/src/
├── components/
│   ├── modules/xxx/XxxModule.vue        # Split-pane koordinator
│   └── widgets/
│       ├── XxxInfoWidget.vue            # max 200 LOC
│       └── XxxActionsWidget.vue         # max 200 LOC
└── config/layouts/xxx-detail.ts        # ModuleLayoutConfig
```

---

## Relevantni ADR

- ADR-010 — Floating Windows architektura
- ADR-039 — Widget system (CustomizableModule)
- ADR-044 — File Manager (pokud widget pouziva soubory)

**Vzory kodu:** `docs/reference/DESIGN-SYSTEM.md` | `docs/reference/ARCHITECTURE.md`
