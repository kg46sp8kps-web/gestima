# Architecture Decision Records (ADR)

Tato složka obsahuje důležitá architektonická rozhodnutí pro projekt GESTIMA.

## Co jsou ADR?

ADR dokumentují **proč** byla zvolena určitá architektonická rozhodnutí, **jaké alternativy** byly zvažovány a **jaké důsledky** mají tato rozhodnutí.

## Struktura ADR

Každý ADR obsahuje:
- **Status:** Přijato / Zamítnuto / Nahrazeno / Deprecated
- **Kontext:** Proč řešíme tento problém
- **Rozhodnutí:** Co bylo zvoleno
- **Alternativy:** Co bylo zvažováno a zamítnuto
- **Důsledky:** Dopady rozhodnutí (pozitivní i negativní)

## Seznam ADR

| ID | Název | Status | Datum |
|----|-------|--------|-------|
| 001 | Soft Delete Pattern | Přijato | 2026-01-22 |
| 003 | Integer ID vs UUID | Přijato | 2026-01-22 |
| 004 | Implementation Notes | Implementováno | 2026-01-22 |
| 005 | Authentication & Authorization | Přijato | 2026-01-23 |
| 006 | Role Hierarchy | Přijato | 2026-01-23 |
| 007 | HTTPS via Caddy | Přijato | 2026-01-23 |
| 008 | Optimistic Locking | Implementováno | 2026-01-24 |
| 011 | Material Hierarchy | Implementováno | 2026-01-24 |
| 012 | Minimal Snapshot | Implementováno | 2026-01-24 |
| 013 | LocalStorage UI Preferences | Implementováno | 2026-01-24 |
| 014 | Material Price Tiers | Implementováno | 2026-01-25 |
| 015 | Material Norm Mapping | Implementováno | 2026-01-25 |
| 016 | Material Parser Strategy | Implementováno | 2026-01-26 |
| 017 | 8-Digit Entity Numbering (v2.0) | Přijato | 2026-01-28 |
| 018 | Deployment Strategy | Přijato | 2026-01-27 |
| 019 | Material Catalog Smart Lookup | Implementováno | 2026-01-27 |
| 020 | CSP 'unsafe-eval' for Alpine.js | Přijato | 2026-01-28 |
| 021 | WorkCenter Model Design | Přijato | 2026-01-28 |
| 022 | BatchSet Model (Sady cen) | Přijato | 2026-01-28 |
| 023 | Workspace Module Architecture | Přijato (Design) | 2026-01-28 |
| 024 | Vue SPA Migration + Material Input Refactor | Implementováno | 2026-01-29 |
| 025 | Workspace Layout System | Implementováno | 2026-01-30 |
| 026 | Universal Module Pattern (Split-Pane) | Implementováno | 2026-01-30 |
| VIS-001 | Soft Delete for Future Modules | Přijato | 2026-01-25 |
| VIS-002 | Quotes Workflow & Snapshot Protection | Implementováno | 2026-01-31 |

## Archivované ADRs

| ID | Název | Důvod archivace |
|----|-------|-----------------|
| 002 | Snapshot Pattern (původní návrh) | Nahrazeno ADR-012 (Minimal Snapshot) - implementována minimal verze místo full snapshot |
| 017-v1 | 7-Digit Random Numbering | Nahrazeno ADR-017 v2.0 (8-digit) - rozšíření na 100 prefixů |

## Kdy vytvořit nový ADR?

- Zásadní změna v architektuře databáze
- Volba nové technologie nebo frameworku
- Významná změna v business logice
- Integrace s externími systémy

## Formát

```markdown
# ADR-XXX: Název rozhodnutí

## Status
[Přijato/Zamítnuto/...]

## Kontext
[Popis problému]

## Rozhodnutí
[Zvolené řešení]

## Alternativy
[Co bylo zvažováno]

## Důsledky
[Dopady]
```
