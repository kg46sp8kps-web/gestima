# POUČENÍ Z CHYB

Evidence opakujících se problémů a anti-patternů, které se už nesmí opakovat.

---

## 🔴 KRITICKÁ POUČENÍ (NIKDY NEDĚLAT)

### L-001: Live aktualizace časů - VŽDY přes API, NIKDY v JS

**Chyba:** Počítání časů operací/kroků v JavaScriptu místo volání API  
**Důsledek:** 
- Čas v UI se liší od času v databázi
- Po uložení se čas změní (uživatel vidí "skok")
- Složitá logika duplikovaná v JS + Python
- Při změně vzorce musíš upravit 2 místa

**Správné řešení:**
```javascript
// ❌ ŠPATNĚ - počítání v JS
function updateTime() {
  const time = calculateTimeInJS(vc, f, ap); // NIKDY!
  element.textContent = time;
}

// ✅ SPRÁVNĚ - vždy přes API
async function updateTime() {
  const response = await fetch(`/api/operations/${opId}/change-mode`, {
    method: 'POST',
    body: JSON.stringify({ mode: 'MID' })
  });
  const data = await response.json();
  
  // Backend vrátil přepočítané časy pro VŠECHNY features
  data.features.forEach(f => {
    updateFeatureTimeInUI(f.id, f.predicted_time_sec);
  });
  
  // Aktualizovat i čas celé operace
  updateOperationTimeInUI(opId, data.operation.unit_time_min);
}
```

**Proč to funguje:**
1. API má přístup k databázi řezných podmínek
2. API používá `feature_calculator.py` - JEDEN zdroj logiky
3. API UKLÁDÁ nové časy do databáze
4. UI jen zobrazuje co dostane z API
5. Po uložení stránky jsou časy stejné (není skok)

**Flow:**
```
Uživatel klikne LOW/MID/HIGH
  ↓
POST /api/operations/{id}/change-mode
  ↓
Backend:
  - Načte nové Vc/f/Ap z cutting_conditions
  - Přepočítá VŠECHNY features (feature_calculator.py)
  - Uloží nové časy do DB
  - Vrátí JSON s novými časy
  ↓
Frontend:
  - Aktualizuje UI s časy z JSON
  - NEPOČÍTÁ nic sám!
```

**Opakováno:** 4x (BUG-002, BUG-003, BUG-007, různé verze)

### L-002: Nepočítat stejnou hodnotu na více místech

**Chyba:** Čas operace se počítal v API, v JavaScriptu i v šabloně → vždy jiný výsledek  
**Důsledek:** Čas po uložení se lišil od live zobrazení, uživatel viděl nesmysly  
**Řešení:** 
```
API POČÍTÁ a UKLÁDÁ → Šablona ZOBRAZUJE → JavaScript ZOBRAZUJE
```
**JEDEN zdroj pravdy!**  
**Opakováno:** 3x (BUG-013, BUG-014, různé operace)

### L-002: Po API volání VŽDY aktualizovat celou operaci

**Chyba:** Backend změnil data (přepočítal časy), ale frontend aktualizoval jen část UI  
**Důsledek:** 
- Uživatel vidí zastaralá data
- Čas kroků OK, ale čas operace stále starý (nebo naopak)
- Myslí si že aplikace nefunguje

**Správné řešení:**
```javascript
// ❌ ŠPATNĚ - aktualizuješ jen jednu věc
async function changeMode(opId, mode) {
  const response = await fetch(`/api/operations/${opId}/change-mode`, {
    method: 'POST',
    body: JSON.stringify({ mode })
  });
  const data = await response.json();
  
  // Aktualizuješ jen čas operace, ale features jsou stále staré!
  updateOperationTime(opId, data.operation.unit_time_min);
}

// ✅ SPRÁVNĚ - aktualizuješ VŠE co API změnilo
async function changeMode(opId, mode) {
  const response = await fetch(`/api/operations/${opId}/change-mode`, {
    method: 'POST',
    body: JSON.stringify({ mode })
  });
  const data = await response.json();
  
  // 1. Aktualizovat čas operace
  updateOperationTime(opId, data.operation.unit_time_min);
  
  // 2. Aktualizovat VŠECHNY features (Backend je přepočítal!)
  data.features.forEach(feature => {
    updateFeatureTimeInUI(feature.id, feature.predicted_time_sec);
    updateFeatureConditions(feature.id, feature.vc, feature.f, feature.ap);
  });
  
  // 3. Aktualizovat MODE indikátor (LOW/MID/HIGH)
  updateModeIndicator(opId, mode);
}
```

**Klíčové pravidlo:**
> Pokud API endpoint mění více věcí, frontend MUSÍ aktualizovat VŠE najednou!

