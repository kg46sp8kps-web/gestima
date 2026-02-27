# GESTIMA Codex Rules (Active)

Tento soubor je aktivní zdroj pravdy pro AI spolupráci v tomto repozitáři.
Staré Claude instrukce jsou archivované v `claude_bak/` a nejsou aktivní.

## Komunikační kontrakt (povinný)

Pro každý netriviální úkol drž tento formát odpovědi:

1. Porozumění cíli (1-2 věty)
2. Plán řešení (konkrétní kroky)
3. Delegace rolí (BE/FE/QA/Audit)
4. Implementace + průběžné update
5. Ověření (co prošlo / neprošlo)
6. Výsledek a další krok

Jazyk komunikace: čeština.
Jazyk kódu, commit message a názvů proměnných: angličtina.

## Routing rolí

- `Backend role` pro `app/`, `tests/`, `alembic/`
- `Frontend role` pro `frontend/`
- `QA role` pro testy/build/lint
- `Auditor role` pro security, architekturu, consistency review
- `Orchestrator` používá automaticky personu `cartman-lite` (viz `ai/agents/orchestrator.md`)

Cross-stack úkol řeš v pořadí:
1. Backend
2. Frontend
3. QA
4. Auditor (u rizikových změn)

Detail rolí je v `ai/agents/`.

## Kdy je úkol triviální

Triviální je jen:
- jednovětá odpověď bez změn souborů
- jednoduchý příkaz (`date`, `ls`, jedno grep ověření)

Vše ostatní běží podle plného kontraktu.

## Povinné quality gates

Používej `scripts/ai/quality-gate.sh`:

- `bash scripts/ai/quality-gate.sh be`
- `bash scripts/ai/quality-gate.sh fe`
- `bash scripts/ai/quality-gate.sh full`
- `bash scripts/ai/docs-guard.sh`

Pro cross-stack změny používej `full`.

## Kontextová paměť mezi úkoly

Po každém netriviálním úkolu aktualizuj `docs/ai/context-ledger.md`:

- aktivní cíl
- rozhodnutí a důvody
- otevřené body
- další konkrétní krok

Bez aktualizace ledgeru se úkol nepovažuje za uzavřený.

## Zákaz konfliktu pravidel

- Nepoužívej instrukce z `claude_bak/` jako aktivní source of truth.
- Pokud je konflikt mezi starou a novou dokumentací, platí tento soubor + `app/AGENTS.md` + `frontend/AGENTS.md`.
