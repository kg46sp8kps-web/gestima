# GESTIMA - UI Guide

Kompletní dokumentace UI komponent, layoutů a vzorů pro konzistentní vývoj.

---

## 1. CSS Architektura

### Struktura souborů

```
app/static/css/
├── gestima.css      # Hlavní soubor - importuje všechny moduly
├── variables.css    # CSS proměnné (barvy, stíny)
├── base.css         # Reset, body, main-content
├── layout.css       # Split layout, panely, ribbony
├── components.css   # Tlačítka, tabulky, price bar
└── operations.css   # Specifické pro operace
```

### Import pořadí (gestima.css)
```css
@import 'variables.css';
@import 'base.css';
@import 'layout.css';
@import 'components.css';
@import 'operations.css';
```

---

## 2. Barevná paleta (variables.css)

### Pozadí (tmavé téma)
| Proměnná | Hodnota | Použití |
|----------|---------|---------|
| `--bg-primary` | #0d0d0d | Hlavní pozadí stránky |
| `--bg-secondary` | #161616 | Navbar, footer, karty |
| `--bg-card` | #1a1a1a | Ribbony, dropdown, modaly |
| `--bg-card-hover` | #222222 | Hover stav karet |
| `--bg-input` | #111111 | Input fieldy |
| `--bg-panel` | #141414 | Panely |
| `--bg-tertiary` | #1f1f1f | Další úroveň |

### Akcenty
| Proměnná | Hodnota | Použití |
|----------|---------|---------|
| `--accent-red` | #d62828 | Brand, primární akce, uložit |
| `--accent-blue` | #3b82f6 | Odkazy, focus, informace |
| `--accent-green` | #22c55e | Úspěch, přidat, aktivní |
| `--accent-yellow` | #eab308 | Varování, setup |
| `--accent-orange` | #f97316 | Rychlý skok, pozornost |
| `--accent-purple` | #8b5cf6 | Kooperace |
| `--accent-pink` | #ec4899 | Speciální |

### Text
| Proměnná | Hodnota | Použití |
|----------|---------|---------|
| `--text-primary` | #f5f5f5 | Hlavní text, nadpisy |
| `--text-secondary` | #9ca3af | Sekundární text, labels |
| `--text-muted` | #6b7280 | Pomocný text, placeholdery |

### Okraje a stíny
| Proměnná | Hodnota |
|----------|---------|
| `--border-color` | #2a2a2a |
| `--border-light` | #3a3a3a |
| `--shadow-sm` | 0 1px 2px rgba(0,0,0,0.3) |
| `--shadow-md` | 0 4px 6px rgba(0,0,0,0.4) |

---

## 3. Typografie

### Font
```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
```

### Velikosti
| Účel | Velikost |
|------|----------|
| Base (body) | 13px |
| Nadpis h1 | 1.5rem (24px) |
| Nadpis h2 | 1.1rem (17.6px) |
| Běžný text | 0.8rem (12.8px) |
| Labels | 0.75rem (12px) |
| Small/muted | 0.7rem (11.2px) |
| Tiny (verze, badge) | 0.65rem / 0.55rem |

---

## 4. Layouty

### 4.1 Globální layout (base.css)

**DŮLEŽITÉ:** GESTIMA je desktop aplikace s min-width: 1000px. Layout je definován v `base.css`.

```css
/* base.css */
html {
    min-width: 1000px;
    overflow-x: auto;
}

body {
    min-width: 1000px;
    overflow-x: auto;  /* Horizontal scroll při malém okně */
    overflow-y: hidden;
}

.main-content {
    width: 95%;
    min-width: 1000px;
    overflow-y: auto;
}
```

```html
<!-- Navbar a footer inner div mají inline styly -->
<div style="width: 95%; min-width: 1000px; ...">
```

**Layout hodnoty:**
| Element | min-width | width | overflow-x |
|---------|-----------|-------|------------|
| html | 1000px | - | auto |
| body | 1000px | - | auto |
| .main-content | 1000px | 95% | hidden |
| nav/footer inner | 1000px | 95% | - |

**Proč min-width: 1000px:**
- Desktop-first aplikace pro interní použití
- Komplexní formuláře a tabulky vyžadují prostor
- Při zmenšení okna pod 1000px se zobrazí horizontal scrollbar

### 4.2 Standalone stránka (login.html vzor)

Pro stránky BEZ navbar/footer (login, error pages).

```html
<body style="
    min-height: 100vh;
    min-width: 0;
    background: var(--bg-primary);
    padding: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
">
    <div style="width: 100%; max-width: 700px;">
        <!-- Obsah -->
    </div>
</body>
```

### 4.3 Stránka s navbar (všechny kromě login)

Díky globálním stylům v base.html stačí jen obsah:

```html
{% extends "base.html" %}

{% block content %}
<div>
    <h1 style="text-align: center;">...</h1>
    <!-- Obsah -->
</div>
{% endblock %}
```

**NEPŘIDÁVAT** duplicitní CSS overrides - jsou už v base.html!

### 4.3 Split Layout (edit.html vzor)