**Příklady:**
- Změna MODE → aktualizuj čas operace + časy všech kroků + Vc/f/Ap všech kroků
- Změna materiálu → aktualizuj materiálovou skupinu + Vc/f/Ap všech kroků + časy
- Přidání kroku → aktualizuj seznam kroků + čas operace (zvýšil se!)

**Opakováno:** 3x (BUG-002, BUG-007, změna materiálu)

### L-003: Zachovat stav UI při aktualizaci (expanded, scroll)

**Chyba:** Po API volání a aktualizaci UI ztratit stav (rozbalené karty, scroll pozice)  
**Důsledek:** 
- Uživatel měl rozbalenou operaci/krok
- Po aktualizaci se vše zabalilo → frustrující UX
- Scroll skočil nahoru → uživatel ztratil kontext

**Správné řešení:**
```javascript
// ❌ ŠPATNĚ - přepsat celý HTML
async function changeMode(opId, mode) {
  const data = await fetchChangedMode(opId, mode);
  
  // Přepíše celou kartu operace → ztratí expanded state!
  document.querySelector(`#operation-${opId}`).innerHTML = renderOperation(data);
}

// ✅ SPRÁVNĚ - aktualizovat jen data, zachovat stav
async function changeMode(opId, mode) {
  const data = await fetchChangedMode(opId, mode);
  
  // 1. Zapamatovat si expanded state PŘED aktualizací
  const wasExpanded = isOperationExpanded(opId);
  const expandedFeatures = getExpandedFeatures(opId);
  const scrollPos = window.scrollY;
  
  // 2. Aktualizovat data (časy, podmínky)
  updateOperationTimeInUI(opId, data.operation.unit_time_min);
  data.features.forEach(f => {
    updateFeatureTimeInUI(f.id, f.predicted_time_sec);
    updateFeatureConditions(f.id, f.vc, f.f, f.ap);
  });
  
  // 3. Obnovit expanded state PO aktualizaci
  if (wasExpanded) {
    expandOperation(opId);
  }
  expandedFeatures.forEach(fId => expandFeature(fId));
  window.scrollTo(0, scrollPos);
}
```

**Alternativa - granulární update:**
```javascript
// Místo innerHTML = newHTML
// Použít querySelector a aktualizovat jen textContent
document.querySelector(`#op-${opId} .time`).textContent = newTime;
document.querySelector(`#op-${opId} .mode`).textContent = newMode;
```

**Opakováno:** 2x (BUG-003 změna MODE, live update časů)

### L-004: Nepřepisovat celé soubory při malých změnách

**Chyba:** AI přepsalo celý soubor kvůli změně 3 řádků  
**Důsledek:** Ztráta 7800+ tokenů, neefektivní komunikace  
**Řešení:** Vždy použít `StrReplace` tool pro částečné změny  
**Opakováno:** Vícekrát před zavedením pravidla do `.cursorrules`

### L-008: Žádné hardcoded hodnoty - vždy z API

**Chyba:** Hardcoded seznam materiálů v HTML (14 `<option>` tagů)  
**Důsledek:** 
- Při přidání materiálu do DB musíš upravit HTML na 2+ místech
- Porušení DRY principu
- Porušení pravidla "žádné hardcoded hodnoty"

**Správné řešení:**
```javascript
// ✅ SPRÁVNĚ - načíst z API
materials: [],

async init() {
    const response = await fetch('/api/data/materials');
    this.materials = await response.json();
}
```

```html
<!-- ✅ SPRÁVNĚ - dynamický dropdown -->
<template x-for="mat in materials" :key="mat.code">
    <option :value="mat.code" x-text="mat.name"></option>
</template>
```

**Pravidlo:**
> Pokud data existují v databázi, VŽDY je načti z API. NIKDY je nekopíruj do HTML/JS.

**Opakováno:** 1x (dropdown materiálů)

---

### L-009: Alpine.js x-collapse ořezává obsah - nepoužívat pro dlouhý obsah

**Chyba:** Použití `x-collapse` na sekci s dynamickým obsahem (cena polotovaru)  
**Důsledek:** 
- Obsah sekce je oříznutý (není vidět "CELKEM: 248 Kč")
- `x-collapse` nastavuje `max-height` a `overflow: hidden` inline
- Ribbon se nenatáhne na plnou výšku

**Špatné řešení:**
```html
<!-- ❌ ŠPATNĚ - x-collapse ořezává obsah -->
<div x-show="expanded" x-collapse class="section-body">
    <!-- Dlouhý obsah... -->
</div>
```

**Správné řešení:**
```html
<!-- ✅ SPRÁVNĚ - jen x-show bez animace -->
<div x-show="expanded" class="section-body">
    <!-- Dlouhý obsah plně viditelný -->
</div>
```

**Další potřebné úpravy:**
```css
/* Zabránit zmenšování ribbonů */
.ribbon {
    flex-shrink: 0;  /* Ribbon si zachová plnou výšku */
}

