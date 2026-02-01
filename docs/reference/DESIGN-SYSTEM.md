# GESTIMA Design System v1.6

**"Refined & Subtle"** - Dark-first design s jemným červeným akcentem

**Approved:** 2026-02-01
**Status:** ✅ Production Ready (Subtle borders + Logo red hover + Component Showcase)
**Target Display:** 27" @ 2560x1440 (primary development display)

---

## 🖥️ Target Display Specifications

**PRIMARY:** 27" @ 2560x1440 (Dell/LG UltraSharp equivalent)
- **Pixel density:** ~109 PPI
- **Optimal viewing distance:** 60-80 cm
- **Design philosophy:** ULTRA-compact ERP-style density (Infor, SAP, Oracle)

**SECONDARY:** Laptops @ 1080p (comfortable mode)
- Switch density via toggle: Compact ⟷ Comfortable

---

## 🎨 Overview

GESTIMA design system je **parametrický** - změna palety → všechno se změní automaticky.

**Principy:**
- **Dark-first** - tmavý režim je default (dílna/továrna vibe)
- **Refined & Subtle** - jemné borders (1px), nízký kontrast, červený akcent
- **Ultra-compact** - optimized for 27"+ displays (12px base, 4pt grid)
- **Density-aware** - parametric spacing for different screen sizes
- **Originální** - ne generický Tailwind UI clone
- **Precizní** - monospace pro čísla/data

**Component Showcase:** Kompletní katalog všech UI komponent dostupný na `/showcase`

---

## 🎯 Color Palette

### Default Palette (Refined Red Accent)

| Token | Value | Usage |
|-------|-------|-------|
| `--palette-primary` | `#991b1b` | Buttons, primary actions (dark muted red) |
| `--palette-primary-hover` | `#E84545` | Logo red - vibrant hover states |
| `--palette-accent-red` | `#E84545` | Logo red - explicit use for accents |
| `--palette-primary-dark` | `#7f1d1d` | Darker variant |
| `--palette-secondary` | `#737373` | Neutral alternative buttons |
| `--palette-danger` | `#f43f5e` | Delete, destructive actions (RŮŽOVÁ!) |
| `--palette-danger-dark` | `#be123c` | Danger hover states |
| `--palette-success` | `#059669` | Success states, material OK |
| `--palette-success-light` | `rgba(5, 150, 105, 0.15)` | Success backgrounds |
| `--palette-success-dark` | `#065f46` | Success hover |
| `--palette-warning` | `#d97706` | Warnings |
| `--palette-warning-light` | `rgba(217, 119, 6, 0.15)` | Warning backgrounds |
| `--palette-info` | `#2563eb` | Info, focus states |

**Why pink for danger?**
- Breaking convention (red = primary!)
- Distinctive, memorable
- User preference 💖

### Backgrounds (Black Spectrum)

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-deepest` | `#000000` | Absolute black |
| `--bg-base` | `#0a0a0a` | Main canvas |
| `--bg-surface` | `#141414` | Cards, panels |
| `--bg-raised` | `#1a1a1a` | Modals, elevated |
| `--bg-input` | `#0f0f0f` | Form inputs |

### Text Colors (White Spectrum)

| Token | Value | Usage |
|-------|-------|-------|
| `--text-primary` | `#ffffff` | Headings, emphasis |
| `--text-body` | `#f5f5f5` | Body text (default) |
| `--text-secondary` | `#a3a3a3` | Labels, secondary |
| `--text-tertiary` | `#737373` | Muted text |
| `--text-disabled` | `#525252` | Disabled states |

**DŮLEŽITÉ:** `--text-body` je pro BARVU textu, `--text-base` je pro VELIKOST písma (12px). Nepoužívejte `color: var(--text-base)` - to je chyba!

### Borders (Refined & Subtle)

| Token | Value | Usage |
|-------|-------|-------|
| `--border-subtle` | `#1a1a1a` | Very subtle borders |
| `--border-default` | `#2a2a2a` | Standard borders (subtle, less prominent) |
| `--border-strong` | `#404040` | Emphasized borders |
| `--border-width` | `1px` | Standard border width (refined style) |

**Design Philosophy:**
- **1px borders** - subtle, clean separation without heaviness
- **Low contrast** (`#2a2a2a`) - refined, not harsh
- **Red accent** - used sparingly for important UI elements

### Interactive States

| Token | Value | Usage |
|-------|-------|-------|
| `--state-focus-bg` | `rgba(37, 99, 235, 0.25)` | Input focus background (MODRÁ!) |
| `--state-focus-border` | `#2563eb` | Input focus border |
| `--state-hover` | `#1f1f1f` | Hover states |
| `--state-selected` | `rgba(153, 27, 27, 0.1)` | Selected rows |

### Scrollbars

| Token | Value | Usage |
|-------|-------|-------|
| `--scrollbar-thumb` | `#404040` | Scrollbar handle |
| `--scrollbar-thumb-hover` | `#525252` | Scrollbar handle hover |
| `--scrollbar-track` | `var(--bg-base)` | Scrollbar track background |

### Legacy Aliases (Kompatibilita)

Pro zpětnou kompatibilitu jsou definovány aliasy pro staré proměnné:

