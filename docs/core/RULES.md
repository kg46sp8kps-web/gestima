# GESTIMA Development Rules

**Toto je CORE pravidel. Čti VŽDY před každou akcí.**

---

## MODE DETECTION

### SINGLE AGENT (tento chat)
- Typo, single-line fix
- Otázka, vysvětlení
- Jednoduchá změna v 1-2 souborech
- Explicitní "rychle udělej X"

### MULTI-AGENT (ŠÉFÍK mode)
- Nová feature (víc než 1 soubor)
- Architektonická změna
- Schema/model změna
- Multi-file refactor
- Cokoliv kde je potřeba Backend + Frontend + QA

**Trigger:** "Toto je komplexní úkol. Aktivuji ŠÉFÍK mode." → viz [agents/AGENT-INSTRUCTIONS.md](../agents/AGENT-INSTRUCTIONS.md)

---

## 7 BLOCKING RULES

### 1. TEXT FIRST
Netriviální úkol → návrh → schválení → pak tools.
NEVER: Tools first, explain later.

### 2. EDIT NOT WRITE
Write přepisuje celý soubor. Edit mění jen část.
Write = ztráta kódu pokud nečtu celý soubor.

### 3. GREP BEFORE CODE
```bash
grep -r "PATTERN" app/ frontend/src/
```
Existuje podobný kód? → Použij existující, neduplikuj.

### 4. VERIFICATION BEFORE DONE
```bash
# Paste output jako důkaz:
grep -r "PATTERN" | wc -l  # = 0 matches
pytest -v                   # = X passed, 0 failed
```
BANNED: "mělo by být OK", "teď už to bude fungovat"

### 5. TRANSACTION HANDLING (L-008)
```python
try:
    db.add(entity)
    await db.commit()
except Exception:
    await db.rollback()
    raise
```

### 6. PYDANTIC VALIDATION (L-009)
```python
Field(..., gt=0)        # positive
Field(..., ge=0)        # non-negative
Field(..., max_length=200)
```

### 7. GENERIC-FIRST (L-036)
- Component < 300 LOC
- Reusable, not context-specific
- Thin wrappers over generic components

---

## 4 CRITICAL ANTI-PATTERNS

| ID | Pattern | Důsledek |
|----|---------|----------|
| L-001 | Výpočty v JS | Rozbitá logika |
| L-008 | Chybí transaction | DB corruption |
| L-015 | Validation walkaround | ADR violation |
| L-036 | Fat component >500 LOC | Nereusable |

Full list: [reference/ANTI-PATTERNS.md](../reference/ANTI-PATTERNS.md)

---

## STACK

```
Backend:  FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2
Frontend: Vue 3 + Pinia + TypeScript
DB:       SQLite + WAL
Tests:    pytest + Vitest
```

---

## QUICK COMMANDS

```bash
python gestima.py run        # Start server
python gestima.py test       # Run tests
python gestima.py seed-demo  # Reset DB + demo data
```

---

## REFERENCE

| Topic | File |
|-------|------|
| Anti-patterns | [reference/ANTI-PATTERNS.md](../reference/ANTI-PATTERNS.md) |
| Design system | [reference/DESIGN-SYSTEM.md](../reference/DESIGN-SYSTEM.md) |
| Architecture | [reference/ARCHITECTURE.md](../reference/ARCHITECTURE.md) |
| Vision | [reference/VISION.md](../reference/VISION.md) |
| Agent system | [agents/AGENT-INSTRUCTIONS.md](../agents/AGENT-INSTRUCTIONS.md) |
| Current status | [status/STATUS.md](../status/STATUS.md) |
| ADRs | [ADR/](../ADR/) |

---

**Version:** 5.0 (2026-01-31)
**Lines:** 100
