# Anti-Patterns & Lessons Learned

**Verze:** 1.0 (2026-01-29)
**Extrahováno z:** CLAUDE.md v3.9

Tento dokument obsahuje detailní popisy všech anti-patternů (L-001 až L-021) naučených během vývoje GESTIMA.

---

## Quick Reference

| ID | Problém | Řešení |
|----|---------|--------|
| L-001 | Výpočty v JS | Python services/ |
| L-002 | Duplikace logiky | Single Source |
| L-003 | Ztráta UI stavu | Zapamatovat/obnovit |
| L-004 | Write místo Edit | Edit pro změny |
| L-005 | Částečný UI update | Vše po API |
| L-006 | Hardcoded data | API |
| L-007 | Chybějící audit | created_by/updated_by |
| L-008 | Žádné try/except | Transaction handling |
| L-009 | Pydantic bez validací | Field() vždy |
| L-010 | Záplatování bugů | Opravit root cause |
| L-011 | CSS conflicts | Inline override global CSS |
| L-012 | HTMX boost + Alpine | NEPOUŽÍVAT hx-boost s Alpine.js |
| L-013 | Debounced race + NaN | Sequence tracking + isNaN() |
| L-014 | Alpine x-show null errors | Použít x-if místo x-show |
| L-015 | **Změna validace → fit data** | **READ ADRs! Fix DATA, ne validaci** |
| L-016 | Regex partial match | Použít `\b` word boundaries |
| L-017 | Alpine Proxy race condition | JSON.parse(JSON.stringify()) snapshot |
| L-018 | `select()` na `input[type="number"]` | Použít data-fresh pattern |
| L-019 | Debounce data loss při rychlém opuštění | beforeunload warning + sync flush |
| L-020 | Module name collision | Jen JEDNA implementace per modul |
| L-021 | HTML Select string/number mismatch | `parseInt(selectedId, 10)` |

---

## Detailní popisy

### L-001: Výpočty v JavaScript

**Pravidlo:** Všechny business výpočty POUZE v Python `services/`.

**Proč:**
- Single Source of Truth
- Testovatelnost
- Konzistence mezi frontend/backend

**Soubory:**
- `services/price_calculator.py`
- `services/time_calculator.py`

---

### L-002: Duplikace logiky

**Pravidlo:** PŘED Write/Edit vždy zkontroluj duplicity.

```bash
# Existuje podobný kód?
grep -r "PATTERN" app/

# Kolik výskytů?
grep -r "PATTERN" app/ | wc -l
```

**IF výskyt > 1:**
- STOP! Nepiš nový kód.
- Použij existující NEBO navrhni extrakci do sdílené komponenty.

---

### L-003 až L-009: Základní pravidla

| ID | Pravidlo |
|----|----------|
| L-003 | Zachovat UI stav (expanded, scroll position) |
| L-004 | Edit místo Write pro změny existujících souborů |
| L-005 | Kompletní UI update po každém API call |
| L-006 | Žádné hardcoded hodnoty - vše z API/config |
| L-007 | Audit fields (created_by, updated_by) na každé mutaci |
| L-008 | try/except + rollback pro všechny DB operace |
| L-009 | Pydantic Field() s validacemi (gt, ge, max_length) |

---

### L-010: STOP záplatování - Fix root cause

**Symptomy záplatování:**
- "Zkusím ještě tohle..."
- 3+ pokusy bez pochopení problému
- Přidávání !important, inline stylů, try/except bez logiky

**Pravidlo 3 pokusů:**
- Pokus 1: Rychlý fix (OK)
- Pokus 2: Hmm, nefunguje (pozor)
- Pokus 3: **STOP!** Debuguj root cause

**Správný postup:**
```
IF bug:
    STOP nasazování záplat
    ASK: "Co je root cause?"
    DEBUG: Logování, breakpoints, traceback
    FIX: Oprav příčinu, ne symptom
    TEST: Ověř že problém je pryč
    CLEAN: Smaž všechny záplaty
```

---

### L-011: CSS Conflicts - Global vs. Component Styles

