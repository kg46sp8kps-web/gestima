# Status & Next Steps

**Date:** 2026-01-27 | **GESTIMA:** 1.5.0

**⚠️ DŮLEŽITÉ:** Pro kompletní status před beta release viz [BETA-RELEASE-STATUS.md](BETA-RELEASE-STATUS.md)

---

## ✅ CODE AUDIT DOKONČEN (2026-01-27)

### Komplexní Code Audit - DONE ✅

**Status:** ✅ HOTOVO - Viz [AUDIT-2026-01-27.md](AUDIT-2026-01-27.md)

**Kritické opravy:**
- ✅ Falsy defaults fix v `time_calculator.py` (0 jako validní hodnota)
- ✅ FK cascade rules v `part.py` (ondelete="SET NULL")
- ✅ Number generator infinite loop prevention

**Dead code removal:** ~18,350 řádků
- Deprecated funkce v price_calculator.py
- Obsolete scripts folder
- Nepoužívané JS komponenty
- Console.log debug statements

**Known issues (backlog):**
- 19× bare `except Exception` → nahradit specifickými exceptions
- 57× copy-paste error handling → refaktorovat na `safe_commit()`

**Hodnocení:** 7.5/10 → **8.5/10** (po opravách)

---

## ✅ NOVĚ IMPLEMENTOVÁNO (2026-01-27)

### Admin UI: 4-Tab Material Management - DONE ✅

**Status:** ✅ HOTOVO - Admin UI s kompletním přehledem materiálů a cen

**Co bylo implementováno:**
- ✅ **4-tab admin interface** (`/admin/material-norms`)
  - **Tab 1: Material Norms** - Správa W.Nr. materiálových norem (EN ISO, ČSN, AISI)
  - **Tab 2: Material Groups (12)** - Zobrazení materiálových skupin (code, name, density)
  - **Tab 3: Ceny (37)** - Cenové kategorie s vnořenými price tiers tabulkami
    - Každá kategorie zobrazuje 3 hmotnostní pásma (0-15kg, 15-100kg, 100+kg)
    - Ceny zobrazené přímo v UI (Kč/kg)
  - **Tab 4: Nastavení** - Systémové koeficienty
  - Search/filter na každém tabu
- ✅ **Material Catalog Seed Script** (`scripts/reset_and_seed_catalog.py`)
  - Automatický seed databáze s kompletní strukturou
  - 12 MaterialGroups + 37 MaterialPriceCategories + 97 MaterialPriceTiers + 108 MaterialNorms
  - Ceny převzaty z existující tabulky nebo odhadnuty podle materiálové rodiny
  - Spuštění: `python3 scripts/reset_and_seed_catalog.py`
- ✅ **Bug fix:** AttributeError při None material_group v admin router
  - Eager loading s `selectinload()` pro related entities
  - Správná kontrola `if entity else None` v JSON serializaci

**Effort:** ~3 hodiny (4-tab UI + seed script + debugging)

**Impact:**
- Admin má kompletní přehled všech materiálů, norem, cen a koeficientů v jednom UI
- Seed script umožňuje rychlý reset a inicializaci databáze
- Price tiers viditelné přímo v UI (nemusí se složitě zjišťovat z DB)

**Dokumentace:**
- [CHANGELOG.md](../CHANGELOG.md) - nová sekce "Admin UI for Material Catalog"
- [temp/README-MATERIAL-IMPORT.md](../temp/README-MATERIAL-IMPORT.md) - aktualizováno URL + popis 4-tab UI
- [temp/PRICE-STRUCTURE.md](../temp/PRICE-STRUCTURE.md) - přehled cenové struktury

---

### Material Catalog Import - PREPARED (⏸️ Odloženo)

**Status:** ⏸️ ODLOŽENO - Nízká priorita, zdržuje vývoj core funkcí

**Co bylo připraveno:**
- ✅ Parser materiálových kódů: `scripts/analyze_material_codes.py`
  - **3322 položek zparsováno z 4181 (79.5% pokrytí)**
  - Podporované formáty: ocel (tyče, trubky, bloky), hliník (bloky, pásy), litina, plasty
  - Output: `temp/material_codes_preview.csv` (ready pro import)
