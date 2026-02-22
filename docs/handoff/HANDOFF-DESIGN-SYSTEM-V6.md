# Design System v6.0 — Handoff Documentation

> Migrace z v4.0 (legacy tokeny, Inter font) na v6.0 (pure v2 tokeny, DM Sans).
> Provedeno: 2026-02-22

## Stav migrace

### Hotovo (v6.0)
- [x] `design-system.css` kompletně přepsán — v4.0 (1258 LOC) → v6.0 (~650 LOC)
- [x] Všechny v2 tokeny definovány v `:root` (51 tokenů: 35 v2 + 16 app-specific)
- [x] Globální CSS třídy přepsány na v2 tokeny (zachovány názvy, změněny hodnoty)
- [x] Hardcoded hex barvy opraveny v ~20 .vue souborech
- [x] JS `getPropertyValue` opraveno (DashboardOverviewPanel, DashboardDetailsPanel)
- [x] `!important` odstraněn z operations.css
- [x] `frontend.md` agent aktualizován na v2 tokeny
- [x] `CLAUDE.md` pravidla potvrzena pro v6.0
- [x] `validate-frontend-v2.sh` hook rozšířen
- [x] Dead code smazán (PartDetailTabs.vue — 1203 LOC, 13 nepoužívaných CSS tříd)
- [x] Font: DM Sans (ne Inter) — načítán v `index.html`

### Zbývá (mimo scope této migrace)
- [ ] 5 wrapper modulů přepsat na native v2 (TilePartsList, TilePricing, TileDrawing, TileMaterial, TileProduction)
- [ ] ResizeDivider zapojit do PartWorkspace
- [ ] Smazat legacy WindowsView/FloatingWindow/Taskbar (Phase 4 cleanup)
- [ ] Přepsat zbývající moduly pro tiling workspace

## Token Reference

### V2 Core Tokeny (35)

| Token | Hodnota | Účel |
|-------|---------|------|
| `--red` | `#E53935` | Brand — jediný chromatický akcent |
| `--red-glow` | `rgba(229,57,53,0.15)` | Červený glow efekt |
| `--red-dim` | `rgba(229,57,53,0.08)` | Jemný červený podklad |
| `--red-10` | `rgba(229,57,53,0.10)` | 10% červená |
| `--red-20` | `rgba(229,57,53,0.20)` | 20% červená (selection) |
| `--green` | `#22c55e` | Peníze/ceny |
| `--green-10` | `rgba(34,197,94,0.10)` | 10% zelená |
| `--green-15` | `rgba(34,197,94,0.15)` | 15% zelená |
| `--base` | `#08080a` | Nejhlubší pozadí |
| `--ground` | `#0e0e10` | Inputy, subtle pozadí |
| `--surface` | `rgba(18,18,20,0.88)` | Hlavní plochy (glassmorphism) |
| `--raised` | `rgba(26,26,28,0.92)` | Zvýšené plochy |
| `--glass` | `rgba(20,20,22,0.65)` | Skleněné panely |
| `--t1` | `#ededf0` | Primární text, nadpisy |
| `--t2` | `#cdcdd0` | Body text, výchozí |
| `--t3` | `#8e8e96` | Sekundární, labely, mutovaný |
| `--t4` | `#5c5c64` | Disabled, placeholdery |
| `--b1` | `rgba(255,255,255,0.06)` | Subtilní border, hover bg |
| `--b2` | `rgba(255,255,255,0.10)` | Default border |
| `--b3` | `rgba(255,255,255,0.15)` | Silný border, edit mode |
| `--ok` | `#34d399` | Status OK |
| `--warn` | `#fbbf24` | Status varování |
| `--err` | `#f87171` | Status chyba |
| `--la` | `var(--red)` | Link group A |
| `--lb` | `var(--green)` | Link group B |
| `--font` | `'DM Sans', -apple-system, sans-serif` | UI font |
| `--mono` | `'JetBrains Mono', monospace` | Čísla, kódy, ceny |
| `--fs` | `12px` | Standardní velikost písma |
| `--fsl` | `11px` | Malé labely |
| `--gap` | `3px` | Mezera mezi panely |
| `--pad` | `8px` | Výchozí padding |
| `--r` | `7px` | Border radius |
| `--rs` | `4px` | Malý radius |
| `--ease` | `cubic-bezier(0.4,0,0.2,1)` | Standard easing |
| `--spring` | `cubic-bezier(0.34,1.56,0.64,1)` | Bounce easing |