| Legacy Token | Maps To | Usage |
|--------------|---------|-------|
| `--accent-blue` | `var(--palette-info)` | forms.css, legacy components |
| `--error` | `var(--color-danger)` | Error states |
| `--success` | `var(--color-success)` | Success states |
| `--warning` | `var(--color-warning)` | Warning states |
| `--bg-primary` | `var(--bg-base)` | Background alias |
| `--bg-secondary` | `var(--bg-surface)` | Surface alias |
| `--border-color` | `var(--border-default)` | Border alias |

**PRAVIDLO:** V nových komponentách používejte **semantic tokeny** (`--color-*`, `--bg-*`), ne legacy aliasy!

---

## 🔤 Typography

### Font Families

```css
--font-sans: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Arial, sans-serif;
--font-mono: 'SF Mono', ui-monospace, 'Cascadia Code', 'Courier New', monospace;
```

**Apple-inspired** system fonts = native look & feel

### Font Sizes (Optimized for 27" @ 2560x1440)

| Token | Size | Usage |
|-------|------|-------|
| `--text-2xs` | 9px | Tiny labels, fine print |
| `--text-xs` | 10px | Captions, table headers |
| `--text-sm` | 11px | Small text, buttons |
| `--text-base` | **12px** | Body (optimized for large displays) |
| `--text-lg` | 13px | Large body |
| `--text-xl` | 14px | Subheadings |
| `--text-2xl` | 16px | Headings |
| `--text-3xl` | 18px | Large headings |
| `--text-4xl` | 20px | Section titles |
| `--text-5xl` | 24px | Page headers |
| `--text-6xl` | 32px | Hero text |
| `--text-7xl` | 48px | Empty state icons |
| `--text-8xl` | 64px | Large display icons |

**Note:** Font sizes optimized for 27" displays. Use **Settings → Typografie** to adjust each size individually.

### Design Token Editor (Settings)

GESTIMA podporuje **plné přizpůsobení všech design tokenů** přes Settings stránku. Uživatel může nastavit přesnou hodnotu v pixelech pro každý token.

**Editovatelné tokeny:**

| Kategorie | Tokeny | Počet |
|-----------|--------|-------|
| **Typografie** | `--text-2xs` až `--text-8xl` | 13 |
| **Spacing** | `--space-1` až `--space-10` | 8 |
| **Density** | row-height, cell padding, btn padding | 9 |

**Funkce:**
- **Live preview** - změny se aplikují okamžitě
- **Persistence** - ukládá se do `localStorage` jako `gestima_design_tokens`
- **Auto-load** - tokeny se načtou při startu aplikace
- **Reset** - možnost resetovat jednotlivé kategorie nebo vše

**Implementation:**
```typescript
// V App.vue - načtení při startu
function initDesignTokens() {
  const saved = localStorage.getItem('gestima_design_tokens')
  if (saved) {
    const tokens = JSON.parse(saved)
    Object.entries(tokens).forEach(([name, value]) => {
      document.documentElement.style.setProperty(`--${name}`, `${value / 16}rem`)
    })
  }
}
```

**Persistence:** Saved in `localStorage` under `gestima_design_tokens` key.

### Font Weights

```css
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
```

---

## 📐 Spacing (4pt Grid for Large Monitors)

| Token | Size | Usage |
|-------|------|-------|
| `--space-1` | 4px | Tiny gaps |
| `--space-2` | **6px** | Base unit (reduced from 8px) |
| `--space-3` | 8px | Small padding |
| `--space-4` | 12px | Medium padding (reduced from 16px) |
| `--space-6` | 20px | Large padding (reduced from 24px) |
| `--space-8` | 24px | Extra large (reduced from 32px) |

**4pt grid** = ultra-compact for 27"+ displays (was 8pt in v1.1)

### Density System

**Compact Mode (default)** - 27" @ 2560x1440+
- Module padding: 6px
- Cell padding: 4px/8px
- Row height: 24px

**Comfortable Mode** - Laptops @ 1080p
- Module padding: 12px
- Cell padding: 8px/12px
- Row height: 36px

Toggle: Click density toggle in header

**DŮLEŽITÉ:** Density-font tokeny (`--density-font-sm`, `--density-font-base`, `--density-font-md`) nyní odkazují na `--text-*` tokeny:
```css
--density-font-sm: var(--text-xs);
--density-font-base: var(--text-sm);
--density-font-md: var(--text-base);
```
To znamená **jeden zdroj pravdy** pro font velikosti - editujete `--text-*` v Settings a vše se aktualizuje.

---

## 🎭 Border Radius

| Token | Size | Usage |
|-------|------|-------|
| `--radius-sm` | 4px | Small elements |
| `--radius-md` | 6px | Inputs, buttons |
| `--radius-lg` | 8px | Cards, panels |
| `--radius-xl` | 12px | Large containers |

**Sharp edges on data tables** (precision), rounded on UI controls

---

## 🎨 Icons