- ✅ Material Norms Database: `scripts/generate_material_norms.py`
  - **83 W.Nr. materiálů s kompletními normami (100% pokrytí)**
  - Mapování W.Nr. → EN ISO, ČSN, AISI
  - Output: `temp/material_norms_seed.sql` (ready pro import do DB)
- ✅ Dokumentace: `docs/MATERIAL-CATALOG-IMPORT.md`
  - Kompletní dokumentace parseru, import workflow, statistiky
  - Důvod odkladu, TODO pro budoucnost

**Effort:** ~4 hodiny (parser + normy + dokumentace)

**Důvod odkladu:**
- Potřeba řešit povrchové úpravy (EP, Zn, Vs, Kl) → vyžaduje novou tabulku
- Profily (L, U, UPE) → vyžaduje custom geometrii nebo nový StockShape
- Tyče s tolerancemi (h6, f7) → vyžaduje tolerance pole v DB
- Zdržuje vývoj core funkcí (Parts, Operations, Batches)

**Kdy se vrátit:**
- Po dokončení core modulů (Parts, Operations, Batches stabilní)
- Až budeme potřebovat kompletní materiálový katalog pro produkci
- Když budeme řešit integraci s dodavateli

**Připravené soubory:**
- `scripts/analyze_material_codes.py` - ready
- `scripts/generate_material_norms.py` - ready
- `scripts/import_material_catalog.py` - TODO: implement `execute_import()`
- `temp/material_codes_preview.csv` - 3322 záznamů ready
- `temp/material_norms_seed.sql` - 83 materiálů ready

**Impact:**
- Parser a normy jsou připravené pro dokončení později
- Dokumentace zajišťuje že se k tomu můžeme vrátit bez ztráty kontextu
- Core vývoj může pokračovat bez zdržení

---

## ✅ NOVĚ IMPLEMENTOVÁNO (2026-01-26)

### ISSUE #1: Machine Selection Persistence - FIXED ✅

**Problém:** Machine dropdown prázdný nebo nepersistoval výběr po navigaci (P0-BLOCKER)

**Root Causes (nalezeno 5 issues):**
1. 500 error `/api/parts/{id}/full` - přístup k neexistujícímu `price_per_kg`
2. 500 error `/api/parts/{id}/stock-cost` - MissingGreenlet lazy-load
3. Pydantic import error - server crash
4. Missing eager-load `price_category.tiers`
5. Alpine.js dropdown binding issue

**Opravy:**
- ✅ [parts_router.py](app/routers/parts_router.py) - Eager-load `price_category.tiers`, odstraněn deprecated field
- ✅ [price_calculator.py](app/services/price_calculator.py) - Try/except MissingGreenlet fallback
- ✅ [material_norm.py](app/models/material_norm.py) - TYPE_CHECKING forward reference
- ✅ [edit.html](app/templates/parts/edit.html) - Explicitní `:selected` binding

**Effort:** 3h debugging + 5 clean root cause fixes (žádné workarounds)
**Impact:** Machine selection nyní funguje správně, žádné 500 errors

---

### Machines CRUD & Pricing Calculator - DONE ✅

**Breaking Change:** Machine hourly_rate → 4-component breakdown

**Co bylo implementováno:**
- ✅ DB: SystemConfig model + Machine hourly rate breakdown (4 komponenty)
- ✅ Computed properties: hourly_rate_setup (bez nástrojů) vs hourly_rate_operation (s nástroji)
- ✅ Machines REST API: GET/POST/PUT/DELETE /api/machines + search endpoint
- ✅ Machines UI: /machines (list), /machines/new, /machines/{id}/edit
- ✅ 7-section machine form s živým výpočtem Setup/Operace sazeb
- ✅ Pricing API: GET /api/parts/{id}/pricing + /pricing/series
- ✅ Pricing UI: /parts/{id}/pricing s detailním rozpadem nákladů
- ✅ Coefficient-based pricing model (overhead × margin + material × coef + coop × coef)
- ✅ Reusable components: macros.html, forms.css, crud_components.js (ADR-015)
- ✅ Database migration pro machines table (auto-migrace při init_db)
- ✅ Seed scripts: seed_config.py (4 koeficienty), seed_machines.py (5 strojů)
- ✅ Dashboard tile "Stroje" funkční