Pro editační stránky s levým a pravým panelem.

```html
<div class="split-layout">
    <div class="left-panel">
        <!-- Ribbony s nastavením -->
    </div>
    <div class="right-panel">
        <div class="right-panel-sticky">
            <!-- Sticky header (čas, summary) -->
        </div>
        <div class="right-panel-content">
            <!-- Scrollable obsah -->
        </div>
    </div>
</div>
```

**CSS třídy:**
- `.split-layout` - flex kontejner, 100% výška
- `.left-panel` - 320px šířka, overflow-y: auto
- `.right-panel` - flex: 1, overflow: hidden
- `.right-panel-sticky` - sticky header
- `.right-panel-content` - scrollable

### 4.4 Seznam stránka (parts_list.html vzor)

Pro tabulkové seznamy s filtrováním.

```html
<div style="padding: 1.5rem; max-width: 2400px; margin: 0 auto;">
    <!-- Header -->
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
        <h1>...</h1>
        <button class="btn-flat btn-save">+ Nový</button>
    </div>

    <!-- Filter -->
    <div style="display: flex; gap: 1rem; margin-bottom: 1rem;">
        <input type="text" placeholder="Hledat...">
    </div>

    <!-- Table -->
    <div style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 5px;">
        <table>...</table>
    </div>
</div>
```

---

## 5. Komponenty

### 5.1 Ribbony (skládací sekce)

```html
<div class="ribbon">
    <div class="ribbon-header" @click="expanded = !expanded">
        <div class="ribbon-title">📋 Název sekce</div>
        <div class="ribbon-toggle" x-text="expanded ? '▼' : '▶'">▼</div>
    </div>
    <div class="ribbon-body" x-show="expanded">
        <!-- Obsah -->
    </div>
</div>
```

**Varianty:**
- `.ribbon-body` - s paddingem (0.8rem)
- `.ribbon-body-sections` - bez paddingu (pro vnořené sekce)

### 5.2 Tlačítka

```html
<!-- Základní -->
<button class="btn-flat">Akce</button>

<!-- Primární (uložit) -->
<button class="btn-flat btn-save">Uložit</button>

<!-- Přidat (dashed border) -->
<button class="btn-flat btn-add-op">+ Přidat</button>
```

**Inline tlačítko (bez třídy):**
```html
<button style="
    background: var(--accent-red);
    color: white;
    padding: 0.65rem 1rem;
    border: none;
    border-radius: 5px;
    font-weight: 500;
    cursor: pointer;
">Přihlásit</button>
```

### 5.3 Formulářové prvky

```html
<!-- Input -->
<input type="text" placeholder="..."
    style="
        width: 100%;
        padding: 0.4rem 0.5rem;
        background: var(--bg-input);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        color: var(--text-primary);
        font-size: 0.8rem;
    ">

<!-- Select -->
<select style="
    width: 100%;
    padding: 0.4rem 0.5rem;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    color: var(--text-primary);
    font-size: 0.75rem;
">
    <option>...</option>
</select>

<!-- Label -->
<label style="
    color: var(--text-muted);
    font-size: 0.7rem;
    display: block;
    margin-bottom: 0.25rem;
">Label</label>
```

**Skrytí šipek u number inputů:**
```css
input[type="number"]::-webkit-inner-spin-button,
input[type="number"]::-webkit-outer-spin-button {
    -webkit-appearance: none;
    margin: 0;
}
input[type="number"] {
    -moz-appearance: textfield;
}
```

### 5.4 Dlaždice (Dashboard tiles)

```html
<!-- Funkční dlaždice -->
<a href="/path" style="
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: var(--bg-secondary);
    border: 2px solid var(--accent-blue);
    border-radius: 12px;
    padding: 1.5rem;
    text-decoration: none;
    transition: all 0.2s;
    min-height: 120px;
    width: 180px;
" onmouseover="this.style.background='var(--accent-blue)'; this.style.transform='translateY(-2px)';"
   onmouseout="this.style.background='var(--bg-secondary)'; this.style.transform='none';">
    <span style="font-size: 2.5rem; margin-bottom: 0.5rem;">📋</span>
    <span style="color: var(--text-primary); font-weight: 600;">Název</span>
    <span style="color: var(--text-muted); font-size: 0.75rem;">Popis</span>
</a>

<!-- Nefunkční dlaždice -->
<div style="
    ...stejné styly...
    opacity: 0.5;
    border-color: var(--border-color);
">
    <span style="font-style: italic;">Připravujeme</span>
</div>
```

**Barvy okrajů podle funkce:**
- Modrá (`--accent-blue`) - navigace, seznamy
- Zelená (`--accent-green`) - vytvořit nový
- Oranžová (`--accent-orange`) - rychlé akce
- Šedá (`--border-color`) - nefunkční/připravujeme

### 5.5 Dropdown menu

```html
<div x-data="{ open: false }" style="position: relative;">
    <button @click="open = !open" class="btn-flat">Menu</button>
    <div x-show="open" @click.away="open = false"
        style="
            position: absolute;
            right: 0;
            top: 100%;
            margin-top: 0.5rem;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 5px;
            padding: 0.75rem;
            min-width: 200px;
            z-index: 100;
            box-shadow: var(--shadow-md);
        ">
        <!-- Položky -->
    </div>
</div>
```

