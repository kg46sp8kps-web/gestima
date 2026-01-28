# Archiv dokumentace

Tento adresář obsahuje zastaralé nebo nahrazené dokumenty.

## Proč archiv?

Místo mazání dokumentů je přesouváme do archivu, aby byla zachována historie a kontext projektu.

## Archivované dokumenty (2026-01-28)

| Dokument | Důvod archivace |
|----------|-----------------|
| **MATERIAL-NORMS-GUIDE.md** | Konsolidováno do docs/MATERIAL-GUIDE.md |
| **MATERIAL-CATALOG-IMPORT.md** | Konsolidováno do docs/MATERIAL-GUIDE.md |
| **MATERIAL-CATALOG-QUICKREF.md** | Konsolidováno do docs/MATERIAL-GUIDE.md |

---

## Archivované dokumenty (2026-01-24)

| Dokument | Důvod archivace |
|----------|-----------------|
| **FUTURE_STEPS.md** | Zastaralý - mluví o neexistujících bugech (BUG-001 až BUG-007), Kalkulator3000, Excel databázi, batch_optimizer.py - nic z toho není v aktuálním systému Gestima v1.0 |
| **ROADMAP.md** | Zastaralý - mluví o verzi v9.1 → 10.0, Guesstimator - nesouhlasí s aktuálním stavem (v1.0, SQLite, Gestima) |
| **ADR-002-snapshot-pattern.md** | Nahrazeno ADR-012 (Minimal Snapshot) - původní návrh nebyl implementován, místo full snapshot byla zvolena minimal varianta |

## Starší archivované dokumenty (před 2026-01-23)

- ARCHITECTURE.md, DB_ARCHITECTURE.md - nahrazeny aktuálními verzemi v docs/
- CLAUDE_ORIG.md - původní verze CLAUDE.md
- COMMANDS.md - nahrazeno README.md
- FEATURE_STOCK_PRICE.md - implementováno
- FILE_GUIDE.md, SETUP_COMPLETE.md, STATUS.md - nahrazeny CLAUDE.md
- IMPLEMENTATION_SUMMARY.md, SESSION_SUMMARY.md - historické záznamy
- KONTEXT.md, START_PROMPT.md - startup dokumenty
- LESSONS.md - integrováno do CLAUDE.md (anti-patterns)
- QUICK_START.md - nahrazeno docs/ARCHITECTURE.md
- UI_v1.0_CHANGELOG.md - changelog pro UI, nahrazeno CHANGELOG.md
- lofas.md - prázdný soubor

---

**Pravidlo:** Pokud potřebuješ historický kontext, dokumenty jsou zde. Pro aktuální práci vždy používej soubory v `docs/` nebo root složce.
