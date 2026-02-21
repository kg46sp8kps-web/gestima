# Gestima — Operační kontext pro AI

## NESMÍŠ

- Používat smazané services
- Dělat DELETE ALL + INSERT v seed scriptech (rozbije FK)
- Duplikovat sdílené datové struktury (typy, enumy, katalogy) — VŽDY definuj JEDNOU v jednom souboru a všude importuj. Při multi-agent orchestraci NEJDŘÍV vytvoř sdílený kontrakt, POTOM spouštěj agenty.
- Přidávat sem historické záznamy — tento soubor MUSÍ zůstat pod 50 řádků

## MUSÍŠ

- Pro vývoj: `python gestima.py dev` (backend --reload + vite dev, oba auto-refresh)
- Pro produkci: `npm run build` → `python gestima.py run` (bez --reload)
- Seed scripty: UPSERT pattern (UPDATE existing + INSERT new), inline data, idempotentní

## STAV

- v2.0.0 (2026-02-16)
- Fine-tuned model AKTIVNÍ: `ft:gpt-4o-2024-08-06:kovo-rybka:gestima-v1:D8oakyjH`
- ai_provider: `openai_ft` (fine-tuned) nebo `openai` (base)
- 3 časy: estimated_time_min (AI), human_estimate_min (člověk), actual_time_min (výroba)
- Status lifecycle: estimated → calibrated (human odhad) → verified (produkční čas)
- TimeVision integrace v Technologii: AI panel + ML ribbon, BEZ lockování, BEZ auto-sync
- **Technology Builder Phase 1 AKTIVNÍ** — viz sekce níže

## TECHNOLOGY BUILDER (Phase 1)

- POST /api/technology/generate — 3 operace: OP10 Řezání, OP20 Strojní (AI), OP100 QC
- Řezání: výška_řezu/posuv z cutting_conditions DB (reálné tabulky, NE AI), stroj BOMAR STG240A
- UPSERT by seq — uživatelovy ruční operace nedotčeny, auto-regen při změně materiálu

## MATERIÁLOVÝ IMPORT

- Infor item → W.Nr extraction → MaterialNorm → MaterialGroup → Shape → PriceCategory
- PriceCategory matching přes `shape` sloupec (ne keyword matching)
- Chybějící PriceCategory = ERROR (import blokován, ne tichý fallback)
- Seed data: 10 groups, 118 norms (82 metal + 6 litina + 30 plastic), 51 categories (se shape), 153 tiers, 315 cutting conditions (288+27 sawing)
- Non-metal parsing: `NON_METAL_PREFIX_HINTS` set v importer, `startswith` matching
- Litina: GG/GGG prefix → MaterialGroup 'Litina' (code 20910009), 4 PriceCategories (KR, HR, DE, casting)
- Plasty: materiálový kód = w_nr v MaterialNorm (POM-C, PA6, PEEK-GF30, PP-EL, PP-EL-S atd.)

## FILE MANAGER (ADR-044)

- Preview: `/api/files/{id}/preview` (bez auth, PDF only) | Download: `/download` (s auth)
- TimeVision PDF: vždy filename-based endpoint (pdf.js nemůže auth)
- **Infor Document Import AKTIVNÍ** — viz sekce níže
- **HYBRID stav:** TimeVision má dual identity (pdf_filename + file_id), Drawing model nemá file_id vůbec
- **CÍLOVÝ stav:** Všichni konzumenti jen file_id FK → FileRecord

## INFOR DOCUMENT IMPORT

- IDO: `SLDocumentObjects_Exts`, filter `DocumentType = 'Výkres-platný'`
- Service: `infor_document_importer.py` (list → preview → execute)
- **Matching:** word-boundary token (`[^a-zA-Z0-9]` separátory), longest match wins, exact > token
- **Paralelní download:** `asyncio.Semaphore(10)`, batch commit po 100 řádcích
- **Flow:** QueryPanel (generic IDO `/data` endpoint, limit=5000) → preview → execute
- **Storage:** `file_service.store_from_bytes()` → `parts/{article_number}/` → FileLink(part, drawing)
- Part.file_id FK updatován, PartDrawingWindow checkuje `file_id` first → `/api/files/{id}/preview`

## UI DESIGN SYSTEM v4.0 (2026-02-16)

- **Zdroj pravdy:** `frontend/template.html` (vizuální) + `design-system.css` (runtime)
- **Docs:** `docs/reference/DESIGN-SYSTEM.md` (patterns, BEZ hardcoded tokenů)
- Ghost buttons ONLY, WHITE focus ring, neutrální selected rows
- Ikony: `ICON_SIZE.*` z `@/config/design`, aliasy z `@/config/icons`

## INFOR ROUTING IMPORT (Krok 2)

- IDO: `SLJobRoutes`, default filter `Type = 'S'` (jen standardní postup, NE výrobní příkazy)
- Grupování po `DerJobItem` (article_number) → Part lookup → Operations UPSERT by seq
- **WC Mapper:** exact match + prefix fallback (KOO1→KOO→80000016), `warmup_cache()` pro batch
- **Mapping:** 19 entries v config.py (PS/PSa/PSm/PSv→SAW, KOO→KOOPERACE, viz `INFOR_WC_MAPPING`)
- **Skip pravidla:** CLO*, CADCAM, ObsDate → `_skip=True` (neimportuje se)
- **Kooperace:** KOO* → `is_coop=True`, type="coop", op_time=0, manning=100%
- **Časy:** `operation_time_min = 60/DerRunMchHrs` (ks/hod→min/ks), `manning = (Mch/Lbr)*100`
- **Batch:** preview 5000/batch, execute 2000/batch, `postWithRetry()` na 429
- **UI:** Virtual scroll (60 visible rows), Set-based selection pro 210k+ řádků
- **NEXT:** Import z VP (výrobních příkazů) — nový filtr, jiná logika

## LIST PERFORMANCE PATTERN (ADR-049) — VŽDY TAKTO

```
Backend:  skip/limit=200, { items, total }, BEZ selectinload
Store:    initialLoading + hasItems + hasMore + loaded guard (if loaded return)
Panel:    TanStack Virtual (NIKDY DataTable pro >100 řádků)
onMounted: if (!store.hasItems) await store.fetchItems()
onUnmounted: reset filtry
Spinner:  v-if="store.initialLoading" (NIKDY v-if="store.loading")
Prefetch: přidat do usePrefetch.ts
```
Vzor: `PartListPanel.vue` + `parts.ts` | ADR: `docs/ADR/049-virtualized-list-performance.md`

## TECH DEBT

- 45 Vue komponent > 300 LOC (L-036), file_service.py 855 LOC
- ~26 pre-existing padajících testů (Part fixtures po ADR-024 — opraveno z 58)
