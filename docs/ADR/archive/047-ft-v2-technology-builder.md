# ADR-047: Fine-Tuning v2 — Kompletní technologický postup z výkresu

**Status:** WAITING (data uploaded, čeká na kredit ~$130)
**Date:** 2026-02-20
**Decision:** FT v2 model se naučí z výkresu generovat kompletní technologický postup

---

## Kontext

FT v1 (`gestima-v1`, 55 vzorků, loss 0.037) odhaduje **jeden celkový čas** z výkresu.
To nestačí — potřebujeme kompletní technologický postup: operace, stroje, časy, manning, setup.

## Rozhodnutí

Model dostane **pouze výkres** (při inferenci) a outputuje **kompletní technologický postup** včetně:
- Materiál (čtený z rohového razítka výkresu, v jakémkoliv formátu — W.Nr, ČSN, EN, AISI)
- Polotovar (shape, rozměry)
- Stroje s kategoriemi (SAW/LATHE/MILL/DRILL/MANUAL/QC)
- Celkový strojní čas per kategorie stroje (min/ks) — zahrnuje řez, přejezdy, výměny nástrojů, upínání kusu
- Celkový seřizovací čas per kategorie stroje
- Manning coefficient (%) per kategorie
- Počet operací (upnutí) per kategorie

Ground truth pochází z **VP (production_records)** — reálná výrobní data z Infor.

---

## Dataset v2 — Přesná specifikace (2026-02-20)

### Složení datasetu

Dataset se skládá ze **2 vrstev** — base + extra díly pro pokrytí větších rozměrů:

| Vrstva | Popis | Dílů | Filtr |
|--------|-------|------|-------|
| **BASE** | Malé díly, přísný filtr | 476 | Preciz Cut + CV ≤ 0.5 |
| **EXTRA LATHE** | Soustružené D>40mm | 116 | VP≥2, manning≥40%, ratio≤5 |
| **EXTRA MILL** | Frézované průřez>1000mm² | 165 | VP≥2, manning≥60%, ratio≤5 |
| **Overlap** | Díly v obou extra | -62 | |
| **CELKEM** | | **694** | |

### BASE vrstva (476 dílů) — Preciz Cut + CV combined

**Vstupní podmínky:**
- `parts.file_id IS NOT NULL` (má PDF výkres)
- `parts.article_number NOT LIKE 'DRE%'`
- `parts.deleted_at IS NULL`
- Minimálně **3 VP** (výrobní příkazy) s `actual_time_min > 0`
- Musí mít SAW operaci (ne `only_saw`)
- Musí mít materiál (extractable W.Nr z material_items.code)
- Musí mít PDF soubor na disku
- `total_prod_time` (bez QC) mezi 0.1 a 120 min

**Preciz Cut filtr:**
```
LATHE: manning ≥ 50% AND manning ≤ 100% AND norm_ratio ≤ 5.0
MILL:  manning ≥ 70% AND manning ≤ 100% AND norm_ratio ≤ 5.0
```

**CV combined filtr (pouze na LATHE a MILL kategorie):**
```
LATHE: time_cv ≤ 0.5 AND manning_cv ≤ 0.5
MILL:  time_cv ≤ 0.5 AND manning_cv ≤ 0.5
SAW/QC/DRILL/MANUAL: CV se NEKONTROLUJE (legitimně vysoká variabilita)
```

### EXTRA LATHE vrstva (116 dílů) — velké průměry

**Účel:** Pokrytí dílů D>40mm, které v BASE chybí (87% BASE je pod D40).

**Filtr:**
```
- stock_diameter > 40 mm
- VP ≥ 2
- Manning (LATHE+MILL) ≥ 40%
- Norm ratio ≤ 5.0
- NOT already in BASE dataset
- Má SAW + má LATHE stroj
- Má PDF, materiál, není DRE*
```

**Zdůvodnění manning ≥ 40%:**
Manning pod 40% má norm ratio medián 2.76× (zkreslená data).
Při 40% je norm ratio medián 1.12× — blízko realitě.