/* Padding musí přepsat Alpine.js inline styly */
.section-body {
    padding: 0.75rem !important;
}
```

**Pravidlo:**
> `x-collapse` používej jen pro krátký obsah (max 3-4 řádky). Pro dlouhý/dynamický obsah použij `x-show` bez animace.

**Opakováno:** 1x (sekce polotovar)

---

### L-010: Fixní layout (100vh) - body + flex-shrink: 0

**Chyba:** Stránka scrolluje i když chci aby scrollovaly jen panely uvnitř  
**Důsledek:** 
- Navbar a footer se scrollují pryč
- Špatný UX - uživatel nevidí navigaci
- Panely nemají fixní výšku

**Špatné řešení:**
```css
/* ❌ ŠPATNĚ - body má min-height, umožňuje scroll */
body {
    min-height: 100vh;
    overflow-x: auto;
}
```

**Správné řešení:**
```css
/* ✅ SPRÁVNĚ - fixní výška, zakázat scroll */
body {
    height: 100vh;        /* Fixní výška */
    overflow: hidden;     /* Zakázat scroll stránky */
    display: flex;
    flex-direction: column;
}

nav, footer {
    flex-shrink: 0;       /* Nezmenšovat */
}

.main-content {
    flex: 1;              /* Zabere zbytek */
    overflow: hidden;     /* Zakázat scroll */
    display: flex;
    flex-direction: column;
}

.split-layout {
    height: 100%;
    overflow: hidden;
}

.left-panel, .right-panel {
    height: 100%;
    overflow-y: auto;     /* Scroll uvnitř panelu */
}
```

**Pravidlo:**
> Pro fixní layout: `body { height: 100vh; overflow: hidden; }` + `flex-shrink: 0` pro navbar/footer + scroll v panelech.

**Opakováno:** 1x (edit.html layout)

---

## 🟡 DŮLEŽITÁ POUČENÍ

### L-005: Mapování názvů polí API ↔ JavaScript

**Chyba:** Backend vrací `predicted_time_sec`, JavaScript očekává `predicted_time`  
**Důsledek:** Čas se nezobrazuje, protože pole neexistuje  
**Řešení:** 
```javascript
// Vždy fallback
const time = feature.predicted_time || feature.predicted_time_sec || 0;
```
**Opakováno:** 2x (různé featury)

### L-006: Konzistence názvů Model ↔ Excel ↔ API

**Chyba:** Model má jiné názvy sloupců než Excel, API vrací jiné než Model  
**Důsledek:** Data se nenačtou, nebo se ztratí při uložení  
**Řešení:** 
- Zkontrolovat `to_dict()` - jaké názvy skutečně vrací
- Konzistentní snake_case všude
- Dokumentovat mapování pokud nutné  
**Opakováno:** Několikrát při migraci v8.0 → v9.0

### L-007: Testovat před označením "hotovo"

**Chyba:** Funkce označena jako hotová, ale netestovaná v prohlížeči  
**Důsledek:** Buggy kód v produkci, zpětné opravy  
**Řešení:** 
- Po každé změně otestovat v prohlížeči
- Ověřit že API vrací správná data
- Zkontrolovat že UI zobrazuje správné hodnoty  
**Opakováno:** 3x

---

## 📋 CHECKLIST PŘED KAŽDOU ZMĚNOU

Použij tento checklist VŽDY před dokončením úkolu:

- [ ] **Jeden zdroj pravdy:** Existuje jen JEDNO místo kde se hodnota počítá?
- [ ] **UI update:** Po API volání se UI aktualizuje s fresh daty?
- [ ] **Konzistence názvů:** Názvy polí jsou stejné v Model ↔ Excel ↔ API?
- [ ] **Fallback:** JavaScript má fallback pro různé názvy polí?
- [ ] **Testování:** Otestoval jsi změnu v prohlížeči?
- [ ] **StrReplace:** Použil jsi StrReplace místo přepsání celého souboru?

---

## 🎓 HLAVNÍ PRINCIPY

### 1. DRY - Don't Repeat Yourself
Když dvě akce dělají podobnou věc, použít STEJNOU funkci.

### 2. Single Source of Truth
Každá hodnota má JEDNO místo kde se počítá/ukládá, všichni ostatní ji jen čtou.

### 3. API First
Backend je zdroj pravdy, frontend je jen view. Vždy načítat data z API.

### 4. Jinja2 vs JavaScript
- **Jinja2** = server (při renderování stránky)
- **JavaScript** = prohlížeč (po načtení stránky)
- Pro AJAX vždy načítat data z API, ne ze šablony

---

*Append only - přidávej nové poučení na začátek sekce kde patří (Kritická/Důležitá)*
