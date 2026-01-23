# GESTIMA - UI v1.0 CHANGELOG

**Datum:** 2026-01-22  
**Status:** 🔒 LOCKED

---

## 🎨 DESIGN ZMĚNY

### **1. Layout System**
- ✅ Responsivní šířka: 80% (min 1200px, max 2400px)
- ✅ Pruhy po stranách (10% vlevo, 10% vpravo)
- ✅ Levý panel: 320px (sticky, vlastní scroll)
- ✅ Pravý panel: flex: 1 (vnitřní scroll)

### **2. Ribbony - Konzistentní Design**
- ✅ **Všechny sekce jsou ribbony:**
  - Levý panel: Základní údaje, Cenový přehled
  - Pravý panel: Čas na kus (sticky), Operace
- ✅ **Sjednocené headery:**
  - `min-height: 38px` (garantuje stejnou výšku)
  - `padding: 0.5rem 0.8rem`
  - Font size: `0.85rem` (všude stejný)
- ✅ **Collapsible:** Všechny ribbony lze sbalit/rozbalit

### **3. Sticky Pozice**
- ✅ Navbar: `top: 0` (vždy nahoře)
- ✅ Levý panel: `top: 60px` (pod navbarem)
- ✅ Čas na kus: `top: 0` v pravém panelu (sticky v kontejneru)
- ✅ Operace: Scrollují pod časem

### **4. Branding**
- ✅ Logo: KOVO RYBKA (header, footer, watermark)
- ✅ Watermark opacity: `0.079` (+58% od originálu)
- ✅ Slogan: "Be lazy. It's way better than talking to people."
- ✅ Tech stack: FastAPI + SQLite + HTMX + Alpine.js
- ✅ Footer: Grid layout (1fr auto 1fr) - perfektně symetrický

### **5. Toast Notifikace**
- ✅ Pozice: `bottom: 35px` (těsně nad footerem)
- ✅ Zarovnání: zprava (`align-items: flex-end`)
- ✅ Pozadí: 50% opacity (rgba)
- ✅ Border: 2px solid (barevný podle typu)
- ✅ Text: bílý (lepší kontrast)
- ✅ Backdrop blur: 8px
- ✅ Barvy:
  - Success: zelená (#22c55e)
  - Error: červená (#d62828)
  - Info: modrá (#3b82f6)

---

## 🔧 TECHNICKÉ ZMĚNY

### **CSS Soubory:**
```
gestima.css (main import)
├── variables.css    # Barvy, font sizes
├── base.css         # Body, watermark (0.079 opacity)
├── layout.css       # Split layout, sticky panels, ribbon headery
├── components.css   # Ribbons, buttons, forms
└── operations.css   # Operation cards, mode buttons
```

### **Alpine.js State:**
```javascript
showBasic: true,       // Základní údaje (levý panel)
showTime: true,        // Čas na kus (pravý panel, sticky)
showOperations: true,  // Operace (pravý panel, scrollable)
```

### **HTML Struktura:**
```html
<div class="split-layout">
  <!-- LEFT PANEL (sticky) -->
  <div class="left-panel">
    <div class="ribbon"><!-- Základní údaje --></div>
    <div class="ribbon"><!-- Cenový přehled --></div>
  </div>
  
  <!-- RIGHT PANEL -->
  <div class="right-panel">
    <!-- STICKY RIBBON -->
    <div class="right-panel-sticky">
      <div class="ribbon"><!-- Čas na kus --></div>
    </div>
    
    <!-- SCROLLABLE CONTENT -->
    <div class="right-panel-content">
      <div class="ribbon"><!-- Operace --></div>
    </div>
  </div>
</div>
```

---

## 🐛 OPRAVENÉ PROBLÉMY

1. ✅ Duplicitní číslo výkresu → UNIQUE constraint
2. ✅ Layout levá/pravá strana prohozená → opraveno
3. ✅ Design neodpovídá Guesstimator → CSS implementován
4. ✅ Responsivní layout → 80% šířka s pruhy
5. ✅ Sticky čas se hýbal → vnitřní scroll v pravém panelu
6. ✅ Ribbon headery různé výšky → sjednoceno (min-height: 38px)
7. ✅ Toast neviditelné → 50% opacity, 2px border, bílý text
8. ✅ Toast pozice špatná → bottom: 35px, zarovnání zprava

---

## 📋 CHECKLIST PRO DALŠÍ SESSION

### **Zbývá implementovat:**
- [ ] Přidání operace (otestovat API)
- [ ] Features (kroky operace)
- [ ] Formulář pro geometrii kroků
- [ ] Výpočet času (time_calculator)
- [ ] Kalkulace cen (price_calculator)
- [ ] Vytvoření dávek (100ks, 200ks, 1000ks)
- [ ] Editace operace (název, stroj, seřízení)
- [ ] Smazání operace/dílu

### **UI je LOCKED:**
- 🔒 Layout system
- 🔒 Ribbon design
- 🔒 Sticky pozice
- 🔒 Toast notifikace
- 🔒 Branding (logo, slogan, footer)

---

**Verze:** 1.0 🔒 LOCKED  
**Další změny UI:** Pouze v případě kritických bugů nebo explicitního požadavku