**Effort:** ~10 hodin (DB + API + UI + pricing + components + docs)

**SystemConfig koeficienty:**
- `overhead_coefficient = 1.20` (+20% režie na stroje)
- `margin_coefficient = 1.25` (+25% marže na práci)
- `stock_coefficient = 1.15` (+15% skladový na materiál)
- `coop_coefficient = 1.10` (+10% kooperační)

**5 demo strojů:**
- NLX2000 (1000/1200 Kč/h) - Hlavní sériový soustruh
- SPRINT32 (900/1100 Kč/h) - Rychlý soustruh pro malé díly
- DMU50 (1150/1400 Kč/h) - 5-osá frézka
- CTX450 (850/1000 Kč/h) - Univerzální soustruh
- MAZAK510 (750/900 Kč/h) - 3-osá frézka

**Impact:**
- Stroje mají transparentní rozpad nákladů (odpisy/mzda/nástroje/režie)
- Pricing je plně trackovatelný (každá složka ceny viditelná)
- Reusable komponenty urychlí implementaci Materials/CuttingConditions CRUD

---

### Admin Console for SystemConfig - DONE ✅

**Co bylo implementováno:**
- ✅ API: config_router.py (GET /, GET /{key}, PUT /{key}) - admin only
- ✅ UI: /settings admin page s Alpine.js formulářem
- ✅ Dashboard: Fialová "Nastavení" dlaždice (admin only)
- ✅ Optimistic locking pro konkurenční změny
- ✅ Real-time validace + success/error messaging
- ✅ 9 comprehensive tests (API + UI + auth) - všechny procházejí
- ✅ Fixtures: test_db_session, admin/operator tokens

**Effort:** ~2 hodiny (API + UI + testy + fixtures)

**Impact:**
- Admin může editovat pricing koeficienty bez změny kódu
- Audit trail (kdo + kdy upravil)
- Konkurentní změny jsou bezpečně ošetřené
- Comprehensive test coverage pro admin funkce

**TODO:**
- [ ] Testy pro pricing calculator
- [ ] ADR-015 (Reusable CRUD Components)
- [ ] ADR-016 (Coefficient-based Pricing Model)

---

### ADR-014: Material Price Tiers - DONE ✅

**Breaking Change:** Dynamické ceny materiálů podle množství

**Co bylo implementováno:**
- ✅ DB schema: `MaterialPriceCategory` (13 kategorií) + `MaterialPriceTier` (~40 tiers)
- ✅ Dynamic price selection: `get_price_per_kg_for_weight(category, total_weight, db)`
- ✅ Pravidlo: Největší min_weight ≤ total_weight (nejbližší nižší tier)
- ✅ API CRUD endpoints pro categories + tiers (admin only)
- ✅ Seed scripts: `seed_price_categories.py` + updated `seed_materials.py`
- ✅ 7 unit/integration testů (všechny passed)
- ✅ Dokumentace: ADR-014, CHANGELOG, BETA-RELEASE-STATUS

**Effort:** ~9 hodin (DB + API + tests + seeds + docs)

**Impact:**
- ISSUE #4 (z BETA-RELEASE-STATUS.md) ✅ RESOLVED
- Frozen batches imunní vůči změnám cen (snapshot)
- Množstevní slevy automatické podle batch quantity

---

## Pre-Beta Audit Status (2026-01-26)

**Audit report:** [docs/audits/2026-01-26-pre-beta-audit.md](audits/2026-01-26-pre-beta-audit.md)

