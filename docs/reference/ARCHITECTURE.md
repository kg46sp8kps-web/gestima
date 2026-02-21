# GESTIMA - Architecture Overview

**Verze:** 2.0 (2026-02-17)

---

## Stack

```
Backend:  FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2 + SQLite (WAL)
Frontend: Vue 3 + Pinia + TypeScript + Vite
Tests:    pytest (backend) + Vitest (frontend)
Deploy:   Caddy (reverse proxy, HTTPS) + systemd
```

## Entity Hierarchy

```
MaterialGroup → MaterialPriceCategory (1:N) → MaterialPriceTier (1:N)
                                             → MaterialItem (1:N) → MaterialNorm (N:1)

Part → MaterialInputs (1:N) ↔ Operations (M:N via material_operation_link)
     → Operations (1:N) → Features (1:N)
     → Batches (1:N) → BatchSet (N:1)
     → Drawings (1:N)

WorkCenter (physical + virtual machines, ADR-021)
FileRecord → FileLink (1:N, polymorphic entity_type+entity_id)
Quote → QuoteItem (1:N) → Part (N:1)
Partner (customer/supplier)
```

## Directory Map

```
app/
├── models/          # SQLAlchemy modely (AuditMixin: timestamps, soft-delete, versioning)
├── routers/         # FastAPI endpoints (/api/*)
├── services/        # Business logika
├── schemas/         # Pydantic v2 request/response
├── database.py      # DB setup, AuditMixin, safe_commit()
├── config.py        # Settings (env-based)
└── gestima_app.py   # App factory, middleware, route registration

frontend/src/
├── components/
│   ├── modules/     # Feature modules (*ListModule, *ListPanel, *DetailPanel)
│   ├── ui/          # Reusable UI primitives (Button, Modal, DataTable)
│   └── layout/      # App layout (Sidebar, WindowManager)
├── stores/          # Pinia stores (per-entity CRUD + UI state)
├── api/             # HTTP client wrappers (per-entity)
├── types/           # TypeScript interfaces
├── composables/     # Vue composables (useDebounce, useDialog, etc.)
└── config/          # Design tokens, icons, router

scripts/             # Seed data, migrations, audit tools
docs/                # ADRs, guides, reference
```

## Key Patterns

| Pattern | Where | Reference |
|---------|-------|-----------|
| Floating Windows UI | `WindowsView.vue` + `*Module.vue` | ADR-023, ADR-025 |
| Split-pane modules | `*ListModule.vue` (LEFT: list, RIGHT: detail) | CLAUDE.md |
| UPSERT seeds | `scripts/seed_*.py` (idempotent, inline data) | CLAUDE.md |
| Soft delete + versioning | `AuditMixin` in `database.py` | ADR-001, ADR-008 |
| JWT HttpOnly Cookie | `auth_router.py` | ADR-005 |
| File Manager | `FileRecord` + `FileLink` (polymorphic) | ADR-044 |
| TimeVision AI | Fine-tuned GPT-4o + feature-based calc | ADR-045 |
| Infor integration | Material import, routing import, purchase prices | ADR-032, ADR-046 |
| Technology Builder | Auto-generate operations (saw + machine + QC) | CLAUDE.local.md |

## Window Linking System

→ Presunuto do [UX-GUIDE.md](UX-GUIDE.md) sekce 2.7.

---

## Key ADRs

| ADR | Decision |
|-----|----------|
| 001 | Soft delete (deleted_at + audit trail) |
| 005 | JWT + HttpOnly Cookie auth |
| 008 | Optimistic locking (version column) |
| 021 | WorkCenter (physical + virtual) |
| 022 | BatchSet (frozen price snapshots) |
| 023 | Workspace floating windows |
| 024 | Lean Part + MaterialInput refactor |
| 044 | Centralized File Manager |
| 045 | Feature-based time calculation |
| 046 | Infor CloudSuite connector |
