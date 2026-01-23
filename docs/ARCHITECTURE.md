# GESTIMA - Architecture Overview

**Verze:** 1.1 (2026-01-24)
**Účel:** Rychlá orientace v projektu (5 minut k pochopení)

---

## 🎯 Quick Start

```
FastAPI + SQLAlchemy 2.0 (async) + SQLite + Jinja2 + Alpine.js + HTMX
Backend: Python 3.9+, Frontend: Server-rendered HTML
```

**Hierarchie entit:**
```
Part (Díl)
  ├─ Operations (1:N) - technologické kroky
  │    └─ Features (1:N) - konkrétní úkony s geometrií
  └─ Batches (1:N) - cenové kalkulace pro dávky
```

---

## 📁 Directory Map

```
gestima/
├── app/
│   ├── models/              # SQLAlchemy modely (Part, Operation, Feature, Batch)
│   ├── routers/             # API endpoints (parts_router.py, operations_router.py...)
│   ├── services/            # Business logika (price_calculator.py, time_calculator.py)
│   ├── templates/           # Jinja2 HTML (index.html, edit.html)
│   ├── static/              # CSS, JS (main.js, tailwind.css)
│   ├── database.py          # DB setup + AuditMixin (soft delete)
│   ├── logging_config.py    # Structured logging (JSON + console)
│   ├── rate_limiter.py      # Rate limiting (slowapi)
│   └── gestima_app.py       # FastAPI app + global error handler
├── data/                    # CSV data (materials, machines, cutting_conditions)
├── tests/                   # pytest testy
└── docs/                    # Dokumentace
```

**Kde co najdu:**

