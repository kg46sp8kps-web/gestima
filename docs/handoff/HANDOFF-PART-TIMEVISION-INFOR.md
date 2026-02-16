# Handoff: Part↔TimeVision FK + Infor Connector

**Datum:** 2026-02-16
**Účel:** Zkopíruj celý obsah do nového Claude Code chatu.

---

## CO JE GESTIMA

ERP systém pro CNC strojírenský podnik. Backend FastAPI + SQLAlchemy 2.0, frontend Vue 3 + Pinia + TypeScript, SQLite + WAL. Floating windows UI (ne views!). Projektu rozuměj přes `CLAUDE.md` a `CLAUDE.local.md` v root directory.

**Spuštění:** `python gestima.py dev` (backend :8000 + vite :5173)

---

## KROK 1: Přidat `part_id` FK na TimeVisionEstimation

### Proč
Dnes Part a TimeVisionEstimation nemají přímou vazbu. Spojení je přes filename (string match), což je křehké — smaž operace a vazba zmizí. Dva Parts se stejným výkresem sdílejí estimaci (nežádoucí). Potřebujeme FK pro Infor connector i pro budoucí ML pipeline.

### Co udělat

1. **Migrace** — nový sloupec:
```sql
ALTER TABLE time_vision_estimations ADD COLUMN part_id INTEGER REFERENCES parts(id) ON DELETE SET NULL;
CREATE INDEX ix_tve_part_estimation ON time_vision_estimations(part_id, estimation_type);
```

2. **Model** — `app/models/time_vision.py`:
```python
# Na TimeVisionEstimation přidej:
part_id = Column(Integer, ForeignKey("parts.id", ondelete="SET NULL"), nullable=True, index=True)
part = relationship("Part", foreign_keys=[part_id])
```

3. **Backfill** — v migraci projdi existující estimace, páruj přes filename:
```python
# Pseudo-code pro backfill:
for est in all_estimations:
    # Najdi Drawing s matching filename
    drawing = query Drawing WHERE file_path LIKE '%' + est.pdf_filename
    if drawing:
        est.part_id = drawing.part_id
```

4. **UPSERT update** — `app/routers/time_vision_router.py` endpoint `process-openai`:
   - Přijímej `part_id` v requestu (optional)
   - Hledej existující estimaci na `(part_id, estimation_type)` pokud part_id je dán
   - Fallback na `(pdf_filename, estimation_type)` pro zpětnou kompatibilitu
   - **ZACHOVEJ** logiku preservace calibration dat (actual_time_min, human_estimate_min)

5. **Nový endpoint**: `GET /api/time-vision/estimations/by-part/{part_id}`
   - Vrací estimace pro daný Part

6. **Frontend** — `frontend/src/components/modules/operations/AIEstimatePanel.vue`:
   - Posílej `part_id` v requestu na `process-openai`

7. **Pydantic schemas** — `TimeVisionResponse`, `TimeVisionListItem`:
   - Přidej `part_id: Optional[int] = None`

### EXISTUJÍCÍ UPSERT LOGIKA (NEROZBIJ!)

Soubor `app/routers/time_vision_router.py`, endpoint `/process-openai` (~řádek 490-550):
```python
# Stávající logika:
if file_record_id:
    existing = query by (file_id, estimation_type)
else:
    existing = query by (pdf_filename, estimation_type)

if existing:
    # UPDATE - zachovej kalibrační data!
    existing.ai_provider = ...
    existing.estimated_time_min = ...
    # ALE NEZAPISUJ actual_time_min a human_estimate_min (uživatel je zadal!)
    if existing.actual_time_min:
        existing.status = "verified"  # nepřepisuj na "estimated"
    elif existing.human_estimate_min:
        existing.status = "calibrated"
    else:
        existing.status = "estimated"
else:
    # INSERT nový
    estimation = TimeVisionEstimation(...)
    db.add(estimation)
```

**DŮLEŽITÉ:** Tuto logiku rozšiř o `part_id`, ale NEZAMĚNUJ pořadí — part_id má nejvyšší prioritu, pak file_id, pak filename.

---

## KROK 2: Infor Connector (architektura + mock)

### Aktuální stav
- `app/services/infor_api_client.py` — HTTP client na CloudSuite Industrial REST API (funguje, token auth)
- `app/services/infor_material_importer.py` — Import MaterialItems z Inforu (UPSERT by code, funguje)
- `app/routers/infor_router.py` — Endpointy pro material import (preview → execute, funguje)

### 3 IDO importy (zatím jen SLItems pro materiály existuje)

| IDO | Maps To | Párování | Status |
|-----|---------|----------|--------|
| **SLItems** | MaterialItem | by Item code | ✅ DONE |
| **Routing IDO** | Operation + MaterialInput | by part.article_number + seq | ❌ TODO |
| **Production IDO** | ProductionRecord | by part.article_number + order_number | ❌ TODO |

### Co udělat (Phase 1 — mock endpointy)

