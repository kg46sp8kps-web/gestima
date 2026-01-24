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

## Archivované ADRs

| ID | Název | Důvod archivace |
|----|-------|-----------------|
| 002 | Snapshot Pattern (původní návrh) | Nahrazeno ADR-012 (Minimal Snapshot) - implementována minimal verze místo full snapshot |

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