### 5.6 Toast notifikace

```javascript
// Použití (gestima.js poskytuje window.showToast)
window.showToast('Zpráva', 'success');  // success, error, info
```

---

## 6. Alpine.js vzory

### 6.1 Základní komponenta

```html
<div x-data="componentName()">
    <span x-text="value"></span>
    <button @click="doAction()">Akce</button>
</div>

<script>
function componentName() {
    return {
        value: '',
        loading: false,

        async init() {
            // Volá se automaticky při inicializaci
            await this.loadData();
        },

        async loadData() {
            this.loading = true;
            try {
                const response = await fetch('/api/...');
                const data = await response.json();
                this.value = data;
            } catch (error) {
                console.error('Error:', error);
                window.showToast('Chyba', 'error');
            } finally {
                this.loading = false;
            }
        },

        doAction() {
            // ...
        }
    }
}
</script>
```

### 6.2 Collapsible sekce

```html
<div x-data="{ expanded: true }">
    <div @click="expanded = !expanded" style="cursor: pointer;">
        <span>Nadpis</span>
        <span x-text="expanded ? '▼' : '▶'"></span>
    </div>
    <div x-show="expanded">
        <!-- Obsah -->
    </div>
</div>
```

### 6.3 Loading stav

```html
<div x-data="{ loading: false }">
    <button @click="action()" :disabled="loading">
        <span x-show="!loading">Akce</span>
        <span x-show="loading">Načítání...</span>
    </button>
</div>
```

### 6.4 Debounced input

```html
<input type="text" x-model="search" @input.debounce.300ms="loadData()">
```

---

## 7. Responsive vzory

### Layout overrides

**NEPŘIDÁVAT!** Všechny overrides jsou už v `base.html` globálně.
Viz sekce 4.1 výše.

### Flexbox s wrap pro dlaždice

```html
<div style="display: flex; flex-wrap: wrap; gap: 1rem; justify-content: center;">
    <!-- Dlaždice s pevnou šířkou (width: 180px) -->
</div>
```

---

## 8. HTMX integrace

### DŮLEŽITÉ: hx-boost je VYPNUTÝ!

```html
<!-- base.html -->
<body>  <!-- BEZ hx-boost! -->
```

**Proč:**
- `hx-boost` způsobuje nekonzistentní chování s Alpine.js
- Scripty se nespouští při AJAX navigaci
- Viz CLAUDE.md L-012

**HTMX používáme pro:**
- Dynamické načítání fragmentů (`hx-get`, `hx-post`)
- Inline editing
- Partial updates

**HTMX NEPOUŽÍVÁME pro:**
- Globální SPA-like navigaci

### HTMX request indicator (pokud potřeba)
```css
.htmx-request {
    opacity: 0.5;
    pointer-events: none;
}
```

---

## 9. Checklist pro novou stránku

### Standalone stránka (bez navbar)
- [ ] Vlastní `<body>` s inline styly
- [ ] `min-width: 0`, `padding: 20px`
- [ ] `display: flex; align-items: center; justify-content: center`
- [ ] Vnitřní kontejner s `max-width`

### Stránka s navbar (extends base.html)
- [ ] Extend base.html
- [ ] Override CSS v `{% block head %}` pokud potřeba
- [ ] Obsah v `{% block content %}`
- [ ] Skripty v `{% block scripts %}`

### Formulářová stránka
- [ ] Ribbony pro sekce
- [ ] Labels s `--text-muted`
- [ ] Inputy s `--bg-input` nebo `--bg-primary`
- [ ] Tlačítka `.btn-flat`

### Seznam stránka
- [ ] Header s nadpisem a tlačítkem
- [ ] Filter input s debounce
- [ ] Tabulka v `--bg-card` kontejneru
- [ ] Pagination (pokud potřeba)

---

## 10. Příklady

### Quick reference - inline styly

```html
<!-- Nadpis -->
<h1 style="font-size: 1.5rem; font-weight: 700; color: var(--text-primary);">

<!-- Sekundární nadpis -->
<h2 style="font-size: 1.1rem; font-weight: 600; color: var(--text-secondary);">

<!-- Label -->
<label style="color: var(--text-muted); font-size: 0.7rem; display: block; margin-bottom: 0.25rem;">

<!-- Muted text -->
<span style="color: var(--text-muted); font-size: 0.75rem; font-style: italic;">

<!-- Karta/box -->
<div style="background: var(--bg-secondary); border-radius: 8px; padding: 1rem 1.5rem;">

<!-- Flex row -->
<div style="display: flex; gap: 1rem; align-items: center;">

<!-- Flex column -->
<div style="display: flex; flex-direction: column; gap: 0.75rem;">

<!-- Grid 2 sloupce -->
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;">

<!-- Centrovaný text -->
<div style="text-align: center;">
```

---

**Verze:** 1.0 (2026-01-25)