### EXTRA MILL vrstva (165 dílů) — velké průřezy

**Účel:** Pokrytí frézovaných dílů s průřezem >1000mm², které v BASE chybí
(BASE medián průřezu = 600mm², P90 = 2250mm²).

**Filtr:**
```
- cross_section > 1000 mm² (W×H pro flat/plate/square, π×(D/2)² pro round)
- VP ≥ 2
- Manning (MILL) ≥ 60%
- Norm ratio ≤ 5.0
- NOT already in BASE dataset
- Má SAW + má MILL stroj
- Má PDF, materiál, není DRE*
```

**Zdůvodnění manning ≥ 60%:**
Data ukazují sweet spot při 60-70% — norm ratio medián 1.30×, odchylka od 1.0 = 0.39.
Pod 60% kvalita dat prudce klesá. Nad 70% se nezlepšuje ale ztrácíme díly.

| Manning bracket | Dílů | Norm ratio medián | |1-ratio| medián |
|-----------------|------|-------------------|-----------------|
| 0-30% | 14 | 3.55× | 2.55 |
| 30-40% | 12 | 2.76× | 1.76 |
| 40-50% | 25 | 2.28× | 1.28 |
| 50-60% | 47 | 1.54× | 0.61 |
| **60-70%** | **63** | **1.30×** | **0.39** ← sweet spot |
| 70-80% | 44 | 1.22× | 0.37 |
| 80-100% | 38 | 1.23× | 0.42 |

---

## GT Computation Pipeline

### SQL time threshold

```
SAW, QC:              actual_time_min > 0   (legitimně krátké časy u velkých dávek)
LATHE, MILL, DRILL:   actual_time_min > 0.05 (filtruje šum)
MANUAL:               actual_time_min > 0.05
```

**Důvod:** SAW na dílech z metrové tyče = jeden řez pro 1000+ kusů → čas/ks = 0.01 min.
Threshold 0.05 by odfiltroval 63.8% SAW záznamů u dávek 1000+.
Implementováno v `_compute_gt_from_records()` přes `_LOW_THRESHOLD_CATS`.

### Postup

1. **Eligible parts:** `parts.file_id IS NOT NULL` + `≥N VP` + `NOT LIKE 'DRE%'`
2. **Per VP:** group operations by machine category → sum times/setups, avg manning
3. **Across VPs:** trimmed_mean_10 per category → final GT
4. **Manning clamping:** `min(manning, 100.0)`, `max(manning, 1.0)` — Infor data quality
5. **Filters:** skip if no_material, no_saw, only_saw, time_too_high, time_too_low, no_pdf

### Normalizace strojů

| Input | → Output | Poznámka |
|-------|----------|----------|
| FV20 (klasická fréza) | MCV 750 | Konvenční → CNC ekvivalent |
| VS20 (vrtačka) | VS20 | Normalizace diakritiky |
| **MILLTAP 700 5AX** | MILLTAP 700 5AX | **Samostatný** — 5-osá manuální |
| **MILLTAP 700 5AX + WH3** | MILLTAP 700 5AX + WH3 | **Samostatný** — 5-osá + robot |
| **MILLTAP 700 + WH3** | MILLTAP 700 + WH3 | **Samostatný** — 3-osá + robot |

**DŮLEŽITÉ:** WH3 varianty se NESJEDNOCUJÍ — jsou to odlišné stroje:
- MILLTAP 700 5AX = 5-osá fréza, manuální obsluha
- MILLTAP 700 5AX + WH3 = 5-osá fréza + robot (sériová výroba)
- MILLTAP 700 + WH3 = 3-osá fréza + robot (sériová výroba)

### Výběr stroje

Nejčastější stroj napříč VP (`Counter.most_common(1)`):
```python
machine_counts = Counter(agg["machines"])
main_machine = machine_counts.most_common(1)[0][0]
```

---

## Distribuce rozměrů v datasetu