### App-Specific Tokeny (16)

| Token | Hodnota | Účel |
|-------|---------|------|
| `--chart-material` | `#3b82f6` | Graf: materiál |
| `--chart-machining` | `#E53935` | Graf: obrábění |
| `--chart-setup` | `#f59e0b` | Graf: seřízení |
| `--chart-cooperation` | `#6b7280` | Graf: kooperace |
| `--chart-revenue` | `#10b981` | Graf: příjmy |
| `--chart-expenses` | `#f43f5e` | Graf: výdaje |
| `--chart-profit` | `#3b82f6` | Graf: zisk |
| `--chart-wages` | `#8b5cf6` | Graf: mzdy |
| `--chart-depreciation` | `#f59e0b` | Graf: odpisy |
| `--chart-energy` | `#06b6d4` | Graf: energie |
| `--chart-tools` | `#84cc16` | Graf: nástroje |
| `--link-group-red` | `#ef4444` | Linking: červená |
| `--link-group-blue` | `#3b82f6` | Linking: modrá |
| `--link-group-green` | `#10b981` | Linking: zelená |
| `--link-group-yellow` | `#f59e0b` | Linking: žlutá |
| `--link-group-neutral` | `#6b7280` | Linking: neutrální |

### Co v2 NETOKENIZUJE (používej literální hodnoty)

| Typ | Hodnoty |
|-----|---------|
| **Font-weight** | `400`, `420` (body), `500`, `600`, `700` |
| **Font-size** (mimo --fs/--fsl) | `9px`, `10px`, `14px`, `16px`, `28px` |
| **Spacing** | `2px`, `4px`, `6px`, `8px`/`var(--pad)`, `12px`, `16px`, `20px`, `24px` |
| **Stíny** | `0 4px 12px rgba(0,0,0,0.5)` atd. |
| **Přechody** | `all 100ms var(--ease)`, `all 150ms var(--ease)` |
| **Radius** (mimo --r/--rs) | `8px`, `12px`, `99px` |
| **Focus** | `rgba(255,255,255,0.5)` (outline), `rgba(255,255,255,0.03)` (bg) |

## Globální CSS třídy

Definovány v `design-system.css`, používané napříč aplikací:

| Třída | Počet souborů | Účel |
|-------|---------------|------|
| `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-danger` | 96 | Ghost buttony |
| `.badge`, `.badge-dot-*` | 43 | Monochromatické badges se status tečkou |
| `.table`, `.data-table` | 29+8 | Datové tabulky |
| `.spinner` | 24 | Loading spinner |
| `.icon-btn`, `.icon-btn-*` | 22 | Ikonové buttony |
| `.empty-state` | 21 | Prázdný stav |
| `.form-group`, `.form-field`, `.form-input` | 19+8+8 | Formulářové prvky |
| `.card` | 14 | Karty |
| `.search-input` | 11 | Vyhledávací pole |
| `.modal-overlay`, `.modal-content` | 10+8 | Modální okna |
| `.split-layout` | 8 | Split-pane layout |
| `.loading-state` | 7 | Loading stav |
| `.filter-tabs`, `.tab-button` | 2+4 | Záložky filtru |
| `.info-ribbon`, `.info-grid` | 4 | Info ribbon |
| `.help-text` | 3 | Nápověda |
| `.icon-toolbar` | 3 | Toolbar ikon |

## Enforcement — 4 vrstvy

