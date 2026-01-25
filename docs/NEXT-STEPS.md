# Status & Next Steps

**Date:** 2026-01-25 | **GESTIMA:** 1.1.0

---

## Production Status

### P0 - BLOCKER (vše hotovo)
| Req | Status |
|-----|--------|
| Authentication (OAuth2 + JWT HttpOnly) | DONE |
| Authorization (RBAC) | DONE |
| Role Hierarchy | DONE |
| HTTPS (Caddy docs) | DONE |
| DEBUG=False | DONE |

### P1 - KRITICKÉ (vše hotovo)
| Req | Status |
|-----|--------|
| Global error handler | DONE |
| Structured logging | DONE |
| Transaction error handling | DONE |
| Backup strategie | DONE |
| Audit trail | DONE |
| CORS | DONE |
| Rate limiting | DONE |

### P2 - DŮLEŽITÉ (vše hotovo)
| Req | Status |
|-----|--------|
| Optimistic locking (ADR-008) | DONE |
| Material Hierarchy (ADR-011) | DONE |
| Batch Snapshot/Freeze (ADR-012) | DONE |
| Business validace (Pydantic) | DONE |
| Health check | DONE |
| Graceful shutdown | DONE |

**Testy:** 137/137 passed ✅

---

## Recent Updates

### ✅ Parts List with Filtering (v1.1.0 - 2026-01-25)

**Implementováno:**
- Nová stránka `/parts` - Seznam dílů s pokročilým filtrováním
- Multi-field search (ID, part_number, article_number, name)
- Column visibility selector (localStorage persistence)
- Actions: Edit, Duplicate, Delete (admin-only)
- Real-time HTMX filtering (debounce 300ms)
- API: `GET /api/parts/search`, `POST /api/parts/{id}/duplicate`
- DB: Přidán `article_number` field do Part modelu
- 10 nových testů (all passing)

**Tech:**
- HTMX + Alpine.js
- Multi-field ILIKE search (OR logic)
- Pagination support (50/page)

---

## Next Steps (prioritizované)

### 1. Business Validace - Snapshot Pre-Conditions
**Priority:** HIGH | **Effort:** 1-2h

Problém: Snapshot může zachytit nulovou cenu materiálu.

```python
# snapshot_service.py - přidat validaci
if material_item.price_per_kg <= 0:
    raise ValueError("Nelze zmrazit: materiál má nulovou cenu")
```

**TODO:**
- [ ] Validace v snapshot_service.py
- [ ] 3 testy (zero price fails, valid succeeds)

---

### 2. UI Indikace Frozen Batch
**Priority:** MEDIUM | **Effort:** 2-3h

- Badge "ZMRAZENO" na frozen batches
- Disabled inputs pro frozen
- Clone button místo edit

---

### 3. Extended Health Check
**Priority:** MEDIUM | **Effort:** 2h

- Backup folder integrity
- Disk space warning
- Recent backup check

---

## Archive

Detailní implementační plány P2: [docs/archive/P2-PHASE-B-SUMMARY.md](archive/P2-PHASE-B-SUMMARY.md)

---

**Last Updated:** 2026-01-24
