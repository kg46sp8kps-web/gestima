# BETA RELEASE STATUS - 2026-01-26

**Účel:** Kompletní přehled stavu před beta release pro kontinuitu přes více chatů.

---

## 📊 EXECUTIVE SUMMARY

| Kategorie | Status | Poznámka |
|-----------|--------|----------|
| **P0 Audit Fixes** | 10/12 DONE | 2 odloženy (větší refaktoring) |
| **P1 Audit Fixes** | 23/23 DONE | Všechny high-priority hotovo |
| **P2 Audit Fixes** | 5/21 DONE | Low priority, backlog |
| **Testy** | 166/167 PASSED | ✅ Stabilní |
| **UI Základní funkcionalita** | ✅ FUNGUJE | Parts list, edit page, login |
| **UI Kalkulace** | ⚠️ ČÁSTEČNĚ | Backend OK, frontend má issues |
| **Production Data** | ❌ DEMO DATA | Potřeba reálné stroje + materiály |

**Verdikt:** Backend ready pro P0 opravy. Frontend + data vyžadují cleanup před beta.

---

## 🔴 KRITICKÉ PROBLÉMY (zjištěny při testu 2026-01-26)

### ISSUE #1: Operace bez strojů v UI
**Symptom:** Screenshot ukazuje "- Vyberte stroj -" na obou operacích
**Expected:** Op #10: NLX2000, Op #20: DMU50
**Root Cause:** TBD - seed script přiřadil machine_id, ale UI neukazuje
**Impact:** Bez stroje nelze počítat machining_cost
**Priority:** P0 - BLOCKER

**Debug steps:**
1. Zkontrolovat DB: `SELECT id, seq, machine_id FROM operations WHERE part_id = 4`
2. Zkontrolovat API response: `GET /api/operations?part_id=4`
3. Zkontrolovat frontend: Alpine.js state `operations`

---

### ISSUE #2: Bar charty statické (P0-006)
**Symptom:** Změna materiálu/času → bar charty se nemění
**Root Cause:** Bar chart procenta počítána v JS (edit.html:318-325):
```javascript
materialPercent: (batch.material_cost / batch.unit_cost * 100).toFixed(1),
machiningPercent: (batch.machining_cost / batch.unit_cost * 100).toFixed(1),
coopPercent: (batch.coop_cost / batch.unit_cost * 100).toFixed(1),
```

**Expected behavior:**
- Backend vypočítá procenta při každém GET/POST
- Frontend jen zobrazí ready hodnoty

**Fix:**
1. Přidat do `BatchPriceBreakdown` schema:
   ```python
   material_percent: float
   machining_percent: float
   setup_percent: float
   coop_percent: float
   ```
2. Vypočítat v `calculate_batch_prices()`
3. Upravit edit.html aby použil `batch.material_percent` místo výpočtu

**Effort:** 2-3h
**Priority:** P0 (audit issue)
**Impact:** Porušení Pravidla #1 (výpočty pouze Python)

---

### ISSUE #3: Demo data místo production
**Symptom:** Seed stroje nejsou reálné
**Current:** NLX2000, CTX450, DMU50, Sprint32, Mazak510
**Expected:** NL, NZX, SMARTURN, MASTUR, MCV, H40, MILLTAP (3x)

**Action needed:**
- Uživatel poskytne seznam strojů s hodinovými sazbami
- Vytvořit `scripts/seed_production_machines.py`

**Priority:** HIGH (před beta testing)

---

### ISSUE #4: Materiály flat price místo tiers
**Symptom:** Jeden MaterialItem = jedna cena (45 Kč/kg)
**Expected:** Price tiers podle množství:
```
11SMn30:
  - 1kg: 50 Kč/kg
  - 10kg: 45 Kč/kg
  - 100kg: 42 Kč/kg
```

**Impact:** Redesign Material modelu vyžadován
**Effort:** 4-6h (DB schema + API + UI)
**Priority:** MEDIUM (lze odložit na beta feedback)

**Alternativa pro beta:** Použít průměrnou cenu (flat)

---

## ✅ CO FUNGUJE

### Backend Infrastructure
- ✅ P0 fixes (10/12) - soft delete, division by zero, nullable constraints, atomicity
- ✅ P1 fixes (23/23) - auth, XSS, localStorage, error handling, response models
- ✅ Health check (4 kontroly: DB, backup, disk, recent backup)
- ✅ Optimistic locking (version field)
- ✅ Audit trail (created_by, updated_by)
- ✅ Backup system (gzip compression, rotation)

