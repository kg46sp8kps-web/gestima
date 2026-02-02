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

## 8 BLOCKING RULES

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

### 8. REUSABLE BUILDING BLOCKS (L-039)
**Principle:** 1× napsat, N× použít

**ALWAYS vytvářej:**
- Generic komponenty (DataTable, ColumnChooser, Modal, etc.)
- Composables (useResizablePanel, usePagination, etc.)
- Utility functions (formatters, validators, etc.)

**NEVER duplikuj:**
- Resize logiku (use composable)
- Column visibility (use ColumnChooser)
- List/detail pattern (use generic layout)

**Example:**
```typescript
// ✅ GOOD: Reusable composable
export function useResizablePanel(options: {
  storageKey: string
  defaultWidth?: number
  minWidth?: number
  maxWidth?: number
}) {
  // 84 LOC, works with ANY split-pane
  return { panelWidth, isDragging, startResize }
}

// ✅ GOOD: Generic component
<DataTable :data="items" :columns="cols" />
// Works with: Parts, Quotes, Operations, Materials, Orders

// ❌ BAD: Copy/paste resize logic to každý modul
// = 500 LOC duplicity, bugs v každé kopii
```

**Benefits:**
- 950 LOC infrastructure → použitelné 10× = 9500 LOC saved
- Bug fix jednou → opraveno všude
- Konzistentní UX napříč app
- Nový modul = 15 minut (not 5 hodin)

---

## 6 CRITICAL ANTI-PATTERNS

| ID | Pattern | Důsledek |
|----|---------|----------|
| L-001 | Výpočty v JS | Rozbitá logika |
| L-008 | Chybí transaction | DB corruption |
| L-015 | Validation walkaround | ADR violation |
| L-036 | Fat component >500 LOC | Nereusable |
| L-040 | Doc soubory v rootu | Bordel, nepřehlednost |
| L-041 | Zanechané session notes | Duplicitní dokumentace |

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

## DOCUMENTATION PLACEMENT RULES

### L-040: Documentation Placement (BLOCKING!)

**Rule:** Root directory obsahuje POUZE:
- README.md (project overview)
- CLAUDE.md (AI rules)
- CHANGELOG.md (version history)

**ALL ostatní docs patří do `docs/`:**

```
✅ docs/ADR/NNN-decision-name.md        # Architecture decisions
✅ docs/guides/FEATURE-GUIDE.md          # How-to guides
✅ docs/audits/YYYY-MM-DD-audit.md       # Session notes, audits
✅ docs/design/FEATURE-SPEC.md           # Design specifications
✅ scripts/script_name.sh                # Shell scripts

❌ FEATURE_SUMMARY.md                     # NIKDY v rootu!
❌ IMPLEMENTATION_CHECKLIST.md            # NIKDY v rootu!
❌ DEBUG_SOMETHING.sh                     # NIKDY v rootu!
```

**Porušení:** Violation code L-040

---

### L-041: Documentation Lifecycle (BLOCKING!)

**Rule:** Session-based implementation notes NESMÍ zůstat v rootu.

**Workflow:**
1. Implementuješ feature → píšeš notes během práce (root je OK dočasně)
2. Feature hotová → vytvoř ADR v `docs/ADR/`
3. Session notes:
   - **Historical value?** → přesuň do `docs/audits/YYYY-MM-DD-feature.md`
   - **Duplicitní?** → smaž (ADR = single source of truth)
4. NIKDY nenechávej implementation docs v rootu!

**Pattern: Session-Based Documentation Dumping (ANTI-PATTERN!)**

```
❌ BAD:
- Implementuješ feature
- Vytvoříš 3-6 summary souborů v rootu
- Feature skončí v ADR + CHANGELOG
- Summary soubory zůstávají navždy
- Repeat → bordel!

✅ GOOD:
- Implementuješ feature
- Vytvoříš temporary notes v rootu (během práce)
- Feature hotová → ADR + CHANGELOG
- Temporary notes → přesuň do docs/audits/ (nebo smaž)
- Root zůstane čistý!
```

**Porušení:** Violation code L-041

---

**Version:** 5.1 (2026-02-02)
**Lines:** 220