**Problém:** Global CSS ovlivňuje komponenty které to nepotřebují.

**Debug checklist:**
1. DevTools → Elements → Computed styles
2. Odkud přichází padding/margin/width?
3. Najdi konfliktní CSS v globálních stylech
4. Přepiš inline nebo v samostatném `<style>` bloku

---

### L-012: HTMX Boost + Alpine.js = NEPOUŽÍVAT

**Rozhodnutí:** `hx-boost` je v GESTIMA **VYPNUTÝ**.

**Proč:**
- HTMX při AJAX navigaci NESPOUŠTÍ `<script>` tagy
- Alpine komponenty se nezaregistrují
- CSS/layout se chová jinak než při full page load

**HTMX používáme pro:**
- Dynamické načítání fragmentů (`hx-get`, `hx-post`)
- Inline editing
- Partial updates

**HTMX NEPOUŽÍVÁME pro:**
- Globální SPA-like navigaci (`hx-boost`)

---

### L-013: Debounced Updates - Race Condition + NaN Handling

**Problém:** Stale API responses přijdou v nesprávném pořadí.

**Řešení:**
```javascript
// 1. Sequence counter
operationUpdateSequence: 0,

// 2. Increment before update
debouncedUpdate(item) {
    this.operationUpdateSequence++;
    const currentSequence = this.operationUpdateSequence;
    // ...
}

// 3. Ignore stale responses
if (requestSequence < this.operationUpdateSequence) {
    return;  // Stale - ignore
}
```

**NaN Handling:**
```javascript
const normalizeValue = (value, defaultValue) => {
    if (value === 0) return 0;  // Keep 0!
    if (value === null || value === undefined || isNaN(value) || value === '') {
        return defaultValue;
    }
    return value;
};
```

---

### L-014: Alpine.js x-show with Null Object Properties

**Problém:** Alpine.js evaluuje VŠECHNY expressions, i když parent má `x-show="false"`.

**❌ ŠPATNĚ:**
```html
<div x-show="parseResult && parseResult.confidence > 0">
    <span x-text="parseResult.confidence"></span>  <!-- Evaluuje se! -->
</div>
```

**✅ SPRÁVNĚ:**
```html
<template x-if="parseResult && parseResult.confidence > 0">
    <div>
        <span x-text="parseResult.confidence"></span>  <!-- Jen když existuje -->
    </div>
</template>
```

**Rule of thumb:**
```
IF (používáš object.property V child elements):
    → Použij x-if na parent
ELSE:
    → x-show je OK
```

---

### L-015: Changing Validation to Fit Bad Data (CRITICAL!)

**Problém:** Validace failuje → místo opravy dat se změní validace.

**Red Flags:**
- 🚨 Changing `max_length`, `min_length`, removing `gt=0`
- 🚨 "Validation too strict" feedback
- 🚨 Seed/demo data fail validation
- 🚨 SQLite passes but Pydantic fails

**Correct Workflow:**
```
IF ValidationError:
    1. STOP! Nenavrh změnu validace!
    2. READ: docs/ADR/ (search by entity/field name)
    3. ANALYZE: Co je SPRÁVNĚ podle ADR?
    4. IDENTIFY: Jsou data wrong nebo validace wrong?
    5a. IF data wrong → FIX DATA
    5b. IF validace wrong → UPDATE ADR FIRST
```

**Related:** ADR-017, L-010

---

### L-016: Regex Partial Match

**Problém:** Regex bez word boundaries matchuje částečně.

**Řešení:** Použít `\b` word boundaries.

```javascript
// ❌ ŠPATNĚ
/[67]\d{3}/  // Matchne 16000, 167890

// ✅ SPRÁVNĚ
/\b[67]\d{3}\b/  // Matchne pouze 6000-7999
```

---

### L-017: Alpine Proxy Race Condition

**Problém:** Alpine.js objekty jsou Proxy - mění se v reálném čase.

**Řešení:** Snapshot před asynchronní operací.

