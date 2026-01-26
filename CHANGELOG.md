# Changelog

Všechny významné změny v projektu GESTIMA budou dokumentovány v tomto souboru.

Formát vychází z [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
projekt dodržuje [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [UNRELEASED] - Critical Pricing Fixes (2026-01-26)

### Fixed

**🚨 CRITICAL FIXES: Data Loss Prevention + Race Conditions**

Audit report: [docs/audits/2026-01-26-pricing-data-loss-audit.md](docs/audits/2026-01-26-pricing-data-loss-audit.md)

1. **CRITICAL-001: Race Condition in Batch Recalculation**
   - **Problem:** `recalculateAllBatches()` sent N parallel POST requests → backend could read stale Part data before savePart() commit
   - **Fix:** Changed from `Promise.all()` parallel to sequential `for...of` loop
   - **Impact:** Prevents incorrect batch costs after material/stock changes
   - **File:** `app/templates/parts/edit.html:859-888`

2. **CRITICAL-002: Silent Failures in Error Handlers**
   - **Problem:** 10+ fetch handlers had `catch (error) { console.error() }` without user feedback → data loss, user unaware of errors
   - **Fix:** Added `window.showToast()` to ALL catch blocks + response.ok validation
   - **Impact:** User now sees errors immediately, can retry failed operations
   - **Files:** `app/templates/parts/edit.html` (8 functions updated)

3. **CRITICAL-003: Redundant Percentage Calculations**
   - **Problem:** Percentages calculated 2× (Python BatchPrices dataclass + Pydantic computed fields) → code duplication (L-002 anti-pattern)
   - **Fix:** Removed percentages from `BatchPrices` dataclass, use ONLY Pydantic `BatchResponse` computed fields
   - **Impact:** Single Source of Truth, reduces overhead, future-proof for VISION (frozen batches need computed percentages)
   - **Files:** `app/services/price_calculator.py:24-46`, `tests/test_batch_percentages.py`

4. **HIGH-005: Missing Response Validation**
   - **Problem:** Fetch handlers didn't check `response.ok` → 500 errors left data empty, user saw "No data"
   - **Fix:** Added `else { showToast, log error }` branches to all fetch handlers
   - **Impact:** User sees specific error messages instead of empty lists
   - **Files:** Same as CRITICAL-002

5. **HIGH-006: Optimistic Locking UX Improvement**
   - **Problem:** 409 conflict showed toast that disappeared after 3s → user didn't reload, got stuck in loop
   - **Fix:** Changed toast to `confirm()` modal: "Reload page?" → Yes: reload, No: fetch latest version
   - **Impact:** User can recover from conflicts without losing work
   - **File:** `app/templates/parts/edit.html:822-833`

**Tests:**
- ✅ All `test_batch_percentages.py` updated and passing
- ✅ BatchPrices dataclass simplified (removed __post_init__)
- ✅ Pydantic computed fields remain unchanged (backward compatible)

---

## [1.4.0] - Material Norm Auto-Mapping (2026-01-26)

### Added

**FEATURE: MaterialNorm Conversion Table - Auto-assign MaterialGroup z normy**

**Problém:**
- Uživatel má 4000-5000 polotovarů s různými označeními (1.0503, C45, 12050, AISI 1045)
- Každé označení = stejný materiál → stejná hustota, řezné podmínky
- Manuální vyplnění `material_group_id` pro každou položku = neefektivní
- Duplikace hustoty v datech (4000× stejná hodnota 7.85 kg/dm³)

**Implementace:**

1. **DB Model** (`app/models/material_norm.py`):
   - `MaterialNorm` tabulka s 4 fixed columns: W.Nr, EN ISO, ČSN, AISI
   - Každý řádek = převodní záznam (min. 1 sloupec vyplněn) → `material_group_id`
   - Case-insensitive search napříč všemi 4 sloupci
   - Audit fields + soft delete + optimistic locking

2. **Service Functions** (`app/services/material_mapping.py`):
   - `auto_assign_group(norm_code)` - hledá normu napříč všemi 4 sloupci
   - `auto_assign_categories(norm_code, shape)` - přiřadí group + price category
   - Case-insensitive lookup (1.0503 = 1.0503, c45 = C45)

3. **Admin Console** (`app/routers/admin_router.py`, `app/templates/admin/material_norms.html`):
   - `/admin/material-norms` - stránka se 2 tabs (Material Norms | System Config)
   - Jednoduchá tabulka: W.Nr | EN ISO | ČSN | AISI | Kategorie | Hustota | Akce
   - CRUD API: GET/POST/PUT/DELETE `/api/material-norms`
   - Modal form pro create/edit s 4 input fieldy
   - Search autocomplete (300ms debounce, cross-column search)
   - Admin-only access (require_role([UserRole.ADMIN]))

4. **Seed Data** (`scripts/seed_material_norms.py`):
   - ~22 běžných převodních záznamů (W.Nr | EN ISO | ČSN | AISI format)
   - Pokrytí: Ocel konstrukční/legovaná/automatová, Nerez 304/316L, Hliník 6060/7075, Mosaz, Plasty
   - Auto-seed při startu aplikace

5. **MaterialGroup Naming** (`app/seed_materials.py`):
   - Přejmenování na user-friendly názvy:
     - "Ocel konstrukční (automatová/S235/C45)"
     - "Ocel legovaná (42CrMo4/16MnCr5)"
     - "Nerez (304/316L)"
     - "Hliník (6060/7075 dural)"
     - "Mosaz (CuZn37/automatová)"
     - "Plasty (PA6/POM)"

**User Workflow:**
```
User vytváří MaterialItem:
  Input: code = "D20 11109" (nebo "1.0036-HR005w05-T"), shape = "round_bar"

  System auto-assign:
    1. Extrahuje normu (např. "11109" nebo "1.0036")
    2. Lookup MaterialNorm ("11109") v ČSN sloupci → MaterialGroup (Ocel konstrukční, 7.85 kg/dm³)
    3. Lookup PriceCategory (Ocel + round_bar) → "OCEL-KRUHOVA"

  Result: MaterialItem s auto-vyplněným group + category
```

**Files Changed:**
- `app/models/material_norm.py` - NEW (MaterialNorm model + schemas)
- `app/services/material_mapping.py` - NEW (auto-assign functions)
- `app/routers/admin_router.py` - NEW (admin API + page)
- `app/templates/admin/material_norms.html` - NEW (admin UI)
- `app/templates/admin/material_norm_form.html` - NEW (create/edit modal)
- `scripts/seed_material_norms.py` - NEW (seed script)
- `app/seed_materials.py` - Updated (MaterialGroup names)
- `docs/ADR/015-material-norm-mapping.md` - NEW (architecture decision)

**Impact:**
- ✅ Auto-přiřazení MaterialGroup při vytváření MaterialItem
- ✅ Alias support (1.4301 = X5CrNi18-10 = AISI 304 → všechny vedou na stejný MaterialGroup)
- ✅ Case-insensitive search (c45 = C45)
- ✅ Editovatelné přes Admin UI (bez redeploy)
- ✅ Performance: Index na všechny 4 sloupce → <1ms lookup

**Budoucí rozšíření:**
- Bulk import z Excelu (4000-5000 položek od uživatele)
- Web scraping (steelnumber.com, matweb.com) pro auto-doplňování

**Effort:** 6h implementation + debugging + tests + docs

### Fixed

**BUG FIX: Admin UI Edit Functionality**

**Problém:**
- Při úpravě existující normy se vytvořil nový záznam místo update
- Edit form se nenahrával s existujícími daty

**Root Cause:**
- Alpine.js components (adminPanel + materialNormForm) v nested struktuře
- `$refs.normForm.openEdit()` nefunguje - nelze přistupovat k metodám nested component přes $refs
- Form component naslouchá `'edit-material-norm'` eventu, ale editNorm() ho nedispatchoval

**Opravy:**
- `app/templates/admin/material_norms.html:343-357` - editNorm() nyní dispatchuje CustomEvent
- `app/templates/admin/material_norms.html:338-342` - openCreateNorm() dispatchuje CustomEvent
- `app/templates/admin/material_norm_form.html:146-150` - přidán listener pro 'create-material-norm' event

**Impact:**
- ✅ Edit nyní správně updateuje existující záznam (PUT endpoint)
- ✅ Form se pre-filluje s existujícími daty
- ✅ Create funguje přes event dispatch (consistency)

**Effort:** 30min debugging + fix

**BUG FIX: Form Saving Stuck Issue**

**Problém:**
- Form se zasekl na "Ukládám..." spinner
- Materiál se nevytvořil, zaseknuté i po refresh

**Root Cause:**
- Frontend posílal empty strings `""` místo `null` pro prázdné fieldy
- Backend očekával `null` pro optional fields
- Způsobilo validační/DB chybu

**Opravy:**
- `app/templates/admin/material_norm_form.html:188-211` - submitForm() konvertuje empty strings → null
- Přidána frontend validace (min. 1 norm column vyplněn)
- Vylepšen error handling s try/catch pro JSON parsing

**Impact:**
- ✅ Ukládání funguje správně pro všechny kombinace vyplněných/prázdných polí
- ✅ Backend dostává správný formát dat

**Effort:** 20min debugging + fix

**BUG FIX: JSON Serialization Error**

**Problém:**
- Chyba při načítání admin stránky: "Object of type MaterialNorm is not JSON serializable"
- Admin stránka nešla otevřít

**Root Cause:**
- Pokus o JSON serialization SQLAlchemy ORM objektů v Jinja2 template
- `{{ norms | tojson }}` nefunguje s ORM objekty

**Opravy:**
- `app/routers/admin_router.py:50-68` - vytvoření `norms_json` jako list of plain dicts
- Manuální konverze všech ORM fields (id, w_nr, en_iso, csn, aisi, material_group, note, version)
- Konverze Decimal → float pro density field
- Template používá `{{ norms_json | tojson }}`

**Impact:**
- ✅ Admin stránka se načítá správně
- ✅ Alpine.js dostává validní JSON data

**Effort:** 15min debugging + fix

**IMPROVEMENT: Live Filtering**

**Request:**
- User požadoval "živě filtrovat jak píšu s debounced"
- Původní implementace neměla funkční search

**Implementace:**
- `app/templates/admin/material_norms.html:313-334` - Alpine.js computed property `filteredNorms`
- Client-side filtering (instant response, no API calls)
- Search napříč všemi 4 sloupci (W.Nr, EN ISO, ČSN, AISI) + kategorie
- Case-insensitive matching
- Zobrazení počtu výsledků: "Nalezeno: 5 z 22"

**Impact:**
- ✅ Instant filtering bez debounce (client-side = dostatečně rychlé)
- ✅ Search v reálném čase během psaní

**Effort:** 15min implementation

**FIX: Dashboard Link Inconsistency**

**Problém:**
- Dashboard link vedl na `/settings` (SystemConfig only)
- Header link vedl na `/admin/material-norms` (full admin UI)
- Matoucí pro uživatele

**Opravy:**
- `app/templates/index.html:113-123` - změna odkazu z `/settings` → `/admin/material-norms`
- Změna názvu z "Nastavení" → "Admin"
- Popisek z "Systémové koeficienty" → "Normy + nastavení"

**Impact:**
- ✅ Konzistentní navigace z dashboardu i headeru
- ✅ Oba odkazy vedou na stejnou stránku s 2 tabs

**Effort:** 5min fix

**DATA: MaterialNorms Seed**

**Status:**
- ✅ Seed script spuštěn: `python3 scripts/seed_material_norms.py`
- ✅ Vytvořeno: 9 nových záznamů, 14 přeskočeno (duplikáty)
- ✅ Celkem v DB: 34 MaterialNorms (23 z seed scriptu + 11 již existujících)

**Pokrytí:**
- Ocel konstrukční (11SMnPb30, C45, C45E, S235JR)
- Ocel legovaná (42CrMo4, 16MnCr5)
- Nerez (304, 304L, 316, 316L)
- Hliník (6060, 7075, EN AW variants)
- Mosaz (CuZn37, CuZn39Pb3, CW508L, CW614N)
- Plasty (PA6, POM, POM-C, POM-H)

**Effort:** 5min seed execution

---

## [UNRELEASED] - Batch Cost Recalculation (2026-01-26)

### Added

**FEATURE: Automatický přepočet batch nákladů (P0-CRITICAL)**

**Problém:**
- Batches se vytvářely s default hodnotami (0 Kč)
- Ceny se nepřepočítávaly po změně materiálu/operací
- Kalkulačka byla nepoužitelná bez správných cen

**Implementace:**

1. **Nový service** (`app/services/batch_service.py`):
   - `recalculate_batch_costs()` - přepočítá všechny náklady batche
   - Integruje material cost (z Part stock + MaterialItem price tiers)
   - Integruje machining cost (z Operations: tp, tj, machine hourly rates)
   - Setup cost distribuován přes quantity
   - Coop cost s min price logic

2. **Backend Auto-recalculate** (`app/routers/batches_router.py`):
   - `POST /batches/` - auto-calculate při vytvoření
   - `POST /batches/{id}/recalculate` - on-demand přepočet
   - Zamrznuté batches nelze přepočítat (409 Conflict)

3. **Frontend Auto-recalculate** (`app/templates/parts/edit.html`):
   - `recalculateAllBatches()` - helper funkce
   - Trigger po: změně materiálu, změně operace (tp/tj/machine), přidání operace
   - Debounced update (400ms) pro stock fields

4. **Testy** (`tests/test_batch_recalculation.py`):
   - 3 testy (basic, no material, with coop) - 100% pass
   - Ověřuje material cost calculation (volume × density × price tier)
   - Ověřuje machining/setup cost distribution
   - Ověřuje coop min price logic

**Files Changed:**
- `app/services/batch_service.py` - NEW (recalculation logic)
- `app/routers/batches_router.py` - Updated (auto-calc + recalc endpoint)
- `app/templates/parts/edit.html` - Updated (frontend auto-trigger)
- `tests/test_batch_recalculation.py` - NEW (3 tests)

**Impact:**
- ✅ Batches mají správné ceny okamžitě po vytvoření
- ✅ Ceny se auto-aktualizují při změnách materiálu/operací
- ✅ Kompletní kalkulace: material + machining + setup + coop
- ✅ Integruje dynamic price tiers (ADR-014)
- ✅ Bar charts nyní zobrazují reálné hodnoty (ne 0%)

**Effort:** 3h implementation + debugging + tests

---

## [UNRELEASED] - Static Bar Charts Fix (2026-01-26)

### Fixed

**ISSUE #P0-006: Bar charty zobrazující rozpad cen byly statické (CRITICAL AUDIT)**

**Root Cause:**
- Bar charty v `parts/edit.html` počítaly percentages v JavaScriptu místo v Pythonu
- Porušení CLAUDE.md Rule #1: "Výpočty POUZE Python"
- JavaScript výpočty: `${(batch.material_cost / batch.unit_cost * 100).toFixed(1)}%`

**Opravy:**
- `app/services/price_calculator.py:24-47` - Přidány `material_percent`, `machining_percent`, `setup_percent`, `coop_percent` do `BatchPrices` dataclass s `__post_init__` výpočtem
- `app/services/price_calculator.py:461-469` - Výpočet percentages v `calculate_batch_prices()` funkci
- `app/models/batch.py:4` - Import `computed_field` pro Pydantic
- `app/models/batch.py:88-119` - Přidány `@computed_field` properties pro percentages v `BatchResponse` schema
- `app/templates/parts/edit.html:318-325` - Nahrazeny JS výpočty za backend hodnoty (`batch.material_percent`)
- `tests/test_batch_percentages.py` - Nový test soubor (5 testů, 100% pass)

**Impact:**
- ✅ Bar charty nyní zobrazují správné percentages z backendu
- ✅ CLAUDE.md Rule #1 compliance (výpočty v Pythonu)
- ✅ Konzistence mezi frontend/backend
- ✅ Testovatelné a maintainable řešení

**Tests:**
```
tests/test_batch_percentages.py::test_batch_prices_percentages_basic PASSED
tests/test_batch_percentages.py::test_batch_prices_percentages_zero_cost PASSED
tests/test_batch_percentages.py::test_calculate_batch_prices_with_percentages PASSED
tests/test_batch_percentages.py::test_batch_response_computed_percentages PASSED
tests/test_batch_percentages.py::test_batch_response_percentages_zero_cost PASSED
```

**Effort:** 1h implementation + tests

---

## [UNRELEASED] - Machine Selection Persistence Fix (2026-01-26)

### Fixed

**ISSUE #1: Machine dropdown nepersistoval výběr po navigaci (P0-BLOCKER)**

**Root Causes (5 issues):**
1. **500 error `/api/parts/{id}/full`**: Přístup k neexistujícímu `material_item.price_per_kg` (field odstraněn v ADR-014)
2. **500 error `/api/parts/{id}/stock-cost`**: SQLAlchemy MissingGreenlet - lazy-loading `price_category.tiers` v async context
3. **Pydantic import error**: Import `MaterialGroupResponse` uvnitř class definition (server crash)
4. **Missing eager-load**: `price_category.tiers` nebyl eager-loaded v `/stock-cost` endpoint
5. **Dropdown binding**: Alpine.js x-model nedokázal synchronizovat selected state

**Opravy:**
- `app/routers/parts_router.py:305` - Odstraněn deprecated `price_per_kg`, přidán `price_category_id` (ADR-014 compliance)
- `app/routers/parts_router.py:272,332` - Přidán `selectinload(MaterialPriceCategory.tiers)` pro eager-loading
- `app/services/price_calculator.py:60-68` - Try/except `MissingGreenlet` fallback (SQLAlchemy async best practice)
- `app/models/material_norm.py:5-6,96` - `TYPE_CHECKING` forward reference (Pydantic recommended pattern)
- `app/templates/parts/edit.html:427` - Explicitní `:selected="machine.id === op.machine_id"` binding

**Impact:**
- ✅ Machine selection nyní persistuje správně po navigaci
- ✅ Žádné 500 errors na `/api/parts/{id}/full` a `/stock-cost`
- ✅ Server se spouští bez Pydantic chyb
- ✅ Clean professional fixes (žádné workarounds)

**Effort:** 3h debugging (10+ pokusů o patche odmítnuto) + 5 clean root cause fixes

---

## [UNRELEASED] - Vision Documentation (2026-01-26)

### Added (Vision & Long-term Planning)

**Documentation:**
- `docs/VISION.md` - Long-term roadmap (1 year, 5 modules: Quotes, Orders, PLM, MES, Tech DB)
- `docs/ADR/VIS-001-soft-delete-for-future-modules.md` - Arch decision: Soft delete policy for future modules
- `CLAUDE.md` - New section "VISION AWARENESS (Roy's Radar)" - Proactive conflict detection

**Roadmap (AI-accelerated estimates):**
- v2.0 (Q1 2026, ~3 weeks): Quotes & Orders
- v3.0 (Q2 2026, ~4 weeks): PLM & Drawings (version control)
- v4.0 (Q3 2026, ~6 weeks): MES & Work Orders (shop floor tracking)
- v5.0 (Q4 2026, ~4 weeks): Technology Database (materials, cutting conditions, tools)

**Architectural Principles:**
- VIS-001: Soft delete everywhere (Orders/WorkOrders need stable FK references)
- VIS-002: Immutable snapshots (freeze data when locking references)
- VIS-003: Version tracking everywhere (optimistic locking)
- VIS-004: API versioning for breaking changes
- VIS-007: Monolithic app (NOT microservices, in-house <100 users)

**Migration Strategy:**
- v1.x-v3.x: SQLite (current)
- v4.x: PostgreSQL evaluation (if >10 concurrent users)
- v5.x+: Read replicas (if >50 users or heavy analytics)

---

## [UNRELEASED] - Admin Console for SystemConfig (2026-01-26)

### Added

**Admin Interface:**
- `/settings` - Admin page pro editaci systémových koeficientů
- Dashboard tile "Nastavení" (fialová, admin-only, ⚙️ icon)
- Alpine.js form s real-time validací (1.0-5.0 rozsah)
- Success/error messaging + auto-reload po úspěšném uložení
- Info box s vysvětlením jak koeficienty fungují
- Historie změn (kdo + kdy upravil) pod každým polem

**API:**
- `GET /api/config/` - List all SystemConfig (admin only)
- `GET /api/config/{key}` - Get specific config (admin only)
- `PUT /api/config/{key}` - Update config with optimistic locking (admin only)
- `app/routers/config_router.py` - REST API router pro SystemConfig

**Testing:**
- `tests/test_config_admin.py` - 9 comprehensive tests (all passing)
- Tests: API endpoints, auth (admin/operator), optimistic locking, UI pages
- `tests/conftest.py` - Enhanced fixtures:
  - `test_db_session` - DB with users + SystemConfig seed
  - `client` - AsyncClient s ASGITransport
  - `admin_token` / `operator_token` - Auth fixtures
  - `admin_headers` / `operator_headers` - Cookie headers

**Security:**
- Admin-only access via `require_role([UserRole.ADMIN])`
- Optimistic locking proti konkurentním změnám (version checking)
- Validace rozsahu hodnot (1.0-5.0) client + server side

**User Experience:**
- Real-time validace před odesláním
- Jasné error zprávy při konfliktu verzí ("modified by another user")
- Auto-reload po úspěšné změně pro refresh timestamps
- Zobrazení aktuální hodnoty + audit trail

### Fixed
- `require_role()` nyní správně přijímá `[UserRole.ADMIN]` místo stringu `"admin"`
- Cookie authentication v test client (ASGITransport)
- Trailing slash redirects v API testech (307 → 200)

---

## [UNRELEASED] - Machines CRUD & Pricing Calculator (2026-01-26)

### Added (ADR-016: Coefficient-based Pricing Model)

**Breaking Change:** Machine.hourly_rate → 4-component breakdown

**New Database Models:**
- `SystemConfig` - Globální konfigurační položky (koeficienty pro pricing)
- Machine hourly rate breakdown:
  - `hourly_rate_amortization` - Odpisy stroje (depreciation)
  - `hourly_rate_labor` - Mzda operátora (operator wage)
  - `hourly_rate_tools` - Nástroje (tooling costs)
  - `hourly_rate_overhead` - Provozní režie (operational overhead)
  - Computed: `hourly_rate_setup` (bez nástrojů), `hourly_rate_operation` (s nástroji)

**Machines CRUD:**
- Full REST API: `GET/POST/PUT/DELETE /api/machines`
- Search endpoint: `GET /api/machines/search?search={query}`
- UI pages: `/machines`, `/machines/new`, `/machines/{id}/edit`
- 7-section form s živým výpočtem Setup/Operace sazeb
- Optimistic locking, audit trail, soft delete

**Pricing Calculator:**
- `GET /api/parts/{id}/pricing?quantity={n}` - Detailní rozpad ceny
- `GET /api/parts/{id}/pricing/series?quantities={1,10,50}` - Porovnání sérií
- UI page: `/parts/{id}/pricing` - Vizualizace nákladů
- Coefficient-based model:
  - Work = (machines + overhead_coef) × margin_coef
  - Material = raw_cost × stock_coefficient
  - Cooperation = raw_cost × coop_coefficient
  - Total = Work + Material + Cooperation

**Reusable Components (ADR-015):**
- `app/templates/macros.html` - Jinja2 form macros (input, select, checkbox, textarea, buttons)
- `app/static/css/forms.css` - Form styling (grid layouts, inputs, cards)
- `app/static/js/crud_components.js` - Alpine.js factories (entityList, pricingWidget)

**Seed Scripts:**
- `scripts/seed_config.py` - SystemConfig with 4 pricing coefficients
- `scripts/seed_machines.py` - 5 machines (NLX2000, CTX450, DMU50, SPRINT32, MAZAK510)
- `scripts/run_migration.py` - Database migration runner

**Database Migration:**
- Auto-migration for machines table (4-component hourly rate)
- Backward-compatible (old hourly_rate column preserved)

**Documentation:**
- Dashboard updated with functional "Stroje" tile

### Changed
- `price_calculator.py` - Complete rewrite with coefficient-based model
- `index.html` - Machines tile added to dashboard

---

## [UNRELEASED] - Material Price Tiers Implementation (2026-01-26)

### Added (ADR-014: Dynamic Price Tiers)

**Breaking Change:** MaterialItem.price_per_kg → MaterialPriceCategory with dynamic tiers

**New Database Models:**
- `MaterialPriceCategory` - Cenová kategorie (13 kategorií podle PDF ceníku)
- `MaterialPriceTier` - Konfigurovatelné cenové pásmo (min_weight, max_weight, price_per_kg)
- ~40 price tiers vytvořeno podle PDF ceníku

**Features:**
- Dynamický výběr ceny podle celkové váhy batch (quantity × weight_kg)
- Pravidlo: Největší min_weight ≤ total_weight (nejbližší nižší tier)
- Příklad: Batch 10 ks (5 kg) → 49.4 Kč/kg, Batch 100 ks (25 kg) → 34.5 Kč/kg, Batch 300 ks (150 kg) → 26.3 Kč/kg
- Frozen batches imunní vůči změnám cen (snapshot price_per_kg)

**API Endpoints:**
- `GET /api/materials/price-categories` - Seznam kategorií
- `GET /api/materials/price-categories/{id}` - Detail s tiers
- `POST /api/materials/price-categories` - Vytvoření (admin)
- `PUT /api/materials/price-categories/{id}` - Update (admin)
- `GET /api/materials/price-tiers` - Seznam tiers (filtrovatelné)
- `POST /api/materials/price-tiers` - Vytvoření (admin)
- `PUT /api/materials/price-tiers/{id}` - Update (admin)
- `DELETE /api/materials/price-tiers/{id}` - Soft delete (admin)

**Seed Scripts:**
- `scripts/seed_price_categories.py` - Seed 13 kategorií + ~40 tiers podle PDF
- Updated `app/seed_materials.py` - Mapování MaterialItems → PriceCategories
- Updated `scripts/seed_complete_part.py` - Výpočet cen s tiers

**Tests:**
- `tests/test_material_price_tiers.py` - 7 unit + integration testů
- Pokrytí: tier selection (small/medium/large), boundary cases, batch pricing, flat price, edge cases

**Documentation:**
- `docs/ADR/014-material-price-tiers.md` - Architektonické rozhodnutí
- Updated `CLAUDE.md` - Poznámka o ADR-014

### Changed

**Breaking Changes:**
- `MaterialItem`: Removed `price_per_kg` field, added `price_category_id` FK
- `calculate_stock_cost_from_part()`: Now async, requires `quantity` and `db` parameters
- `app/seed_materials.py`: MaterialItems mapovány na price categories
- `app/services/snapshot_service.py`: Výpočet price_per_kg pro snapshot

**Updated:**
- `app/services/price_calculator.py`: New `get_price_per_kg_for_weight()` function
- `app/routers/parts_router.py`: Eager load price_category
- `app/routers/batches_router.py`: Eager load price_category for freeze
- `tests/conftest.py`: Test fixtures s price categories + tiers

### Fixed

- Issue #4 (z BETA-RELEASE-STATUS): Materiály flat price → RESOLVED with dynamic tiers

---

## [UNRELEASED] - Pre-Beta Diagnostic Session (2026-01-26)

### Added

**Seed Scripts:**
- `scripts/seed_complete_part.py` - vytváří kompletní demo díl s operacemi a batches pro testování

**Documentation:**
- `docs/BETA-RELEASE-STATUS.md` - kompletní status report před beta release
  - Executive summary (P0/P1/P2 status)
  - 4 kritické problémy identifikované při manuálním testu
  - Co funguje vs co ne
  - Prioritní akční plán
  - Otevřené otázky pro uživatele
  - Reference na klíčové soubory

### Identified Issues (při manuálním testu)

**Issue #1: Operace bez strojů v UI**
- Symptom: Dropdown ukazuje "- Vyberte stroj -" i když seed přiřadil machine_id
- Priority: P0 - BLOCKER
- Status: TBD debugging

**Issue #2: Bar charty statické (P0-006)**
- Symptom: Změna materiálu/času → bar charty se nemění
- Root cause: JS výpočty místo Pythonu (edit.html:318-325)
- Priority: P0 (audit issue)
- Status: Identified, čeká na fix

**Issue #3: Demo data místo production**
- Current: NLX2000, CTX450, DMU50, Sprint32, Mazak510
- Expected: NL, NZX, SMARTURN, MASTUR, MCV, H40, MILLTAP (3x)
- Priority: HIGH
- Status: Čeká na data od uživatele

**Issue #4: Materiály flat price místo tiers** ✅ RESOLVED
- ~~Current: Jeden MaterialItem = jedna cena~~
- ~~Expected: Price tiers podle množství (1kg, 10kg, 100kg)~~
- Priority: MEDIUM
- Status: ✅ **IMPLEMENTED** (ADR-014) - Dynamic price tiers podle quantity

### Status

**Backend:** ✅ Ready pro P0 opravy
- 10/12 P0 fixes done (2 odloženy - větší refaktoring)
- 23/23 P1 fixes done
- 166/167 testů passing

**Frontend:** ⚠️ Částečně functional
- Základní UI funguje (parts list, edit page, login)
- Kalkulace má issues (bar charty, stroje)

**Data:** ❌ Demo data
- Potřeba production stroje + materiály

---

## [1.3.3] - 2026-01-26 - P2 Audit Fixes (Quick Wins + Medium)

### Fixed

**Production Cleanup (P2-002):**
- **Console.log removal** - odstraněny všechny console.log z produkčního kódu
  - gestima.js: 4 console.log/error statements
  - parts/edit.html: 8 console.log statements
  - Ponechány console.error pro debugging kritických chyb

**Security (P2-003):**
- **.env.example SECRET_KEY** - změněno z "15adi" na explicitní placeholder
  - Nový placeholder jasně říká "CHANGE_ME_IN_PRODUCTION_minimum_32_chars"
  - Přidán komentář o minimální délce 32 znaků

**Code Quality (P2-008):**
- **Extrakce konstant v time_calculator.py** - hardcoded hodnoty přesunuty do konstant
  - `DEFAULT_MAX_RPM = 4000`
  - `DEFAULT_VC = 150` (m/min)
  - `DEFAULT_FEED = 0.2` (mm/rev)
  - `DEFAULT_AP = 2.0` (mm)

**Frontend Validation (P2-012):**
- **min="0" na numeric inputs** - všechny rozměrové inputy mají validaci
  - parts/edit.html: délka, průměr, šířka, výška, tloušťka stěny
  - Operation times: operation_time_min, setup_time_min
  - Zabraňuje záporným hodnotám na úrovni HTML

**Already Done:**
- P2-014: Dead code (parts/list.html, list_fragment.html) - již smazáno v předchozím commitu

**Testy:** 166 passed, 1 skipped ✅

---

## [1.3.2] - 2026-01-26 - P1 Audit Fixes (Code Quality & API Standards)

### Fixed

**Code Quality (P1-003, P1-006):**
- **localStorage try/catch** - gestima.js nyní gracefully handluje disabled storage (private mode)
- **Typed API parameter** - `change_mode()` endpoint používá `ChangeModeRequest` Pydantic model místo raw dict
  - Přidán `CuttingMode` enum pro validaci cutting_mode hodnot
  - Pydantic validace pro version field

**API Standards (P1-005, P1-009):**
- **Response timestamps** - MachineResponse a CuttingConditionResponse nyní obsahují created_at, updated_at
- **DELETE status codes** - všechny DELETE endpointy nyní vrací HTTP 204 No Content
  - parts_router.py, operations_router.py, features_router.py
  - batches_router.py, materials_router.py

**Database (P1-012):**
- **Index na frozen_by_id** - batch.frozen_by_id má nyní index pro rychlejší queries

**Code Cleanup (P1-013+):**
- **CuttingMode enum deduplikace** - odstraněn duplicitní enum z operation.py, používá se centrální z enums.py

### Already Fixed (verified during audit)

**Security (P1-001, P1-002, P1-010, P1-011):**
- P1-001: Auth na `/api/data/*` - implementováno (Depends(get_current_user))
- P1-002: XSS v toast - opraveno (textContent místo innerHTML)
- P1-010: Rate limiting - implementováno (@limiter.limit na misc endpointech)
- P1-011: Cache invalidace - clear_cache() v reference_loader.py

**Code Quality (P1-004, P1-007, P1-008):**
- P1-004: Error handling v services - všechny services mají try/except
- P1-007: Pydantic Field validace - Machine, CuttingCondition mají Field()
- P1-008: Response Models - misc endpointy mají FactResponse, WeatherResponse

**Testy:** 166 passed, 1 skipped ✅

---

## [1.3.1] - 2026-01-26 - P0 Audit Fixes (Pre-Beta Critical)

### Fixed

**Data Integrity (P0-001, P0-003):**
- **Soft delete filtry** - přidán `.where(*.deleted_at.is_(None))` do všech SELECT queries
  - parts_router.py (get_parts, search_parts, get_part)
  - operations_router.py (get_operations)
  - features_router.py (get_features)
  - batches_router.py (get_batches)
  - materials_router.py (get_material_groups, get_material_items)
- **nullable=False constraints** - machine.py (code, name, type), batch.py (quantity)

**Runtime Errors (P0-002, P0-005, P0-010):**
- **Division by Zero** - `calculate_coop_cost()` nyní kontroluje `quantity <= 0`
- **scalar_one_or_none** - snapshot_service.py používá správnou metodu s null check
- **TUBE geometry validation** - ValueError při nevalidní geometrii (wall_thickness >= radius)

**Transaction Safety (P0-004, P0-011):**
- **Atomický batch freeze** - snapshot + freeze metadata v jednom try/except bloku
- **Race condition fix** - duplicate_part() má retry logiku s max 10 pokusů

**Concurrency (P0-012):**
- **Cache thread safety** - asyncio.Lock() v reference_loader.py pro get_machines/get_material_groups

### Technical Details

**Opravené soubory:**
- `app/services/price_calculator.py` - division by zero, TUBE validation, logging
- `app/services/snapshot_service.py` - scalar_one_or_none
- `app/services/reference_loader.py` - asyncio.Lock
- `app/models/machine.py` - nullable=False
- `app/models/batch.py` - nullable=False
- `app/routers/*.py` - soft delete filtry (6 souborů)

**Zbývající P0 (vyžaduje větší refaktoring):**
- P0-006: Frontend výpočty → Python (edit.html bar charts)
- P0-009: Double rounding → Decimal pro finanční výpočty

**Testy:** 166 passed, 1 skipped ✅

---

## [1.3.0] - 2026-01-26 - Edit Page UI Overhaul (Price Breakdown & Operations)

### Added

**Price Overview Visualization:**
- **Sticky price panel** - cenový přehled přesunut do sticky pozice nahoře pravého panelu
- **Bar charts** - proporční vizualizace rozkladu nákladů (materiál/výroba/seřízení/kooperace)
- **Čas/ks column** - nový sloupec v tabulce dávek
- **Detail modal** - modal s kompletním rozpadem všech dávek (📊 Detail button)
- **Material/ks summary** - INFO ribbon v levém panelu zobrazuje materiál/ks
- **Cooperation summary** - INFO ribbon zobrazuje celkové náklady na kooperace

**Operation Inline Editing:**
- **Stroj dropdown** - přímý výběr stroje v hlavičce operace
- **tp/tj inputs** - inline editace operation_time_min a setup_time_min
- **Auto-save** - změny se ukládají automaticky při úpravě
- **Optimistic locking** - version field pro detekci konfliktů
- **Mode selection** - LOW/MID/HIGH buttons přesunuty do detail sekce

**Machine Management:**
- `scripts/seed_machines.py` - seed script s 5 demo stroji
- **Demo machines:**
  - DMG MORI NLX2000 (lathe, 1200 Kč/h, sériová výroba)
  - DMG CTX 450 (lathe, 1000 Kč/h, kusová výroba)
  - DMG DMU 50 (mill, 5-axis, 1400 Kč/h)
  - INDEX Sprint 32 (lathe, 1100 Kč/h, malé díly)
  - Mazak VTC-510 (mill, 3-axis, 900 Kč/h)

**API Integration:**
- `GET /api/data/machines` - načítání seznamu strojů (již existoval, nyní použit)
- `PUT /api/operations/{id}` - update operace s machine_id, tp, tj
- Machines cache v reference_loader.py

### Changed

**Edit Page Layout (parts/edit.html):**
- **Right panel sticky** - cenový přehled vždy viditelný při scrollování
- **Table structure** - Dávka | Čas/ks | Cena/ks (s bar chart) | Celkem
- **Bar chart proportions** - šířky based on % podílu jednotlivých nákladů
- **Operation header** - kompletně přepracována na inline editing
- **Detail section** - vyhrazena pro features (zatím placeholder "📝 Kroky operace")
- **Mode buttons** - přesunuty z hlavičky do detail sekce pod "Režim řezání"

**Operation Card Structure:**
```
Header (inline editable):
├── Seq + Icon
├── Stroj dropdown
├── tp input (min)
└── tj input (min)

Detail (expandable):
├── Režim řezání: LOW | MID | HIGH
└── Kroky operace (placeholder)
```

**Computed Properties:**
- `totalCoopCost` - suma cen kooperací ze všech operací
- `coopOperations` - počet kooperačních operací

### Removed

- **Operation name** - odstraněno zobrazení názvu operace (redundantní)
- **Kooperace checkbox** - kooperace je typ operace, ne vlastnost každé operace

### Technical Details

**Bar Chart Implementation:**
```html
<div style="display: flex; height: 8px;">
  <div :style="`width: ${(batch.material_cost / batch.unit_cost * 100).toFixed(1)}%; background: var(--accent-green);`"></div>
  <div :style="`width: ${(batch.machining_cost / batch.unit_cost * 100).toFixed(1)}%; background: var(--accent-blue);`"></div>
  <div :style="`width: ${(batch.setup_cost / batch.unit_cost * 100).toFixed(1)}%; background: var(--accent-yellow);`"></div>
  <div :style="`width: ${(batch.coop_cost / batch.unit_cost * 100).toFixed(1)}%; background: var(--accent-purple);`"></div>
</div>
```

**Operation Update:**
- Inline editing s @click.stop pro prevenci event bubbling
- Debounced save (auto při změně)
- Version check pro optimistic locking
- Error handling s rollback

**Color Scheme:**
- Materiál: `--accent-green` (zelená)
- Výroba: `--accent-blue` (modrá)
- Seřízení: `--accent-yellow` (žlutá)
- Kooperace: `--accent-purple` (fialová)

### Database

**Machines seed data:**
- 5 strojů s kompletními parametry
- Type: lathe (3x), mill (2x)
- Hourly rates: 900-1400 Kč
- Priority sorting (10-30)
- Active by default

### User Experience

**Visual Improvements:**
- Cenový přehled vždy viditelný (sticky)
- Bar charty poskytují okamžitou vizuální orientaci v nákladech
- Detail modal pro hloubkový pohled na všechny dávky
- Inline editing - rychlejší workflow bez otevírání formulářů

**Workflow Improvements:**
- Stroj lze změnit jedním kliknutím v dropdownu
- tp/tj lze upravit přímo v hlavičce
- Změny se ukládají automaticky
- LOW/MID/HIGH dostupné v detail sekci

---

## [1.2.0] - 2026-01-25 - New Edit Page (Hybrid Material Model)

### Added

**Part Model - Stock Geometry Fields:**
- `stock_diameter` - průměr polotovaru (mm)
- `stock_length` - délka polotovaru (mm)
- `stock_width` - šířka polotovaru (mm)
- `stock_height` - výška polotovaru (mm)
- `stock_wall_thickness` - tloušťka stěny trubky (mm)

**Hybrid Material Model:**
- MaterialItem určuje materiál (cena/kg, hustota z group)
- Part.stock_* pole umožňují custom rozměry pro konkrétní díl
- Rozměry lze kopírovat z katalogu nebo zadat ručně

**API Endpoints:**
- `GET /api/parts/{id}/full` - Part s eager-loaded MaterialItem + Group
- `GET /api/parts/{id}/stock-cost` - výpočet ceny polotovaru (Python, L-001 compliant)
- `POST /api/parts/{id}/copy-material-geometry` - kopíruje rozměry z MaterialItem do Part

**Services:**
- `calculate_stock_cost_from_part()` - nová funkce pro výpočet z Part.stock_* polí

**Frontend (edit.html) - kompletní přepis:**
- **Searchable dropdown** pro výběr polotovaru (MaterialItem)
- **Dynamické rozměry** podle shape (round_bar, tube, flat_bar, plate, ...)
- **Cena polotovaru z backendu** - konec JS výpočtů (L-001 fix)
- **Přidání batche** s tlačítkem
- **Seznam operací** s change mode (LOW/MID/HIGH)
- Split layout (left panel 320px + right panel)

### Changed

**Database Migration:**
- Automatická migrace přidává stock_* sloupce do existující DB
- `_migrate_parts_stock_columns()` v database.py

**Part Model:**
- `material_item_id` nyní nullable (pro legacy díly bez materiálu)
- `PartBase`, `PartUpdate` rozšířeny o stock_* pole
- `PartFullResponse` - Part s nested MaterialItem + Group
- `StockCostResponse` - response pro /stock-cost endpoint

**Duplicate Part:**
- Kopíruje nově i stock_* pole

### Technical Details

**Architektura (Hybrid Model):**
```
MaterialItem (katalog)          Part (konkrétní díl)
├── price_per_kg ─────────────► použ. pro výpočet ceny
├── group.density ────────────► použ. pro výpočet váhy
│
└── shape (template) ─────────► stock_diameter, stock_length, ...
                                (kopie při výběru, pak editovatelné)
```

**Volume Calculations (Python):**
- ROUND_BAR: π × r² × L
- SQUARE_BAR: a² × L
- FLAT_BAR: w × h × L
- HEXAGONAL_BAR: (3√3/2) × a² × L
- PLATE: w × h × L
- TUBE: π × (r_o² - r_i²) × L
- CASTING/FORGING: π × r² × L (aproximace)

**Tests:** 161/161 passed ✅

---

## [1.1.7] - 2026-01-25 - UI Frozen Batch & Extended Health Check

### Added

**UI Indikace Frozen Batch (edit.html):**
- Badge "ZMRAZENO" na frozen batches v cenovém přehledu
- Warning ikona (⚠️) s tooltip pokud snapshot obsahuje varování
- Tlačítko "Klonovat" pro frozen batches - vytvoří nový nezmrazený batch
- Clone funkce volá existující API `POST /api/batches/{id}/clone`

**Extended Health Check (`/health` endpoint):**
- Rozšířený health check o 3 nové kontroly
- **Backup folder integrity** - existence a write permissions
- **Disk space check** - free space s thresholdy (5% critical, 10% warning)
- **Recent backup age** - kontrola zda poslední backup není starší než 48 hodin
- Nový stav **"degraded"** - warnings ale ne kritické (status 200)
- Backwards compatible - stále vrací `status` + `version`
- Nová struktura: `checks` dict s detaily jednotlivých kontrol

**Health check stavy:**
- `healthy` - vše OK (200)
- `degraded` - warnings, ale ne kritické (200)
- `unhealthy` - kritické problémy (503)
- `shutting_down` - graceful shutdown (503)

### Changed

**Frontend (edit.html):**
- Cenový přehled tabulka rozšířena o 3. sloupec "Akce"
- První sloupec zobrazuje quantity + frozen badge + warning ikona
- Tooltip zobrazuje seznam warnings z snapshotu

**Health Check Response Format:**
```json
{
  "status": "degraded",
  "version": "1.1.7",
  "checks": {
    "database": {"status": "healthy"},
    "backup_folder": {"status": "healthy"},
    "disk_space": {
      "status": "warning",
      "free_gb": 15.2,
      "total_gb": 250.0,
      "percent_free": 6.1
    },
    "recent_backup": {
      "status": "healthy",
      "latest_backup": "gestima.db.backup-20260125-183000.gz",
      "age_hours": 2.5
    }
  }
}
```

### Tests

**Nové testy (5):**
- `test_disk_space_check_exists` - disk space je v health response
- `test_backup_folder_check_exists` - backup folder check existuje
- `test_recent_backup_check_exists` - recent backup check existuje
- `test_degraded_status_on_warnings` - degraded status vrací 200
- `test_unhealthy_status_returns_503` - unhealthy vrací 503

**Aktualizované testy (2):**
- `test_health_response_structure` - kontroluje novou strukturu s `checks`
- `test_health_reports_valid_status` - akceptuje všechny stavy (healthy/degraded/unhealthy)

**Celkem:** 161 testů ✅ (předchozích 156 + 5 nových)

### Technical Details

**Backup Location:**
- Backup folder: `{BASE_DIR}/backups/`
- Pattern: `*.db.backup*`
- TODO: Přidat `BACKUP_DIR` do config.py (zatím hardcoded)

**Disk Space Thresholdy:**
- < 5% free → `critical` status → unhealthy (503)
- < 10% free → `warning` status → degraded (200)
- >= 10% free → `healthy` status

**Backup Age Threshold:**
- > 48 hodin → `warning` status → degraded (200)

---

## [1.1.6] - 2026-01-25 - Snapshot Pre-Conditions Validation

### Added

**Snapshot Warnings System:**
- Snapshot nyní sbírá varování o podezřelých hodnotách před zmrazením
- Warnings neblokují freeze - umožňují edge cases (prototypy, zkušební díly)
- Warnings ukládány do snapshot JSON pro pozdější audit
- Logování warnings pro audit trail

**Validované podmínky:**
- Materiál s nulovou/zápornou cenou (`price_per_kg <= 0`)
- Nulové náklady na materiál (`material_cost <= 0`)
- Nulové náklady na obrábění (`machining_cost <= 0`)
- Nulové celkové náklady (`total_cost <= 0`)
- Chybějící materiál na dílu

**Snapshot struktura rozšířena:**
```json
{
  "frozen_at": "...",
  "frozen_by": "...",
  "costs": {...},
  "metadata": {...},
  "warnings": [
    "Materiál 'Ocel 11300' má podezřelou cenu: 0.0 Kč/kg",
    "Náklady na obrábění: 0.0 Kč"
  ]
}
```

### Changed

**`app/services/snapshot_service.py`:**
- `create_batch_snapshot()` sbírá warnings před vytvořením snapshotu
- Loguje warnings s extra context (batch_id, part_id, user)
- Warnings persisted v snapshot JSON

### Tests

**Nové testy (3):**
- `test_freeze_with_zero_price_logs_warning` - materiál s nulovou cenou
- `test_freeze_with_zero_costs_logs_warnings` - batch s nulovými náklady
- `test_freeze_with_valid_data_no_warnings` - validní freeze bez varování

**Celkem:** 156 testů ✅ (předchozích 153 + 3 nové)

### Design Decision

**Proč warnings místo blokování?**
- ✅ Neblokuje uživatele v edge cases (prototypy zdarma, zkušební díly)
- ✅ Audit trail - loguje podezřelé případy
- ✅ Future: UI může zobrazit varování při freeze
- ✅ Warnings persisted v snapshotu - viditelné i později
- ✅ Pragmatické - nulová cena může být validní (vnitřní výroba, prototypy)

**Alternativy zvážené:**
- ❌ Striktní validace (blokovat vše) - příliš restriktivní
- ❌ Jen logování (bez uložení) - ztráta informace po freeze

---

## [1.1.5] - 2026-01-25 - RSS Feeds Integration

### Changed

**Login Page - "Víte, že..." sekce:**
- Změněn feed z Wikipedia random article na **rotující české RSS zdroje**
- Nadpis změněn z "DENNÍ ČLÁNEK Z WIKIPEDIE" na "VÍTE, ŽE..."
- Zobrazují se **2 články** místo jednoho
- **Celý řádek je klikatelný** - lepší UX, úspora místa
- Hover efekt při najetí myší

**API - RSS Parser:**
- Endpoint `/api/misc/fact` přepsán z Wikipedia API na RSS aggregátor
- Rotace mezi 4 českými zdroji:
  - OSEL.cz (legendární vědecký portál)
  - VTM.cz (věda, technika, zajímavosti)
  - iROZHLAS (věda a technologie)
  - 21stoleti.cz (populární věda)
- Každý reload = jiný zdroj + 2 náhodné články
- HTML tags automaticky stripovány
- Text zkrácen na ~150 znaků (2 články na 1 obrazovku)

### Added

**Dependencies:**
- `feedparser==6.0.12` - RSS feed parsing
- `sgmllib3k==1.0.0` - feedparser dependency

**Features:**
- Multi-source RSS aggregation (4 české vědecké zdroje)
- Náhodný výběr zdroje při každém requestu
- Výběr 2 náhodných článků z top 20 nejnovějších

### Technical Details

**Response format změněn:**
```json
// Před (1 článek):
{"title": "...", "text": "...", "url": "..."}

// Po (2 články):
{"facts": [
  {"title": "...", "text": "...", "url": "..."},
  {"title": "...", "text": "...", "url": "..."}
]}
```

**Frontend změny:**
- Alpine.js state: `wiki` → `facts` (array)
- Template: 2x `<template x-if>` bloky s clickable cards
- Error handling: fallback pro oba články

---

## [1.1.4] - 2026-01-25 - P3 Sprint (Low Priority Cleanup)

### Removed

**Dead Code:**
- `app/templates/parts/list.html` - starý nepotřebný seznam dílů
- `app/templates/parts/list_fragment.html` - starý HTMX fragment
- `MaterialDB` alias v `app/models/__init__.py` - backward compatibility odstraněna
- Zastaralý TODO komentář v `database.py`

### Added

**Rate Limiting:**
- `/api/misc/fact` - 10 requests/minute
- `/api/misc/weather` - 10 requests/minute

### Changed

**Refactoring:**
- `reference_loader.py` - používá `MaterialGroup` místo `MaterialDB` alias
- `scripts/seed_materials.py` - opravený import (MaterialGroup)

### Deferred

- `calculate_material_cost()` - deprecated ale ponechána (live preview use case)

---

## [1.1.3] - 2026-01-25 - P2 Sprint

### Added

**DB Helpers:**
- `safe_commit()` - helper pro konzistentní error handling v routerech
  - Eliminuje opakující se try/except bloky (L-008)
  - Auto-refresh entity, standardní HTTP responses (409, 500)

**Tests:**
- `test_materials.py` - 16 nových testů pro materials router
  - MaterialGroup CRUD, validace, duplicity
  - MaterialItem shapes, soft delete, FK constraints
  - Celkem: 153 testů ✅

**Documentation:**
- ADR-013: localStorage for UI Preferences
  - Zdůvodnění volby localStorage vs DB sync
  - Trade-offs a future enhancement path

### Changed

- `ARCHITECTURE.md` → v1.2
  - Aktualizovaná hierarchie entit (MaterialGroup/Item)
  - Nové ADR odkazy (008, 011, 012, 013)
  - DB helpers reference

### Fixed

**Cache Invalidation:**
- `clear_cache()` voláno po CRUD operacích v materials_router
- Dříve: cache se nikdy neinvalidovala při změně dat

---

## [1.1.2] - 2026-01-25 - Audit Fixes (P1)

### Security

- **XSS fix v toast.innerHTML** - použití `textContent` místo `innerHTML`
- **Auth na data_router** - všechny endpointy nyní vyžadují přihlášení

### Added

**Pydantic Update schémata:**
- `CuttingConditionUpdate` (s optimistic locking)
- `MachineUpdate` (s optimistic locking)
- `BatchUpdate` (s optimistic locking)

**Response models:**
- `data_router`: `MachineRefResponse`, `MaterialRefResponse`, `FeatureTypeResponse`
- `misc_router`: `FactResponse`, `WeatherResponse`

### Changed

**Pydantic Field validace (20+ fieldů):**
- `CuttingConditionBase`: `Field()` s `max_length`, `gt=0`
- `MachineBase`: `Field()` s `max_length`, `gt=0`, `ge=0`
- `LoginRequest`: `Field()` s `min/max_length`

**Database:**
- `Operation.machine_id` - přidán FK constraint (`ondelete="SET NULL"`)

**Error handling v services:**
- `auth_service`: try/except v `create_user()` s rollback
- `cutting_conditions`: try/except v `get_conditions()`
- `reference_loader`: try/except v `get_machines()`, `get_material_groups()`
- `snapshot_service`: try/except v `create_batch_snapshot()`

---

## [1.1.1] - 2026-01-25 - Security Audit Fixes (P0)

### Security

**P0 Fixes (CRITICAL - Audit 2026-01-25):**

- **SECRET_KEY validace** (CVSS 9.1 → Fixed)
  - Pydantic validator - odmítne default hodnotu v produkci
  - Minimální délka 32 znaků
  - Při startu v produkci bez validního klíče → crash (bezpečnější než tiché selhání)

- **DEBUG default False** (CVSS 7.5 → Fixed)
  - Změněno z `DEBUG: bool = True` na `False`
  - Vývojář musí explicitně zapnout v `.env`

- **Security Headers Middleware** (CVSS 6.1 → Fixed)
  - X-Frame-Options: DENY (clickjacking)
  - X-Content-Type-Options: nosniff (MIME sniffing)
  - X-XSS-Protection: 1; mode=block
  - Referrer-Policy: strict-origin-when-cross-origin
  - Permissions-Policy: geolocation=(), microphone=(), camera=()

### Fixed

- **Soft delete bug** v `materials_router.py:245`
  - Sync DB operace v async kontextu → `datetime.utcnow()`
  - Konzistentní s `batches_router.py`

### Changed

- Verze synchronizována na 1.1.x across config.py, README.md

### Added

- `docs/audits/` - Auditní zprávy
- `docs/audits/2026-01-25-full-audit.md` - Kompletní audit report
- `app/routers/misc_router.py` - Weather/fact API (nyní v gitu)
- `app/templates/auth/login.html` - Login stránka (nyní v gitu)
- `.gitignore` - `*.db.backup-*` pattern

---

## [1.1.0] - 2026-01-25 - Parts List with Filtering

### Added

**Parts List Page:**
- Nová stránka `/parts` - Seznam dílů s pokročilým filtrováním
- Multi-field search: ID, číslo výkresu, article number, název
- Real-time HTMX filtrování (debounce 300ms)
- Column visibility toggle (localStorage persistence)
- **Reset button** - "Reset na výchozí" pro obnovení výchozího nastavení sloupců
- Akce: Edit, Duplicate, Delete (admin-only)
- Empty state handling
- Pagination support (50 items/page)

**Database:**
- Přidán `article_number VARCHAR(50)` do tabulky `parts`
- Index na `article_number` pro rychlé vyhledávání

**API:**
- `GET /api/parts/search` - Filtrování dílů s multi-field search
- `POST /api/parts/{id}/duplicate` - Duplikace dílu (auto-generuje part_number-COPY-N)
- Parametry: `search`, `skip`, `limit`
- Response: `{parts, total, skip, limit}`

**Models:**
- `Part.article_number` - nový field (Optional[str])
- `PartBase`, `PartUpdate` - aktualizovány pro article_number

**Templates:**
- `parts_list.html` - kompletní seznam dílů s Alpine.js state management
- Column selector dropdown
- Responsive table design

**Tests:**
- `test_parts_filtering.py` - 10 testů (all passing ✅)
  - article_number CRUD
  - Multi-field search (OR logic)
  - Pagination
  - Duplicate detection

### Changed

- `pages_router.py` - `/parts` route zjednodušen (data loading přes API)
- `base.html` - menu už obsahuje odkaz "Díly"
- Dashboard (`/`) zůstává pro budoucí statistiky

### Technical Details

- HTMX pro live filtering bez page reload
- Alpine.js pro column visibility state
- **localStorage persistence** - preferences uloženy v browseru (device-specific)
  - Zero latency (0ms response)
  - Reset button pro obnovení defaults
  - Future: Export/Import config pro multi-device (v1.2+)
- Debounced input (300ms) pro optimalizaci API calls

### Design Decisions

**Proč localStorage místo DB sync?**
- ✅ Zero latency (žádné flashing UI)
- ✅ Zero race conditions
- ✅ Simple implementation (KISS)
- ✅ Internal tool (většina users = 1 zařízení)
- Future: Export/Import config pokud metrics ukážou potřebu multi-device sync

---

## [1.0.0] - 2026-01-24 - First Production Release

### Summary

První produkční verze GESTIMA - webová aplikace pro výpočet nákladů a časů obrábění na CNC strojích.

**Status:** ✅ Production Ready
- P0 (Blocker) - UZAVŘENO
- P1 (Kritické) - UZAVŘENO
- P2 (Důležité) - UZAVŘENO

**Testy:** 127/127 passed ✅

---

### Added - P0: Blocker Requirements ✅

**Authentication & Authorization:**
- OAuth2 + JWT v HttpOnly Cookie (SameSite=strict)
- RBAC: Admin / Operator / Viewer roles
- Role Hierarchy: Admin >= Operator >= Viewer (ADR-006)
- Password hashing (bcrypt)
- Protected API endpoints (401/403)
- CLI: `python gestima.py create-admin`
- ADR-005: Authentication & Authorization

**HTTPS Deployment:**
- Caddy reverse proxy documentation
- SECURE_COOKIE setting (production)
- ADR-007: HTTPS via Caddy

**Debug Mode:**
- `.env.example` vytvořen (DEBUG, JWT_SECRET_KEY)

---

### Added - P1: Critical Requirements ✅

**Structured Logging:**
- `app/logging_config.py` - JSON structured logging
- Log levels: INFO, WARNING, ERROR
- Correlation IDs pro request tracking

**Global Error Handler:**
- `app/gestima_app.py` - exception handler pro 500 errors
- User-friendly error messages

**Transaction Error Handling:**
- Try/except bloky ve všech routerech (14 míst)
- IntegrityError → HTTP 409
- SQLAlchemyError → HTTP 500
- Rollback při chybách

**Backup Strategie:**
- `app/services/backup_service.py`:
  - create_backup() - SQLite backup s gzip kompresí
  - list_backups() - seznam záloh
  - restore_backup() - obnovení ze zálohy
  - cleanup_old_backups() - rotace (retention count)
- CLI commands:
  - `python gestima.py backup`
  - `python gestima.py backup-list`
  - `python gestima.py backup-restore <name>`
- Config: BACKUP_DIR, BACKUP_RETENTION_COUNT, BACKUP_COMPRESS

**Audit Trail:**
- AuditMixin.created_by, updated_by vyplňováno ve všech routerech
- Audit helper: set_audit(obj, user) eliminuje L-002 duplikaci

**CORS:**
- CORSMiddleware s konfigurovatelným whitelist
- Config: CORS_ORIGINS (comma-separated)
- Support pro credentials (cookies)

**Rate Limiting:**
- slowapi integration
- 100 requests/min - obecné API
- 10 requests/min - auth endpoints
- Config: RATE_LIMIT_ENABLED, RATE_LIMIT_DEFAULT, RATE_LIMIT_AUTH

---

### Added - P2: Important Requirements ✅

**P2 Fáze 1: Optimistic Locking (ADR-008)**

- Version check v 4 routerech (parts, operations, features, batches)
- HTTP 409 Conflict při concurrent updates
- "Data byla změněna jiným uživatelem. Obnovte stránku a zkuste znovu."
- Auto-increment version (SQLAlchemy event listener)
- 11 testů ✅

**P2 Fáze A: Material Hierarchy (ADR-011)**
- Dvoustupňová hierarchie:
  - MaterialGroup (kategorie) - code, name, density
  - MaterialItem (polotovaru) - code, shape, diameter, price_per_kg, supplier
- StockShape enum (8 tvarů: ROUND_BAR, SQUARE_BAR, FLAT_BAR, HEXAGONAL_BAR, PLATE, TUBE, CASTING, FORGING)
- API: `/api/materials/groups`, `/api/materials/items`
- Seed data: 13 groups, 21 items
- Single Source of Truth - materiály v DB (L-006 fixed)

**P2 Fáze B: Minimal Snapshot (ADR-012)**

- Batch freeze fields: is_frozen, frozen_at, frozen_by_id, snapshot_data
- Snapshot struktura (JSON): costs + metadata
- API: POST /freeze, POST /clone
- Soft delete pro frozen batches
- Price stability - změna ceny materiálu neovlivní frozen batch
- 8 testů ✅

**P2: Health Check Endpoint**

- GET /health - stav aplikace a databáze
- Bez autentizace (pro load balancery, Kubernetes)
- Response: status, version, database status
- HTTP 200 (healthy) / 503 (unhealthy)
- 5 testů ✅

**P2: Graceful Shutdown**

- Lifespan cleanup - proper resource disposal
- Database engine dispose při shutdown
- Health check vrací 503 během shutdown (load balancer)
- Logging: startup/shutdown events
- 4 testy ✅

**P2: Business Validations**

- Pydantic Field validace pro všechny modely:
  - Part: part_number (min/max length), length >= 0
  - Batch: quantity > 0
  - Feature: count >= 1, blade_width > 0, dimensions >= 0
  - Operation: seq >= 1, times >= 0, coop_price >= 0
- 20 testů ✅

---

### Added - Core Functionality

**Backend:**
- CRUD API pro parts, operations, features, batches
- Services: price_calculator, time_calculator, reference_loader
- SQLite + WAL mode (async via aiosqlite)
- AuditMixin (created_at, updated_at, created_by, updated_by, deleted_at, deleted_by, version)

**Frontend:**
- UI s Alpine.js + HTMX
- Jinja2 templates
- Responsivní layout

**Tech Stack:**
- FastAPI + Pydantic v2
- SQLAlchemy 2.0 (async)
- pytest + pytest-asyncio

---

### Documentation

**ADRs:**
- ADR-001: Soft Delete Pattern
- ADR-003: Integer ID vs UUID
- ADR-004: Implementation Notes
- ADR-005: Authentication & Authorization
- ADR-006: Role Hierarchy
- ADR-007: HTTPS via Caddy
- ADR-008: Optimistic Locking
- ADR-011: Material Hierarchy
- ADR-012: Minimal Snapshot

**Dokumenty:**
- `CLAUDE.md` - AI assistant pravidla + production requirements
- `docs/ARCHITECTURE.md` - architektura (5 min quick start)
- `docs/GESTIMA_1.0_SPEC.md` - kompletní specifikace
- `docs/TESTING.md` - testovací strategie
- `docs/audit.md` - auditní zpráva (original)
- `docs/audit-p2b.md` - auditní zpráva P2B (post-implementation)
- `docs/VERSIONING.md` - verzovací politika
- `CHANGELOG.md` - tento soubor

---

### Known Issues (P2 Fáze C - Planned)

**A1: Frozen Ghost (HIGH)**
- Snapshot neobsahuje geometry hash
- Změna geometrie po freeze → warning missing
- Tracked in: `docs/audit-p2b.md`

**A2: Silent Failure (HIGH)**
- Health check endpoint chybí
- No monitoring pro backupy/disk space
- Tracked in: `docs/audit-p2b.md`, `docs/NEXT-STEPS.md`

**A3: Zero-Price Bomb (MEDIUM)**
- Pre-freeze validace chybí (nulové ceny)
- Tracked in: `docs/audit-p2b.md`, `docs/NEXT-STEPS.md`

**A4: UX Trap (MEDIUM)**
- UI nemá frozen batch indikaci
- Tracked in: `docs/audit-p2b.md`, `docs/NEXT-STEPS.md`

---

## Pre-release (Development History)

**Note:** Tyto verze byly během migrace z Kalkulator3000 v9.x na GESTIMA.
Uchovány pro historický kontext. První produkční verze je [1.0.0] - 2026-01-24.

### [2.10.0] - 2026-01-24 (pre-release)
- P2 Fáze B: Minimal Snapshot

### [2.9.0] - 2026-01-24 (pre-release)
- P2 Fáze A: Material Hierarchy

### [2.8.0] - 2026-01-24 (pre-release)
- P2 Fáze 1: Optimistic Locking

### [2.7.0] - 2026-01-24 (pre-release)
- P2 Implementační plán

### [2.6.0] - 2026-01-24 (pre-release)
- P1: Rate Limiting

### [2.5.0] - 2026-01-23 (pre-release)
- P1: Backup Strategie

### [2.4.0] - 2026-01-23 (pre-release)
- P1: CORS Configuration

### [2.3.0] - 2026-01-23 (pre-release)
- P0: HTTPS Documentation

### [2.2.0] - 2026-01-23 (pre-release)
- P0: Role Hierarchy

### [2.1.0] - 2026-01-23 (pre-release)
- P1: Error Handling & Logging

### [2.0.0] - 2026-01-23 (pre-release)
- P0: Authentication & Authorization

### [0.1.0] - 2026-01-22 (pre-release)
- Initial development version


---

## Formát záznamů

### Types of Changes

- `Added` - nové features
- `Changed` - změny v existující funkcionalitě
- `Deprecated` - brzy odstraněné features
- `Removed` - odstraněné features
- `Fixed` - bug fixes
- `Security` - bezpečnostní změny

### Versioning

- **MAJOR** (X.0.0) - breaking changes
- **MINOR** (x.Y.0) - nové features (backwards compatible)
- **PATCH** (x.y.Z) - bug fixes (backwards compatible)