| Hledám... | Soubor |
|-----------|--------|
| Výpočty cen | services/price_calculator.py |
| Výpočty časů | services/time_calculator.py |
| Backup/restore DB | services/backup_service.py |
| API díly | routers/parts_router.py |
| API operace | routers/operations_router.py |
| API auth | routers/auth_router.py |
| DB modely | models/*.py |
| HTML šablony | templates/*.html |
| Frontend logika | static/main.js (Alpine.js) |
| Testy | tests/test_*.py |
| Error handling | logging_config.py, gestima_app.py |
| Rate limiting | rate_limiter.py |
| Auth service | services/auth_service.py |

---

## 🔄 Data Flow

### Typický request cycle
```
1. User Action (browser)
2. HTMX/Alpine.js → API call (fetch)
3. Router (routers/*.py) → validates input
4. Service (services/*.py) → business logic + calculations
5. DB (SQLAlchemy async) → CRUD operations
6. Response (JSON) → backend
7. Frontend updates (Alpine.js) → re-render
```

### Příklad: "Změna cutting_mode"
```
User clicks "HIGH mode"
  ↓
POST /api/operations/{id}/change-mode {"cutting_mode": "high"}
  ↓
operations_router.py:change_mode()
  ↓
db.commit() [with error handling]
  ↓
Response: Updated operation JSON
  ↓
Alpine.js: Update UI + recalculate features
```

---

## 🏗️ System Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     BROWSER (User)                      │
│  Jinja2 Templates + Alpine.js + HTMX + TailwindCSS     │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP (JSON/HTML)
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI (gestima_app.py)               │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Routers (API endpoints)                         │  │
│  │  - parts_router.py    - operations_router.py     │  │
│  │  - features_router.py - batches_router.py        │  │
│  │  - data_router.py     - pages_router.py          │  │
│  └──────────────────────────────────────────────────┘  │
│                     ▼                                    │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Services (Business Logic)                       │  │
│  │  - price_calculator.py                           │  │
│  │  - time_calculator.py                            │  │
│  └──────────────────────────────────────────────────┘  │
│                     ▼                                    │
│  ┌──────────────────────────────────────────────────┐  │
│  │  SQLAlchemy 2.0 (async ORM)                      │  │
│  │  Models: Part, Operation, Feature, Batch         │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         SQLite + WAL mode (gestima.db)                  │
│  Tables: parts, operations, features, batches,          │
│          materials, machines, cutting_conditions        │
└─────────────────────────────────────────────────────────┘
```

---

## 🔑 Key Architectural Decisions

| Rozhodnutí | Důvod | ADR |
|------------|-------|-----|
| **Soft delete** | Audit trail + data recovery | ADR-001 |
| **Integer IDs** | Simplicity vs UUIDs | ADR-003 |
| **JWT + HttpOnly Cookie** | Security (XSS/CSRF protection) | ADR-005 |
| **Role Hierarchy** | Admin >= Operator >= Viewer | ADR-006 |
| **HTTPS via Caddy** | TLS termination + reverse proxy | ADR-007 |
| **Async SQLAlchemy** | Performance + modern Python | N/A |
| **Server-side rendering** | SEO + simplicity | N/A |

---

## 🚀 Critical Paths (User Flows)

### 1. Vytvoření dílu
```
GET / → index.html
  ↓
User: "Nový díl"
  ↓
POST /api/parts {"part_number": "...", "material_group": "..."}
  ↓
parts_router.create_part()
  ↓
DB: INSERT into parts
  ↓
Response: Created part JSON
  ↓
UI: Redirect to /edit/{part_id}
```

### 2. Přidání operace
```
/edit/{part_id}
  ↓
User: "Přidat operaci"
  ↓
POST /api/operations {"part_id": X, "operation_type": "turning"}
  ↓
operations_router.create_operation()
  ↓
DB: INSERT into operations
  ↓
Response: New operation JSON
  ↓
UI: Add operation card to DOM
```

### 3. Výpočet ceny
```
User změnil material/rozměry/quantities
  ↓
Frontend: Shromáždí všechna data
  ↓
POST /api/calculate (nebo GET s params)
  ↓
price_calculator.py:
  - Material cost (volume * density * price)
  - Machining cost (time * hourly_rate)
  - Setup cost (setup_time * hourly_rate / quantity)
  ↓
Response: Calculated prices per batch
  ↓
UI: Update price ribbons
```

---

## 📋 Production Checklist

### P0 - BLOCKER (bez tohoto nelze nasadit)
| Status | Requirement |
|--------|-------------|
| ✅ | Authentication (OAuth2 + JWT HttpOnly Cookie) |
| ✅ | Authorization (RBAC: Admin/Operator/Viewer) |
| ✅ | Role Hierarchy (Admin >= Operator >= Viewer) |
| ✅ | HTTPS dokumentace (Caddy reverse proxy) |
| ✅ | DEBUG=False (.env.example) |

### P1 - KRITICKÉ (všechny splněny ✅)
| Status | Requirement |
|--------|-------------|
| ✅ | Transaction error handling (14 míst) |
| ✅ | Structured logging (logging_config.py) |
| ✅ | Global error handler (gestima_app.py) |
| ✅ | Backup strategie (CLI: backup, backup-list, backup-restore) |
| ✅ | Audit trail (set_audit helper) |
| ✅ | CORS (konfigurovatelný whitelist) |
| ✅ | Rate limiting (slowapi: 100/min API, 10/min auth) |

**Detaily:** [CLAUDE.md](../CLAUDE.md#production-requirements)

---

## 📚 Reference

- **Kompletní spec:** [GESTIMA_1.0_SPEC.md](GESTIMA_1.0_SPEC.md) (997 řádků, datový model + API)
- **Pravidla vývoje:** [CLAUDE.md](../CLAUDE.md) (workflow + patterns)
- **ADR:** [docs/ADR/](ADR/) (architektonická rozhodnutí)
- **UI dokumentace:** [UI_REFERENCE.md](UI_REFERENCE.md)
- **Testing:** [TESTING.md](TESTING.md)

---

**Verze:** 1.1
**Poslední update:** 2026-01-24
**Autor:** Auto-generated
