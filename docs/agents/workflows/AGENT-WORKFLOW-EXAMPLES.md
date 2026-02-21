# Agent Workflow Examples

**Version:** 2.0 (2026-02-17)
**Agent definitions:** `.claude/agents/` | **Orchestration rules:** `docs/agents/AGENT-INSTRUCTIONS.md`

---

## Workflow Decision Tree

```
User Request
     |
     v
Simple (1-2 files, one stack)?  -->  2-3 agents, parallel
     |
Complex (3+ files, BE+FE)?      -->  5-7 agents
     |
     +-- Feature/Bug fix?        -->  parallel
     +-- Schema/Migration?       -->  sequential (BE -> Auditor -> FE -> QA)
     +-- Validation change?      -->  Auditor first
```

---

## Example 1: Bug Fix (parallel, 3 agents)

**Request:** "Tlacitko Delete v parts listu nefunguje"

**CARTMAN dispatch:**
```
Backend:  SKIP (no API change)
Frontend: "Najdi a oprav delete button v PartsListModule.vue. Pravdepodobna pricina: chybejici argument v @click handleru."
QA:       "Ovcr ze delete tlacitko funguje: klik -> part odstranen, konzole bez chyb, API vrati 204."
```

**Result:** `@click="deletePart"` -> `@click="deletePart(part.id)"`, 3 testy prosly.

---

## Example 2: New Feature (parallel, full team)

**Request:** "Pridej export parts do Excelu s moznosti vybrat sloupce"

**CARTMAN dispatch (paralelne):**
```
Backend:  "Vytvor POST /api/parts/export. Accepts { part_ids: [], columns: [] }, vraci StreamingResponse
           (Excel). Service v app/services/export_service.py, schema ExportRequest. Pouzij openpyxl.
           Transakcni handling (L-008), Pydantic Field() (L-009). Napis 5 testu."

Frontend: "Vytvor ExportModal.vue (<300 LOC) s column picker (checkboxes) a export tlacitkem.
           Reusable pro libovolnou entitu. Pouzij design-system.css tokeny (--modal-*, --checkbox-*).
           Napis 6 testu."

Auditor:  "Zkontroluj export feature na L-008/L-009/L-036. Pokud novy architektonicky vzor,
           vytvor ADR. Zkontroluj bezpecnost: file injection, input validation."

QA:       "Po dokonceni backend+frontend: spust pytest + npm test:unit. Benchmark: 10/100/1000 parts."
```

**Sequential dependency:** QA spusti az po dokonceni Backend + Frontend.

---

## Example 3: DB Schema Change (sequential — povinne!)

**Request:** "Pridej pole 'priority' (1-5) do Part modelu"

**Povinne sekuencni workflow:**

```
Krok 1 — Backend:
  "Pridej priority: int = Field(default=3, ge=1, le=5) do Part modelu.
   Vytvor alembic migraci. Updatuj PartCreate/PartResponse schema.
   Napis 3 testy. CEKEJ na Auditor approval pred odeslanim vysledku."

Krok 2 — Auditor (az po Kroku 1):
  "Zkontroluj priority field na Part modelu: ADR potreba? Validace spravna?
   Migrace reverzibilni? Je default hodnota rozumna? Blokuj pokud chybi ADR."

Krok 3 — Frontend (az po Auditor approval):
  "Pridej priority field do part.ts typov. Vytvor PrioritySelect.vue komponent
   (reusable, 1-5 hvezdicky). Updatuj PartsListModule.vue (sloupec + sort).
   Napis 4 testy."

Krok 4 — QA:
  "Spust plny test suite (pytest + npm test:unit). Otestuj validaci:
   priority=0 odmitnut, priority=6 odmitnut, update 1->5 funguje."
```

**Auditor blokoval:** Chybejici ADR -> Backend vytvoril ADR-027 -> Auditor re-approved -> Frontend pokracoval.

---

## Example 4: Auditor-First (validation change request)

**Request:** "Zmen max_length batch_id z 7 na 50, protoze DEMO-001 nefunguje"

**CARTMAN dispatch — Auditor PRVNI:**
```
Auditor:  "Zkontroluj request: zmena max_length batch_id z 7 na 50 kvuli DEMO-001.
           Je to L-015 (validation walkaround)? Zkontroluj ADR-017 pro batch_id format.
           Pokud L-015 detekovan, navrhni spravny fix (oprava dat, ne validace). BLOKUJ."
```

**Auditor detekoval L-015:** DEMO-001 je neplatne seedovaci datum, ne chyba validace.

**Po rejection — spravny fix:**
```
Backend:  "Oprav seed_demo.py: odstraN DEMO-XXX polozky, nahrad platnymi batch_id
           (7 cislic, format 1XXXXXX). NEMEN max_length validaci."

QA:       "Spust pytest tests/test_seed_scripts.py. Ovcr: zadne DEMO-XXX, vsechna
           batch_id 7 cislic."
```

---

## Example 5: Performance Issue (diagnostic-first)

**Request:** "Parts list se nacita 5 sekund"

**CARTMAN dispatch — QA diagnostika prvni:**
```
QA:       "Zmer: GET /api/parts latence, pocet SQL queries (zapni echo=True),
           frontend render cas. Identifikuj bottleneck a posli report Backendovi."
```

**QA nasel:** N+1 problem, 601 queries pro 100 parts.

**Po diagnoze:**
```
Backend:  "Oprav N+1 query v parts service: pridej selectinload(Part.operations)
           a selectinload(Part.material_inputs). Zmens na 1 query. Napis performance test
           (limit: <100ms pro 100 parts)."

QA:       "Ovcr: GET /api/parts < 100ms, plny test suite prochazi."
```

**Vysledek:** 4 200ms -> 67ms (63x zrychleni).

---

## Task Prompt Template

```
"[Co udelat]. [Kde to je / jake soubory]. [Specificke pozadavky / omezeni].
 [Co napis za testy]. [Na co cekat / kdo musi schvalit pred pokracovanim]."
```

Kazdy task prompt obsahuje: akci + soubory + omezeni + testy + dependencies.