### API Endpoints
- ✅ Authentication (OAuth2 + JWT HttpOnly)
- ✅ Parts CRUD + search + duplicate
- ✅ Operations CRUD + change_mode
- ✅ Features CRUD (backend ready, UI chybí)
- ✅ Batches CRUD + freeze + clone
- ✅ Materials (groups + items)
- ✅ Machines (CRUD)
- ✅ Data endpoints (reference data)

### UI Pages
- ✅ Login page (RSS feeds z českých zdrojů)
- ✅ Parts list (filtering, column visibility, localStorage)
- ✅ Edit page (split layout, ribbony, cenový přehled)
- ✅ Dashboard (dlaždice)

### Edit Page Features
- ✅ Stock rozměry (Ø, délka, šířka, výška)
- ✅ Material dropdown (searchable)
- ✅ Operations list
- ✅ Inline editing (stroj dropdown, tp, tj)
- ✅ Batch table (quantity, čas/ks, cena/ks, celkem)
- ✅ Bar charts (vizualizace nákladů)
- ✅ Detail modal (kompletní rozpis)
- ✅ Sticky price panel

---

## ⏸️ ODLOŽENÉ P0 ISSUES

### P0-006: Frontend výpočty → Python
**Status:** IDENTIFIED, čeká na fix
**Effort:** 2-3h
**Důvod odložení:** Vyžaduje změnu API response + frontend update

### P0-009: Double Rounding → Decimal
**Status:** IDENTIFIED, lower priority
**Effort:** 2h
**Impact:** Akumulace chyb u velkých sérií (1000+ ks)
**Důvod odložení:** Edge case, netýká se běžného použití

---

## 🗂️ SEED DATA STATUS

### Machines (5 demo strojů)
**File:** `scripts/seed_machines.py`

| Code | Type | Hourly Rate | Status |
|------|------|-------------|--------|
| NLX2000 | lathe | 1200 Kč/h | ✅ Seeded |
| CTX450 | lathe | 1000 Kč/h | ✅ Seeded |
| DMU50 | mill | 1400 Kč/h | ✅ Seeded |
| SPRINT32 | lathe | 1100 Kč/h | ✅ Seeded |
| MAZAK510 | mill | 900 Kč/h | ✅ Seeded |

**Action:** Replace s production stroji (čekáme na data od uživatele)

---

### Materials (13 groups, 21 items)
**File:** `scripts/seed_materials.py`

**Struktur:**
```
MaterialGroup (kategorie)
  - code: "11SMn30"
  - name: "Ocel 11 300 automatová (11SMn30)"
  - density: 7.85 kg/dm³

MaterialItem (polotovar)
  - code: "11SMn30-D16"
  - shape: ROUND_BAR
  - diameter: 16mm
  - price_per_kg: 45 Kč/kg
```

**Limitation:** Flat price, no quantity tiers

---

### Complete Demo Part
**File:** `scripts/seed_complete_part.py`

**Created:**
```
Part #4: DEMO-COMPLETE
  - Stock: Ø40mm × 100mm
  - Material: 11SMn30-D16 (45 Kč/kg)
  - Operations:
    - #10: Soustružení (tp=8.5min, tj=15min)
    - #20: Frézování (tp=5min, tj=10min)
  - Batches:
    - 1 ks: 864.39 Kč/ks
    - 10 ks: 384.39 Kč/ks
    - 100 ks: 336.39 Kč/ks
```