```
Layer 1: GITHUB ACTIONS CI (.github/workflows/ci.yml)
  → Hardcoded colors, 'any' types, missing auth, build+lint+test

Layer 2: GIT PRE-COMMIT HOOK (.githooks/pre-commit)
  → Same checks as CI, runs before commit

Layer 3: CLAUDE CODE HOOKS (.claude/hooks/)
  → validate-frontend-v2.sh: 11 checks (6 errors + 5 warnings)
    ERROR 1: Hardcoded hex colors
    ERROR 2: TypeScript 'any'
    ERROR 3: !important
    ERROR 4: Missing <style scoped>
    ERROR 5: Options API
    ERROR 6: Legacy/non-v2 tokens (~40 patterns)
    WARN 7: @media queries
    WARN 8: Inline styles
    WARN 9: Direct axios import
    WARN 10: Business calculations
    WARN 11: getPropertyValue with legacy tokens
  → validate-backend.sh: checks auth deps, safe_commit, soft_delete, SQL injection
  → validate-wiring.sh: checks new components are imported somewhere

Layer 4: CLAUDE.MD + Agent rules
  → Design system tokens, naming, patterns
```

## Pravidla pro další vývoj

1. **Žádné hex barvy** — vše přes `var(--token)`. Hook to blokuje.
2. **Žádné legacy tokeny** — `--text-primary`, `--bg-surface`, `--border-default` atd. Hook to blokuje.
3. **Font DM Sans** — `var(--font)`, ne Inter, ne Space Grotesk
4. **Font JetBrains Mono** — `var(--mono)` pro čísla, kódy, ceny
5. **Dark-only** — žádný light mode, žádné alternativní palety
6. **Ghost buttony only** — `.btn-primary/secondary/danger`, všechny transparentní
7. **White focus ring** — `rgba(255,255,255,0.5)`, nikdy modré/červené
8. **Container queries** — `@container`, ne `@media` v komponentech
9. **Nový token?** — ptej se, nevymýšlej. 51 tokenů stačí.

## Klíčové soubory

| Soubor | Účel |
|--------|------|
| `frontend/src/assets/css/design-system.css` | Source of truth — v6.0 tokeny + globální třídy |
| `frontend/tiling-preview-v2.html` | Vizuální reference — otevřít v prohlížeči |
| `.claude/hooks/validate-frontend-v2.sh` | Enforcement — 11 kontrol |
| `.claude/agents/frontend.md` | Agent pravidla pro frontend |
| `CLAUDE.md` | Globální pravidla projektu |
| `frontend/index.html` | Načítá DM Sans + JetBrains Mono z Google Fonts |

## Token Mapping v4 → v2 (pro referenci)

Pokud narazíš na starý kód se v4 tokeny, zde je převodová tabulka:

```
--bg-base/--bg-deepest    → var(--base)
--bg-input/--bg-subtle    → var(--ground)
--bg-surface              → var(--surface)
--bg-raised/--bg-elevated → var(--raised)
--text-primary            → var(--t1)
--text-body/--text-secondary → var(--t2)
--text-muted/--text-tertiary → var(--t3)
--text-disabled           → var(--t4)
--border-subtle           → var(--b1)
--border-default          → var(--b2)
--border-strong           → var(--b3)
--brand                   → var(--red)
--status-ok               → var(--ok)
--status-error            → var(--err)
--status-warn             → var(--warn)
--font-sans               → var(--font)
--font-mono               → var(--mono)
--text-sm                 → var(--fs)
--space-3                 → var(--pad)
--radius-md               → var(--rs)
--radius-lg               → var(--r)
--hover                   → var(--b1)
```

## Migration History

### What Changed (v4.0 → v6.0)

**Removed:**
- 40+ legacy token aliases (`--text-primary`, `--bg-surface`, `--border-default`, etc.)
- Inter font (replaced with DM Sans)
- Semantic spacing tokens (`--space-1` through `--space-8`)
- Complex token indirection (tokens pointing to tokens pointing to tokens)
- 13 unused CSS classes (`.panel-toolbar-buttons`, `.panel-content-grid`, etc.)
- 1203 LOC dead code (PartDetailTabs.vue)

