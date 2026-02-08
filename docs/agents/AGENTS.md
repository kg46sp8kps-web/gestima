# Gestima Multi-Agent System

**Single source of truth pro agent architekturu a hook pokrytí per agent.**
**Hook-enforced rules a enforcement vrstvy:** viz [docs/core/RULES.md](../core/RULES.md)

**Version:** 4.0 | **Status:** Production

---

## Architektura

```
┌───────────────────────────────────────────────┐
│  UŽIVATEL                                      │
│  zadá úkol → AI auto-detekuje režim           │
├──────────────┬────────────────────────────────┤
│ SINGLE AGENT │  ŠÉFÍK (multi-agent)           │
│ (hlavní chat)│  ├─ Backend (sonnet)           │
│              │  ├─ Frontend (sonnet)          │
│              │  ├─ QA (haiku, read-only)      │
│              │  ├─ Auditor (opus, read-only)  │
│              │  └─ DevOps (haiku)             │
├──────────────┴────────────────────────────────┤
│  HOOK ENFORCEMENT (automatické, nelze obejít)  │
│  6 vrstev — viz docs/core/RULES.md             │
└───────────────────────────────────────────────┘
```

## Agent definice

| Agent | Model | Soubor | Role |
|-------|-------|--------|------|
| ŠÉFÍK | sonnet | `.claude/agents/sefik.md` | Orchestrátor (osobnost + routing) |
| Backend | sonnet | `.claude/agents/backend.md` | FastAPI, SQLAlchemy, Pydantic |
| Frontend | sonnet | `.claude/agents/frontend.md` | Vue 3, Pinia, TypeScript |
| QA | haiku | `.claude/agents/qa.md` | pytest, Vitest, performance |
| Auditor | opus | `.claude/agents/auditor.md` | Review, ADR, security (READ-ONLY!) |
| DevOps | haiku | `.claude/agents/devops.md` | Git, build, versioning |

## Konfigurace

| Soubor | Účel |
|--------|------|
| `.claude/settings.local.json` | Hooky pro hlavní chat |
| `.claude/agents/*.md` (frontmatter) | Hooky + permissions pro subagenty |

## Jak to funguje

1. Uživatel zadá úkol → AI **automaticky** rozhodne režim (viz [CLAUDE.md](../../CLAUDE.md))
2. Single → udělá sám. ŠÉFÍK → spustí agenty přes Task tool
3. Hooky automaticky kontrolují každou operaci — viz [docs/core/RULES.md](../core/RULES.md)
4. Definition of Done — agent nemůže skončit bez splnění DoD
5. Learning Agent — po session zapíše poučení do CLAUDE.local.md

## Enforcement princip

```
Dokumentace (.md) = "měl bys"    → AI MŮŽE ignorovat
Hook (exit 2)     = "MUSÍŠ"     → AI NEMŮŽE obejít
```

Hooky jsou Python3 skripty (ne bash+grep) protože macOS nemá `jq` a BSD `grep` nemá `-P`.

## Detaily

- **Workflow + 8 blocking rules:** [CLAUDE.md](../../CLAUDE.md)
- **Hook-enforced rules + enforcement architektura:** [docs/core/RULES.md](../core/RULES.md)
- **Anti-patterns (L-001 až L-049):** [docs/reference/ANTI-PATTERNS.md](../reference/ANTI-PATTERNS.md)
- **ŠÉFÍK protokol + routing:** [AGENT-INSTRUCTIONS.md](AGENT-INSTRUCTIONS.md)