**Status:** ✅ Vytvořen, ale operace nemají machine_id v UI (Issue #1)

---

## 📋 TODO: P0 FIXES PRO BETA

### 1. Debug Issue #1 (Operace bez strojů)
**Priority:** P0 - BLOCKER
**Steps:**
1. Query DB: Mají operace machine_id?
2. Test API: Vrací se machine_id v response?
3. Test Frontend: Načítá se machine_id do Alpine.js state?
4. Fix bug kde se ztratilo

**Effort:** 30min - 1h

---

### 2. Fix P0-006 (Bar chart percentages)
**Priority:** P0 (audit issue)
**Steps:**
1. Přidat `*_percent` fieldy do `BatchPriceBreakdown` dataclass
2. Vypočítat v `calculate_batch_prices()`:
   ```python
   result.material_percent = (result.material_cost / result.unit_cost * 100) if result.unit_cost > 0 else 0
   result.machining_percent = ...
   result.setup_percent = ...
   result.coop_percent = ...
   ```
3. Update `BatchResponse` Pydantic schema
4. Update edit.html bar charts:
   ```html
   <!-- Místo -->
   :style="`width: ${(batch.material_cost / batch.unit_cost * 100).toFixed(1)}%`"

   <!-- Použít -->
   :style="`width: ${batch.material_percent}%`"
   ```

**Effort:** 2-3h
**Files to edit:**
- `app/services/price_calculator.py` (výpočet)
- `app/models/batch.py` (schema)
- `app/routers/batches_router.py` (response)
- `app/templates/parts/edit.html` (bar charts)

---

### 3. Production Machines Seed
**Priority:** HIGH (před beta)
**Waiting on:** Uživatel poskytne seznam

**Template:**
```python
# scripts/seed_production_machines.py
machines = [
    {"code": "NL", "name": "...", "type": "lathe", "hourly_rate": ???},
    {"code": "NZX", "name": "...", "type": "lathe", "hourly_rate": ???},
    # ... atd
]
```

---

## 🧪 TEST CHECKLIST (po opravě Issue #1 a P0-006)

**Manual Testing:**
- [ ] Otevřít http://localhost:8000/parts/4/edit
- [ ] Ověřit stroje v dropdownu (Op #10, Op #20)
- [ ] Změnit tp na Op #10 → auto-save → bar charty se updatují
- [ ] Změnit materiál → bar charty se updatují
- [ ] Přidat batch → bar chart se vytvoří
- [ ] Otevřít modal 📊 Detail → správné rozpisy
- [ ] Změnit stroj → hodinová sazba se updatuje → bar charty se updatují

**Automated Testing:**
```bash
pytest tests/ -v
# Expected: 166 passed, 1 skipped
```

---

## 📈 PRIORITNÍ PLÁN PRO DALŠÍ CHAT

### Fáze 1: Debug + Quick Fixes (2-3h)
1. ✅ Debug Issue #1 (proč operace nemají stroje)
2. ✅ Fix P0-006 (bar chart percentages)
3. ✅ Manuální test (checklist výše)

### Fáze 2: Production Data (1-2h)
**Čeká na uživatele:**
1. Seznam strojů (název, typ, sazba)
2. Excel s materiály (nebo rozhodnutí použít flat price pro beta)

**Akce:**
1. Vytvořit production seed skripty
2. Re-seed databáze
3. Test s reálnými daty

### Fáze 3: Optional (4-6h)
- P0-009: Double rounding → Decimal (pokud čas dovolí)
- Features UI (kroky operací)
- Kooperace UI

---

## 🔗 REFERENCE

### Dokumenty
- [docs/audits/2026-01-26-pre-beta-audit.md](audits/2026-01-26-pre-beta-audit.md) - Kompletní audit
- [docs/NEXT-STEPS.md](NEXT-STEPS.md) - Prioritizované next steps
- [CHANGELOG.md](../CHANGELOG.md) - Historie změn
- [CLAUDE.md](../CLAUDE.md) - Pravidla (včetně Pravidla #1!)

### Seed Scripts
- `scripts/seed_machines.py` - Demo stroje
- `scripts/seed_materials.py` - Materiály (13 groups, 21 items)
- `scripts/seed_complete_part.py` - Demo díl s operacemi a batches

### Klíčové soubory
- `app/services/price_calculator.py` - Výpočty cen (zde P0-006 fix)
- `app/templates/parts/edit.html` - Edit page UI (bar charty)
- `app/models/batch.py` - Batch model + schemas

---

## ❓ OTEVŘENÉ OTÁZKY PRO UŽIVATELE

1. **Stroje:**
   - Máš seznam s názvy, typy (lathe/mill), hodinovými sazbami?
   - Potřebuješ 3x MILLTAP jako samostatné stroje nebo lze použít jeden záznam?

2. **Materiály:**
   - Máš excel s materiály a price tiers?
   - Nebo použijeme flat price pro beta a tiers přidáme v1.4+?

3. **Issue #1:**
   - Editoval jsi operace manuálně v UI před screenshotem?
   - Nebo seed script vytvořil a ty jsi jen otevřel stránku?

4. **Testing workflow:**
   - Máš přístup k `pytest` pro spuštění testů?
   - Nebo preferuješ jen manual testing?

---

## 🎯 CÍLE PRO BETA RELEASE

**Must Have:**
- ✅ Issue #1 debugged + fixed
- ✅ P0-006 fixed (bar charty z Pythonu)
- ✅ Production machines seeded
- ✅ Manuální test passed
- ✅ pytest 166/167 passed

**Nice to Have:**
- ⏸️ P0-009 (Decimal)
- ⏸️ Features UI
- ⏸️ Kooperace UI
- ⏸️ Material price tiers

**Can Wait:**
- P2 issues (console.log cleanup, responsive, etc.)
- Export/Import config
- Advanced health monitoring

---

**Last Updated:** 2026-01-26 10:50 UTC
**Author:** Claude Sonnet 4.5
**Session:** Pre-Beta Diagnostic + Status Report
**Next Session:** Debug Issue #1 → Fix P0-006 → Production Data
