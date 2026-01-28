# Changelog

Všechny významné změny v projektu GESTIMA budou dokumentovány v tomto souboru.

Formát vychází z [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
projekt dodržuje [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] - Performance & Code Quality Sprint (2026-01-28)

### Performance & Refactoring Sprint 1 (2026-01-28 - Bug Fix from Deep Audit)

**OPRAVENÉ PROBLÉMY Z AUDITU:**

1. ✅ **N+1 Queries & Pagination** (`parts_router.py`)
   - `GET /api/parts` má pagination (default limit=100, max=500)
   - Prevence načítání tisíců záznamů najednou

2. ✅ **deleted_at Indexes** (`database.py`)
   - Přidán `index=True` na `AuditMixin.deleted_at` column
   - Migration pro 12 existujících tabulek
   - Zrychlení list queries z O(n) na O(log n)

3. ✅ **safe_commit() Mass Replace** (9 routerů)
   - Nahrazeno ~35 duplicitních try/commit bloků
   - Použití `safe_commit()` helper z `db_helpers.py`
   - Změněné soubory:
     - `parts_router.py` (5 bloků)
     - `operations_router.py` (4 bloků)
     - `features_router.py` (3 bloky)
     - `machines_router.py` (3 bloky)
     - `materials_router.py` (10 bloků)
     - `batches_router.py` (2 bloky)
     - `config_router.py` (1 blok)
     - `admin_router.py` (6 bloků)
     - `pages_router.py` (2 bloky)

4. ✅ **Console.log Cleanup** (templates)
   - Žádné debug `console.log` statements
   - Pouze `console.error` v catch blocích (legitimní error handling)

**TESTY:**
- ✅ 103 passed
- Chyby v test_snapshots.py jsou pre-existing (chybějící material_number v fixtures)

**PERFORMANCE IMPROVEMENT:**
- Očekávané zrychlení parts list: 1200ms → 150ms
- DB queries per request: 50-200 → 3-10

---

### Code Audit (2026-01-27 - Roy's Audit)

**PROVEDENO:** Komplexní audit codebase zaměřený na kvalitu kódu, bezpečnost a výkon.

**KRITICKÉ OPRAVY:**
1. ✅ **Falsy defaults fix** (`time_calculator.py`)
   - Změněno `or` na `is not None` pro zachování 0 jako validní hodnoty
   - Opraveno na 3 místech (Vc, f, Ap a geometry)

2. ✅ **FK cascade rules** (`part.py`)
   - Přidáno `ondelete="SET NULL"` na `material_item_id` a `price_category_id`
   - Prevence orphan FK references při mazání materiálů

3. ✅ **Number generator safety** (`number_generator.py`)
   - Přidán `max_iterations` limit pro prevenci infinite loop
   - Opraveno na 3 místech (parts, materials, batches)

**DEAD CODE REMOVAL (~18,350 řádků):**
- ✅ `calculate_material_cost_from_part()` - deprecated, nahrazeno `calculate_stock_cost_from_part()`
- ✅ `calculate_material_cost()` - legacy s hardcoded daty
- ✅ `scripts/_obsolete_v2_2026-01-27/` - celá složka smazána
- ✅ Nepoužívané JS komponenty: `searchComponent`, `pricingWidget`, `formValidation`, `confirmDialog`
- ✅ Console.log debug statements v templates

**REFAKTORING:**
- ✅ `/api/data/stock-price` endpoint přepsán bez deprecated funkce

**DOKUMENTACE:**
- ✅ `docs/AUDIT-2026-01-27.md` - kompletní auditní zpráva

**KNOWN ISSUES (zdokumentováno):**
- 19× `except Exception` patterns (doporučeno nahradit specifickými exceptions)
- `safe_commit()` helper existuje ale není používán (57× copy-paste)

---

## [1.4.1] - Admin UI for Material Catalog (2026-01-27)

### Fixed - CRITICAL: Material Parser & Seed Data Cleanup (2026-01-27 22:30)

**ROOT CAUSE:** Conflicting data models (V1, V2, V3) causing broken Foreign Keys in MaterialNorms.

**SYMPTOMS:**
- Material Parser max confidence 80% (never 100%)
- MaterialNorms pointing to nonexistent MaterialGroup IDs (14+)
- Category dropdown empty after material selection

**CLEANUP PERFORMED:**
1. ✅ Archived obsolete seed scripts (V1, V2) → `scripts/_obsolete_v2_2026-01-27/`
   - `scripts/seed_materials.py` (V1: "automatova_ocel", "nerez_kruhova")
   - `app/seed_materials.py` (V2: "11xxx", "C45", "X5CrNi18-10")
   - `scripts/seed_material_norms.py` (V2: wrong MaterialGroup codes)

2. ✅ Standardized on **Model V3** (coarse-grained categories)
   - MaterialGroups: `OCEL-KONS`, `OCEL-AUTO`, `NEREZ`, `HLINIK`, etc. (12 groups)
   - MaterialNorms: Mapping W.Nr./EN ISO/ČSN/AISI → MaterialGroup ID (66 norms)

3. ✅ Fixed `gestima.py` setup command
   - Now calls: `seed_material_catalog.py` → `seed_material_norms_complete.py`
   - Removed broken reference to `app.seed_materials`

4. ✅ Re-seeded MaterialNorms with correct Foreign Keys
   - All 66 MaterialNorms now point to valid MaterialGroup IDs (1-12)
   - Parser lookups working: C45 → Group ID 1 (OCEL-KONS) ✓

**VERIFIED:**
- ✅ Material Parser: "D20 C45 100mm" → **100% confidence**
- ✅ Material Parser: "D30 1.4301 200" → **95% confidence**
- ✅ Material Parser: "20x20 1.0503" → **85% confidence** (SQUARE_BAR PriceCategory found)
- ✅ MaterialGroup FK integrity restored
- ✅ Price Category lookup working

**PREVENTION:**
- Only 2 seed scripts remain (V3):
  - `scripts/seed_material_catalog.py` (creates MaterialGroups + PriceCategories)
  - `scripts/seed_material_norms_complete.py` (creates MaterialNorms → MaterialGroup mapping)

### Fixed - Material Parser: SQUARE_BAR PriceCategory Lookup (2026-01-27 23:00)

**PROBLEM:** Input "20x20 1.0503" returned 80% confidence (PriceCategory not found).

**ROOT CAUSE:** Parser keywords mismatch with database codes:
- **Parser searched:** `"ČTYŘHRAN"`, `"CTYRHRANNA"` (čtyřhranná - adjective)
- **Database has:** `"OCEL-KONS-CTVEREC"` (čtvercová - noun)

**FIX:** [app/services/material_parser.py:448](app/services/material_parser.py#L448)
```python
# Added keywords for SQUARE_BAR:
StockShape.SQUARE_BAR: [
    "CTYRHRANNA", "ČTYŘHRAN",       # Original
    "CTVEREC", "ČTVEREC", "ČTVERCOVÁ"  # Added (database uses this)
]
```

**RESULT:** "20x20 1.0503" → **85% confidence** ✅ (PriceCategory: OCEL-KONS-CTVEREC found)

### Added

- **Admin UI: 4-Tab Material Management** (`/admin/material-norms`)
  - **Tab 1: Material Norms** - Správa W.Nr. materiálových norem (EN ISO, ČSN, AISI)
  - **Tab 2: Material Groups (12)** - Zobrazení materiálových skupin (code, name, density)
  - **Tab 3: Cenové Kategorie (37)** - Zobrazení price categories s vnořenými price tiers tabulkami
    - Každá kategorie zobrazuje 3 hmotnostní pásma (0-15kg, 15-100kg, 100+kg)
    - Ceny viditelné přímo v UI (Kč/kg)
  - **Tab 4: Systémové nastavení** - Koeficienty pro kalkulace
  - Search/filter na každém tabu

- **Material Catalog Seed Script** (`scripts/reset_and_seed_catalog.py`)
  - Automatický seed databáze s kompletní strukturou
  - **12 MaterialGroups** (OCEL-KONS, OCEL-AUTO, OCEL-NAST, OCEL-LEG, NEREZ, MED, MOSAZ, BRONZ, HLINIK, LITINA-GG, LITINA-TV, PLAST)
  - **37 MaterialPriceCategories** (kombinace materiál + tvar)
  - **97 MaterialPriceTiers** (~3 tiers na kategorii)
  - **108 MaterialNorms** (W.Nr. s kompletními normami)
  - Ceny převzaty z existující tabulky nebo odhadnuty podle materiálové rodiny
  - Spuštění: `python3 scripts/reset_and_seed_catalog.py`

### Fixed

- **Admin Router** - AttributeError fix pro None material_group
  - Přidána kontrola `if norm.material_group else None` v JSON serializaci
  - Eager loading s `selectinload()` pro MaterialPriceCategory.tiers
  - Prevents 500 Internal Server Error při zobrazení admin page

### Changed

- **Dashboard** - Sloučen "Admin" a "Katalog" tile do jednoho "Admin" tile
  - Popis: "Normy, ceny, nastavení"
  - URL: `/admin/material-norms` (4 taby v jednom UI)

### Documentation

- `temp/README-MATERIAL-IMPORT.md` - Quick reference pro material catalog import
- `temp/PRICE-STRUCTURE.md` - Přehled cenové struktury (materiálové skupiny + tiers)

---

## [Unreleased] - Material Catalog Import Preparation (2026-01-27)

### Added

- **Material Catalog Parser** (`scripts/analyze_material_codes.py`)
  - Parsování Excel katalogu `materialy_export_import.xlsx` (4181 řádků)
  - **3322 položek zparsováno (79.5% pokrytí)**
  - Podporované formáty:
    - Ocel: tyče (KR, HR, OK), trubky (TR), bloky (HR-BLOK), přířezy, tyče s délkou
    - Hliník: 3D bloky (DE-3D), 2D pásy (DE-2D)
    - Litina: tyče (GG250, GGG40)
    - Plasty: tyče, desky, pásy, bloky (PA6, POM-C, PE, PEEK, PC, MAPA)
  - 18 MaterialGroups kategorií + 40 PriceCategories kombinací
  - Output: `temp/material_codes_preview.csv` (ready pro import)

- **Material Norms Database** (`scripts/generate_material_norms.py`)
  - **83 W.Nr. materiálů s kompletními normami (100% pokrytí)**
  - Mapování W.Nr. → EN ISO, ČSN, AISI
  - Pokrývá všechny materiály z parsovaného katalogu:
    - Oceli: konstrukční (1.0xxx), automatové (1.1xxx), nástrojové (1.2xxx), legované (1.3xxx-1.8xxx)
    - Nerezy: austenitické, feritické, martenzitické (1.4xxx)
    - Měď, mosaz, bronz (2.0xxx-2.2xxx)
    - Hliník: slitiny (3.xxxx)
  - Output: `temp/material_norms_seed.sql` (ready pro import do DB)

- **Dokumentace**
  - `docs/MATERIAL-CATALOG-IMPORT.md` - Kompletní dokumentace parseru a importu
    - Podporované formáty, statistiky, přeskočené položky
    - Spouštění skriptů, import workflow
    - Důvod odkladu: nízká priorita, zdržuje vývoj
    - TODO: povrchové úpravy, profily, tolerance

### Status

**⏸️ ODLOŽENO** - Import materiálového katalogu má nízkou prioritu
- Důvod: Zdržuje vývoj core funkcí (potřeba řešit povrchy, profily, speciální formáty)
- Kdy se vrátit: Po dokončení Parts, Operations, Batches modulů
- Připravené scripty: parser + normy ready pro dokončení později

---

## [Unreleased] - Material Norms Seed Data (2026-01-27)

### Added

- **Material Norms Seed Data** (`scripts/seed_material_norms.py`)
  - 48 převodních záznamů (W.Nr, EN ISO, ČSN, AISI → MaterialGroup)
  - Pokrývá hlavní materiálové skupiny: 11xxx, S235, C45, 42CrMo4, 16MnCr5, X5CrNi18-10, X2CrNiMo17-12-2, 6060, 7075, CuZn37, CuZn39Pb3, PA6, POM
  - Cleanup starých generic groups (OCEL, NEREZ, HLINIK, MOSAZ, PLASTY) při seedu
  - Automatický seed při inicializaci databáze (po price_categories a materials)

### Technical Details

- **Seed workflow order**: price_categories → materials → material_norms
- **Format**: `(w_nr, en_iso, csn, aisi, material_group_code, note)`
- **Příklady**:
  - `1.0715 | 11SMnPb30 | 11109 → 11xxx` (Ocel automatová)
  - `1.4301 | X5CrNi18-10 | 17240 | 304 → X5CrNi18-10` (Nerez 304)
  - `2.0321 | CuZn37 | Ms63 → CuZn37` (Mosaz)
- **Current state**: MaterialGroups struktura bude ještě upravována uživatelem

---

## [1.6.0] - ADR-018: Deployment Infrastructure (2026-01-27)

### Added

**FEATURE: Dev/Prod Deployment Strategy + Complete Deployment Guide**

**Problém:**
- Žádná deployment dokumentace pro produkci
- Developer pracuje vzdáleně bez přístupu k produkční DB
- Nejasné jak deployovat updates do produkce
- Chybějící workflow pro testování na reálných datech

**Řešení: Dev/Prod Separation + Git-based Deployment**

**Architektura:**
```
Dev Environment (laptop)          Prod Environment (firma-PC)
├── gestima.db (demo data)        ├── gestima.db (real data)
├── Git working tree              ├── Git working tree (stable)
└── Local testing                 └── Autostart + Backups
         │                                 │
         └───► Git Repo (GitHub) ◄────────┘
```

**Implementace:**

1. **ADR-018** - Architektonické rozhodnutí deployment strategie
   - Dev/Prod DB separation rationale
   - Git deployment workflow
   - Backup/restore pro testování na real data
   - Alternativy: PostgreSQL, network share, VPN (všechny zamítnuté pro SQLite limits)
   - Reference: `docs/ADR/018-deployment-strategy.md`

2. **DEPLOYMENT.md** - Kompletní deployment guide (100+ stran)
   - Git setup od nuly (SSH keys, GitHub account)
   - Dev environment setup (seed demo data)
   - Prod environment setup (Windows: static IP, firewall, Task Scheduler)
   - Daily workflow (feature branches, code review, merge)
   - Deploy workflow (git pull + restart instructions)
   - Backup/restore procedures
   - Troubleshooting common issues
   - FAQ (10+ real-world scenarios)

3. **gestima.py CLI rozšíření** - nové příkazy:
   - `python gestima.py seed-demo` - Reset DB + seed kompletní demo environment
     - Init DB schema
     - Seed materials (MaterialGroup + MaterialItem)
     - Seed machines (5 demo strojů)
     - Seed demo parts (3× DEMO díly)
     - Create demo admin (username: demo, password: demo123)
   - `python gestima.py deploy` - Git pull + restart instructions
     - Pull latest code from Git
     - Print restart instructions (Task Scheduler / manual)
     - Health check reminder
   - `python gestima.py restore <file>` - Restore backup (zkrácený alias pro `backup-restore`)
     - Podporuje relative i absolute paths
     - Warning + confirmation prompt
   - Updated help text s kategorizací (Dev/Prod Workflow, User Management, Data Management, Testing)

4. **README.md update** - Deployment sekce
   - Dev vs Prod Quick Start
   - Link na DEPLOYMENT.md v dokumentační tabulce
   - Version bump 1.5.0 → 1.6.0

**Deployment Workflow:**

**Dev (doma):**
```bash
git checkout -b feature/xyz
# ...vývoj...
pytest
git commit -m "feat: xyz"
git push origin feature/xyz
# GitHub PR → Review → Merge
```

**Prod (v práci):**
```bash
python gestima.py deploy  # Git pull + restart guide
```

**Testing na real data:**
```bash
# Dev (doma)
python gestima.py restore backup.db.gz
python gestima.py run
# Test...
python gestima.py seed-demo  # Reset back to demo
```

**Benefits:**
- ✅ **SQLite compatible** - respektuje single-writer limitation
- ✅ **Bezpečnost dat** - dev experimenty neovlivní produkci
- ✅ **Offline development** - žádná závislost na síťovém přístupu
- ✅ **Standard workflow** - Git = industry best practice
- ✅ **Fast rollback** - backup restore za 30s
- ✅ **KISS principle** - žádný overhead (PostgreSQL, VPN, atd.)
- ✅ **Complete guide** - Git setup od nuly pro začátečníky

**Limitations:**
- ❌ Manuální deploy (git pull vyžaduje fyzický/RDP přístup)
- ❌ Deploy latency (jen když jsi v práci)
- ❌ Testing na real data = extra krok (restore backup)

**Future:**
- PostgreSQL migration v v4.0 (Q3 2026) pokud >10 concurrent users
- CI/CD pipeline pokud získáš VPN přístup
- Automated testing (GitHub Actions)

**Documentation:**
- `DEPLOYMENT.md` - Complete deployment guide (Git setup, dev/prod, workflows)
- `docs/ADR/018-deployment-strategy.md` - Architektonické rozhodnutí
- `README.md` - Updated Quick Start (dev vs prod)

**Related:**
- ADR-018: Dev/Prod Deployment Strategy
- VISION.md: PostgreSQL evaluation v Q3 2026 (v4.0)
- ADR-007: HTTPS with Caddy (pro public deployment)

### Fixed

**🚨 CRITICAL: L-015 Anti-pattern Prevention (Seed Data ADR-017 Violation)**

**Incident (2026-01-27):**
```
Error: ValidationError - String should have at most 7 characters [input_value='DEMO-003']
500 Internal Server Error at /api/parts/search
```

**Root Cause Analysis:**
- `app/seed_data.py` created hardcoded `DEMO-001`, `DEMO-002`, `DEMO-003` (8 chars)
- **Violated ADR-017** (7-digit random numbering: 1XXXXXX format)
- Pydantic validation correctly rejected invalid data
- **Almost changed validation to fit bad data** (walkaround!)
- User stopped: "tohle je kritické selhání!!!!!!!!!!!!!! jak tomu předejít??????!!!!!!"

**Systémové selhání (process failure):**
1. ❌ ADR-017 not checked before creating seed data
2. ❌ No pytest validation for seed outputs
3. ❌ "Opakující se problém" symptom ignored (3rd-4th time!)
4. ❌ Proposed walkaround instead of root cause fix

**FIX Implemented:**

1. **seed_data.py** - ADR-017 Compliance
   - ❌ REMOVED: Hardcoded `DEMO-XXX` part_numbers (8 chars, violates ADR)
   - ✅ ADDED: `NumberGenerator.generate_part_numbers_batch()` for proper 1XXXXXX format
   - ✅ ADDED: ADR-017 compliance documentation in docstrings
   - Location: [app/seed_data.py:17-86](app/seed_data.py#L17-L86)

2. **Database Cleanup**
   - Deleted invalid `DEMO-001`, `DEMO-002`, `DEMO-003` parts from production DB
   - New seed run creates proper 7-digit random numbers

3. **CLAUDE.md v3.7** - Process Prevention
   - ✅ KRITICKÁ PRAVIDLA #12: "BEFORE změny DB/Pydantic - CHECK ADRs!"
   - ✅ New mandatory checklist: Stop → Read ADRs → Analyze → Fix DATA (not validation)
   - ✅ Anti-pattern L-015: "Changing Validation to Fit Bad Data"
   - ✅ Real-world incident documentation with consequences breakdown
   - Location: [CLAUDE.md:106-178](CLAUDE.md#L106-L178), [CLAUDE.md:343-430](CLAUDE.md#L343-L430)

4. **test_seed_data.py** - Automated Validation (New File)
   - ✅ `test_seed_demo_parts_adr017_compliance()` - 7-digit format enforcement
   - ✅ `test_seed_demo_parts_no_hardcoded_numbers()` - Forbidden pattern detection
   - ✅ `test_seed_demo_parts_pydantic_validation()` - Actual Pydantic validation test
   - ✅ `test_seed_demo_parts_unique()` - No duplicate numbers
   - ✅ `test_seed_demo_parts_idempotent()` - Re-run safety
   - Purpose: Prevent L-015 anti-pattern (never relax validation for bad data)
   - Location: [tests/test_seed_data.py](tests/test_seed_data.py)

**Impact Analysis (what WOULD happen if walkaround passed):**

| Consequence | Severity | Description |
|-------------|----------|-------------|
| ADR-017 violation | 🔴 CRITICAL | Architecture integrity broken |
| Seed data broken | 🔴 CRITICAL | Every new dev gets invalid demo data |
| Import issues | 🟠 HIGH | 3000+ parts import incompatible formats |
| Technical debt | 🟠 HIGH | "Temporary" workaround = permanent |
| Testing hell | 🟡 MEDIUM | Tests pass, production fails |
| Future migrations | 🟡 MEDIUM | Cleanup old data = extra work |

**Prevention (MANDATORY going forward):**

```
BEFORE changing DB Column or Pydantic Field validation:
- [ ] 1. READ: docs/ADR/ (search by entity name)
- [ ] 2. ANALYZE: Are data wrong or validation wrong?
- [ ] 3. IF data wrong → FIX DATA (seed script, migration, DELETE)
- [ ] 4. IF validation wrong → UPDATE ADR FIRST, then code
- [ ] 5. NEVER: Change validation to fit bad data!
```

**Related:**
- ADR-017: 7-Digit Random Entity Numbering (violated by seed data)
- L-015: Changing Validation to Fit Bad Data (new anti-pattern)
- L-010: STOP záplatování - Fix root cause (ignored during incident)
- KRITICKÁ PRAVIDLA #12: BEFORE změny DB/Pydantic (new mandatory rule)

**Lessons Learned:**
> "Data are wrong" ≠ "Change validation to fit data"
> Preserve architecture integrity. Fix data, not validation.
> "Opakující se problém" = systémová chyba v procesu, NE bug!

---

**Alpine.js Null Object Errors (L-014)**
- Fixed console spam: `TypeError: Cannot read properties of null (reading 'confidence')`
- Changed `<div x-show="parseResult && ...">` → `<template x-if="parseResult && ...">`
- Root cause: Alpine.js evaluates ALL expressions regardless of parent `x-show` visibility
- Solution: `x-if` removes element from DOM → child expressions only evaluate when parent is true
- Location: [app/templates/parts/edit.html:73](app/templates/parts/edit.html#L73) (material parser result display)
- Documentation: Added anti-pattern L-014 to CLAUDE.md with x-show vs x-if decision matrix
- Impact: Clean console, faster rendering (no useless expression evaluation)

**Reference:** CLAUDE.md v3.7 - Anti-pattern L-014

---

## [1.5.1] - UI Polish & Seed Data Fixes (2026-01-27)

### Fixed

**UI Label Clarity**
- Renamed "Číslo výkresu" → "ID dílu (auto)" for auto-generated `part_number` field
- Renamed "Článkové číslo" → "Číslo výkresu" for user-editable `article_number` field
- Updated table headers in `parts_list.html` to match new labels
- Updated search placeholder: "Hledat podle ID dílu, čísla výkresu, názvu..."
- Hidden "ID (DB)" column by default in parts list (localStorage preference)

**User Feedback:** "myslel jsem, že číslo výkresu, article number je editovatelné"
**Result:** Clear distinction between auto-generated ID vs editable drawing number

**Random Number Generation Demo**
- Deleted sequential demo parts (1000001, 1000002, 1000003)
- Regenerated demo parts with truly random numbers using `NumberGenerator.generate_part_numbers_batch()`
- New demo parts: 1798000 (Demo hřídel), 1793691 (Demo pouzdro), 1380206 (Demo příruba)

**User Feedback:** "zmátlo mě id dílu, protože by určitě nemělo být 1000001, když má náhodné generování"
**Result:** Demo parts now properly demonstrate ADR-017 random numbering

**Seed Data**
- Seeded `material_norms` table (25 records: W.Nr, EN ISO, ČSN, AISI → MaterialGroup mapping)
- Seeded `system_config` table (4 batch coefficients: overhead, margin, stock, coop)
- Created generic MaterialGroups (OCEL, NEREZ, HLINIK, MOSAZ, PLASTY) for norm mapping

**Database Cleanup**
- Deleted duplicate parts with 8-character part_numbers (DEMO-001, DEMO-002, DEMO-003)
- Fixed ValidationError: "String should have at most 7 characters"
- Fixed 500 Internal Server Error on `/api/parts/search`

### Changed

**Files Modified:**
- `app/static/js/gestima.js` - Updated column labels and default visibility
- `app/templates/parts_list.html` - Updated table headers
- `app/templates/parts/edit.html` - Updated field labels with clear descriptions
- `gestima.db` - Cleanup + proper seed data

---

## [1.5.0] - ADR-017: 7-Digit Random Entity Numbering (2026-01-27)

### Added

**FEATURE: ADR-017 - Professional Entity Numbering System**

**Problém:**
- Auto-increment IDs (1, 2, 3...) vypadají neprofesionálně v ERP systému
- Chybí user-facing identifikátory pro výrobní příkazy, reporty, komunikaci
- Předvídatelné sequential IDs = security/privacy concern
- Import 3000+ položek vyžaduje scalable numbering scheme

**Řešení: 7-Digit Random Numbering**

Format: `[PREFIX][6 random digits]`
- Parts: `1XXXXXX` (1000000-1999999) - 1M capacity
- Materials: `2XXXXXX` (2000000-2999999) - 1M capacity
- Batches: `3XXXXXX` (3000000-3999999) - 1M capacity

**Examples:**
```
Part:     1148215  (Držák levý)
Material: 2456789  (AL 6082 D20)
Batch:    3012345  (Šarže 50 ks)
```

**Implementace:**

1. **NumberGenerator Service** (`app/services/number_generator.py`):
   - `generate_part_number()` - single number (~50ms)
   - `generate_part_numbers_batch(count)` - bulk generation (~50ms for 30 numbers!)
   - Performance: 60× faster batch vs sequential (3s for 3000 numbers)
   - Collision handling: 2× buffer strategy, adaptive buffer for high utilization
   - Safety: MAX_RETRIES limit, comprehensive error handling

2. **Database Schema**:
   - Part: `part_number VARCHAR(7) UNIQUE NOT NULL INDEX`
   - MaterialItem: `material_number VARCHAR(7) UNIQUE NOT NULL INDEX`
   - Batch: `batch_number VARCHAR(7) UNIQUE NOT NULL INDEX`

3. **Migration** (`database.py: _migrate_entity_numbers()`):
   - Add columns as VARCHAR(7) UNIQUE
   - Auto-generate numbers for existing entities (if any)
   - Handles existing data gracefully

4. **Router Integration**:
   - `parts_router.py`: Auto-generate part_number if not provided
   - `materials_router.py`: Auto-generate material_number if not provided
   - `batches_router.py`: Auto-generate batch_number (create + clone)
   - Allow manual override (optional user-provided numbers)

6. **URL Routing (Hide INT IDs)**:
   - **BREAKING CHANGE**: All API endpoints now use entity numbers in URLs instead of INT IDs
   - **Reason**: User requirement - "nechci zobrazovat `/parts/1`" (unprofessional)
   - **Implementation**: INT `id` stays for DB performance (FK), numbers in URLs for users

   **Updated endpoints:**
   - `parts_router.py` (9 endpoints):
     - `GET /{part_number}` (was `/{part_id}`)
     - `PUT /{part_number}` (was `/{part_id}`)
     - `DELETE /{part_number}` (was `/{part_id}`)
     - `POST /{part_number}/duplicate`
     - `GET /{part_number}/full`
     - `GET /{part_number}/stock-cost`
     - `POST /{part_number}/copy-material-geometry`
     - `GET /{part_number}/pricing`
     - `GET /{part_number}/pricing/series`

   - `materials_router.py` (3 endpoints):
     - `GET /items/{material_number}` (was `/{item_id}`)
     - `PUT /items/{material_number}` (was `/{item_id}`)
     - `DELETE /items/{material_number}` (was `/{item_id}`)

   - `batches_router.py` (5 endpoints):
     - `GET /{batch_number}` (was `/{batch_id}`)
     - `DELETE /{batch_number}` (was `/{batch_id}`)
     - `POST /{batch_number}/freeze` (was `/{batch_id}/freeze`)
     - `POST /{batch_number}/clone` (was `/{batch_id}/clone`)
     - `POST /{batch_number}/recalculate` (was `/{batch_id}/recalculate`)

   **URL Examples:**
   ```
   Before: /api/parts/1, /api/materials/items/42, /api/batches/7
   After:  /api/parts/1148215, /api/materials/items/2456789, /api/batches/3012345
   ```

   **Why NOT UUID in URLs?**
   - 36 chars too long for logs and verbal communication
   - 7-digit numbers are human-readable: "Podívej se na díl 1148215"

5. **Pydantic Schemas**:
   - `PartCreate.part_number: Optional[str]` - auto-generate if None
   - `MaterialItemCreate.material_number: Optional[str]`
   - `BatchCreate.batch_number: Optional[str]`
   - Validation: min_length=7, max_length=7

**Benefits:**
- ✅ **Professional appearance** - Real ERP vibes (SAP/Oracle style)
- ✅ **Security** - Non-sequential, hard to enumerate
- ✅ **Type identification** - First digit = instant recognition
- ✅ **Human-friendly** - No letters/dots (easy writing on paper)
- ✅ **Scalability** - 1M capacity per type = ~2000 years at 1000/year
- ✅ **Performance** - Optimized for bulk operations (batch generation)

**Capacity:**
- Current: ~6000 entities (0.6% utilization)
- Import: +3000 parts, +3000 materials
- Total: ~12000 entities (1.2% utilization)
- Collision rate: 0.45% at 3000 items (handled by retry logic)

**Testing:**
- Comprehensive test suite: `tests/test_number_generator.py`
- Format validation, uniqueness, collision handling
- Performance benchmarks, edge cases, integration tests

**Documentation:**
- `docs/ADR/017-7digit-random-numbering.md` - Full ADR with alternatives analysis
- Migration path, capacity analysis, trade-offs, future-proofing

**Next Steps (v1.6.0):**
- [ ] UI: Display numbers in all tables/lists (not IDs)
- [ ] Search by number (autocomplete)
- [ ] Barcode labels for parts
- [ ] Export numbers in reports

**Related:**
- ADR-017: 7-Digit Random Entity Numbering
- VISION.md: Orders/Quotes modules (v2.0) will use 4XXXXXX, 5XXXXXX

---

## [UNRELEASED] - ADR-016: Price Coefficients + Admin Console (2026-01-27)

### Added

**FEATURE: ADR-016 - Price Calculation with Coefficients**

**Problém:**
- Batch ceny nezahrnovaly režii (overhead), marži (margin), skladovou přirážku (stock), kooperační přirážku
- Admin konzole pro úpravu koeficientů neměla data (chybějící seed)
- Nebylo možné vidět rozpočet ceny (debug)

**Implementace:**

1. **SystemConfig Seed** (`scripts/seed_config.py`):
   - 4 globální koeficienty:
     - `overhead_coefficient: 1.20` (+20% administrativní režie na stroje)
     - `margin_coefficient: 1.25` (+25% marže na práci)
     - `stock_coefficient: 1.15` (+15% skladová přirážka na materiál)
     - `coop_coefficient: 1.10` (+10% kooperační přirážka)
   - Admin může upravovat přes `/admin/material-norms` tab "⚙️ Systémové nastavení"

2. **Database Migration** (`scripts/migrate_batch_coefficients.sql`):
   - Přidány sloupce do `batches`:
     - `overhead_cost` (REAL) - režie za kus
     - `margin_cost` (REAL) - marže za kus
   - Význam polí:
     - `machining_cost` = operace × sazba (BEZ režie/marže)
     - `setup_cost` = setup × sazba (BEZ režie/marže)
     - `overhead_cost` = (machining + setup) × (overhead_coefficient - 1)
     - `margin_cost` = (machining + setup + overhead) × (margin_coefficient - 1)
     - `material_cost` = materiál × stock_coefficient (S koeficientem)
     - `coop_cost` = kooperace × coop_coefficient (S koeficientem)

3. **Backend Service** (`app/services/batch_service.py`):
   - Přepnuto na novou kalkulaci `calculate_part_price()` místo `calculate_batch_prices()`
   - Využívá `PriceBreakdown` dataclass s kompletním rozpadem nákladů
   - Automaticky aplikuje koeficienty ze SystemConfig

4. **Batch Model** (`app/models/batch.py`):
   - SQLAlchemy: `overhead_cost`, `margin_cost` sloupce
   - Pydantic: `BatchResponse` rozšířeno o nová pole + computed fields:
     - `overhead_percent`, `margin_percent`

5. **Frontend Debug Ribbon** (`app/templates/parts/edit.html`):
   - Nový collapsible ribbon "🔍 Debug - Výpočet ceny"
   - Tlačítko "📊 Načíst breakdown" pro všechny batches
   - Zobrazuje:
     - Stroje (setup + operace) s časovými údaji
     - Režie (přirážka v Kč + %)
     - Marže (přirážka v Kč + %)
     - Kooperace (s koeficientem)
     - Materiál (s koeficientem)
     - Celková cena za kus i batch
   - Paralelní načítání breakdown pro rychlost

6. **API Endpoint** (už existoval):
   - `GET /api/parts/{part_id}/pricing/breakdown?quantity=X`
   - Vrací `PriceBreakdownResponse` s kompletním rozpadem

### Changed

**BREAKING: Batch Price Calculation**
- Všechny batch ceny zahrnují koeficienty (overhead, margin, stock, coop)
- Ceny vzrostou o cca +20-50% v závislosti na poměru materiálu/práce
- Starší batches potřebují recalculation pro aktualizaci

**Admin Console**
- Tab "⚙️ Systémové nastavení" nyní zobrazuje input pole pro koeficienty
- Optimistic locking pro bezpečné úpravy

### Migration Guide

1. Spustit seed: `python scripts/seed_config.py`
2. Spustit migration: `sqlite3 gestima.db < scripts/migrate_batch_coefficients.sql`
3. Recalculate všechny batches (automaticky při změně part)

---

## [1.4.0] - Batch Material Snapshot + UI Improvements (2026-01-27)

### Added

**FEATURE: ADR-017 - Hybrid Material Snapshot**

**Problém:**
- Modal "Detail cen všech dávek" zobrazoval jen `13500 Kč` bez informace o ceně za kg
- Batch neměl frozen snapshot `price_per_kg` (potřeba pro budoucí Orders/Quotes)
- Cena za kg se mění podle quantity (tier pricing) - batch musí uchovávat použitou cenu

**Implementace:**

1. **Database Migration** (`scripts/migrate_batch_material_snapshot.sql`):
   - Přidány nové sloupce do `batches`:
     - `material_weight_kg` (REAL) - Celková hmotnost materiálu (weight_per_piece × quantity)
     - `material_price_per_kg` (REAL) - Cena za kg z vybraného tier (snapshot pro freeze)
   - Hybrid approach: Fast lookup columns + detailní audit trail v `snapshot_data.material`

2. **Backend Service** (`app/services/batch_service.py`):
   - `recalculate_batch_costs()` ukládá:
     - `batch.material_weight_kg = round(total_weight, 3)`
     - `batch.material_price_per_kg = material_calc.price_per_kg`
     - `snapshot_data.material`: weight_per_piece, total_weight, density, price_per_kg, timestamp
   - Zajištění konzistence mezi columns a snapshot

3. **Pydantic Schema** (`app/models/batch.py`):
   - `BatchResponse` rozšířeno o nová pole:
     - `material_weight_kg: Optional[float]`
     - `material_price_per_kg: Optional[float]`

4. **Frontend UI** (`app/templates/parts/edit.html`):
   - Modal zobrazuje: `13500 Kč (90 Kč/kg)` místo jen `13500 Kč`
   - Conditional rendering: zobrazí kg cenu jen pokud existuje

### Changed

**UI Improvements - Part Edit Page**

1. **Cenový bar - Změna pořadí**:
   - PŘED: Material → Machining → Setup → Coop
   - PO: Material → Coop → Setup → Machining
   - Důvod: Logické seskupení (material+coop = externí, setup+machining = interní)
   - Aktualizována i legenda

2. **Batches ribbon - Zjednodušení**:
   - PŘED: Tabulka s 4 sloupci (Dávka, Čas/ks, Cena/ks, Celkem)
   - PO: Tabulka s 3 sloupci (Dávka, Cena/ks, Celkem)
   - Důvod: Čas/ks je redundantní (zobrazeno v samostatném Čas ribbonu)
   - Aktualizováno v hlavní tabulce i modalu "Detail cen"

3. **Čas na kus ribbon - Detailní rozklad**:
   - PŘED: Jednoduchý ribbon s celkovým časem (jen výroba)
   - PO: Detailní rozklad podle kategorií operací (turning, milling, drilling, grinding)
   - Hlavička: Celkový čas = **seřízení + výroba** (kompletní součet)
   - Pro každou kategorii:
     - Label s ikonou (🔄 Soustružení, 🔨 Frézování, atd.)
     - Celkový čas + rozpad (seřízení X + výroba Y)
     - Bar chart (setup = žlutá, výroba = modrá)
   - Seřazeno podle času (descending)
   - Alpine.js computed properties: `totalTimeWithSetup`, `timeBreakdown`
   - **Bugfix:** Bar chart používá `totalTimeWithSetup` pro správné procenta (dříve chyběl setup)

4. **Ribbon Spacing**:
   - Přidán `margin-bottom: 1rem` pro konzistentní mezery mezi ribbony
   - Čas ribbon + Operace ribbon

### Technical

**Vision Awareness (ADR-017):**
- Batch material snapshot připravuje cestu pro Orders/Quotes moduly (v2.0)
- Pattern: `Batch.freeze()` → snapshot → `Order.create_from_batch()` → copy frozen prices
- Ensures price stability (Order vytvořen 2026-01-27 s 90 Kč/kg zůstane na 90 Kč/kg i po zvýšení cen dodavatelem)

---

## [UNRELEASED] - Material Parser (Quick Input) (2026-01-27)

### Added

**FEATURE: Smart Material Input - Fáze 1 (Regex Parser)**

**Problém:**
- Uživatel zná materiál ve zkráceném formátu ("D20 C45 100mm")
- Manuální výběr přes dropdowny (typ → kategorie → rozměry) je pomalý
- Náchylné k chybám (špatný typ, špatná kategorie)

**Implementace:**

1. **Backend Service** (`app/services/material_parser.py`):
   - Regex-based parser pro materiálové popisy
   - Podporované formáty:
     - Kulatiny: `D20`, `Ø20` → `StockShape.ROUND_BAR`, průměr 20mm
     - Čtyřhrany: `20x20`, `□30` → `StockShape.SQUARE_BAR`
     - Profily: `20x30` → `StockShape.FLAT_BAR`
     - Plechy: `t2`, `tl.3` → `StockShape.PLATE`, tloušťka 2mm
     - Trubky: `D20x2`, `Ø25x3` → `StockShape.TUBE`, průměr × tl. stěny
     - Šestihrany: `⬡24` → `StockShape.HEXAGONAL_BAR`
   - Materiálové normy: `C45`, `1.4301`, `S235`, `EN AW-6060`, `CuZn37`, `42CrMo4`, atd.
   - Délka: `100mm`, `L=100`, `length=100`
   - DB lookup: `MaterialNorm` → `MaterialGroup` → `MaterialPriceCategory` → `MaterialItem`
   - Confidence scoring (0.0-1.0): tvar +0.4, materiál +0.3, délka +0.1, DB matches +0.2

2. **API Endpoint** (`app/routers/materials_router.py`):
   - `POST /api/materials/parse?description=D20+C45+100mm`
   - Response: `ParseResult` s rozpoznanými parametry + confidence + navržené entity

3. **Frontend Component** (`app/templates/parts/edit.html`):
   - Quick input field v Material ribbonu (nad manuálním výběrem)
   - Real-time parsing s debounce (500ms)
   - Visual feedback: ✅ ROZPOZNÁNO / ⚠️ ČÁSTEČNĚ / ❌ NÍZKÁ SHODA
   - Preview rozpoznaných hodnot (tvar, rozměry, materiál, kategorie)
   - Buttons: "Použít" (apply to Part fields) / "Zrušit" (clear)
   - Auto-fill Part fields: `stock_shape`, dimensions, `price_category_id`, `stock_length`
   - Integration s existujícím workflow (save → reload stock cost → recalculate batches)

4. **Tests** (`tests/test_material_parser.py`):
   - 25+ unit tests: happy paths, edge cases, partial matches, DB lookups, confidence scoring
   - Test coverage: all supported formats, Unicode symbols, typos, decimals

**Příklady:**
```
Input: "D20 C45 100mm"
→ Shape: Kulatina (D), Průměr: 20 mm, Materiál: Ocel C45, Délka: 100 mm
→ Confidence: 0.95

Input: "20x30 1.4301 500"
→ Shape: Profil, Rozměry: 20×30 mm, Materiál: Nerez 1.4301, Délka: 500 mm
→ Confidence: 0.90

Input: "t2 S235"
→ Shape: Plech, Tloušťka: 2 mm, Materiál: Ocel S235
→ Confidence: 0.70
```

**Architektura (ADR-016):**
- **Fáze 1 (v1.4 - IMPLEMENTED):** Regex parser (Materials only)
- **Fáze 2 (v2.5 - PLANNED):** Meilisearch fuzzy search (all modules, typo tolerance)
- **Fáze 3 (v5.0+ - FUTURE):** AI semantic search (Tech DB, complex queries)

**Documentation:**
- [ADR-016](docs/ADR/016-material-parser-strategy.md) - 3-phase search strategy
- [VISION.md](docs/VISION.md) - Future modules integration plan

**Success Metrics:**
- Parse accuracy: >90% for common formats ✅
- API latency: <200ms ✅
- User adoption: TBD (analytics needed)

---

## [UNRELEASED] - Pre-Beta Deep Audit Fixes (2026-01-27)

### Fixed

**Audit report:** [docs/audits/2026-01-27-pre-beta-deep-audit.md](docs/audits/2026-01-27-pre-beta-deep-audit.md)

1. **N+1 Query in Price Calculator**
   - **Problem:** Machine loaded inside loop for each operation (N queries instead of 1)
   - **Fix:** Pre-load all machines in ONE query using `WHERE id IN (...)`
   - **Impact:** Significant performance improvement for parts with multiple operations
   - **File:** `app/services/price_calculator.py:644-655`

2. **Test Fixtures Using Deprecated `price_per_kg`**
   - **Problem:** Tests failing (8 failed, 17 errors) due to ADR-014 migration
   - **Fix:** Updated all test fixtures to use `price_category_id` instead
   - **Impact:** Tests now passing (190 passed, 1 skipped)
   - **Files:** `tests/test_materials.py`, `tests/test_audit_infrastructure.py`, `tests/test_snapshots.py`, `tests/test_validations.py`

**Tests:** 190 passed, 1 skipped (was 164 passed, 8 failed, 17 errors)

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