```javascript
// ❌ ŠPATNĚ
setTimeout(() => {
    sendAPI(op);  // op se mezitím změnil!
}, 250);

// ✅ SPRÁVNĚ
const snapshot = JSON.parse(JSON.stringify(op));
setTimeout(() => {
    sendAPI(snapshot);  // Kopie, stabilní
}, 250);
```

---

### L-018: select() na input[type="number"]

**Problém:** `$el.select()` nefunguje konzistentně ve všech prohlížečích.

**Řešení (data-fresh pattern):**
```html
<input type="number"
       @focus="$el.dataset.fresh = 'true'"
       @keydown="if($el.dataset.fresh === 'true' && $event.key.length === 1 && !$event.ctrlKey && !$event.metaKey) { $el.value = ''; $el.dataset.fresh = 'false' }"
       @blur="$el.dataset.fresh = 'false'">
```

---

### L-019: Debounce Data Loss při Rychlém Opuštění Stránky

**Business Risk:**
```
1. Pod tlakem: zákazník na telefonu
2. Rychle upravíš tp: 30 → 5 min
3. Klikneš jinam (< 250ms)
4. Timeout nestihne → stará hodnota (30)
5. Nabídka = ztracená zakázka 💸
```

**Řešení:**
```javascript
async init() {
    window.addEventListener('beforeunload', (e) => {
        if (this.hasPendingChanges) {
            e.preventDefault();
            e.returnValue = '';  // Browser warning
            this.flushPendingOperationSync();  // Best effort save
        }
    });
}
```

**Real-world implementace:**
- [app/templates/parts/edit.html:1050-1065](app/templates/parts/edit.html#L1050-L1065)
- [app/templates/parts/edit.html:1431-1447](app/templates/parts/edit.html#L1431-L1447)

---

### L-020: Module Name Collision (window.foo Conflict)

**Problém:** Když VÍCE souborů exportuje do `window.foo`, poslední přepíše předchozí.

**Symptomy:**
- Alpine.js errors: `statusFilter is not defined`
- Všechny properties undefined
- Page prázdná i když backend vrací data

**Detection:**
```bash
grep -r "window.MODULENAME" .
# Pokud více než 1 výsledek → COLLISION!
```

**Prevention:**
- Před exportem: `grep -r "window.foo" .`
- Naming convention: `window.fooListModule`, `window.fooDetailModule`

**Real-world incident (2026-01-28):**
- Deleted: `app/static/js/modules/batch-sets.js` (skeleton)
- Active: `app/templates/pricing/batch_sets.html:216-371` (inline)

---

### L-021: HTML Select x-model String/Number Mismatch

**Problém:** HTML `<select>` VŽDY vrací STRING, API vrací NUMBER.

**Symptomy:**
- `array.filter(x => x.id === selectedId)` vrací prázdné pole
- Batches zmizí po vytvoření setu, pak se objeví po refreshi

**❌ ŠPATNĚ:**
```javascript
get displayedBatches() {
    return this.batches.filter(b => b.batch_set_id === this.selectedSetId);
    // 5 === "5" → FALSE!
}
```

**✅ SPRÁVNĚ:**
```javascript
get displayedBatches() {
    const setIdNum = parseInt(this.selectedSetId, 10);
    return this.batches.filter(b => b.batch_set_id === setIdNum);
}
```

**Prevention Checklist:**
```
IF (dropdown + API data + filter/find):
  - [ ] Dropdown x-model → STRING
  - [ ] API response → NUMBER
  - [ ] Porovnání MUSÍ přetypovat: parseInt() nebo String()
```

**Files opraveny (2026-01-29):**
- [app/static/js/modules/part-pricing.js:349-350](app/static/js/modules/part-pricing.js#L349-L350)
- [app/static/js/modules/part-pricing.js:369-370](app/static/js/modules/part-pricing.js#L369-L370)

---

## Kdy přidat nový anti-pattern

```
IF (bug způsobil >30 min debugging OR se opakoval):
    1. Přidej L-XXX do tohoto souboru
    2. Aktualizuj Quick Reference tabulku v CLAUDE.md
    3. Commit: "docs: Add L-XXX anti-pattern"
```

---

**Zpět na:** [CLAUDE.md](../../CLAUDE.md)
