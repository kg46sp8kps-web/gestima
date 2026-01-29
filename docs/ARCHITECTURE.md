# GESTIMA - Architecture Overview

**Verze:** 1.3 (2026-01-29)
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
  └─ MaterialItem (1:N) - konkrétní polotovary s cenami

Part (Díl)
  ├─ Operations (1:N) - technologické kroky
  │    └─ Features (1:N) - konkrétní úkony s geometrií
  ├─ Batches (1:N) - cenové kalkulace pro dávky
  │    └─ BatchSet (N:1) - sada zmrazených batchů (ADR-022)
  └─ MaterialItem (N:1) - vazba na polotovar

WorkCenter (Pracoviště) - fyzický stroj nebo virtuální pracoviště (ADR-021)
```

---

## Directory Map

```
gestima/
├── app/
│   ├── models/              # SQLAlchemy modely
│   │   ├── part.py          # Part, Operation, Feature, Batch
│   │   ├── work_center.py   # WorkCenter (ADR-021)
│   │   └── batch_set.py     # BatchSet (ADR-022)
│   ├── routers/             # API endpoints
│   │   ├── parts_router.py
│   │   ├── operations_router.py
│   │   ├── work_centers_router.py  # NEW
│   │   └── pricing_router.py       # BatchSet freeze
│   ├── services/            # Business logika
│   │   ├── price_calculator.py
│   │   ├── time_calculator.py
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
| Výpočty časů | services/time_calculator.py |
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
│  │  - price_calculator, time_calculator             │  │
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