1. **Mock data endpoint** — `GET /api/infor/mock/routing/{article_number}`:
   - Vrací fake Infor routing data pro testování
   - Format odpovědi musí odpovídat skutečnému Infor IDO response

2. **Import Routing** — `POST /api/infor/import/routing/execute`:
   - Input: article_number + routing data
   - Najdi Part by article_number
   - UPSERT Operations by (part_id, seq)
   - Vrať created/updated/skipped counts

3. **Import Production** — `POST /api/infor/import/production/execute`:
   - Input: article_number + production records
   - Najdi Part by article_number
   - INSERT ProductionRecords (duplicity check by order_number + op_seq)

### Klíčová pravidla
- UPSERT = UPDATE existing + INSERT new (NIKDY DELETE ALL + INSERT!)
- Part MUSÍ existovat před routing/production importem
- WorkCenter matching přes stávající WorkCenter tabulku
- `actual_time_min` z production záznamu → propaguj do TimeVisionEstimation (status → verified)

---

## KLÍČOVÉ SOUBORY K PŘEČTENÍ

```
# Modely
app/models/time_vision.py          — TimeVisionEstimation (SEM přidej part_id FK)
app/models/part.py                  — Part model (article_number = párovací klíč)
app/models/operation.py             — Operation model (ai_estimation_id FK)
app/models/production_record.py     — ProductionRecord model (existuje)

# Routery
app/routers/time_vision_router.py   — UPSERT logika pro estimace (~490-550)
app/routers/technology_builder_router.py — Technology generation (3 operace)
app/routers/infor_router.py         — Stávající material import

# Services
app/services/infor_api_client.py    — HTTP client (token auth, IDO queries)
app/services/infor_material_importer.py — UPSERT vzor pro MaterialItems

# Frontend
frontend/src/components/modules/operations/AIEstimatePanel.vue — AI panel v Technologii

# ADR
docs/ADR/046-infor-connector.md     — DRAFT specifikace (přečti celý)
docs/ADR/043-timevision-technology-integration.md — TimeVision↔Technologie integrace
```

---

## EXISTUJÍCÍ MODELY (reference)

### TimeVisionEstimation (klíčové sloupce)
```
id, pdf_filename, pdf_path, file_id(FK), ai_provider, ai_model,
part_type(ROT|PRI|COMBINED), complexity, material_group_id(FK),
estimated_time_min, confidence, estimation_breakdown_json,
human_estimate_min, actual_time_min,
status(pending→extracted→estimated→calibrated→verified),
estimation_type(time_v1|features_v2), features_json, calculated_time_min
```
**CHYBÍ:** `part_id` FK — to je Krok 1!

### Part (klíčové sloupce)
```
id, part_number(8-digit, unique), article_number(Infor item, unique, nullable),
name, revision, status(active|deprecated|archived), length
```
**Relationships:** material_inputs, operations, drawings, production_records

### Operation (klíčové sloupce)
```
id, part_id(FK), seq(10,20,30...), name, type(turning|milling|cutting|qc),
work_center_id(FK), setup_time_min, operation_time_min,
ai_estimation_id(FK→TimeVisionEstimation, nullable)
```

### ProductionRecord (existuje, ověř strukturu)
```
app/models/production_record.py — přečti před implementací
```

---

## PRAVIDLA PROJEKTU (zkrácená)

1. **EDIT NOT WRITE** — Existující soubory EDITUJ, nepřepisuj Write nástrojem
2. **GREP BEFORE CODE** — Než něco napíšeš, ověř jestli to neexistuje
3. **UPSERT** — UPDATE existing + INSERT new (NIKDY DELETE ALL + INSERT)
4. **TRANSACTION** — try/except/rollback pro DB operace
5. **Field()** — Pydantic validace přes Field(), ne holé typy
6. **Migrace** — Každá změna modelu = alembic migrace
7. **Testy** — Každý nový service/router = pytest test

**Spouštění:**
```bash
python gestima.py dev    # Development (hot reload)
python gestima.py test   # Testy
```

---

## POŘADÍ IMPLEMENTACE

1. **Krok 1A:** Alembic migrace — přidej `part_id` na `time_vision_estimations`
2. **Krok 1B:** Model update — `TimeVisionEstimation.part_id` + relationship
3. **Krok 1C:** Backfill script v migraci — propoj existující estimace s Parts přes filename
4. **Krok 1D:** Router update — UPSERT preferuje part_id, nový by-part endpoint
5. **Krok 1E:** Frontend — AIEstimatePanel posílá part_id
6. **Krok 1F:** Pydantic schemas — part_id v response
7. **Krok 2A:** Mock Infor routing endpoint
8. **Krok 2B:** Routing import service + UPSERT operations
9. **Krok 2C:** Production import service + INSERT records

---

*Tento handoff obsahuje kompletní kontext. Přečti CLAUDE.md a CLAUDE.local.md pro projektová pravidla. Začni Krokem 1A (migrace).*
