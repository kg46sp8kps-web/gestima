# ADR-045: Infor Connector + Part↔TimeVision vazba

**Status:** DRAFT
**Date:** 2026-02-16
**Context:** FT_v2 trénink potřebuje reálná data z Inforu. Nejdřív musíme opravit vazbu Part↔TimeVisionEstimation.

---

## Problém 1: Chybí přímá vazba Part ↔ TimeVisionEstimation

### Současný stav
```
Part → Drawing → (filename match) → TimeVisionEstimation
                                           ↑
                    Operation.ai_estimation_id ─┘
```

- Vazba je přes **filename** (string match), ne FK
- Part neví přímo, jestli má estimaci
- Smazáním operací se ztratí odkaz
- Dva Parts se stejným výkresem → sdílí estimaci (nežádoucí)
- Nelze jednoduše zjistit "které Parts nemají AI odhad"

### Řešení: Přidat `part_id` FK na TimeVisionEstimation

```
Part ──── part_id FK ────→ TimeVisionEstimation
  └── operations ──→ Operation.ai_estimation_id ──→ (same estimation)
```

**Migrace:**
- `ALTER TABLE time_vision_estimations ADD COLUMN part_id INTEGER REFERENCES parts(id) ON DELETE SET NULL`
- Index na `(part_id, estimation_type)` pro rychlý lookup
- **Zpětná kompatibilita:** Backfill existujících estimací přes filename matching

**Backend změny:**
- `process-openai` endpoint: přijímá `part_id` v requestu, ukládá ho
- UPSERT logika: hledá na `(part_id, estimation_type)` místo filename
- Nový endpoint: `GET /api/time-vision/estimations/by-part/{part_id}`

**Frontend změny:**
- `AIEstimatePanel.vue`: posílá `part_id` v requestu
- Part detail: může zobrazit "má AI odhad" badge

---

## Problém 2: Infor Connector

### 3 IDO (Integration Data Objects)

| IDO | Co čteme | Kam mapujeme |
|-----|----------|--------------|
| **SLItems** | article_number, popis, materiál, váha | `Part` (update/create) |
| **Routing IDO** | operace (seq, WC, plánovaný čas), materiál polotovaru | `Operation` + `MaterialInput` |
| **Production IDO** | zakázkové číslo, dávka, operace, skutečný čas, stroj, datum | `ProductionRecord` |

### Párování
- **Klíč:** `article_number` (Part) ↔ Infor item number (`DerJobItem`)
- Part MUSÍ existovat před importem routing/production dat
- WorkCenter matching přes `InforWcMapper` (JSON mapping + prefix fallback)

### Import flow
```
1. SLItems IDO → UPSERT Parts (by article_number)           ✅ DONE
2. SLJobRoutes IDO (Type='S') → UPSERT Operations (by seq)  ✅ DONE
3. SLJobRoutes IDO (VP) → Operations z výrobních příkazů     ⏳ PENDING
4. Production IDO → ProductionRecords (actual times)         ⏳ PENDING
```

### WC Mapper (`app/services/infor_wc_mapper.py`)
- Resolution: exact match → prefix fallback (min 2 chars) → None + warning
- 19 entries in `INFOR_WC_MAPPING` (config.py default)
- `warmup_cache(db)` pre-resolves all in 1 query for batch processing
- Prefix example: `KOO1` → starts with `KOO` → 80000016 (KOOPERACE)

### Skip/Special rules (routing import)
- `CLO*`, `CADCAM` → skip (not imported)
- `ObsDate` populated → skip (obsolete operation)
- `KOO*` → kooperace (is_coop=True, type="coop", op_time=0, manning=100%)

### Architektura (actual)
```
app/services/
  ├── infor_api_client.py           # HTTP client, LoadCollection, GetIDOInfo
  ├── infor_importer_base.py        # Generic importer base class
  ├── infor_wc_mapper.py            # WC code → Gestima WC id (with cache)
  ├── infor_part_importer.py        # SLItems → Parts
  ├── infor_job_routing_importer.py # SLJobRoutes → Operations
  └── infor_production_importer.py  # SLJobRoutes → ProductionRecords (stub)

app/routers/
  ├── infor_router.py               # IDO discovery, data loading
  └── infor_import_router.py        # Preview/Execute endpoints (batch)
```

---

## Priorita implementace

1. **Part↔TimeVision vazba** (part_id FK) — malá změna, základ pro vše
2. **Infor client** — HTTP connector na IDO API
3. **SLItems import** — Parts UPSERT
4. **Routing import** — Operations UPSERT
5. **Production import** — ProductionRecords INSERT
6. **FT_v2 data export** — tréninkový dataset z importovaných dat

---

## Data model po implementaci

```
Part (article_number = párovací klíč)
├── time_vision_estimation_id FK → TimeVisionEstimation (NOVÉ - přímá vazba)
├── drawings → Drawing[]
├── operations → Operation[]
│   ├── work_center_id → WorkCenter
│   └── ai_estimation_id → TimeVisionEstimation
├── production_records → ProductionRecord[] (NOVÉ)
│   └── work_center_id → WorkCenter
└── material_inputs → MaterialInput[]
```
