# Tiling Rewrite — Handoff Prompt

## Kontext
Gestima je CNC kalkulačka (FastAPI + Vue 3 + SQLite). Přecházíme z floating windows na tiling layout.

## Rozhodnutí
Po 4 neúspěšných pokusech o wrapping starých komponent jsme zvolili **Option B: kompletní přepis UI modulů**. Staré komponenty mají vlastní styling, který nelze snadno přepsat — proto se musí moduly napsat znovu od nuly, ale se zachováním business logic (API calls, stores, types).

## Vizuální reference
**`frontend/tiling-preview-v2.html`** — otevři v prohlížeči. Toto je JEDINÝ schválený design. v3 je experimentální, NEPOUŽÍVAT.

## Co existuje a funguje (NEMĚNIT)
- `types/workspace.ts` — typy (LinkingGroup, WorkspaceType, LayoutPreset)
- `stores/workspace.ts` — Pinia store (activeWorkspace, layoutPreset, savedViews, localStorage)
- `components/tiling/TilingWorkspace.vue` — hlavní kontejner, boot, FAB, ⌘1-4
- `components/tiling/BootSequence.vue` — boot animace
- `components/tiling/CncBackground.vue` — pozadí (grid, orbs, toolpath)
- `components/tiling/FabButton.vue` — FAB + module picker
- `components/tiling/GlassPanel.vue` — glassmorphism panel wrapper
- `components/tiling/PartWorkspace.vue` — CSS Grid 4 presety
- `components/tiling/WorkspaceSwitcher.vue` — workspace tabs
- `components/tiling/LayoutPresetSelector.vue` — layout preset chips
- Router: /workspace → TilingWorkspace, / redirect
- AppHeader (36px), AppFooter (22px) — glassmorphism
- Celý backend BEZE ZMĚN
- Všech 12 Pinia stores, 20+ API modulů, 23 type souborů — BEZE ZMĚN

## Co se musí udělat
1. **Přepsat PartDetailTabs.vue** — místo wrappování starých komponent napsat nové renderování dat přímo podle v2 CSS
2. **Nové tile-content komponenty** pro: Operations, Pricing, Drawing, Material, Production — každý renderuje data z existujících stores/API ale s NOVÝM UI podle preview
3. **Tiling features**: resizable panely, nezávislé kontexty, volná kombinace modulů, drag-and-drop tabů
4. **Fullscreen pouze**: MasterAdmin, TimeVision — vše ostatní v tiling panelech

## Klíčové CSS třídy z v2 preview
Panel: `.pnl` → `.ph` (header 28px) → `.ptab` (tabs) → `.pb` (body)
Ribbon: `.rib` → `.rib-r` (info) → `.rib-kpis` (KPI cards) → `.acts` (buttons)
Operace: `.ot` table → `.tb` time badges (`.tb.s` setup=red dot, `.tb.o` op=green dot)
Kalkulace: `.prc` cards → `.ring-svg` donut → `.bt` batch table (green values)
Seznam: `.pi` items → `.pn` number → `.pm` name → `.spark` sparkline → `.pd` status dot

## Design tokeny (v2)
```
--red: #E53935  --green: #22c55e  --base: #08080a  --surface: rgba(18,18,20,0.88)
--t1: #ededf0  --t2: #cdcdd0  --t3: #8e8e96  --t4: #5c5c64
--b1: rgba(255,255,255,0.06)  --b2: 0.10  --b3: 0.15
--font: DM Sans  --mono: JetBrains Mono  --fs: 12px  --gap: 3px  --pad: 8px  --r: 7px
```

## Pravidla
- Přečti CLAUDE.md — obsahuje všechna pravidla projektu
- Přečti `frontend/tiling-preview-v2.html` — vizuální reference
- Žádné hardcoded barvy, žádný `any`, žádný `!important`, žádný `@media`
- `<style scoped>`, `data-testid` na interaktivní elementy
- Build + lint musí projít: `npm run build -C frontend && npm run lint -C frontend`

## Podrobná dokumentace
Viz `docs/handoff/HANDOFF-TILING-REWRITE.md` pro kompletní analýzu všech modulů, business logic, a implementační strategii.

## Start
1. `cat frontend/tiling-preview-v2.html` — nastuduj design
2. Přečti existující tiling komponenty v `components/tiling/`
3. Začni s Operations tab — nejvíc viditelný modul
