# FUTURE STEPS

## 🔴 P1 - KRITICKÉ (Týden 1)

### BUG-001: Cenový ribbon
**Status:** ❌ TODO
**Soubory:**
- `app/routers/batches_router.py` - endpoint `/calculate-price`
- `app/services/price_calculator.py` - už existuje
- `app/templates/parts/edit.html` - přidat ribbon
- `app/static/js/gestima.js` - live update

**Akce:**
1. Implementovat endpoint `POST /api/parts/{id}/calculate-price`
2. Přidat ribbon "💰 Cena polotovaru" do levého panelu
3. Alpine.js: auto-update při změně materiálu/rozměrů

**Test:** Změna průměru → cena se přepočítá live

---

### BUG-002: Zobrazení strojního času
**Status:** ⚠️ OVĚŘIT
**Soubory:**
- `app/routers/features_router.py` - vrací `predicted_time_sec`?
- `app/templates/parts/edit.html` - zobrazení času operace
- `app/static/js/gestima.js` - update UI

**Akce:**
1. Ověřit API response: `feature.predicted_time_sec` přítomen?
2. Ověřit UI: časy se zobrazují po uložení?
3. Ověřit: čas operace = součet časů features?

**Test:** Přidat feature → čas se zobrazí správně

---

### BUG-003: Test přepočtu MODE
**Status:** ❌ TODO
**Soubory:**
- `app/routers/operations_router.py` - nový endpoint
- `app/services/cutting_conditions.py` - načíst Vc/f/Ap
- `app/services/time_calculator.py` - přepočítat
- `app/static/js/gestima.js` - update všech features

**Akce:**
1. Endpoint: `POST /api/operations/{id}/change-mode` (body: `{mode: "MID"}`)
2. Backend:
   - Načíst nové Vc/f/Ap pro MODE
   - Přepočítat VŠECHNY features
   - Uložit do DB
   - Return: všechny features + operation
3. Frontend: aktualizovat časy + podmínky (Vc/f/Ap)
4. **KRITICKÉ:** Zachovat expanded state (LESSONS L-003)

**Test:** Změna LOW→MID→HIGH → časy se mění live

---

## 🟡 P2 - DŮLEŽITÉ (Týden 2)

### BUG-004: Vizuální indikace zamykání
**Soubory:** `app/templates/parts/edit.html`, `app/static/css/gestima.css`
**Akce:** Ikona zámku u zamčených Vc/f/Ap (🔒 vs 🔓)

---

### BUG-005: Tvorba dávek
**Soubory:** `app/routers/batches_router.py`, templates
**Akce:** UI pro vytvoření batch (množství) + zobrazení unit_cost

---

### BUG-006: Výběr stroje
**Soubory:** `app/routers/operations_router.py`, templates
**Akce:** Dropdown strojů v operaci → hourly_rate

---

### BUG-007: Přepočet při změně materiálu
**Soubory:** `app/static/js/gestima.js`
**Akce:** Změna materiálu → reload cutting conditions → přepočítat časy

---

## 🟢 P3 - ROZŠÍŘENÍ (Týden 3+)

### Refaktoring batch_optimizer.py
**Status:** ⏳ LOW
**Důvod:** Stará verze, nekompatibilní s v9.0 modely

---

### Toast notifikace
**Status:** ⏳
**Akce:** Success/error messages (Alpine.js)

---

### Validace dat
**Status:** ⏳
**Akce:** Client-side + server-side validation (průměr > 0, materiál vybrán...)

---

### Export do Excel
**Status:** ⏳
**Akce:** Tlačítko "Export" → stáhnout kalkulaci jako XLSX

---

### AI Vision testování
**Status:** ⏳
**Akce:** Upload výkresu → OCR → automatické vyplnění rozměrů

---

## 📋 Checklist před implementací

Pro KAŽDÝ bug/feature:

- [ ] **Přečíst LESSONS.md** - neudělat stejnou chybu
- [ ] **Přečíst CLAUDE.md** - dodržet pravidla
- [ ] **API First** - logika v Pythonu, ne JS
- [ ] **Single Source of Truth** - jedna hodnota = jedno místo výpočtu
- [ ] **Update celé UI** - po API volání aktualizovat VŠE
- [ ] **Zachovat stav** - expanded, scroll pozice
- [ ] **Testovat** - pytest + manuální test v prohlížeči
- [ ] **Type hints** - všude
- [ ] **Dokumentace** - komentáře u složité logiky

---

## 🎯 Priority Order (doporučeno)

1. **BUG-002** - Zobrazení času (základ funkcionality)
2. **BUG-003** - MODE přepočet (klíčová UX feature)
3. **BUG-001** - Cenový ribbon (potřebné pro kalkulaci)
4. **BUG-006** - Výběr stroje (pro správné ceny)
5. **BUG-007** - Změna materiálu (UX improvement)
6. **BUG-004** - Zamykání (visual feedback)
7. **BUG-005** - Dávky (pro finální kalkulaci)

---

## 📊 Metriky úspěchu

### Týden 1 (Fáze 1)
- ✅ Všechny P1 bugy opraveny
- ✅ Technolog může vytvořit díl s operacemi
- ✅ Časy a ceny se zobrazují správně
- ✅ MODE přepočet funguje

### Týden 2 (Fáze 2)
- ✅ Všechny P2 bugy opraveny
- ✅ UX je intuitivní
- ✅ Toast notifikace fungují

### Týden 3+ (Fáze 3-5)
- ✅ Export funguje
- ✅ Validace zabraňuje chybám
- ✅ Refaktoring dokončen