### LATHE (soustružení) — průměr polotovaru

| Průměr | BASE (476) | + EXTRA | Celkem |
|--------|-----------|---------|--------|
| D0-20 | 105 (54%) | — | 105 |
| D20-40 | 63 (33%) | — | 63 |
| D40-60 | 14 (7%) | +46 | 60 |
| D60-80 | 3 (1.5%) | +26 | 29 |
| D80-100 | 6 (3%) | +17 | 23 |
| D100-120 | 3 (1.5%) | +9 | 12 |
| D120-150 | 0 | +6 | 6 |
| D150-200 | 0 | +12 | 12 |

### MILL (frézování) — průřez polotovaru

| Průřez mm² | BASE | + EXTRA | Celkem |
|------------|------|---------|--------|
| 0-200 | 45 | — | 45 |
| 200-500 | 82 | — | 82 |
| 500-1k | 71 | — | 71 |
| 1k-2k | 66 | +? | ~100+ |
| 2k-5k | 24 | +? | ~80+ |
| 5k-10k | 8 | +? | ~40+ |
| 10k+ | 1 | +? | ~20+ |

---

## Model a Upload

| Parametr | Hodnota |
|----------|---------|
| **Base model** | `gpt-4o-2024-08-06` |
| **File ID** | `file-SPjqrsFEn9pTRC1ynAX1Sx` |
| **Training samples** | 694 |
| **JSONL size** | 715 MB (750 MB uploaded) |
| **Epochs** | 3 |
| **Suffix** | `gestima-v2-694` |
| **Estimated cost** | ~$130 |
| **Status** | File uploaded, waiting for credit top-up |
| **Credit remaining** | $1.28 |

### Starší modely (reference)

| Model | Suffix | Samples | Status |
|-------|--------|---------|--------|
| `ft:gpt-4o-2024-08-06:kovo-rybka:gestima-test-10:DB6XhMRn` | gestima-test-10 | 10 | Test OK (format validated) |
| `ft:gpt-4o-2024-08-06:kovo-rybka:gestima-v1:D8oakyjH` | gestima-v1 | 55 | Produkční (v1, jen celkový čas) |

---

## System Prompt (finální verze v2)

Uložen v `app/services/ft_debug_service.py` jako `SYSTEM_PROMPT`.
Klíčový rozdíl oproti v1: JSON key je `"material_norm"` (ne `"material"`).

---

## JSONL Format (per sample)

```json
{
  "messages": [
    {"role": "system", "content": "<system prompt>"},
    {"role": "user", "content": [
      {"type": "image_url", "image_url": {"url": "data:image/png;base64,...", "detail": "high"}},
      {"type": "text", "text": "Analyzuj výkres a navrhni technologický postup."}
    ]},
    {"role": "assistant", "content": "{\"material_norm\": \"1.0503\", \"stock\": {\"shape\": \"round_bar\", \"diameter_mm\": 25, ...}, \"operations\": [...]}"}
  ]
}
```

---

## Reprodukce datasetu

### Krok 1: BASE dataset (476 dílů)

```python
# API: GET /api/ft/debug/parts → FtPartsResponse
# Filtrace v Pythonu (nebo frontend FtDataDebugTab.vue):

# 1. Eligible: is_eligible == True (min 3 VP, has PDF, SAW, material, etc.)

# 2. Preciz Cut:
def passes_preciz_cut(part):
    for op in part.operations:
        if op.category == 'LATHE':
            if op.manning_pct > 100 or op.manning_pct < 50: return False
            if op.norm_ratio is not None and op.norm_ratio > 5.0: return False
        if op.category == 'MILL':
            if op.manning_pct > 100 or op.manning_pct < 70: return False
            if op.norm_ratio is not None and op.norm_ratio > 5.0: return False
    return True

# 3. CV combined (jen LATHE a MILL):
def passes_cv(part):
    for op in part.operations:
        if op.category not in ('LATHE', 'MILL'): continue
        if op.cv is not None and op.cv > 0.5: return False
        if op.manning_cv is not None and op.manning_cv > 0.5: return False
    return True

base_ids = [p.part_id for p in parts if p.is_eligible and passes_preciz_cut(p) and passes_cv(p)]
# → 476 IDs
```

