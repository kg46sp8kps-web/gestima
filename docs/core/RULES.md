# GESTIMA Development Rules

**Single source of truth pro hook-enforced pravidla a enforcement architekturu.**
**Workflow pravidla a 8 blocking rules:** viz [CLAUDE.md](../../CLAUDE.md) (vstupní bod)

---

## HOOK-ENFORCED RULES (automaticky vynucované)

Tyto pravidla se vynucují automaticky přes Claude Code hooks.
`exit 2` = BLOCK (operace se neprovede). WARNING = jen upozornění.

### BLOCKING (hook nedovolí uložit)

| ID | Pravidlo | Hook | Scope |
|----|----------|------|-------|
| L-008 | Transaction handling (try/except/rollback) | validate_edit.py | `app/**/*.py` |
| L-009 | Pydantic Field() validace (ne holé typy) | validate_edit.py | `app/schemas/*.py` |
| L-036 | Komponenta < 300 LOC | validate_frontend.py | `*.vue` |
| L-040 | Docs POUZE v `docs/` (ne root) | validate_docs.py | `*.md` |
| L-042 | Žádné secrets/credentials v kódu | validate_edit.py | `app/**/*.py` |
| L-043 | Žádné bare `except:` / `except...pass` | validate_edit.py | `app/**/*.py` |
| L-044 | Žádné print()/breakpoint() v produkci | validate_edit.py | `app/{services,routers,models}/*.py` |
| L-044 | Žádné console.log/debug v produkci | validate_frontend.py | `*.vue`, `*.ts` (ne testy) |
| L-049 | Žádný `any` typ v TypeScriptu | validate_frontend.py | `*.vue` `<script>`, `*.ts` |

### WARNING (hook upozorní, neblokuje)

| ID | Pravidlo | Hook |
|----|----------|------|
| L-001 | Business výpočty nepatří do routerů | validate_edit.py |
| L-007 | Audit fields (created_at/by) na modelech | validate_edit.py |
| L-015 | Oslabení validačních constraints | validate_edit.py |
| L-028 | SQLite Enum handling (String wrapper) | validate_edit.py |
| L-045 | Missing type hints na public functions | validate_edit.py |
| L-046 | TODO/FIXME/HACK tracking | validate_edit.py + validate_frontend.py |
| L-047 | Missing response_model na endpointech | validate_edit.py |
| L-048 | Missing docstring na public functions | validate_edit.py |

### PROCESS (git + Definition of Done)

| Kontrola | Hook | Kdy |
|----------|------|-----|
| Sensitive files (.env, .pem, credentials) | commit_guard.py | Před `git commit` |
| Debug kód ve staged diff | commit_guard.py | Před `git commit` |
| Commit message formát | commit_guard.py | Před `git commit` |
| CHANGELOG pro feat: commity | commit_guard.py | Před `git commit` |
| Co-Authored-By header | commit_guard.py | Před `git commit` |
| Testy pro změněné services/routers | definition_of_done.py | Před ukončením agenta |
| Migrace pro změněné modely | definition_of_done.py | Před ukončením agenta |
| Build freshness pro frontend | definition_of_done.py | Před ukončením agenta |
| response_model na nových endpointech | definition_of_done.py | Před ukončením agenta |

Full anti-pattern list: [reference/ANTI-PATTERNS.md](../reference/ANTI-PATTERNS.md)

---

## ENFORCEMENT ARCHITECTURE

### 6 vrstev (od nejnižší po nejvyšší)

