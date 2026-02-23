# ADR-030: Universal Responsive Module Template System

**Status:** Prijato
**Date:** 2026-02-02
**Nahrazuje:** ADR-026 (Universal Module Pattern)
**Souvisi s:** ADR-025 (Workspace Layout System)

---

## Context

Frontend mel 5 zavaznych problemu: (1) split-pane layout duplikovany v 7 modulech (~500 LOC), (2) 7 komponent > 500 LOC (L-036 violations), (3) pevne sloupce bez responzivniho layoutu, (4) zadna uzivatelska customizace, (5) 3 ruzne implementace resize logiky.

---

## Decision

Implementovat **Universal Responsive Module Template** na bazi widget systemu s gridstack.js.

### Komponenty systemu

**1. CustomizableModule.vue** (< 300 LOC koordinator)
- Widget-based architektura (stavebni bloky)
- Drag & drop, resize, pridani/odebrání widgetu
- localStorage persistence vlastnich layoutu

**2. SplitPane.vue** — nahrazuje 7 duplikatu split-pane logiky
- `useResizeHandle.ts` composable — standardizovana resize logika
- Sdilene CSS `_split-pane.css`

**3. Widget system**
- `WidgetDefinition` — typ widgetu, size constraints, resizable/removable
- `WidgetLayout` — pozice v gridu (x, y, w, h)
- `WidgetWrapper.vue` — chrome (drag handle, titulek, menu)
- Dynamicke nacitani komponent (lazy-load)

**4. Responzivni breakpointy (container queries, NE media queries)**
```
< 400px  → 1 sloupec
400-600  → 2 sloupce
600-900  → 3 sloupce
900-1200 → 4 sloupce
> 1200   → 6 sloupcu  (max-width: 1600px na ultrawide)
```
Container queries reagují na sirku kontejneru, ne viewportu — spravne chovani ve floating windows.

**5. gridstack.js** (MIT, 8700+ hvezd, Grafana/Kibana pouzivaji)
- 30KB minified vcetne CSS
- TypeScript native, Vue 3 support
- Drag & drop, resize, nested grids

**Update 2026-02-02:** GridStack nepodporuje vertical fill (fixed-height rows). Reseni: hybridni pristup — Flexbox pro vertikalni stackovani, GridStack pro horizontalni layouty. Viz `docs/guides/HYBRID-LAYOUT-SOLUTION.md`.

### Struktura souboru

```
frontend/src/
├── components/layout/
│   ├── CustomizableModule.vue
│   ├── SplitPane.vue
│   ├── GridLayoutArea.vue
│   └── ResizeHandle.vue
├── components/widgets/
│   ├── WidgetWrapper.vue
│   ├── InfoCard.vue
│   ├── ActionBar.vue
│   └── FormWidget.vue
├── composables/
│   ├── useGridLayout.ts
│   ├── useResizeHandle.ts
│   └── useWidgetRegistry.ts
├── types/
│   ├── widget.ts
│   └── layout.ts
└── assets/css/modules/
    ├── _split-pane.css
    ├── _grid-layout.css
    └── _widgets.css
```

### Migracni plan (5 tyzdnu)

| Tyden | Co |
|-------|----|
| 1 | Foundation: SplitPane, typy, composables |
| 2 | Core: CustomizableModule, GridLayoutArea, WidgetWrapper |
| 2-3 | Prvni migrace: PartDetailPanel (454 -> < 100 LOC) |
| 3-4 | Fat components: PricingDetailPanel (1119), MaterialDetailPanel (969), QuoteFromRequestPanel (958) |
| 5 | Zbyvajici moduly + testy + dokumentace |

---

## Key Files

- `frontend/src/components/layout/CustomizableModule.vue`
- `frontend/src/components/layout/SplitPane.vue`
- `frontend/src/composables/useResizeHandle.ts`
- `frontend/src/types/widget.ts`
- `docs/guides/HYBRID-LAYOUT-SOLUTION.md`
- `docs/guides/CUSTOMIZABLE-MODULE-GUIDE.md`

---

## Consequences

- 2500+ LOC eliminovano (17 % frontendu), vsechny panely < 300 LOC (L-036)
- Jedna sablona pro vsechny budouci moduly — zadna duplikace
- Responzivni layout pro tablet (768px) az ultrawide (3440px)
- Uzivatelska customizace: drag, resize, ulozeni layoutu
- +35KB bundle (gridstack.js) — lazy-load mitiguje dopad
- 5 tyzdnu migracniho usili, ucici krivka pro widget API

---

## Alternatives Rejected

- **CSS Grid auto-fit only** — resi jen responzivitu, ne duplikaci ani L-036
- **Pure container queries bez widgetu** — resi jen responzivitu
- **Custom grid system** — 3-4 tyzdny vyvoje jen grid logiky, reinventing the wheel