### Krok 2: EXTRA LATHE (116 dílů)

```sql
-- Díly se stock_diameter > 40, VP >= 2, SAW + LATHE stroj, PDF + materiál
-- Pak v Pythonu: manning >= 40%, norm_ratio <= 5, NOT IN base_ids
-- WC pro LATHE: SMARTURN 160, NLX 2000, NZX 2000, MASTURN 32
```

### Krok 3: EXTRA MILL (165 dílů)

```sql
-- Díly s cross_section > 1000 mm², VP >= 2, SAW + MILL stroj, PDF + materiál
-- Cross section: W×H pro FLAT_BAR/PLATE/SQUARE_BAR, π(D/2)² pro ROUND_BAR
-- Pak v Pythonu: manning >= 60%, norm_ratio <= 5, NOT IN base_ids
-- WC pro MILL: MCV 750, MILLTAP 700 5AX, MILLTAP 700 5AX + WH3, MILLTAP 700 + WH3, TAJMAC H40
```

### Krok 4: Export

```python
combined_ids = base_ids | lathe_extra_ids | mill_extra_ids
# POST /api/ft/debug/export {"part_ids": sorted(combined_ids)}
# → JSONL soubor
```

---

## Klíčová rozhodnutí z datové analýzy

### Manning vysvětluje norm overrun
- Nízký manning → vyšší apparent norm_ratio (ne špatné normy, jiné měření času)
- Při manning 100%: LATHE ratio=0.82, MILL ratio=1.10
- Manning > 100% je data quality issue z Infor (hodnoty jako 4165%)

### Batch size NEMÁ vliv
- MILL +23% overrun je strukturální napříč všemi batch sizes (1-500+)
- Nefiltrujeme podle batch size

### SAW a QC zůstávají v trénování
- Model vrací kompletní technologii (SAW → LATHE/MILL → DRILL → MANUAL → QC)
- Technology Builder si vybere co použije a co přepočítá vlastní logikou
- SAW: Builder počítá řezání z cutting_conditions DB, AI čas ignoruje
- QC: Medián 0.10 min, 90% pod 0.85 min, cenově irelevantní

### Koeficienty patří do cenotvorby, NE do modelu
- Model se trénuje na GT realitě (skutečné výrobní časy)
- Korekční koeficienty (MILL +20-30%) se aplikují při tvorbě ceny, ne v Technology Builder
- Strojní čas je stabilní napříč sériemi — koeficient řeší obchodní logiku

---

## Soubory

| Soubor | Účel |
|--------|------|
| `app/services/ft_debug_service.py` | GT výpočet, export JSONL, inference |
| `app/schemas/ft_debug.py` | Pydantic schémata (FtPartsResponse, FtExportRequest) |
| `app/routers/ft_debug_router.py` | API endpointy (/parts, /export, /infer) |
| `frontend/.../FtDataDebugTab.vue` | UI pro filtraci, preview, export |
| `frontend/.../FtPartDetail.vue` | Detail řádek s operacemi |

---

## Estimated Cost

| Položka | Cena |
|---------|------|
| FT Training (694 samples × 3 epochs) | ~$130 |
| Inference per call | ~$0.05–0.10 (1 image + JSON) |

---

## Version History

- 2026-02-20 v4: Dataset v2 — 694 samples (476 base + 219 extra), přesné filtry, MILLTAP oddělené, SAW threshold fix, GPT-4o
- 2026-02-19 v3: FT job na GPT-4.1, 1,017 samples (bez filtrů — DEPRECATED)
- 2026-02-17 v2: Prompt design, GT metodika per-VP/per-category, baseline test MAPE 33%
- 2026-02-17 v1: Initial draft — data analýza, training sample format
