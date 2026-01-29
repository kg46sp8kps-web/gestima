# GESTIMA - UI REFERENCE v1.0

**Status:** 🔒 LOCKED - Finální design  
**Datum:** 2026-01-22  
**Zdroj:** Guesstimator v9.3.0 (upraveno pro GESTIMA)

---

## 🎨 BARVY (CSS Variables)

```css
:root {
    /* Pozadí - hierarchie tmavosti */
    --bg-primary: #0d0d0d;       /* Nejčernější pozadí */
    --bg-secondary: #161616;      /* Navbar, footer */
    --bg-card: #1a1a1a;          /* Karty, ribbony */
    --bg-card-hover: #222222;     /* Hover state */
    --bg-input: #111111;         /* Input fields */
    
    /* Akcenty */
    --accent-red: #d62828;       /* Primary akce (OP10, OP20...) */
    --accent-blue: #3b82f6;      /* Časy, odkazy */
    --accent-green: #22c55e;     /* Ceny, úspěch */
    --accent-yellow: #eab308;    /* MID režim */
    --accent-orange: #f97316;    /* HIGH režim */
    --accent-purple: #8b5cf6;    /* Kooperace, stroje */
    
    /* Text */
    --text-primary: #f5f5f5;     /* Hlavní text */
    --text-secondary: #9ca3af;   /* Vedlejší text */
    --text-muted: #6b7280;       /* Popisky */
    
    /* Okraje */
    --border-color: #2a2a2a;
    --border-light: #3a3a3a;
}
```

---

## 📐 LAYOUT v1.0 (FINÁLNÍ)

### **Split Layout** (Editace dílu)

```
┌─────────────────────────────────────────────────────────┐
│ NAVBAR (sticky top: 0)                                  │
├──────────────┬──────────────────────────────────────────┤
│ LEFT PANEL   │ ⏱️ Čas na kus (STICKY top: 0)            │ ← Pevné
│ (320px)      ├──────────────────────────────────────────┤
│ STICKY       │ ╔════════════════════════════════════╗   │
│              │ ║ OPERACE (scrollable)               ║   │ ← Scrolluje
│ • Základní   │ ║ OP10 ▶ (collapsed)                 ║   │
│   údaje      │ ║ OP20 ▼ (expanded)                  ║   │
│ • Cenový     │ ║   └─ Kroky operace...              ║   │
│   přehled    │ ║ OP30 ▶                             ║   │
│              │ ║ + Přidat operaci                   ║   │
│ ← Zpět       │ ╚════════════════════════════════════╝   │
└──────────────┴──────────────────────────────────────────┘
```

### **CSS (FINÁLNÍ v1.0) 🔒**
```css
.split-layout {
    display: flex;
    gap: 0;
    align-items: stretch;
}

/* LEFT PANEL - Sticky, samostatný scroll */
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
    overflow: hidden;  /* Nescrolluje celý panel */
}

/* Sticky čas nahoře */
.right-panel-sticky {
    position: sticky;
    top: 0;
    z-index: 50;
    background: var(--bg-primary);
    padding-bottom: 0.75rem;
    flex-shrink: 0;
}

/* Scrollovatelný obsah operací */
.right-panel-content {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
}

/* RIBBON HEADER - Sjednocená výška */
.ribbon-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 0.8rem;
    min-height: 38px;  /* Garantuje stejnou výšku */
    cursor: pointer;
}

.ribbon-title {
    font-size: 0.75rem;
    font-weight: 600;
}

/* Čas v ribbon headeru */
.ribbon-header .time-display {
    font-size: 0.85rem;  /* Stejné jako .op-name */
    font-weight: 700;
}
```

---

## 🎴 KOMPONENTY

### **Ribbon (Sekce v levém panelu)**

```html
<div class="ribbon">
    <div class="ribbon-header">
        <div class="ribbon-title">📋 Název</div>
        <div class="ribbon-toggle">▼</div>
    </div>
    <div class="ribbon-body">
        <!-- Obsah -->
    </div>
</div>
```

**CSS:**
```css
.ribbon {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    overflow: hidden;
}

.ribbon-header {
    padding: 0.6rem 0.8rem;
    cursor: pointer;
}

.ribbon-title {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-primary);
}

.ribbon-body {
    padding: 0.6rem 0.8rem;
    border-top: 1px solid var(--border-color);
}
```

---

### **Operation Card (Karta operace)**

```html
<div class="operation-card">
    <!-- Header -->
    <div class="op-header">
        <div class="op-seq">10</div>
        <div class="op-icon">🔄</div>
        <div class="op-name">Soustružení</div>
        
        <!-- Mode buttons -->
        <div class="mode-buttons-inline">
            <button class="mode-btn-sm mode-low active">LOW</button>
            <button class="mode-btn-sm mode-mid">MID</button>
            <button class="mode-btn-sm mode-high">HIGH</button>
        </div>
        
        <!-- Times -->
        <div class="op-time-display">tp: <strong>5.2 min</strong></div>
        <div class="op-time-display">tj: <strong>30.0 min</strong></div>
    </div>
    
    <!-- Body (features) -->
    <div class="features-section">
        <!-- Kroky operace -->
    </div>
</div>
```

**CSS:**
```css
.operation-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    margin-bottom: 0.5rem;
}

.op-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.6rem;
}

.op-seq {
    min-width: 28px;
    height: 22px;
    background: var(--accent-red);
    color: white;
    font-size: 0.7rem;
    font-weight: 700;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.op-name {
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--text-primary);
    flex: 1;
}
```

---

### **Mode Buttons (LOW/MID/HIGH)**

```html
<div class="mode-buttons-inline">
    <button class="mode-btn-sm mode-low active">LOW</button>
    <button class="mode-btn-sm mode-mid">MID</button>
    <button class="mode-btn-sm mode-high">HIGH</button>
</div>
```