**Library:** [Lucide Vue Next](https://lucide.dev/guide/packages/lucide-vue-next) v0.x

**Přístup:** NO EMOJI - pouze profesionální Lucide ikony

### Používání

```vue
<script setup>
import { Package, Settings, Trash2 } from 'lucide-vue-next'
</script>

<template>
  <!-- Inline icon (text size) -->
  <button>
    <Settings :size="14" :stroke-width="2" />
    Nastavení
  </button>

  <!-- Large icon (empty states) -->
  <div class="empty-state">
    <Package :size="48" :stroke-width="1.5" />
    <p>Žádné díly</p>
  </div>
</template>
```

### Standardní velikosti

| Použití | Size | Stroke Width |
|---------|------|--------------|
| Buttons (inline) | 14-16px | 2 |
| Headers | 20px | 2 |
| Action buttons | 32px | 1.5-2 |
| Empty states | 48px | 1.5 |

### Často používané ikony

| Účel | Ikona | Import |
|------|-------|--------|
| Díly/komponenty | Package | `Package` |
| Operace | Settings | `Settings` |
| Ceny/finance | DollarSign | `DollarSign` |
| Materiál | Box | `Box` |
| Smazat | Trash2 | `Trash2` |
| Upravit | Edit | `Edit` |
| Zavřít | X | `X` |
| Plus/přidat | Plus | `Plus` |
| Link/propojení | Link | `Link` |
| Schválit | CheckCircle | `CheckCircle` |
| Odmítnout | XCircle | `XCircle` |

### Stylingová pravidla

```css
/* Wrapper pro flexbox alignment */
.btn-with-icon {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

/* Icon color inheritance */
.icon {
  color: currentColor; /* Inherits from parent */
}

/* Empty state icons */
.empty-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
}
```

### DŮLEŽITÉ: NO EMOJI

- ❌ **BANNED:** Emoji (🔧, ⚙️, 📦, etc.) v produkčním kódu
- ❌ **BANNED:** Unicode symboly pro UI elementy
- ✅ **ALLOWED:** Geometrické symboly POUZE pro funkční labels (např. □ pro tvar materiálu)
- ✅ **REQUIRED:** Lucide Vue komponenty pro všechny UI ikony

---

## ⚡ Transitions

```css
--duration-fast: 100ms;
--duration-normal: 150ms;
--duration-slow: 300ms;

--ease-out: cubic-bezier(0, 0, 0.2, 1);

--transition-normal: all var(--duration-normal) var(--ease-out);
```

**Fast, snappy** - not slow animations

### UI Timing Constants

```typescript
// frontend/src/constants/ui.ts
export const TOOLTIP_DELAY_MS = 750
```

**Tooltip delay:** 750ms - jednotná hodnota pro celý systém

---

## 📐 Density System (Parametric)

GESTIMA supports **two density levels** for different screen sizes and user preferences.

### Density Levels

| Level | Target | Row Height | Font Base | Cell Padding |
|-------|--------|------------|-----------|--------------|
| `compact` | 27"+ monitors (2560x1440) | 28px | 12px | 6px/10px |
| `comfortable` | Tablets, smaller screens | 42px | 15px | 12px/16px |

### Density Tokens

```css
/* Cell padding */
--density-cell-py: 0.375rem;     /* compact: 6px, comfortable: 12px */
--density-cell-px: 0.625rem;     /* compact: 10px, comfortable: 16px */

/* Row heights */
--density-row-height: 28px;      /* compact: 28px, comfortable: 42px */

/* Font sizes */
--density-font-sm: 0.6875rem;    /* compact: 11px, comfortable: 14px */
--density-font-base: 0.75rem;    /* compact: 12px, comfortable: 15px */
--density-font-md: 0.8125rem;    /* compact: 13px, comfortable: 16px */

/* Form elements */
--density-input-py: 0.25rem;     /* compact: 4px, comfortable: 8px */
--density-input-px: 0.5rem;      /* compact: 8px, comfortable: 12px */
--density-btn-py: 0.25rem;       /* compact: 4px, comfortable: 8px */
--density-btn-px: 0.5rem;        /* compact: 8px, comfortable: 12px */

/* Layout */
--density-module-padding: 0.5rem;           /* compact: 8px, comfortable: 16px */
--density-section-gap: 0.5rem;              /* compact: 8px, comfortable: 16px */
--density-window-min-width: 300px;          /* compact: 300px, comfortable: 400px */
--density-window-content-padding: 0.375rem; /* compact: 6px, comfortable: 8px */
```

### Switching Density

**Method 1: HTML Attribute**
```html
<html data-density="compact">
<html data-density="comfortable">
```

**Method 2: JavaScript (Pinia Store)**
```typescript
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
ui.setDensity('compact')     // Set specific level
ui.toggleDensity()           // Toggle between levels
ui.isCompactDensity          // Check current state
```

**Method 3: User Toggle (AppHeader)**
- 📐 = compact mode (Infor-style density)
- 📏 = comfortable mode (original spacing)

### Usage in Components

```css
/* Always provide fallback to base tokens */
.my-component {
  padding: var(--density-module-padding, var(--space-4));
  font-size: var(--density-font-base, var(--text-sm));
  gap: var(--density-section-gap, var(--space-4));
}

.my-table td {
  padding: var(--density-cell-py, var(--space-3)) var(--density-cell-px, var(--space-4));
}

.my-button {
  padding: var(--density-btn-py, var(--space-2)) var(--density-btn-px, var(--space-3));
}
```

### Persistence

User preference is saved in `localStorage` under key `gestima-density` and restored on app load via `ui.initDensity()` in App.vue.

---

## 🎨 Changing Palettes

### Method 1: HTML Attribute

```html
<html data-palette="blue">
```

### Method 2: JavaScript

```js
document.documentElement.dataset.palette = 'blue';
```

### Method 3: CSS (Uncomment)

In `design-system.css`, uncomment alternative palette:

```css
/* Uncomment to activate blue palette */
:root[data-palette="blue"] {
  --palette-primary: #2563eb;
  --palette-primary-hover: #1d4ed8;
  --palette-primary-light: #3b82f6;
  --palette-danger: #f43f5e;
  --state-selected: rgba(37, 99, 235, 0.1);
}
```

**Everything updates automatically!** ✨

---

## 🧩 Available Palettes

### 1. Default (Red/Black/Pink) ✅ ACTIVE

```css
Primary: #991b1b (muted red)
Danger: #f43f5e (pink)
```

**Vibe:** Industrial, distinctive

### 2. Blue (Professional)

```css
Primary: #2563eb (blue)
Danger: #f43f5e (pink)
```

**Vibe:** Corporate, trustworthy

### 3. Green (Eco)

```css
Primary: #059669 (green)
Danger: #f43f5e (pink)
```

**Vibe:** Sustainable, growth

### 4. Purple (Creative)

```css
Primary: #7c3aed (purple)
Danger: #f43f5e (pink)
```

**Vibe:** Innovative, modern

---

## 📝 Component Patterns

### Input Focus (Critical!)

```css
input:focus {
  background: rgba(37, 99, 235, 0.25) !important;  /* MODRÁ! */
  border-color: #2563eb !important;
  box-shadow: none;
}
```

**Rules:**
- ✅ Modré pozadí při focusu (ne červené!)
- ✅ Celé pole podbarvené
- ✅ Click = select all (but invisible selection)
- ❌ NIKDY šipky u number inputs!

### Collaborative Editing

```css
/* Self edit (modrá) */
.input.editing-self {
  background: rgba(37, 99, 235, 0.2) !important;
  border-color: var(--color-info);
}

/* Others edit (červená) */
.input.editing-other {
  background: rgba(153, 27, 27, 0.2) !important;
  border-color: var(--color-primary);
}
```

---

## 🚀 Usage in Vue Components

### Import in main.ts

```ts
import '@/assets/css/design-system.css';
```

### Use Semantic Tokens

```vue
<style scoped>
.my-button {
  background: var(--color-primary);  /* ✅ Good */
  color: var(--text-base);           /* ✅ Good */
}

/* ❌ BAD - Don't use palette- directly! */
.bad-button {
  background: var(--palette-primary);  /* ❌ Use --color-primary instead! */
}
</style>
```

**Why?** Semantic tokens allow palette swapping without component changes!

---

## 🎯 Design Tokens Hierarchy

```
PALETTE TOKENS (change these to swap palette)
  ↓
SEMANTIC TOKENS (use these in components)
  ↓
COMPONENTS (automatically update)
```

**Example:**

```css
/* Palette token */
:root {
  --palette-primary: #991b1b;
}

/* Semantic token */
:root {
  --color-primary: var(--palette-primary);
}

/* Component uses semantic */
.button-primary {
  background: var(--color-primary);  /* Auto-updates when palette changes! */
}
```

---

## 📊 Data Visualization Colors

```css
--chart-material: #10b981;      /* Green - material cost */
--chart-machining: #3b82f6;     /* Blue - machining */
--chart-setup: #f59e0b;         /* Amber - setup time */
--chart-cooperation: #8b5cf6;   /* Purple - cooperation */
```

**Consistent across** charts, graphs, price breakdowns

---

## 🌓 Dark/Light Mode

### Default: Dark Mode

```css
:root, :root.dark-mode {
  /* Dark colors... */
}
```

### Light Mode Override

```css
:root.light-mode {
  --bg-base: #fafafa;
  --text-base: #171717;
  /* etc... */
}
```

### Toggle in Vue

```vue
<script setup>
const toggleTheme = () => {
  document.documentElement.classList.toggle('light-mode');
};
</script>
```

---

## 🔧 Utility Classes

```css
/* Text colors */
.text-primary, .text-secondary, .text-tertiary
.text-success, .text-danger, .text-warning

/* Backgrounds */
.bg-surface, .bg-raised

/* Fonts */
.font-mono, .font-medium, .font-semibold, .font-bold
```

---

## ✅ Design Checklist

Před použitím v komponenty:

- [ ] Používám `--color-*` (ne `--palette-*`)
- [ ] Text je `var(--text-base)` (ne hardcoded)
- [ ] Dark mode kompatibilní (testováno)
- [ ] Input focus = modrý (ne červený!)
- [ ] Number inputs = no arrows
- [ ] Monospace pro data/čísla
- [ ] Spacing z `--space-*` grid

---

---

# PART 2: CSS Architecture & Layout Patterns

## 📁 CSS Architecture

### Struktura souborů (frontend)

```
frontend/src/assets/css/
├── design-system.css    # Design tokens (tento dokument!) - PRIMARY!
├── base.css             # Global reset, normalizace
├── layout.css           # Layout patterns (split, grid, flex)
├── components.css       # Komponenty (buttons, ribbons, cards)
└── utilities.css        # Utility classes (.text-center, .flex-row)
```

### Import pořadí (main.ts)

```typescript
import '@/assets/css/design-system.css';  // ← FIRST!
import '@/assets/css/base.css';
import '@/assets/css/layout.css';
import '@/assets/css/components.css';
import '@/assets/css/utilities.css';
```

---

## 🖥️ Globální Layout Rules

**GESTIMA = Desktop-first aplikace (min-width: 1000px)**

```css
/* base.css - již implementováno */
html, body {
    min-width: 1000px;
    overflow-x: auto;  /* Horizontal scroll při malém okně */
}

.main-content {
    width: 95%;
    min-width: 1000px;
    margin: 0 auto;
}
```

**Proč min-width: 1000px:**
- Desktop-first aplikace pro interní použití
- Komplexní formuláře a tabulky vyžadují prostor
- Při zmenšení okna → horizontal scrollbar (ne responsive breakpoints)

---

## 📐 Layout Patterns

### Standalone Page (bez navbar)

Pro stránky BEZ navbar/footer (login, error pages).

```vue
<template>
  <div class="standalone-page">
    <div class="standalone-container">
      <!-- Obsah -->
    </div>
  </div>
</template>

<style scoped>
.standalone-page {
  min-height: 100vh;
  background: var(--bg-base);
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.standalone-container {
  width: 100%;
  max-width: 700px;
}
</style>
```

### Page with Navbar (standardní)

```vue
<template>
  <div class="page-container">
    <h1 class="page-title">Nadpis</h1>
    <!-- Obsah -->
  </div>
</template>

<style scoped>
.page-container {
  padding: 1.5rem;
  max-width: 2400px;
  margin: 0 auto;
}

.page-title {
  text-align: center;
  margin-bottom: 1.5rem;
}
</style>
```

### Split Layout (editační stránky)

Pro editační stránky s levým a pravým panelem (např. Part Edit).

```vue
<template>
  <div class="split-layout">
    <!-- Levý panel (sticky) -->
    <div class="left-panel">
      <div class="ribbon">
        <div class="ribbon-header">📋 Základní údaje</div>
        <div class="ribbon-body">
          <!-- Form fields -->
        </div>
      </div>
    </div>

    <!-- Pravý panel (scrollable) -->
    <div class="right-panel">
      <div class="right-panel-sticky">
        <!-- Sticky header (čas, summary) -->
      </div>
      <div class="right-panel-content">
        <!-- Scrollable obsah (operace) -->
      </div>
    </div>
  </div>
</template>

<style scoped>
.split-layout {
  display: flex;
  gap: 0;
  align-items: stretch;
  max-height: calc(100vh - 60px);
}

/* LEFT PANEL - Sticky, vlastní scroll */
.left-panel {
  width: 320px;
  min-width: 320px;
  padding: 0.75rem;
  position: sticky;
  top: 60px;
  max-height: calc(100vh - 60px - 1.5rem);
  overflow-y: auto;
}

/* RIGHT PANEL - Container s vnitřním scrollem */
.right-panel {
  flex: 1;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 60px);
  overflow: hidden;
}

/* Sticky čas nahoře */
.right-panel-sticky {
  position: sticky;
  top: 0;
  z-index: 50;
  background: var(--bg-base);
  padding-bottom: 0.75rem;
  flex-shrink: 0;
}

/* Scrollovatelný obsah operací */
.right-panel-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}
</style>
```

### List Page (tabulkové seznamy)

Pro seznamy s filtrováním (Parts, Materials, Batches).

```vue
<template>
  <div class="list-page">
    <!-- Header -->
    <div class="list-header">
      <h1>Seznam dílů</h1>
      <button class="btn-primary">+ Nový díl</button>
    </div>

    <!-- Filters -->
    <div class="list-filters">
      <input type="text" placeholder="Hledat..." v-model="search" />
    </div>

    <!-- Table -->
    <div class="table-container">
      <table class="data-table">
        <!-- ... -->
      </table>
    </div>
  </div>
</template>

<style scoped>
.list-page {
  padding: 1.5rem;
  max-width: 2400px;
  margin: 0 auto;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.list-filters {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.table-container {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  overflow: hidden;
}
</style>
```

---

# PART 3: Vue Components

## 🧩 Ribbon (skládací sekce)

```vue
<template>
  <div class="ribbon">
    <div class="ribbon-header" @click="expanded = !expanded">
      <div class="ribbon-title">📋 {{ title }}</div>
      <div class="ribbon-toggle">{{ expanded ? '▼' : '▶' }}</div>
    </div>
    <div v-show="expanded" class="ribbon-body">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

defineProps<{ title: string }>();
const expanded = ref(true);
</script>

<style scoped>
.ribbon {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: var(--space-4);
}

.ribbon-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  min-height: 38px;
  cursor: pointer;
  transition: background var(--duration-fast);
}

.ribbon-header:hover {
  background: var(--state-hover);
}

.ribbon-title {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.ribbon-body {
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--border-default);
}

/* Varianta bez paddingu (pro vnořené sekce) */
.ribbon-body-sections {
  padding: 0;
}
</style>
```

---

## 🎴 Operation Card

```vue
<template>
  <div class="operation-card">
    <div class="op-header">
      <div class="op-seq">{{ seq }}</div>
      <div class="op-icon">
        <component :is="iconComponent" :size="16" :stroke-width="2" />
      </div>
      <div class="op-name">{{ name }}</div>

      <!-- Mode buttons -->
      <div class="mode-buttons-inline">
        <button
          v-for="mode in ['LOW', 'MID', 'HIGH']"
          :key="mode"
          :class="['mode-btn-sm', `mode-${mode.toLowerCase()}`, { active: selectedMode === mode }]"
          @click.stop="$emit('changeMode', mode)"
        >
          {{ mode }}
        </button>
      </div>

      <!-- Times -->
      <div class="op-time-display">tp: <strong>{{ setupTime }} min</strong></div>
      <div class="op-time-display">tj: <strong>{{ operationTime }} min</strong></div>
    </div>

    <div v-show="expanded" class="features-section">
      <slot name="features" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, type Component } from 'vue';

defineProps<{
  seq: number;
  iconComponent: Component; // Lucide icon component
  name: string;
  selectedMode: string;
  setupTime: number;
  operationTime: number;
}>();

defineEmits<{
  changeMode: [mode: string];
}>();

const expanded = ref(false);
</script>

<style scoped>
.operation-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-2);
}

.op-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
}

.op-seq {
  min-width: 28px;
  height: 22px;
  background: var(--color-primary);
  color: white;
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
}

.op-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
}

.op-name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  flex: 1;
}

.op-time-display {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

/* Mode buttons */
.mode-buttons-inline {
  display: flex;
  gap: 2px;
}

.mode-btn-sm {
  padding: 0.2rem 0.4rem;
  border: 1px solid var(--border-default);
  background: var(--bg-input);
  color: var(--text-tertiary);
  border-radius: var(--radius-sm);
  font-size: var(--text-2xs);
  font-weight: var(--font-bold);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.mode-btn-sm.mode-low.active {
  background: var(--color-success);
  border-color: var(--color-success);
  color: white;
}

.mode-btn-sm.mode-mid.active {
  background: var(--palette-warning);
  border-color: var(--palette-warning);
  color: #000;
}

.mode-btn-sm.mode-high.active {
  background: var(--palette-warning);
  border-color: var(--palette-warning);
  color: white;
}
</style>
```

---

## 🔘 Buttons

```vue
<!-- Primary button (Save, Submit) -->
<button class="btn-primary">💾 Uložit</button>

<!-- Secondary button -->
<button class="btn-secondary">Zrušit</button>

<!-- Add button (dashed border) -->
<button class="btn-add">+ Přidat operaci</button>

<!-- Danger button (Delete) -->
<button class="btn-danger">🗑️ Smazat</button>

<style>
/* Implementováno v components.css */
.btn-primary {
  background: var(--color-primary);
  color: white;
  padding: var(--space-2) var(--space-4);
  border: none;
  border-radius: var(--radius-md);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: all var(--duration-normal);
}

.btn-primary:hover {
  background: var(--palette-primary-dark);
  transform: translateY(-1px);
}

.btn-secondary {
  background: var(--bg-surface);
  color: var(--text-secondary);
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-weight: var(--font-medium);
  cursor: pointer;
}

.btn-add {
  background: transparent;
  border: 1px dashed var(--color-success);
  color: var(--color-success);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  font-weight: var(--font-medium);
  cursor: pointer;
}

.btn-danger {
  background: var(--color-danger);
  color: white;
  padding: var(--space-2) var(--space-4);
  border: none;
  border-radius: var(--radius-md);
  font-weight: var(--font-medium);
  cursor: pointer;
}
</style>
```

---

## 📝 Form Fields

```vue
<template>
  <div class="form-field">
    <label class="form-label">{{ label }}</label>
    <input
      v-model="modelValue"
      :type="type"
      :placeholder="placeholder"
      class="form-input"
      @input="$emit('update:modelValue', $event.target.value)"
    />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  label: string;
  type?: string;
  placeholder?: string;
  modelValue: string | number;
}>();

defineEmits<{
  'update:modelValue': [value: string | number];
}>();
</script>

<style scoped>
.form-field {
  margin-bottom: var(--space-4);
}

.form-label {
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  display: block;
  margin-bottom: var(--space-1);
}

.form-input {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-family: var(--font-sans);
  transition: all var(--duration-normal);
}

.form-input:focus {
  outline: none;
  background: var(--state-focus-bg);
  border-color: var(--state-focus-border);
}

/* Skrytí šipek u number inputů */
.form-input[type="number"]::-webkit-inner-spin-button,
.form-input[type="number"]::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.form-input[type="number"] {
  -moz-appearance: textfield;
}
</style>
```

---

## 🎴 Dashboard Tiles

```vue
<template>
  <router-link :to="to" class="dashboard-tile" :class="{ disabled: !functional }">
    <span class="tile-icon">{{ icon }}</span>
    <span class="tile-title">{{ title }}</span>
    <span class="tile-description">{{ description }}</span>
  </router-link>
</template>

<script setup lang="ts">
defineProps<{
  to: string;
  icon: string;
  title: string;
  description: string;
  functional?: boolean;
}>();
</script>

<style scoped>
.dashboard-tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--bg-secondary);
  border: 2px solid var(--palette-info);
  border-radius: var(--radius-xl);
  padding: var(--space-6);
  text-decoration: none;
  transition: all var(--duration-normal);
  min-height: 120px;
  width: 180px;
}

.dashboard-tile:hover {
  background: var(--palette-info);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.dashboard-tile.disabled {
  opacity: 0.5;
  border-color: var(--border-default);
  pointer-events: none;
}

.tile-icon {
  font-size: 2.5rem;
  margin-bottom: var(--space-2);
}

.tile-title {
  color: var(--text-primary);
  font-weight: var(--font-semibold);
  font-size: var(--text-base);
  margin-bottom: var(--space-1);
}

.tile-description {
  color: var(--text-secondary);
  font-size: var(--text-xs);
  text-align: center;
}
</style>
```

---

## 📊 Price Bar (cenový breakdown)

```vue
<template>
  <div class="price-bar-container">
    <div class="price-bar">
      <div
        v-for="segment in segments"
        :key="segment.type"
        :class="['bar-segment', segment.type]"
        :style="{ width: segment.percentage + '%' }"
        :title="`${segment.label}: ${segment.value} Kč (${segment.percentage}%)`"
      />
    </div>
    <div class="price-legend">
      <div v-for="segment in segments" :key="segment.type" class="legend-item">
        <span :class="['legend-dot', segment.type]" />
        <span class="legend-label">{{ segment.label }}</span>
        <span class="legend-value">{{ segment.value }} Kč</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  material: number;
  machining: number;
  setup: number;
  cooperation?: number;
}>();

const total = computed(() =>
  props.material + props.machining + props.setup + (props.cooperation || 0)
);

const segments = computed(() => [
  { type: 'mat', label: 'Materiál', value: props.material, percentage: (props.material / total.value) * 100 },
  { type: 'mach', label: 'Obrábění', value: props.machining, percentage: (props.machining / total.value) * 100 },
  { type: 'setup', label: 'Seřízení', value: props.setup, percentage: (props.setup / total.value) * 100 },
  ...(props.cooperation ? [{ type: 'coop', label: 'Kooperace', value: props.cooperation, percentage: (props.cooperation / total.value) * 100 }] : []),
]);
</script>

<style scoped>
.price-bar-container {
  margin-bottom: var(--space-4);
}

.price-bar {
  display: flex;
  height: 16px;
  background: var(--bg-input);
  border-radius: var(--radius-sm);
  overflow: hidden;
  margin-bottom: var(--space-2);
}

.bar-segment {
  transition: width var(--duration-normal);
}

.bar-segment.mat { background: var(--chart-material); }
.bar-segment.mach { background: var(--chart-machining); }
.bar-segment.setup { background: var(--chart-setup); }
.bar-segment.coop { background: var(--chart-cooperation); }

.price-legend {
  display: flex;
  gap: var(--space-4);
  font-size: var(--text-xs);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend-dot.mat { background: var(--chart-material); }
.legend-dot.mach { background: var(--chart-machining); }
.legend-dot.setup { background: var(--chart-setup); }
.legend-dot.coop { background: var(--chart-cooperation); }

.legend-label {
  color: var(--text-secondary);
}

.legend-value {
  color: var(--text-primary);
  font-weight: var(--font-medium);
  font-family: var(--font-mono);
}
</style>
```

---

# PART 4: Vue Patterns & Composables

## 🎯 Základní komponenta s API

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { api } from '@/services/api';

const data = ref<any[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);

async function loadData() {
  loading.value = true;
  error.value = null;
  try {
    const response = await api.get('/api/endpoint');
    data.value = response.data;
  } catch (err: any) {
    error.value = err.message || 'Chyba při načítání';
    console.error('Load error:', err);
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadData();
});
</script>
```

---

## ⏱️ Debounced input (composable)

```typescript
// composables/useDebounce.ts
import { ref, watch } from 'vue';

export function useDebounce<T>(value: Ref<T>, delay: number = 300) {
  const debouncedValue = ref<T>(value.value);
  let timeout: ReturnType<typeof setTimeout>;

  watch(value, (newValue) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => {
      debouncedValue.value = newValue;
    }, delay);
  });

  return debouncedValue;
}
```

**Usage:**
```vue
<script setup lang="ts">
import { ref, watch } from 'vue';
import { useDebounce } from '@/composables/useDebounce';

