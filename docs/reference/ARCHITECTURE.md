# GESTIMA - Architecture Overview

**Verze:** 1.4 (2026-01-29)
**Účel:** Rychlá orientace v projektu (5 minut k pochopení)

---

## Quick Start

```
FastAPI + SQLAlchemy 2.0 (async) + SQLite + Jinja2 + Alpine.js + HTMX
Backend: Python 3.9+, Frontend: Server-rendered HTML
Migrations: Alembic, Security: CSP + HSTS
```

**Hierarchie entit:**
```
MaterialGroup (Kategorie materiálů)
  └─ MaterialPriceCategory (1:N) - cenové kategorie s tiery
       └─ MaterialItem (1:N) - konkrétní polotovary s normami

Part (Díl - Lean Model, ADR-024)
  ├─ MaterialInputs (1:N) - materiálové vstupy (nezávislé)
  │    └─ Operations (M:N) - kdy se spotřebovává
  ├─ Operations (1:N) - technologické kroky
  │    ├─ Features (1:N) - konkrétní úkony s geometrií
  │    └─ MaterialInputs (M:N) - co spotřebovává
  ├─ Batches (1:N) - cenové kalkulace pro dávky
  │    └─ BatchSet (N:1) - sada zmrazených batchů (ADR-022)

WorkCenter (Pracoviště) - fyzický stroj nebo virtuální pracoviště (ADR-021)
```

---

## Directory Map

```
gestima/
├── app/
│   ├── models/              # SQLAlchemy modely
│   │   ├── part.py          # Part, Operation, Feature, Batch
│   │   ├── material_input.py # MaterialInput (ADR-024)
│   │   ├── work_center.py   # WorkCenter (ADR-021)
│   │   └── batch_set.py     # BatchSet (ADR-022)
│   ├── routers/             # API endpoints
│   │   ├── parts_router.py
│   │   ├── operations_router.py
│   │   ├── work_centers_router.py  # NEW
│   │   └── pricing_router.py       # BatchSet freeze
│   ├── services/            # Business logika
│   │   ├── price_calculator.py
│   │   ├── machining_time_estimation_service.py  (ONLY TIME SYSTEM)
│   │   └── snapshot_service.py
│   ├── templates/           # Jinja2 HTML
│   │   ├── parts/           # edit.html, list
│   │   ├── workspace.html   # Workspace modules (ADR-023)
│   │   └── admin/           # master_data.html
│   ├── static/
│   │   ├── js/
│   │   │   ├── core/        # module-registry.js, link-manager.js
│   │   │   └── modules/     # Workspace moduly (ADR-023)
│   │   └── css/
│   ├── database.py          # DB setup + AuditMixin
│   └── gestima_app.py       # FastAPI + CSP/HSTS headers
├── alembic/                 # DB migrations
├── data/                    # CSV seed data
├── tests/                   # pytest
└── docs/
    ├── patterns/            # ANTI-PATTERNS.md, DEBUG-WORKFLOW.md
    └── ADR/                 # 23 architektonických rozhodnutí
```

**Kde co najdu:**

