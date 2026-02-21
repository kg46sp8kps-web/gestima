# ADR-031: Module Defaults Persistence System

**Status:** Accepted
**Date:** 2026-02-02
**Deciders:** Roy + Claude
**Related:** ADR-030, ADR-013, ADR-001, ADR-008

---

## Context

Floating Windows system — uzivatele opakovaně resizuji okna po kazdém otevréní. Kazdy typ modulu (part-main, manufacturing-items, ...) ma ruzne optimalni velikosti, ale vsechny sdilely stejne defaults 800×600px. localStorage je device-specific — laptop ≠ desktop.

---

## Decision

Per-module defaults v backendu (DB), s modal promtem pri zmene velikosti.

### Backend Model

**Table:** `module_defaults`

| Sloupec | Typ | Popis |
|---------|-----|-------|
| `module_type` | str (UNIQUE) | 'part-main', 'manufacturing-items', ... |
| `default_width` | int | 200-3000px |
| `default_height` | int | 200-3000px |
| `settings` | JSON | Extensible: splitPositions, columnWidths |
| audit fields | ... | created_at, updated_at, created_by, updated_by, soft delete |

**API:** `GET/POST/PUT/DELETE /api/module-defaults/{module_type}` (UPSERT logika v POST)

### Frontend UX Flow

```
1. openWindow() → GET /api/module-defaults/part-main → otevre na 900×700
2. User resize → 1000×800
3. User zavře (X)
4. hasChanged? (tolerance 10px) → ANO → modal "Ulozit jako vychozi?"
5. Ulozit → POST /api/module-defaults → priste otevire na 1000×800
```

**Priorita:** Saved Views maji prednost pred defaults (snapshot > default).

---

## Consequences

### Vyhody
- Eliminuje opakovane resizovani (produktivita)
- Multi-device sync (DB misto localStorage)
- Audit trail (kdo zmenil, kdy)
- `settings` JSON extensible pro future: split positions, column widths, GridStack

### Trade-offs
- +1 API call pri otevreni okna (~10-20ms) — future: cache v localStorage
- Modal pri zavreni muze byt neocekavany — mitigace: pouze pri zmene >10px

### Architekturni poznamka

Pixels-based sizing (default_width: 900) bude pri ADR-030 GridStack migraci nahrazeno proporcionálními hodnotami (0.0-1.0) nebo grid cells. Pole `settings.gridDefaults` uz pro toto pripraven.

---

## Implementace (DONE)

**Backend:**
- `app/models/module_defaults.py` — model + Pydantic schemas
- `app/routers/module_defaults_router.py` — 4 CRUD endpoints
- Alembic migrace: `create_module_defaults_table.py`

**Frontend:**
- `frontend/src/types/module-defaults.ts`
- `frontend/src/api/module-defaults.ts`
- `frontend/src/components/modals/SaveModuleDefaultsModal.vue`
- `frontend/src/stores/windows.ts` — load/save defaults integrace
- `frontend/src/components/windows/FloatingWindow.vue` — tracking originalSize

---

## Related ADRs

- ADR-030: Universal Responsive Module Template (GridStack, future)
- ADR-013: localStorage UI Preferences
- ADR-001: Soft Delete Pattern
- ADR-008: Optimistic Locking
