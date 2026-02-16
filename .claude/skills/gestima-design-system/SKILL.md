---
name: gestima-design-system
description: Design system v4.0 tokens, colors, spacing and component patterns for Gestima UI
---

# Gestima Design System v4.0 (2026-02-16)

**Vizualni sablona:** `frontend/template.html` — VZDY konzultovat pred jakoukoli UI zmenou!
**Runtime CSS:** `frontend/src/assets/css/design-system.css`
**Full docs:** `docs/reference/DESIGN-SYSTEM.md`

## Hierarchie zdroju pravdy

1. `frontend/template.html` ← vizualni prototyp (otevri v prohlizeci)
2. `frontend/src/assets/css/design-system.css` ← runtime CSS tokeny
3. `frontend/src/config/design.ts` + `icons.ts` ← TS konstanty
4. `docs/reference/DESIGN-SYSTEM.md` ← patterns a pravidla (BEZ hardcoded tokenu)

## 3 barvy ONLY

Cerna + cervena + sediva. ZADNE jine chromaticke barvy v UI.
Tokeny: `--brand`, `--brand-hover`, `--brand-active`, `--brand-text`, `--brand-subtle`, `--brand-muted`
Presne hex hodnoty viz template.html :root (radky 15-21). NEKOPIROVAT do kodu — pouzit `var(--brand)`.

## Buttony — POUZE ghost styl (ZADNE filled!)

- `.btn-primary`: bily text, transparent bg, default border (Ulozit, Kopirovat)
- `.btn-secondary`: sedy text, transparent bg, default border (Zrusit, Zavrit)
- `.btn-destructive`: cerveny text, cerveny border, transparent bg (Smazat)
- `.icon-btn`: 32x32px, sedy → hover bily
- `.icon-btn-sm`: 24x24px
- `.icon-btn-brand`: hover cerveny (pridat/edit)
- `.icon-btn-danger`: hover cerveny (smazat)

**ZAKAZANO:** filled buttony, `.btn-success`, `.btn-warning`, barevne pozadi

## Focus/Selected/Edit — neutralni, ZADNA barva

- Focus ring: `var(--focus-ring)` = BILY, NIKDY modry/cerveny
- Selected row: `var(--selected)` = bily overlay 6%, NIKDY cerveny/brand tint
- Edit mode: `var(--bg-raised)` + `var(--border-strong)`, NIKDY cerveny ramecek

## Spacing

Tokeny `--space-1` az `--space-8` (definovane v design-system.css v rem).
Ekvivalenty: 4, 6, 8, 12, 16, 20, 24px.
VZDY pouzit `var(--space-X)`, NIKDY hardcoded px.

## Typography

```css
/* Fonty */
font-family: var(--font-sans);  /* Space Grotesk — UI text */
font-family: var(--font-mono);  /* Space Mono — cisla, ceny, kody */
```

Velikosti: `--text-2xs` (11px min) az `--text-2xl`. Presne hodnoty viz design-system.css.
VZDY pouzit `var(--text-sm)` atd., NIKDY hardcoded px.

## Icons

```typescript
import { ICON_SIZE } from '@/config/design'
// SMALL=14, STANDARD=18, LARGE=22, XLARGE=32, HERO=48

import { OperationsIcon, MaterialIcon, PricingIcon, DrawingIcon } from '@/config/icons'
// VZDY importovat z @/config/icons, NIKDY primo z lucide-vue-next
// NIKDY emoji v produkci
```

## Komponenty

- Split-pane: `Module.vue` → `ListPanel.vue` + `DetailPanel.vue` (viz DESIGN-SYSTEM.md #7.2)
- Info ribbon: `.info-ribbon` + `.info-grid` (viz template.html sekce 09)
- Window linking: `useWindowContextStore().setContext()` (viz DESIGN-SYSTEM.md #7.4)
- Data table: `.data-table`, `.col-num`, `.col-currency` (viz template.html sekce 08)
- Badges: monochromaticke + `.badge-dot-ok/error/warn` (viz template.html sekce 06)
- Modal: VZDY ikona v headeru (viz template.html sekce 10)
- Toast: `.toast-ok/error/warn` s levou carou (viz template.html sekce 11)

## Pravidla

- VZDY `var(--token)`, NIKDY hardcoded hex/px
- Container queries, NIKDY `@media`
- Fluid heights (`flex: 1`, `overflow: auto`), NIKDY fixed
- Kazda komponenta < 300 LOC
- 4 stavy: loading/empty/error/data
