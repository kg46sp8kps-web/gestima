# Status & Next Steps

**Date:** 2026-01-25 | **GESTIMA:** 1.1.1

---

## Security Audit Status (2026-01-25)

**Audit report:** [docs/audits/2026-01-25-full-audit.md](audits/2026-01-25-full-audit.md)

### P0 - CRITICAL (6 issues) ✅ DONE
| Issue | CVSS | Status |
|-------|------|--------|
| SECRET_KEY validace | 9.1 | ✅ Fixed |
| DEBUG=True default | 7.5 | ✅ Fixed |
| Soft delete sync bug | Runtime | ✅ Fixed |
| Security headers chybí | 6.1 | ✅ Fixed |
| Verze nesynchronizované | - | ✅ Fixed |
| Untracked soubory | CI/CD | ✅ Fixed |

### P1 - HIGH (11 issues) 🔄 IN PROGRESS
| Issue | Status |
|-------|--------|
| Services bez error handling (7/9) | TODO |
| Operation.machine_id chybí FK | TODO |
| Pydantic Field validace (20+ fieldů) | TODO |
| XSS riziko v toast.innerHTML | TODO |
| Výpočty v JS (edit.html) | TODO |
| response_model na 5 endpointech | TODO |
| Auth na data_router endpointy | TODO |
| Chybějící Update schémata | TODO |

### P2 - MEDIUM (8 issues)
| Issue | Status |
|-------|--------|
| @db_error_handler decorator | TODO |
| Testy pro materials_router | TODO |
| Cache invalidace | TODO |
| ADR-013 (localStorage) | TODO |
| ARCHITECTURE.md update | TODO |

### P3 - LOW (9 issues)
| Issue | Status |
|-------|--------|
| Smazat deprecated funkce | TODO |
| Smazat dead code templates | TODO |
| Rate limit na misc endpointy | TODO |

---

## Production Status (Pre-Audit)

### Original P0-P2 (vše hotovo)
| Req | Status |
|-----|--------|
| Authentication (OAuth2 + JWT HttpOnly) | DONE |
| Authorization (RBAC) | DONE |
| Role Hierarchy | DONE |
| HTTPS (Caddy docs) | DONE |
| Optimistic locking (ADR-008) | DONE |
| Material Hierarchy (ADR-011) | DONE |
| Batch Snapshot/Freeze (ADR-012) | DONE |
| Health check | DONE |
| Graceful shutdown | DONE |

**Testy:** 137/137 passed ✅

---

## Recent Updates

### ✅ Parts List with Filtering (v1.1.0 - 2026-01-25)

**Implementováno:**
- Nová stránka `/parts` - Seznam dílů s pokročilým filtrováním
- Multi-field search (ID, part_number, article_number, name)
- Column visibility selector (localStorage persistence + Reset button)
- Actions: Edit, Duplicate, Delete (admin-only)
- Real-time HTMX filtering (debounce 300ms)
- API: `GET /api/parts/search`, `POST /api/parts/{id}/duplicate`
- DB: Přidán `article_number` field do Part modelu
- 10 nových testů (all passing)
- Demo data seeding system (auto-creates 3 DEMO parts)

**Tech:**
- HTMX + Alpine.js
- Multi-field ILIKE search (OR logic)
- Pagination support (50/page)
- localStorage persistence (device-specific, zero latency)

**Design Decision: localStorage > DB sync**
- Zero latency (0ms vs 150ms)
- Zero race conditions
- Simple implementation (KISS)
- Reset button pro obnovení defaults
- Future: Export/Import config (v1.2+) pokud metrics ukážou potřebu

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

### 4. Export/Import User Config (Future Enhancement)
**Priority:** LOW | **Effort:** 2-3h | **Wait for metrics**

**Kdy implementovat:**
- Pokud >20% users používá multi-device
- Pokud users žádají o config backup

**Co implementovat:**
- Export button → stáhne JSON config soubor
- Import button → nahraje config ze souboru
- Obsahuje: column visibility pro všechny seznamy
- Reset all settings button

**Alternativa:**
- DB sync s proper conflict resolution (effort 8-12h)

---

## Archive

Detailní implementační plány P2: [docs/archive/P2-PHASE-B-SUMMARY.md](archive/P2-PHASE-B-SUMMARY.md)

---

**Last Updated:** 2026-01-25
