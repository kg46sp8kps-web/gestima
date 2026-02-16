# HANDOFF: Infor Connector + Part↔TimeVision vazba

**Zkopíruj tento prompt do nového chatu jako první zprávu.**

---

## KONTEXT

Gestima je manufacturing planning systém (FastAPI + Vue 3 + SQLite). Pracujeme na napojení na ERP Infor — potřebujeme importovat reálná výrobní data pro trénink FT_v2 modelu (AI odhad výrobních časů z výkresů).

**Předchozí session vytvořila:**
- `ProductionRecord` model/service/router/frontend (kompletní CRUD)
- `ProductionHistoryPanel.vue` integrovaný jako collapsible v `OperationsRightPanel.vue`
- ADR-045 draft: `docs/ADR/046-infor-connector.md`

---

## ÚKOL (2 kroky, v tomto pořadí)

### Krok 1: Přidat `part_id` FK na TimeVisionEstimation

**Proč:** Teď je vazba Part↔TimeVision přes filename (string match). Chybí přímý FK → Part neví jestli má estimaci, smazáním operací se ztratí odkaz.

**Co udělat:**

1. **Migrace:** Přidat `part_id` (Integer, FK→parts.id, ON DELETE SET NULL, nullable, indexed) na `time_vision_estimations`. Přidat index na `(part_id, estimation_type)`.

2. **Model** (`app/models/time_vision.py`):
   - Přidat `part_id` Column + relationship `part = relationship("Part")`
   - Přidat do Pydantic Response schémat

3. **Part model** (`app/models/part.py`):
   - Přidat `time_vision_estimations` relationship (back_populates)

4. **Router** (`app/routers/time_vision_router.py`):
   - `ProcessRequest`: přidat `part_id: Optional[int] = Field(default=None)`
   - `process-openai` endpoint: UPSERT logika rozšířit — pokud `part_id` je posláno, hledat na `(part_id, estimation_type)` PŘED filename fallbackem
   - Při INSERT nastavit `part_id`
   - Nový endpoint: `GET /api/time-vision/estimations/by-part/{part_id}` → vrátí estimace pro Part

5. **Frontend** (`AIEstimatePanel.vue`):
   - `runEstimation()`: posílat `part_id` v requestu na `process-openai`
   - Přidat kontrolu: pokud Part už má estimaci (přes nový endpoint), zobrazit ji místo nabízení nového běhu

6. **Backfill migrace:** Script pro propojení existujících estimací s Parts přes filename matching (Drawing.filename ↔ TimeVisionEstimation.pdf_filename)

### Krok 2: Infor Connector specifikace

**POZOR:** Tento krok je zatím jen specifikace/architektura, NE plná implementace. Nemáme ještě přístup k Infor API — potřebujeme nejdřív definovat:

1. **Architektura** — kam půjdou soubory:
   ```
   app/services/infor/
     ├── infor_client.py        # HTTP client (placeholder, mock data)
     ├── infor_mapper.py        # IDO → Gestima mapping
     └── infor_sync_service.py  # Import orchestrace
   app/routers/infor_router.py  # API endpoints
   ```

2. **3 IDO mappingy:**
   - `SLItems` → Part (UPSERT by article_number)
   - Routing IDO → Operation (UPSERT by part_id + seq)
   - Production IDO → ProductionRecord (INSERT, source="infor")

3. **Mock import endpoint** — `POST /api/infor/sync` s mock daty pro testování flow

---

## KLÍČOVÉ SOUBORY (přečti před prací)

| Soubor | Co v něm je |
|--------|-------------|
| `app/models/time_vision.py` | TimeVisionEstimation model + schémata |
| `app/models/part.py` | Part model (article_number je párovací klíč) |
| `app/models/operation.py` | Operation model (ai_estimation_id FK) |
| `app/models/production_record.py` | ProductionRecord model (NOVÉ) |
| `app/models/work_center.py` | WorkCenter model |
| `app/routers/time_vision_router.py` | process-openai endpoint s UPSERT logikou |
| `frontend/src/components/modules/operations/AIEstimatePanel.vue` | Frontend entry point pro AI odhad |
| `docs/ADR/046-infor-connector.md` | ADR draft s kompletním plánem |
| `CLAUDE.md` | Pravidla projektu (MUSÍŠ dodržet!) |
| `CLAUDE.local.md` | Operační kontext (verze, stav) |

## TECHNICKÝ KONTEXT

- **Alembic head:** `z9a0b1c2d3e4` (production_records table)
- **Aktuální verze:** v2.0.0
- **FT model:** `ft:gpt-4o-2024-08-06:kovo-rybka:gestima-v1:D8oakyjH`
- **Dev server:** `python gestima.py dev` (backend + vite)
- **Build:** `cd frontend && npm run build` (vite OK, type-check má pre-existing chyby)
- **Seed:** `python gestima.py seed-demo` (UPSERT pattern, idempotentní)

## PRAVIDLA (z CLAUDE.md)

- **TEXT FIRST** — návrh → schválení → kód
- **EDIT NOT WRITE** — existující soubory edituj, nepřepisuj
- **GREP BEFORE CODE** — zkontroluj duplicity
- **TRANSACTION** — try/except/rollback
- **VALIDATION** — Pydantic Field()
- **Migrace:** MUSÍ být reversibilní (upgrade + downgrade)
- **Seed:** UPSERT pattern (UPDATE + INSERT, nikdy DELETE ALL + INSERT)

## EXISTUJÍCÍ TimeVision UPSERT LOGIKA (kritické — respektuj!)

Backend `process-openai` hledá existující estimaci:
1. Pokud `file_id` → hledej na `file_id + estimation_type`
2. Fallback: hledej na `pdf_filename + estimation_type`
3. Najde → UPDATE (zachovej kalibraci: actual_time_min, human_estimate_min)
4. Nenajde → INSERT

**Tvůj krok 1 přidá:**
3. Nový prioritní lookup: `part_id + estimation_type` (PŘED file_id i filename)

Frontend `AIEstimatePanel.runEstimation()`:
1. `fetchOpenAIEstimation(filename)` → najde → vrátí existující
2. Nenajde → SSE `processFileOpenAI(filename)`

**Tvůj krok 1 změní:**
1. Hledej přes `part_id` (nový endpoint) → najde → vrátí existující
2. Fallback na filename match
3. Nenajde → SSE s `part_id` v requestu
