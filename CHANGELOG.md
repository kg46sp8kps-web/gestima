# Changelog

Všechny významné změny v projektu GESTIMA budou dokumentovány v tomto souboru.

Formát vychází z [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
projekt dodržuje [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