const search = ref('');
const debouncedSearch = useDebounce(search, 500);

watch(debouncedSearch, (newValue) => {
  loadData(newValue);  // Spustí se až 500ms po zastavení psaní
});
</script>
```

---

## ✨ Optimistic update pattern

```typescript
async function updateItem(id: number, changes: Partial<Item>) {
  // 1. Optimistic update (okamžitá UI změna)
  const oldItem = items.value.find(i => i.id === id);
  const index = items.value.findIndex(i => i.id === id);
  items.value[index] = { ...oldItem, ...changes };

  try {
    // 2. Backend update
    const response = await api.put(`/api/items/${id}`, changes);
    items.value[index] = response.data;  // Reálná data z backendu
  } catch (err) {
    // 3. Rollback při chybě
    items.value[index] = oldItem;
    showToast('Chyba při ukládání', 'error');
    throw err;
  }
}
```

---

## 🔄 Loading states

```vue
<template>
  <button @click="submit" :disabled="loading">
    <span v-if="!loading">Uložit</span>
    <span v-else>Ukládání...</span>
  </button>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const loading = ref(false);

async function submit() {
  loading.value = true;
  try {
    await api.post('/api/endpoint', data);
    showToast('Úspěšně uloženo', 'success');
  } catch (err) {
    showToast('Chyba', 'error');
  } finally {
    loading.value = false;
  }
}
</script>
```

---

# PART 5: Checklists & Quick Reference

## ✅ Design Checklist

Před použitím v komponentě:

- [ ] Používám `var(--color-*)` tokeny (NE hardcoded barvy!)
- [ ] Text colors z `--text-*` (primary, secondary, tertiary)
- [ ] Backgrounds z `--bg-*` (base, surface, raised)
- [ ] Spacing z `--space-*` (2, 3, 4, 6, 8)
- [ ] Border radius z `--radius-*` (sm, md, lg, xl)
- [ ] Transitions z `--duration-*` a `--ease-*`
- [ ] Input focus = modrý (--state-focus-bg, --state-focus-border)
- [ ] Monospace pro čísla/data (font-family: var(--font-mono))

---

## 🔧 Funkční Checklist

- [ ] Loading states implementovány
- [ ] Error handling (try/catch + toast)
- [ ] Optimistic updates (okamžitá UI odezva)
- [ ] Debounce pro search/filter inputy
- [ ] API response validation (Pydantic schemas)
- [ ] Accessibility (ARIA labels, keyboard nav)

---

## 📏 Layout Checklist

- [ ] Correct layout type (standalone/navbar/split/list)
- [ ] Min-width: 1000px respektováno
- [ ] Scrolling funguje správně (sticky + scrollable)
- [ ] Responsive (pokud potřeba)

---

## 🚀 Quick Reference (Nejčastější použití)

```vue
<style scoped>
/* Karta/Box */
.card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
}