**Added:**
- DM Sans as primary UI font
- Pure v2 token system (51 tokens total)
- Validation hook with 11 checks
- `--red-10`, `--red-20` for subtle brand tints
- `--green-10`, `--green-15` for money/price UI

**Changed:**
- All global CSS classes now reference v2 tokens internally
- Font weights: removed token variables, use literal values
- Spacing: removed tokens, use literal px values or `var(--pad)`
- Focus ring: always white (`rgba(255,255,255,0.5)`), never blue/red

### Components Updated

~20 Vue components had hardcoded hex colors replaced with v2 tokens:
- All chart components (KpiCard, SvgAreaChart, SvgBarChart, etc.)
- All layout components (AppHeader, AppFooter, AppMainMenu, etc.)
- All module components (PartMainModule, PricingModule, AccountingModule, etc.)
- All UI components (Button, Modal, DataTable, etc.)

### Files Modified in Migration

```
frontend/src/assets/css/design-system.css  (REWRITTEN: 1258 LOC → ~650 LOC)
frontend/src/assets/css/operations.css     (FIXED: removed !important)
frontend/index.html                        (UPDATED: DM Sans font import)
.claude/agents/frontend.md                 (UPDATED: v2 token rules)
.claude/hooks/validate-frontend-v2.sh      (CREATED: 11 checks)
CLAUDE.md                                  (UPDATED: v6.0 references)
```

## FAQ for Future Developers

**Q: Can I add a new color token?**
A: No. 51 tokens is complete. If you need a color, use one of the existing 51. If truly necessary, ask the project owner first.

**Q: Can I use `#ffffff` for a one-off white text?**
A: No. Use `var(--t1)`. The hook will block hex colors.

**Q: Can I use Inter font for a special section?**
A: No. DM Sans is the UI font. JetBrains Mono is for monospace. No exceptions.

**Q: Can I use `--text-primary` since it's in old code?**
A: No. That's a legacy alias. Use `var(--t1)`. The hook will warn you.

**Q: I need a 14px font size but `--fs` is 12px. Can I create `--fs-md`?**
A: No. v2 doesn't tokenize font sizes beyond `--fs` and `--fsl`. Use literal `font-size: 14px`.

**Q: I need a 16px spacing but there's no token for it.**
A: Correct. Use literal `padding: 16px` or `gap: 16px`. v2 only tokenizes `--gap` (3px) and `--pad` (8px).

**Q: Can I use `@media` queries in a component?**
A: The hook will warn you. Prefer `@container` queries for component-level responsive design.

**Q: Why is the focus ring white instead of blue?**
A: Design decision for v2. White (`rgba(255,255,255,0.5)`) is neutral and works with the dark theme.

**Q: Can I use filled buttons instead of ghost buttons?**
A: No. Ghost buttons only (`.btn-primary/secondary/danger`). All transparent with borders/text color.

## Visual Reference

Open `frontend/tiling-preview-v2.html` in a browser to see:
- All 51 tokens in action
- Button variants (primary, secondary, danger, icon buttons)
- Badge variants with status dots
- Input fields (default, focus, error, disabled)
- Data tables (rows, selection, hover, sorting)
- Cards, modals, toasts, empty states
- Typography scale (headings, body, labels, mono)
- Spacing and layout examples
- Chart color palette

## Next Steps

If continuing the tiling workspace migration:
1. Read `docs/handoff/HANDOFF-TILING-REWRITE.md` for tiling architecture
2. Follow the token reference in this document for styling
3. Test all components against `tiling-preview-v2.html` visual reference
4. Ensure `validate-frontend-v2.sh` passes (no errors, minimize warnings)
5. Build and lint before committing (`npm run build && npm run lint`)

## Contact

For questions about design system decisions or v6.0 migration, refer to:
- This document (HANDOFF-DESIGN-SYSTEM-V6.md)
- `CLAUDE.md` (project-wide rules)
- `.claude/agents/frontend.md` (frontend agent rules)
- `tiling-preview-v2.html` (visual reference)