| Hledám... | Soubor |
|-----------|--------|
| Výpočty cen | services/price_calculator.py |
| Výpočty časů | services/machining_time_estimation_service.py (ADR-040) |
| Backup/restore DB | services/backup_service.py |
| Snapshots (freeze) | services/snapshot_service.py |
| API díly | routers/parts_router.py |
| API pracoviště | routers/work_centers_router.py |
| API batch freeze | routers/pricing_router.py |
| DB modely | models/*.py |
| Workspace moduly | static/js/modules/*.js |
| Alembic migrations | alembic/versions/*.py |
| Anti-patterns | docs/patterns/ANTI-PATTERNS.md |
| Debug workflow | docs/patterns/DEBUG-WORKFLOW.md |

---

## System Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     BROWSER (User)                      │
│  Jinja2 Templates + Alpine.js + HTMX                   │
│  Workspace Modules (ADR-023)                            │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP (JSON/HTML)
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Caddy (Reverse Proxy)                      │
│              HTTPS + Rate Limiting                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI (gestima_app.py)                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Security: CSP + HSTS headers (ADR-020)          │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Auth Middleware (JWT HttpOnly Cookie)           │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Routers (API endpoints)                         │  │
│  │  - parts, operations, features, batches          │  │
│  │  - work_centers, pricing, materials              │  │
│  └──────────────────────────────────────────────────┘  │
│                     ▼                                    │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Services (Business Logic)                       │  │
│  │  - price_calculator, machining_time_estimation_service │  │
│  │  - snapshot_service                              │  │
│  └──────────────────────────────────────────────────┘  │
│                     ▼                                    │
│  ┌──────────────────────────────────────────────────┐  │
│  │  SQLAlchemy 2.0 (async ORM)                      │  │
│  │  Models: Part, Operation, Feature, Batch,        │  │
│  │          WorkCenter, BatchSet, MaterialItem      │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         SQLite + WAL mode (gestima.db)                  │
│         Alembic migrations                              │
└─────────────────────────────────────────────────────────┘
```

---

## Key Architectural Decisions

| Rozhodnutí | Důvod | ADR |
|------------|-------|-----|
| **Soft delete** | Audit trail + data recovery | ADR-001 |
| **8-digit numbering** | Scalable entity IDs (PPXXXXXX) | ADR-017 |
| **JWT + HttpOnly Cookie** | Security (XSS/CSRF protection) | ADR-005 |
| **Role Hierarchy** | Admin >= Operator >= Viewer | ADR-006 |
| **Optimistic Locking** | Conflict detection via version | ADR-008 |
| **Minimal Snapshot** | Freeze batch prices | ADR-012 |
| **WorkCenter model** | Physical + virtual machines | ADR-021 |
| **BatchSet model** | Organize frozen batches | ADR-022 |
| **Workspace modules** | Multi-panel linked views | ADR-023 |
| **MaterialInput refactor** | Lean Part + M:N material-operation | ADR-024 |
| **CSP + HSTS** | Security headers | ADR-020 |

---

## New in v1.7.0

### WorkCenter Model (ADR-021)
- Single model for physical machines and virtual workstations
- 8-digit sequential numbering (80XXXXXX)
- Replaces separate Machine model

### BatchSet Model (ADR-022)
- Groups loose batches into frozen sets
- Atomic freeze workflow
- Timestamp-based naming (35XXXXXX)

### Workspace Modules (ADR-023)
- Extracted from edit.html to separate JS files
- 4 modules: parts-list, part-material, part-operations, part-pricing
- LinkManager for cross-module communication

---

## New in v1.8.0

### MaterialInput Refactor (ADR-024)
- **Lean Part model** - Material moved to separate `material_inputs` table
- **M:N relationship** - MaterialInput ↔ Operation via `material_operation_link`
- **Part can have 1-N materials** - Supports assemblies, weldments
- **Independent lifecycle** - MaterialInput exists without operations (buy parts)
- **Revision fields** - Added `revision` (internal A-Z), `customer_revision` (displayed)
- **Status field** - Added `status` (draft/active/archived)
- **BOM-ready** - Prepared for v3.0 PLM migration
- **API endpoints** - 8 new endpoints for CRUD + link/unlink

---

## Production Checklist

### P0 - BLOCKER
| Status | Requirement |
|--------|-------------|
| ✅ | Authentication (OAuth2 + JWT HttpOnly Cookie) |
| ✅ | Authorization (RBAC: Admin/Operator/Viewer) |
| ✅ | HTTPS via Caddy reverse proxy |
| ✅ | CSP + HSTS security headers |

### P1 - KRITICKÉ
| Status | Requirement |
|--------|-------------|
| ✅ | Transaction error handling |
| ✅ | Structured logging |
| ✅ | Backup strategie (CLI commands) |
| ✅ | Alembic migrations |
| ✅ | Rate limiting (100/min API, 10/min auth) |

---

## Reference

| Dokument | Účel |
|----------|------|
| [CLAUDE.md](../CLAUDE.md) | Pravidla, workflow, anti-patterns |
| [docs/patterns/](patterns/) | ANTI-PATTERNS.md, DEBUG-WORKFLOW.md |
| [docs/ADR/](ADR/) | 23 architektonických rozhodnutí |
| [docs/VISION.md](VISION.md) | 1-year roadmap |
| [docs/STATUS.md](STATUS.md) | Aktuální stav projektu |

---

**Verze:** 1.3
**Poslední update:** 2026-01-29
