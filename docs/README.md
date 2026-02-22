# GESTIMA Documentation

## Quick Navigation

| Složka | Obsah | Kdy použít |
|--------|-------|------------|
| **[status/](status/)** | Aktuální stav, roadmap | Plánování, co je hotovo |
| **[reference/](reference/)** | Architektura, patterns | Lookup při implementaci |
| **[guides/](guides/)** | How-to průvodci | Konkrétní úkoly |
| **[ADR/](ADR/)** | Architecture Decision Records | Před schéma změnami |
| **[diagrams/](diagrams/)** | Architekturní diagramy | Vizuální přehled |

## Nejdůležitější soubory

1. **[status/STATUS.md](status/STATUS.md)** — co je hotovo, co je next
2. **[reference/ARCHITECTURE.md](reference/ARCHITECTURE.md)** — directory structure, tech stack
3. **[VISION.md](VISION.md)** — strategická vize, Gestima vs. Infor
4. **[INFOR_FIELD_MAPPING.md](INFOR_FIELD_MAPPING.md)** — IDO field mapping

## Agenti a pravidla

- **AI development rules:** root `CLAUDE.md` (vždy načten)
- **Frontend rules:** `frontend/CLAUDE.md` (auto-načten při FE práci)
- **Backend rules:** `app/CLAUDE.md` (auto-načten při BE práci)
- **Cartman orchestrátor:** `.claude/agents/cartman.md`
- **Specialist agenti:** `.claude/agents/` (frontend, backend, auditor, qa)