/* Nadpis */
.heading {
  font-size: var(--text-2xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

/* Label */
.label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin-bottom: var(--space-1);
}

/* Flex row */
.flex-row {
  display: flex;
  gap: var(--space-4);
  align-items: center;
}

/* Grid 2 columns */
.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}
</style>
```

---

## 📚 Ikony (Emoji Reference)

```
🔄 Soustružení    ⚙️ Frézování     ✂️ Řezání
💎 Broušení       🔩 Vrtání        🏭 Kooperace
📊 Cenový přehled 📋 Základní údaje ⏱️ Čas na kus
💾 Uložit         🗑️ Smazat        ✅ Úspěch
❌ Chyba          ⚠️ Varování      🔒 Zmrazeno
📁 Složka         🔍 Hledat
```

---

## 🔄 Alpine.js → Vue Migration

| Alpine.js | Vue | Poznámka |
|-----------|-----|----------|
| `x-data` | `<script setup>` + `ref()` | Reactive state |
| `x-show` | `v-show` | Toggle visibility |
| `x-if` | `v-if` | Conditional rendering |
| `x-for` | `v-for` | List rendering |
| `x-model` | `v-model` | Two-way binding |
| `@click` | `@click` | Event handling |
| `x-text` | `{{ }}` nebo `v-text` | Text interpolation |
| `:class` | `:class` | Dynamic classes |
| `x-init` | `onMounted()` | Lifecycle hook |
| `$refs` | `ref` + template refs | DOM references |

### Migration Example

**Alpine.js (old):**
```html
<div x-data="{ open: false }">
  <button @click="open = !open">Toggle</button>
  <div x-show="open">Content</div>
