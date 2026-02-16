# GESTIMA Design System v4.0

**Single Source of Truth:** `frontend/template.html` (otevři v prohlížeči = vidíš celý DS)
**Runtime CSS:** `frontend/src/assets/css/design-system.css`
**TS konstanty:** `frontend/src/config/design.ts` + `frontend/src/config/icons.ts`

> **PRAVIDLO:** Tento dokument NIKDY neobsahuje hardcoded hodnoty tokenů.
> Všechny tokeny viz template.html `:root` blok (řádky 15-106).
> Změna tokenu = změna v design-system.css → promítne se VŠUDE.

---

## 1. Filozofie

- **3 barvy:** černá + červená (#991b1b) + šedá. Barva POUZE kde nese informaci.
- **Flat + blur:** Žádné 3D, žádné gradienty. Hloubka přes backdrop-filter, shadows, bordery.
- **Dark-first:** Optimalizováno pro tmavé prostředí (dílna, kancelář večer).
- **Compact density:** Hodně dat na malé ploše — tabulky, formuláře, ribbony.
- **Parametrický:** Vše přes CSS custom properties. Zero hardcoded hodnot v komponentách.

---

## 2. Tokeny (NEKOPÍROVAT — viz template.html)

| Kategorie | Kde najít | Proměnné |
|-----------|-----------|----------|
| **Brand** | template.html :15-21 | `--brand`, `--brand-hover`, `--brand-active`, `--brand-text`, `--brand-subtle`, `--brand-muted` |
| **Backgrounds** | template.html :24-31 | `--bg-base` → `--bg-elevated` (6 stupňů tmavá→světlejší) |
| **Text** | template.html :37-41 | `--text-primary` → `--text-disabled` (5 stupňů bílá→tmavá) |
| **Borders** | template.html :33-35 | `--border-subtle`, `--border-default`, `--border-strong` |
| **Interactive** | template.html :44-48 | `--hover`, `--active`, `--selected`, `--focus-ring`, `--focus-bg` |
| **Status** | template.html :51-53 | `--status-ok` (zelená), `--status-error` (červená), `--status-warn` (žlutá) |
| **Typography** | template.html :56-71 | `--font-sans` (Space Grotesk), `--font-mono` (Space Mono), `--text-2xs`→`--text-2xl` |
| **Spacing** | template.html :73-80 | `--space-1`→`--space-8` (design-system.css, rem units) |
| **Radius** | template.html :83-87 | `--radius-sm`→`--radius-full` (design-system.css) |
| **Shadows** | template.html :90-93 | `--shadow-sm`→`--shadow-xl` (dark-optimized, 0.4-0.7 opacity) |
| **Transitions** | template.html :96-99 | `--t-fast`, `--t-normal`, `--t-slow` |
| **Density** | template.html :102-106 | `--cell-py`, `--cell-px`, `--row-h`, `--input-h` |

**⚠️ NIKDY nekopíruj hex/px hodnoty do dokumentace ani komponent. Vždy `var(--token)`.**

---

## 3. Ikony

**Knihovna:** Lucide Vue Next — import VŽDY z `@/config/icons`, NIKDY přímo z lucide-vue-next.

**Velikosti** (z `@/config/design.ts`):
```typescript
import { ICON_SIZE } from '@/config/design'
// ICON_SIZE.SMALL=14, STANDARD=18, LARGE=22, XLARGE=32, HERO=48
```

**Sémantické aliasy** (z `@/config/icons.ts`):
```typescript
import { OperationsIcon, MaterialIcon, PricingIcon, DrawingIcon } from '@/config/icons'
// Cog, Package, DollarSign, FileText
```

**ZAKÁZÁNO:** Emoji v produkčním UI. Vždy Lucide ikona.

---

## 4. Tlačítka — GHOST ONLY

Všechna tlačítka mají **transparentní pozadí + border**. ŽÁDNÉ filled.

| Varianta | Třída | Kdy použít |
|----------|-------|------------|
| **Primary** | `.btn-primary` | Hlavní akce (Uložit, Kopírovat) |
| **Secondary** | `.btn-secondary` | Sekundární akce (Zrušit, Zavřít) |
| **Destructive** | `.btn-destructive` | Smazání, nebezpečné akce |

**Icon buttons:** `.icon-btn` (32×32px default, `.icon-btn-sm` 24×24px)
- Default: šedý → hover: bílý
- `.icon-btn-brand`: hover červený (přidat/edit)
- `.icon-btn-danger`: hover červený (smazat)

**ZAKÁZÁNO:** `.btn-success`, `.btn-warning`, jakákoli filled varianta, barevné pozadí.

Vizuální reference: template.html sekce "05 Tlačítka"

---

## 5. Focus, Selected, Edit Mode

| Stav | Chování | Token |
|------|---------|-------|
| **Focus ring** | BÍLÝ, nikdy modrý/červený | `--focus-ring` (white 50% opacity) |
| **Focus background** | Jemný bílý tint | `--focus-bg` |
| **Selected row** | Neutrální bílý overlay | `--selected` (white 6% opacity) |
| **Edit mode** | Světlejší bg + silnější border | `--bg-raised` + `--border-strong` |

**ZAKÁZÁNO:**
- Modrý focus ring (starý systém)
- Červený/brand tint na selected řádcích
- Červený border na edit mode

---

## 6. Status barvy

Používat **POUZE** pro statusy:
- Tečky v badges (`.badge-dot-ok`, `.badge-dot-error`, `.badge-dot-warn`)
- Levý border v toastech/calloutech
- **NIKDY** jako pozadí tlačítka

Dataviz (grafy, price bar) = **jediné místo** kde jsou další barvy povoleny.

---

## 7. UI Patterns

### 7.1 Module Architecture (Floating Windows)

```
XxxListModule.vue    — Split-pane coordinator (LEFT: list | RIGHT: detail)
├── XxxListPanel.vue    — Seznam položek + tlačítka
└── XxxDetailPanel.vue  — Detail položky
```

- **VŽDY** `*Module.vue` v `frontend/src/components/modules/`
- **NIKDY** `*View.vue` (deprecated, výjimky: Login, MasterData, Settings, WindowsView)
- Každý modul < 300 LOC (L-036)

### 7.2 Split-Pane Layout

```vue
<div class="split-layout layout-vertical">
  <div class="first-panel" :style="{ width: panelWidth + 'px' }">
    <!-- ListPanel -->
  </div>
  <div class="resize-handle" @mousedown="startResize" />
  <div class="second-panel">
    <!-- DetailPanel -->
  </div>
</div>
```

- `first-panel`: `flex-shrink: 0`, fixed width
- `second-panel`: `flex: 1`, fills remaining space
- `resize-handle`: 3px, brand color on hover
- Container queries pro responsive layout (NE media queries)

### 7.3 Info Ribbon

```vue
<div class="info-ribbon" :class="{ 'edit-mode': isEditing }">
  <div class="icon-toolbar">
    <button class="icon-btn icon-btn-brand" @click="isEditing = !isEditing">
      <Edit3 :size="ICON_SIZE.STANDARD" />
    </button>
  </div>
  <div class="info-grid">
    <div class="info-item">
      <span class="info-label">ČÍSLO DÍLU</span>
      <span class="info-value mono">{{ part.part_number }}</span>
    </div>
    <!-- ... -->
  </div>
</div>
```

- Grid: `auto-fit, minmax(160px, 1fr)`
- View mode: `--bg-surface` + `--border-default`
- Edit mode: `--bg-raised` + `--border-strong` (NE červený border!)
- Toolbar: icon buttons vpravo nahoře

### 7.4 Window Linking

```typescript
// Otevření linked okna
const contextStore = useWindowContextStore()
contextStore.setContext(props.linkingGroup, part.id, part.part_number, part.article_number)
windowStore.openWindow('operations-list', { linkingGroup: part.id })
```

- `linkingGroup` = ID entity (part.id)
- Linked modul: skryje levý panel, zobrazí context ribbon
- `v-if="!linkingGroup"` na levém panelu
- `v-if="linkingGroup && selectedPart"` na context ribbonu

### 7.5 Context Ribbon (pro linked moduly)

```vue
<div v-if="linkingGroup && contextPart" class="context-ribbon">
  <span class="info-label">LINKED PART</span>
  <span class="info-value mono">{{ contextPart.part_number }}</span>
  <span class="info-value">{{ contextPart.article_number }}</span>
</div>
```

### 7.6 Action Cards

```html
<div class="action-grid">
  <button class="action-card" @click="openModule('drawings')">
    <FileText :size="ICON_SIZE.LARGE" />
    <span>Výkresy</span>
  </button>
</div>
```

- Grid: `repeat(4, 1fr)`, container query pro 2-column fallback
- Hover: brand border + translateY(-1px) + subtle glow
- Vizuální reference: template.html sekce "05 Tlačítka → Action Cards"

### 7.7 Data Table

```html
<table class="data-table">
  <thead><tr>
    <th>Kód</th>
    <th class="col-num">Množství</th>
    <th class="col-currency">Cena</th>
  </tr></thead>
</table>
```

- Čísla: `.col-num` (mono, right-align)
- Měna: `.col-currency` (mono, right-align, nowrap)
- Hover: `--hover` na celém řádku
- Selected: `--selected` na celém řádku

### 7.8 Badges

```html
<span class="badge">
  <span class="badge-dot badge-dot-ok"></span>
  Aktivní
</span>
```

- Monochromatické (šedý bg + border)
- Status POUZE přes tečku (`.badge-dot-ok/error/warn/neutral/brand`)
- **NIKDY** barevné pozadí badge

### 7.9 Toast Notifikace

- Monochromatické s barevnou levou čárou (`.toast-ok/error/warn`)
- Vizuální reference: template.html sekce "11 Toasty"

### 7.10 Modaly

- Vždy ikona v headeru (`.modal-icon`)
- Footer: `justify-content: flex-end`, gap `--space-2`
- Vizuální reference: template.html sekce "10 Modal"

---

## 8. CSS Architektura

```
frontend/src/assets/css/
├── design-system.css   ← PRIMÁRNÍ (tokeny + komponenty)
├── tailwind.css         ← Tailwind utilities
├── base.css             ← HTML reset
├── layout.css           ← App layout
└── modules/
    ├── _shared.css      ← Sdílené module styly
    ├── _split-pane.css
    ├── _grid-layout.css
    └── _widgets.css
```

**Import pořadí** (v main.css):
1. design-system.css (tokeny + komponenty — VŽDY první)
2. tailwind.css
3. base.css
4. layout.css

---

## 9. Best Practices

1. **Tokeny, ne hardcode:** `color: var(--text-secondary)`, nikdy `color: #a3a3a3`
2. **Container queries:** `@container (min-width: 600px)`, nikdy `@media`
3. **Fluid heights:** `height: 100%`, `flex: 1`, `overflow: auto`
4. **Ikony z config:** `import { ICON_SIZE } from '@/config/design'`
5. **4 stavy:** loading, empty, error, data — každý modul musí řešit všechny
6. **Window context:** Vždy `setContext()` při výběru entity

---

## 10. Anti-Patterns (ZAKÁZÁNO)

| Co | Proč |
|----|------|
| Hardcoded hex/px v komponentách | Změna tokenu se nepromítne |
| `@media` queries | Použít `@container` |
| Fixed heights (`height: 400px`) | Rozbije různé viewporty |
| Emoji v UI | Vždy Lucide ikona |
| Filled tlačítka | Ghost only |
| Modrý focus ring | Bílý (`--focus-ring`) |
| Červený border na edit mode | `--border-strong` |
| Barevné pozadí badge | Monochromatické + tečka |
| Import ikon přímo z lucide | Vždy z `@/config/icons` |
| Komponenta > 300 LOC | Rozdělit na sub-komponenty |

---

## 11. Density System

Dva režimy: `compact` (default) a `comfortable`.
Přepínání: `<html data-density="compact|comfortable">`

Tokeny v design-system.css bloku `[data-density="compact"]` / `[data-density="comfortable"]`.

**NEKOPÍROVAT hodnoty** — viz design-system.css přímo.

---

## 12. Checklist před každou UI změnou

- [ ] Otevřel jsem `frontend/template.html` v prohlížeči?
- [ ] Používám POUZE `var(--token)`, žádné hardcoded?
- [ ] Ikony z `@/config/icons` s `ICON_SIZE.*`?
- [ ] Ghost tlačítka (ne filled)?
- [ ] Focus ring bílý (ne modrý)?
- [ ] Komponenta < 300 LOC?
- [ ] Container queries (ne media queries)?
- [ ] Fluid heights (ne fixed)?
- [ ] 4 stavy (loading/empty/error/data)?

---

_Verze: 4.0 (2026-02-16) | Zdroj pravdy: `frontend/template.html`_