### P0 - CRITICAL (13 issues) - 12/13 DONE ✅
| # | Issue | Status |
|---|-------|--------|
| P0-001 | Soft Delete filtry v SELECT queries | ✅ Fixed (6 routers) |
| P0-002 | Division by Zero v price_calculator | ✅ Fixed |
| P0-003 | nullable=False v DB modelech | ✅ Fixed (machine, batch) |
| P0-004 | Atomický batch freeze | ✅ Fixed |
| P0-005 | scalar_one() bez null check | ✅ Fixed |
| P0-006 | Výpočty v JS místo Pythonu | ✅ Fixed (bar chart percentages) |
| P0-007 | Sync operace v async kontextu | ✅ Already fixed |
| P0-008 | Chybí FK na operation.machine_id | ✅ Already fixed |
| P0-009 | Double rounding v kalkulacích | ⏸️ Deferred (Decimal refaktoring) |
| P0-010 | Negative Inner Radius v TUBE | ✅ Fixed |
| P0-011 | Race condition v duplicate_part | ✅ Fixed (retry logika) |
| P0-012 | Cache bez thread safety | ✅ Fixed (asyncio.Lock) |
| P0-013 | N+1 query v price_calculator | ✅ Fixed (2026-01-27) |

### P1 - HIGH (23 issues) - ALL DONE ✅
| # | Issue | Status |
|---|-------|--------|
| P1-001 | Auth na /api/data/* endpointy | ✅ Already implemented |
| P1-002 | XSS v toast (innerHTML) | ✅ Already fixed (textContent) |
| P1-003 | localStorage bez try/catch | ✅ Fixed |
| P1-004 | Error handling v services | ✅ Already implemented |
| P1-005 | Timestamps v Response schématech | ✅ Fixed (Machine, CuttingCondition) |
| P1-006 | Untyped dict → Pydantic model | ✅ Fixed (ChangeModeRequest) |
| P1-007 | Pydantic Field validace | ✅ Already implemented |
| P1-008 | Response Models na misc endpointech | ✅ Already implemented |
| P1-009 | status_code na DELETE | ✅ Fixed (5 routers) |
| P1-010 | Rate Limiting na misc | ✅ Already implemented |
| P1-011 | Cache invalidace | ✅ Already implemented (clear_cache) |
| P1-012 | Index na frozen_by_id | ✅ Fixed |
| P1-013+ | Hardcoded cutting_mode → Enum | ✅ Fixed (deduplikace) |

### P2 - MEDIUM (21 issues) - 5/21 DONE ✅
| # | Issue | Status |
|---|-------|--------|
| P2-002 | Console.log statements | ✅ Fixed (gestima.js, edit.html) |
| P2-003 | .env.example SECRET_KEY | ✅ Fixed (placeholder + komentář) |
| P2-008 | Hardcoded values v time_calculator | ✅ Fixed (konstanty) |
| P2-012 | min="0" validation na numeric inputs | ✅ Fixed (všechny geometry a time inputs) |
| P2-014 | Dead code (parts/list.html) | ✅ Already deleted |

### Remaining Work (Low Priority)
| # | Issue | Effort | Priority |
|---|-------|--------|----------|
| P0-009 | Double rounding → Decimal | 2h | Deferred |
| P2-001 | Alembic migrations | 4h | Backlog |
| P2-004 | min-width responsive | 2h | Backlog |
| P2-005 | pip-audit | 1h | Backlog |

**Testy:** 190 passed, 1 skipped ✅

### Deep Audit (2026-01-27)

**Audit report:** [docs/audits/2026-01-27-pre-beta-deep-audit.md](audits/2026-01-27-pre-beta-deep-audit.md)

| Category | Score |
|----------|-------|
| Tests | A (190 passed) |
| CLAUDE.md Compliance | A (95%) |
| Security | A- |
| Performance | B+ |
| **Overall** | **A-** |

**Fixes applied:**
- ✅ N+1 query in price_calculator.py (pre-load machines)
- ✅ Test fixtures updated for ADR-014 (price_category_id)
- ✅ Backup created

---

## Production Status (Post-Audit + Material Tiers)

### Core Features (vše hotovo)
| Req | Status |
|-----|--------|
| Authentication (OAuth2 + JWT HttpOnly) | DONE |
| Authorization (RBAC) | DONE |
| Role Hierarchy | DONE |
| HTTPS (Caddy docs) | DONE |
| Optimistic locking (ADR-008) | DONE |
| Material Hierarchy (ADR-011) | DONE |
| Batch Snapshot/Freeze (ADR-012) | DONE |
| **Material Price Tiers (ADR-014)** | **✅ DONE (2026-01-26)** |
| Health check | DONE |
| Graceful shutdown | DONE |

**Testy:** 166/167 passed ✅

---

## Recent Updates

### ✅ Edit Page UI Overhaul (v1.3.0 - 2026-01-26)

**Implementováno:**
- **Sticky price panel** - cenový přehled vždy viditelný nahoře pravého panelu
- **Bar charts** - vizualizace rozkladu nákladů (materiál/výroba/seřízení/kooperace)
- **Detail modal** - kompletní rozpis všech dávek s tlačítkem "📊 Detail"
- **Čas/ks column** - nový sloupec v cenové tabulce
- **Material/ks summary** - INFO ribbon zobrazuje materiál/ks a kooperace
- **Operation inline editing:**
  - Stroj dropdown přímo v hlavičce operace
  - tp/tj inline inputs s auto-save
  - LOW/MID/HIGH přesunuty do detail sekce
  - Features placeholder ("📝 Kroky operace - zatím neimplementováno")
- **Machine seeding:**
  - 5 demo strojů (3x lathe, 2x mill)
  - DMG MORI NLX2000, CTX 450, DMU 50, INDEX Sprint 32, Mazak VTC-510
  - `scripts/seed_machines.py` pro seed dat

**Technické detaily:**
- Bar charty s proporcionálními šířkami (% z celkových nákladů)
- Alpine.js computed properties: `totalCoopCost`, `coopOperations`
- Inline editing s @click.stop pattern
- Optimistic locking na update operací
- Color coding: zelená (materiál), modrá (výroba), žlutá (seřízení), fialová (kooperace)

**UX vylepšení:**
- Rychlejší workflow - editace bez otevírání formulářů
- Vizuální orientace v nákladech pomocí bar chartů
- Sticky pozice = přehled cen vždy na očích
- Modal pro detailní analýzu všech dávek

---

### ✅ RSS Feeds Integration (v1.1.5 - 2026-01-25)

**Implementováno:**
- Login page feed změněn z Wikipedia na **4 české RSS zdroje**
- Sekce "VÍTE, ŽE..." zobrazuje **2 články** s celým řádkem klikatelným
- Rotace mezi OSEL.cz, VTM.cz, iROZHLAS, 21stoleti.cz
- API `/api/misc/fact` přepsán na RSS parser s feedparser
- Každý reload = jiný zdroj + náhodné články

**Zdroje:**
- **OSEL.cz** - legendární český vědecký portál (fyzika, vesmír, AI)
- **VTM.cz** - věda, technika, motorismus, historie (2-4 články/den)
- **iROZHLAS** - vědecká sekce Českého rozhlasu (1-3 články/den)
- **21stoleti.cz** - "Věda která baví" (vesmír, archeologie, medicína)

**UX vylepšení:**
- Celý řádek klikatelný (úspora místa, lepší target area)
- Hover efekt pro feedback
- Fallback handling při chybě API

---

### ✅ Parts List with Filtering (v1.1.0 - 2026-01-25)

**Implementováno:**
- Nová stránka `/parts` - Seznam dílů s pokročilým filtrováním
- Multi-field search (ID, part_number, article_number, name)
- Column visibility selector (localStorage persistence + Reset button)
- Actions: Edit, Duplicate, Delete (admin-only)
- Real-time HTMX filtering (debounce 300ms)
- API: `GET /api/parts/search`, `POST /api/parts/{id}/duplicate`
- DB: Přidán `article_number` field do Part modelu
- 10 nových testů (all passing)
- Demo data seeding system (auto-creates 3 DEMO parts)

**Tech:**
- HTMX + Alpine.js
- Multi-field ILIKE search (OR logic)
- Pagination support (50/page)
- localStorage persistence (device-specific, zero latency)

**Design Decision: localStorage > DB sync**
- Zero latency (0ms vs 150ms)
- Zero race conditions
- Simple implementation (KISS)
- Reset button pro obnovení defaults
- Future: Export/Import config (v1.2+) pokud metrics ukážou potřebu

---

## Recent Completed

### ✅ New Edit Page - Hybrid Material Model (v1.2.0 - 2026-01-25)

**Implementováno:**
- Part model rozšířen o `stock_*` pole (diameter, length, width, height, wall_thickness)
- **Hybrid model:** MaterialItem = cena/kg + density, Part.stock_* = custom rozměry
- **Nové API:**
  - `GET /api/parts/{id}/full` - Part s MaterialItem + Group
  - `GET /api/parts/{id}/stock-cost` - výpočet ceny polotovaru (Python)
  - `POST /api/parts/{id}/copy-material-geometry` - kopírování z katalogu
- **Nový edit.html:**
  - Searchable dropdown pro MaterialItem
  - Dynamické rozměry podle shape
  - Cena polotovaru z backendu (konec JS výpočtů - L-001 fix)
  - Přidání batche
  - Seznam operací

**Testy:** 161/161 passing ✅

**Architektura:**
```
MaterialItem (katalog)          Part (konkrétní díl)
├── price_per_kg ────────────► použ. pro výpočet ceny
├── group.density ───────────► použ. pro výpočet váhy
└── shape ───────────────────► stock_diameter, stock_length, ...
                               (editovatelné uživatelem)
```

---

### ✅ UI Frozen Batch & Extended Health Check (v1.1.7 - 2026-01-25)

**Implementováno:**
- UI badge "ZMRAZENO" pro frozen batches v cenovém přehledu
- Warning ikona ⚠️ s tooltip pro batches s varováními
- Clone button pro frozen batches (vytvoří nový nezmrazený)
- Extended health check s 4 kontrolami:
  - Database connectivity
  - Backup folder integrity
  - Disk space (thresholdy: 5% critical, 10% warning)
  - Recent backup age (threshold: 48 hodin)
- Nový stav "degraded" pro warnings (status 200)

**Testy:**
- 5 nových testů pro extended health check
- Celkem: 161/161 passing ✅

**Poznámky:**
- Backup folder location zatím dočasná (`BASE_DIR/backups/`)
- TODO: Přidat `BACKUP_DIR` do config.py

---

### ✅ Snapshot Pre-Conditions Validation (v1.1.6 - 2026-01-25)

**Implementováno:**
- Warnings system místo striktního blokování
- Sbírání podezřelých hodnot (zero costs)
- Logování pro audit trail
- Warnings persisted v snapshot JSON
- KISS přístup - kontrola jen finálních costs, ne intermediate hodnot

**Testy:**
- 3 nové testy
- Celkem: 156/156 passing ✅

---

## Next Steps (prioritizované)

### 1. Material Catalog Import + Smart Lookup (ADR-019)
**Priority:** HIGH | **Effort:** ~12h | **Status:** 📋 NAVRŽENO
**Reference:** [ADR-019](ADR/019-material-catalog-smart-lookup.md)

**Quick Summary:**
- Import Excel katalogu (2405 MaterialItems) s 7-digit material_number (2XXXXXX)
- Smart Upward Lookup: zadám Ø21mm → najde nejbližší větší Ø25mm (tolerance UP only!)
- Part.material_item_id integration (OBA fieldy: material_item_id + price_category_id)
- Catalog weight_per_meter priority (přesnější než calculated weight)
- Připravenost pro Orders v2.0 snapshot

**PREP (před implementací):**
```bash
# 1. Seed MaterialNorms (MANDATORY!)
python scripts/seed_material_norms.py

# 2. Preview import (DRY-RUN)
python scripts/import_material_catalog.py

# 3. Execute import
python scripts/import_material_catalog.py --execute
```

**Implementation Tasks:**
- [ ] PREP: Seed MaterialNorms (~48 záznamů)
- [ ] Import: Execute import (2405 MaterialItems)
- [ ] Backend: MaterialSearchService.find_nearest_upward_match()
- [ ] Backend: /api/materials/parse rozšíření (smart lookup)
- [ ] Backend: price_calculator.py weight_per_meter priority
- [ ] Frontend: Material match card UI (parts/edit.html)
- [ ] Frontend: applyMaterialItem() Alpine.js function
- [ ] Tests: Upward tolerance, multi-dim, catalog weight priority
- [ ] Docs: CHANGELOG update

**User Workflow:**
```
User zadá: "1.4404 Ø21"
→ Parse: material_code=1.4404, shape=ROUND_BAR, diameter=21
→ Smart Lookup: najde "1.4404 Ø25mm" (diff=4mm)
→ UI: "📦 Nalezena skladová položka o 4mm větší" [Použít]
→ Apply: uloží material_item_id + price_category_id + auto-fill geometry
→ Pricing: použije weight_per_meter z katalogu (pokud je v DB)
```

**Vision Impact:**
- 🟡 Příprava pro v2.0 Orders (MaterialItem snapshot)
- 🟡 Early start v5.0 Tech DB (MaterialItem CRUD)

---

### 2. Features Implementation (Kroky operací)
**Priority:** MEDIUM | **Effort:** 4-6h

**Aktuální stav:**
- Detail sekce operací má placeholder "📝 Kroky operace (zatím neimplementováno)"
- Backend model `Feature` existuje v `app/models/feature.py`
- API endpoints pro features existují v `app/routers/parts_router.py`

**Co implementovat:**
- UI pro přidávání/editaci features v detail sekci
- Feature types: turning, facing, boring, threading, milling, drilling, ...
- Inline editing features (podobně jako operations)
- Drag & drop pro reorder (optional)
- Auto-kalkulace času podle feature typu a cutting conditions

**Database:**
- Tabulka `features` již existuje (part_id FK, operation_id FK)
- Pole: type, name, count, dimensions, cutting_mode, time_min

**Reference:**
- `app/services/feature_types.py` - definice typů operací
- `app/services/time_calculator.py` - výpočty časů
- `app/services/reference_loader.py:get_feature_types()` - načtení typů

---

### 2. Kooperace Operation Type
**Priority:** MEDIUM | **Effort:** 2-3h

**Aktuální stav:**
- Kooperace není checkbox na každé operaci
- Kooperace je samostatný typ operace (is_coop=True)

**Co implementovat:**
- UI pro přidání kooperační operace
- Typ: "Kooperace" (ikona 🤝)
- Pole: coop_type, coop_price, coop_min_price, coop_days
- Zobrazení v seznamu operací s odlišným stylem
- Zahrnutí v cenových výpočtech (již funguje v totalCoopCost)

---

### 3. Manuální Test - Operation Editing
**Priority:** HIGH | **Effort:** 15min

**Test checklist:**
- [ ] Otevřít edit page
- [ ] Ověřit zobrazení 5 strojů v dropdown
- [ ] Změnit stroj → auto-save
- [ ] Upravit tp hodnotu → auto-save
- [ ] Upravit tj hodnotu → auto-save
- [ ] Změnit LOW/MID/HIGH v detail sekci
- [ ] Ověřit že bar charty správně zobrazují proporce
- [ ] Otevřít modal "📊 Detail" → ověřit kompletní rozpis

---

### 4. Backup Configuration
**Priority:** MEDIUM | **Effort:** 30min

- Přidat `BACKUP_DIR` do config.py
- Aktualizovat backup_service.py aby používal `settings.BACKUP_DIR`
- Aktualizovat health check aby používal `settings.BACKUP_DIR`

---

### 5. Export/Import User Config (Future Enhancement)
**Priority:** LOW | **Effort:** 2-3h | **Wait for metrics**

**Kdy implementovat:**
- Pokud >20% users používá multi-device
- Pokud users žádají o config backup

**Co implementovat:**
- Export button → stáhne JSON config soubor
- Import button → nahraje config ze souboru
- Obsahuje: column visibility pro všechny seznamy
- Reset all settings button

**Alternativa:**
- DB sync s proper conflict resolution (effort 8-12h)

---

## Archive

Detailní implementační plány P2: [docs/archive/P2-PHASE-B-SUMMARY.md](archive/P2-PHASE-B-SUMMARY.md)

---

**Last Updated:** 2026-01-27