```
┌─────────────────────────────────────────────────────────────┐
│  VRSTVA 6: Persistent Memory                                │
│  CLAUDE.local.md — Learning Agent zapisuje po každé session │
├─────────────────────────────────────────────────────────────┤
│  VRSTVA 5: Agent Permissions                                │
│  disallowedTools ve frontmatter (.claude/agents/*.md)       │
│  Auditor: nemá Edit, Write, Bash, Task                      │
│  QA: nemá Edit, Write, Task                                 │
├─────────────────────────────────────────────────────────────┤
│  VRSTVA 4: Context Injection                                │
│  session-context.sh → UserPromptSubmit (workflow do promptu)│
│  inject_subagent_context.py → SubagentStart (rules do agenta│
├─────────────────────────────────────────────────────────────┤
│  VRSTVA 3: Definition of Done (Stop hook)                   │
│  definition_of_done.py — kontroluje git diff:               │
│  DoD-TEST, DoD-MIGRATION, DoD-BUILD, DoD-API                │
├─────────────────────────────────────────────────────────────┤
│  VRSTVA 2: Version Control (PreToolUse Bash)                │
│  commit_guard.py — interceptuje git commit:                 │
│  sensitive files, debug code, message format, CHANGELOG      │
├─────────────────────────────────────────────────────────────┤
│  VRSTVA 1: Static Analysis (PreToolUse Edit/Write)          │
│  validate_edit.py — 5 BLOCKING + 8 WARNING (Python)         │
│  validate_frontend.py — 4 BLOCKING + 3 WARNING (Vue/TS)     │
│  validate_docs.py — 1 BLOCKING (docs placement)             │
└─────────────────────────────────────────────────────────────┘
```

### Hook soubory

```
.claude/hooks/
├── session-context.sh            UserPromptSubmit: workflow injection
├── inject_subagent_context.py    SubagentStart: rules pro subagenty
├── inject-subagent-context.sh    (wrapper)
├── validate_edit.py              PreToolUse Edit/Write: 13 Python rules
├── validate-edit.sh              (wrapper)
├── validate_frontend.py          PreToolUse Edit/Write: 11 Vue/TS rules
├── validate-frontend.sh          (wrapper)
├── validate_docs.py              PreToolUse Edit/Write: docs placement
├── validate-docs.sh              (wrapper)
├── commit_guard.py               PreToolUse Bash: git commit guard
├── commit-guard.sh               (wrapper)
├── definition_of_done.py         Stop: DoD verification
├── definition-of-done.sh         (wrapper)
└── validate-frontend-final.sh    Stop: Vue LOC final check (frontend agent)
```

### Kde se hooky spouští

| Context | Kde definováno | Kdo ovlivní |
|---------|----------------|-------------|
| **Hlavní chat** (single agent) | `.claude/settings.local.json` | PreToolUse + PostToolUse + Stop |
| **Subagenti** (multi-agent) | `.claude/agents/*.md` frontmatter | PreToolUse + Stop |
| **Všechny sessions** | SubagentStart v settings | inject_subagent_context.py |

### Pokrytí agentů

| Agent | Static Analysis | Git Guard | DoD | Permissions |
|-------|----------------|-----------|-----|-------------|
| Hlavní chat | validate-edit + frontend + docs | commit-guard | definition-of-done | N/A |
| Backend | validate-edit + docs | commit-guard | definition-of-done | Write+Edit |
| Frontend | validate-frontend + docs | commit-guard | definition-of-done + LOC | Write+Edit |
| ŠÉFÍK | ALL validators | commit-guard | definition-of-done | Full access |
| DevOps | validate-edit + docs | commit-guard | — | No Write |
| QA | — (read-only) | — | — | No Edit/Write/Task |
| Auditor | — (read-only) | — | — | No Edit/Write/Bash/Task |

### Jak hook blokuje

```
PreToolUse hook:
  Exit 0 → OK, pokračuj
  Exit 2 → BLOCK! Operace se NEPROVEDE. Stderr = chybová hláška.

Stop hook:
  stdout JSON {"decision":"block","reason":"..."} → Agent nemůže skončit
  stdout empty → OK, agent může skončit
```

---

**Version:** 7.0 (2026-02-05)
**Enforcement:** 14 hook souborů, 6 vrstev, 26 automatických kontrol
