# Backlog

Prioritizovaný seznam věcí "na později". Položky se přesouvají do [STATUS.md](STATUS.md) když na nich začneme pracovat.

**Poslední aktualizace:** 2026-01-28

---

## Vysoká priorita (příští sprint)

| Položka | Zdroj | Effort | Poznámka |
|---------|-------|--------|----------|
| Float → Decimal migration | Audit C-2 | 2h | Přesnost pro velké série |
| SQLite FK constraints | Audit C-1 | 2h | `PRAGMA foreign_keys = ON` |
| Features UI (kroky operací) | NEXT-STEPS | 4-6h | Placeholder v edit.html |
| Kooperace Operation Type | NEXT-STEPS | 2-3h | is_coop=True operace |

---

## Střední priorita (tento měsíc)

| Položka | Zdroj | Effort | Poznámka |
|---------|-------|--------|----------|
| Material Catalog Import (ADR-019) | NEXT-STEPS | 12h | Smart Lookup + 2405 items |
| Repository pattern refaktoring | Audit H-8 | 8h | Abstrakce nad DB |
| Geometry Hash pro Frozen Batch | audit-p2b A1 | 4-6h | Detekce změn po freeze |
| Pre-freeze validace (zero price) | audit-p2b A3 | 1-2h | Blokovat freeze s 0 cenou |
| Backup folder configuration | NEXT-STEPS | 30min | BACKUP_DIR do config.py |

---

## Nízká priorita (backlog)

| Položka | Zdroj | Effort | Poznámka |
|---------|-------|--------|----------|
| Export/Import user config | NEXT-STEPS | 2-3h | Čeká na metrics (>20% multi-device) |
| pip-audit security scan | Audit P2-005 | 1h | Dependency vulnerabilities |
| min-width responsive | Audit P2-004 | 2h | Mobile support |
| Console.log cleanup (zbývající) | Audit | 1h | 45 zbývajících |
| CSP nonces (nahradit unsafe-inline) | Sprint 2 | 4h | v2.0 |

---

## Budoucí moduly (v3.0+)

| Položka | Zdroj | Effort | Poznámka |
|---------|-------|--------|----------|
| Workspace UI (ADR-023) | Vision | 9-12 sprintů | Multi-panel linked views |
| Mobile terminály (Capacitor) | Vision | 4-6 sprintů | Shop floor, odvádění práce |
| Virtualizace tabulek | ADR-023 diskuze | 3-5 dní | Pro 1000+ položek |

---

## Nápady (neprioritizované)

- Dark/Light mode toggle
- Keyboard shortcuts (Ctrl+S save, etc.)
- Bulk operations na Parts list
- PDF export nabídek
- Email notifikace při změně ceny materiálu
- Integrace s dodavateli (API pro ceny)
- Multi-language support (EN/DE)

---

## Workflow

```
Nový nápad / issue z auditu
         │
         ▼
    ┌─────────┐
    │ BACKLOG │  ← Zapsat sem s prioritou
    └────┬────┘
         │
    Rozhodneme pracovat
         │
         ▼
    ┌─────────┐
    │ STATUS  │  ← Přesunout do STATUS.md
    └────┬────┘
         │
    Hotovo
         │
         ▼
    ┌───────────┐
    │ CHANGELOG │  ← Zaznamenat
    └───────────┘
```

---

## Reference

- [STATUS.md](STATUS.md) - Co děláme teď
- [VISION.md](VISION.md) - Dlouhodobá vize (rok+)
- [CHANGELOG.md](../CHANGELOG.md) - Co jsme udělali
- [CLAUDE.md](../CLAUDE.md) - Pravidla + Anti-patterns

---

**Verze:** 1.0 (2026-01-28)