</div>
```

**Vue (new):**
```vue
<template>
  <div>
    <button @click="open = !open">Toggle</button>
    <div v-show="open">Content</div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
const open = ref(false);
</script>
```

---

## ❌ Anti-patterns (Co NEDĚLAT!)

| Anti-pattern | Proč je špatně | Správně |
|--------------|----------------|---------|
| Hardcoded barvy | Nepřizpůsobí se palette swapping | `var(--color-primary)` |
| Inline CSS bez proměnných | Nekonzistence | Design tokens |
| `<style>` BEZ scoped | Global pollution | `<style scoped>` |
| Duplicate CSS across components | Maintenance hell | Shared components/utilities |
| Výpočty v template | Špatný performance | `computed()` |
| Chybějící error handling | Crash bez feedback | try/catch + toast |
| Žádný loading state | Zmatený uživatel | `loading` ref |

---

## 📚 References

- **Component Showcase:** `/showcase` (live interactive catalog)
- **Preview:** `/design-preview.html` (legacy interactive demo)
- **Source:** `/frontend/src/assets/css/design-system.css`
- **Approved:** 2026-02-01
- **Version:** 1.6 (Refined & Subtle design)

---

**GESTIMA Design System - Complete Guide: Design Tokens + Vue Implementation**

*"One source of truth for all design and implementation patterns"* ✨

---

## 🎨 Latest Updates (v1.6 - 2026-02-01)

**Refined & Subtle Design:**
- ✅ Borders změněny na **1px** (z 2px) - jemnější, méně výrazné
- ✅ Border color **#2a2a2a** (z #404040) - subtilnější kontrast
- ✅ Logo red hover **#E84545** přidán jako `--palette-primary-hover`
- ✅ **Component Showcase** vytvořen - `/showcase` route
- ✅ Zachována červená z loga (`#991b1b` primary + `#E84545` hover)

**Component Showcase:**
Kompletní katalog všech UI komponent s live preview:
- Color Palette
- Typography samples
- Button variants (všechny states)
- Input fields (error, disabled, readonly)
- Form examples
- Border system showcase
- Data display (badges, tables)

**Přístup:** Naviguj na `/showcase` v běžící aplikaci.