**CSS:**
```css
.mode-btn-sm {
    padding: 0.2rem 0.4rem;
    border: 1px solid var(--border-color);
    background: var(--bg-input);
    color: var(--text-muted);
    border-radius: 3px;
    font-size: 0.65rem;
    font-weight: 700;
    cursor: pointer;
}

.mode-btn-sm.mode-low.active {
    background: var(--accent-green);
    border-color: var(--accent-green);
    color: white;
}

.mode-btn-sm.mode-mid.active {
    background: var(--accent-yellow);
    border-color: var(--accent-yellow);
    color: #000;
}

.mode-btn-sm.mode-high.active {
    background: var(--accent-orange);
    border-color: var(--accent-orange);
    color: white;
}
```

---

### **Cenový Ribbon (Price Table)**

```html
<div class="price-ribbon">
    <div class="price-ribbon-header">
        <div class="price-ribbon-title">📊 Cenový přehled</div>
    </div>
    <div class="price-ribbon-body">
        <table class="price-table">
            <tbody>
                <tr>
                    <td class="batch-qty">100 ks</td>
                    <td class="price-bar-cell">
                        <div class="price-bar">
                            <div class="bar-segment mat" style="width: 20%"></div>
                            <div class="bar-segment mach" style="width: 50%"></div>
                            <div class="bar-segment setup" style="width: 30%"></div>
                        </div>
                    </td>
                    <td class="price-value">320 Kč</td>
                </tr>
            </tbody>
        </table>
    </div>
</div>
```

**CSS:**
```css
.price-bar {
    display: flex;
    height: 16px;
    background: var(--bg-input);
    border-radius: 3px;
    overflow: hidden;
}

.bar-segment.mat { background: var(--accent-green); }
.bar-segment.mach { background: var(--accent-blue); }
.bar-segment.setup { background: var(--accent-yellow); }
.bar-segment.coop { background: var(--accent-purple); }
```

---

### **Buttons (Flat Style)**

```html
<button class="btn-flat">Tlačítko</button>
<button class="btn-flat btn-save">💾 Uložit</button>
<button class="btn-flat btn-delete">🗑️ Smazat</button>
<button class="btn-flat btn-add-op">+ Přidat operaci</button>
```

**CSS:**
```css
.btn-flat {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.4rem 0.8rem;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 5px;
    color: var(--text-secondary);
    font-size: 0.8rem;
    font-weight: 500;
    cursor: pointer;
}

.btn-flat.btn-save {
    background: var(--accent-red);
    border-color: var(--accent-red);
    color: white;
}

.btn-flat.btn-add-op {
    background: transparent;
    border-style: dashed;
    border-color: var(--accent-green);
    color: var(--accent-green);
}
```

---

## 📝 FORMS (Input Fields)

```css
input, select, textarea {
    padding: 0.4rem 0.5rem;
    background: var(--bg-input);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    color: var(--text-primary);
    font-size: 0.8rem;
}

input:focus, select:focus {
    outline: none;
    border-color: var(--accent-blue);
}

/* Zamčený input (ručně upravená hodnota) */
input.locked {
    background: rgba(245, 158, 11, 0.25);
    border-color: var(--accent-yellow);
    color: var(--accent-yellow);
}
```

---

## 🎯 TYPOGRAFIE

```css
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
    font-size: 13px;
    line-height: 1.5;
}

/* Velikosti */
.text-xs { font-size: 0.6rem; }    /* 7.8px */
.text-sm { font-size: 0.75rem; }   /* 9.75px */
.text-base { font-size: 0.85rem; } /* 11.05px */
.text-lg { font-size: 1rem; }      /* 13px */
.text-xl { font-size: 1.3rem; }    /* 16.9px */
```

---

## 📊 IKONY (Emoji)

```
🔄 Soustružení
🔧 Frézování
🔩 Vrtání
🏭 Kooperace
📊 Cenový přehled
📋 Základní údaje
⏱️ Čas na kus
💾 Uložit
🗑️ Smazat
✅ Úspěch
❌ Chyba
⚠️ Varování
```

---

## 🚀 HOTOVÉ SOUBORY

Originální CSS soubory jsou v:
```
/Users/lofas/Documents/Cursor/Guesstimator/static/css/
├── _variables.css
├── _base.css
├── _layout.css
├── _components.css
├── _operations.css
├── main.css
└── ... (další)
```

---

## ✅ IMPLEMENTACE V GESTIMA - HOTOVO

Status: 🔒 **LOCKED v1.0**

1. ✅ CSS zkopírován do `/app/static/css/`
2. ✅ HTML šablony upraveny podle struktur výše
3. ✅ Správné třídy implementovány
4. ✅ Otestováno v prohlížeči

### **Klíčové vlastnosti v1.0:**
- ✅ Responsivní layout (80% šířka, min 1200px, max 2400px)
- ✅ Levý panel sticky s vlastním scrollem
- ✅ Pravý panel s pevným časem nahoře a scrollovatelnými operacemi
- ✅ **Všechny sekce jako ribbony** (Čas, Operace, Základní údaje, Cenový přehled)
- ✅ **Sjednocené ribbon headery** (min-height: 38px, font 0.85rem)
- ✅ Rozbalovací operace (klik na header)
- ✅ Mode buttons s `@click.stop`
- ✅ Footer se symetrickým gridem (1fr auto 1fr)
- ✅ Toast notifikace (bottom: 35px, 50% opacity, zarovnání zprava)

---

**Verze:** 1.0 🔒 LOCKED  
**Datum:** 2026-01-22  
**Zdroj:** Guesstimator v9.3.0 (upraveno)
