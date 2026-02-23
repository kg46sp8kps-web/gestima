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
│   ├── boot/        # BootScreen.vue
│   ├── ambient/     # CncBackground.vue
│   ├── layout/      # AppHeader, StatusBar, FabButton, ModulePicker
│   ├── workspace/   # TilesGrid.vue (binary tree → CSS grid)
│   ├── panels/      # GlassPanel, PanelHeader, ListPanel, WorkPanel
│   ├── ribbon/      # Ribbon, KpiCard, StatusBadge
│   ├── content/     # OpsTable, PricingPanel, DonutChart, DrawingPanel
│   └── ui/          # ConfirmDialog, AlertDialog, ToastContainer
├── stores/          # Pinia stores (workspace + parts + auth + ui)
├── api/             # HTTP client wrappers (per-entity)
├── types/           # TypeScript interfaces
├── composables/     # Vue composables (useDialog, useDarkMode, etc.)
└── config/          # Design tokens, router

scripts/             # Seed data, migrations, audit tools
docs/                # ADRs, guides, reference
```

## Key Patterns

| Pattern | Where | Reference |
|---------|-------|-----------|
| Tiling Workspace | `WorkspaceView.vue` + panel modules | ADR-023 |
| Module Registry | Tree-based binary layout, drag & drop panels | tiling-preview-v3.html |
| UPSERT seeds | `scripts/seed_*.py` (idempotent, inline data) | CLAUDE.md |
| Soft delete + versioning | `AuditMixin` in `database.py` | ADR-001, ADR-008 |
| JWT HttpOnly Cookie | `auth_router.py` | ADR-005 |
| File Manager | `FileRecord` + `FileLink` (polymorphic) | ADR-044 |
| TimeVision AI | Fine-tuned GPT-4o + feature-based calc | ADR-045 |
| Infor integration | Material import, routing import, purchase prices | ADR-032, ADR-046 |
| Technology Builder | Auto-generate operations (saw + machine + QC) | CLAUDE.local.md |

## Context Linking System

Panels in the tiling workspace use context groups (A/B) for linked selection.
Selecting a part in context A updates all panels in context A (e.g., parts list + work detail + operations).
Context B enables comparison mode — a second independent selection context.

---

## Key ADRs

| ADR | Decision |
|-----|----------|
| 001 | Soft delete (deleted_at + audit trail) |
| 005 | JWT + HttpOnly Cookie auth |
| 008 | Optimistic locking (version column) |
| 021 | WorkCenter (physical + virtual) |
| 022 | BatchSet (frozen price snapshots) |
| 023 | Tiling workspace (module registry + binary tree layout) |
| 024 | Lean Part + MaterialInput refactor |
| 044 | Centralized File Manager |
| 045 | Feature-based time calculation |
| 046 | Infor CloudSuite connector |
