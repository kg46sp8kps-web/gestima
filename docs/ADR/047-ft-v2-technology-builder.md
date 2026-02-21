# ADR-047: Fine-Tuning v2 — Kompletní technologický postup z výkresu

**Status:** TRAINING (data uploaded, FT job running on GPT-4.1)
**Date:** 2026-02-19
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

## FT Training — Finální stav (2026-02-19)

### Model a Job

| Parametr | Hodnota |
|----------|---------|
| **Base model** | `gpt-4.1-2025-04-14` |
| **Job ID** | `ftjob-3FJpSmVWYPYreT9e7FgJO0tD` |
| **File ID** | `file-6JZtdHf6WQw8fJkggxyD2S` |
| **Epochs** | 2 |
| **Batch size** | 2 |
| **LR multiplier** | 1.0 |
| **Suffix** | `gestima-v2` |

### Dataset

| Metrika | Hodnota |
|---------|---------|
| **Training samples** | 1,017 |
| **JSONL size** | 955 MB (1.0 GB uploaded) |
| **Eligible parts** | 1,102 (≥3 VP + výkres) |
| **Skipped** | 85 (40 no_material, 23 no_saw, 18 time_too_high, 4 no_pdf) |
| **Min VP per part** | 3 |
| **GT aggregation** | Trimmed mean 10% per category across VPs |

### Pokrytí operací

| Kategorie | Samples | Stroje |
|-----------|:---:|--------|
| SAW | 1,017 | BOMAR STG240A (1017) |
| MILL | 709 | MCV 750 (358), MILLTAP 700 5AX (247), TAJMAC H40 (104) |
| LATHE | 485 | SMARTURN 160 (252), MASTURN 32 (138), NLX 2000 (62), NZX 2000 (33) |
| QC | 584 | KONTROLA (584) |
| DRILL | 178 | VS20 (178) |
| MANUAL | 156 | MECHANIK (156) |

### Materiálové pokrytí

| Skupina | % datasetu |
|---------|:---:|
| Hliník (3.3547, 3.2315...) | 41.6% |
| Nerez (1.4301, 1.4305...) | 28.9% |
| Ocel konstrukční (1.0503, 1.0570...) | 14.8% |
| Ocel automatová (1.0715) | 5.5% |
| Plasty (POM-C, PA6...) | 3.9% |
| Ostatní (legovaná, nástrojová, měď, mosaz, litina) | 5.3% |

### Tvary polotovaru

| Tvar | Dílů |
|------|:---:|
| round_bar | 1,185 |
| plate | 815 |
| flat_bar | 453 |
| square_bar | 102 |
| hexagonal_bar | 76 |
| tube | 18 |

### Kvalita GT (CV analýza)

| Kategorie | Medián CV | % dílů s CV < 0.5 | Poznámka |
|-----------|:---:|:---:|----------|
| **MILL** | 0.40 | **66.6%** | Základ ceny, solidní GT |
| **LATHE** | 0.41 | **63.5%** | Základ ceny, solidní GT |
| SAW | 0.64 | 31.6% | Vysoký CV ale abs. std jen 0.85 min — irelevantní |
| DRILL | 0.49 | 53.4% | Malé časy (medián 0.5 min) |
| MANUAL | 0.58 | 34.9% | Malé časy (medián 0.8 min) |
| QC | 0.91 | 21.8% | Cenově irelevantní (0.25 min medián) |

**Rozhodnutí:** Nefiltrovat podle CV. Trimmed mean 10% dostatečně robustní. 1,017 vzorků > menší čistší dataset.

### Produkční časy

| Percentil | min/ks |
|-----------|--------|
| P5 | 1.16 |
| P25 | 4.25 |
| Medián | 8.05 |
| P75 | 16.80 |
| P95 | 48.56 |
| Max | 118.47 |

### PDF kvalita

| Typ | Počet | % |
|-----|:---:|:---:|
| Text layer (CAD export) | 247 | 22.4% |
| Sken/vector (bez textu) | 850 | 77.1% |

Všechny PDF renderují čitelné obrázky — pro Vision FT je typ PDF irelevantní (model vidí obrázek, ne text).

---

## System Prompt (finální verze)

```
Jsi CNC technolog. Analyzuj výrobní výkres a navrhni technologický postup.
Zakázková strojírenská výroba, malá firma. Časy jsou per kus v minutách.
Odpověz POUZE validním JSON.

MATERIÁL:
- Přečti materiál z rohového razítka výkresu přesně tak, jak je napsaný (W.Nr, ČSN, EN, AISI...).
- Urči materiálovou skupinu a ISO klasifikaci:
  * Ocel automatová (1.0715, 11SMnPb30) — ISO P, HB~180, nejlépe obrobitelná
  * Ocel konstrukční (1.0503, C45, 12050) — ISO P, HB~200
  * Nerez (1.4301, 1.4104, X5CrNi18-10) — ISO M, HB~220, hůře obrobitelná, delší časy
  * Ocel nástrojová (1.2842, 90MnCrV8) — ISO K, HB~300, tvrdá, pomalé řezné podmínky
  * Hliník (3.3547, AlMg4,5Mn) — ISO N, HB~80, rychlé obrábění
  * Plasty (POM-C, PA6) — ISO N, HB~30, velmi rychlé obrábění
- ISO M/K materiály = delší strojní časy než ISO P (pomalejší řezné podmínky).
- ISO N materiály = kratší strojní časy (rychlejší posuvy a otáčky).

POLOTOVAR:
- Urči tvar a rozměry polotovaru z výkresu.
- round_bar: ø + délka (přídavek na upnutí)
- flat_bar: šířka × výška × délka
- square_bar: strana × strana × délka
- hexagonal_bar: šířka (rozměr přes plochy) × délka
- plate: šířka × výška × délka (deska, přířez)
- tube: vnější ø × tloušťka stěny × délka

STROJE:
- BOMAR STG240A (pásová pila, vždy první operace)
- SMARTURN 160 (CNC soustruh, z tyče do ø40mm, menší série)
- NLX 2000 (CNC soustruh, z tyče do ø65mm, 2 vřetena — komplexní rotační díly, nebo poháněné nástroje)
- NZX 2000 (CNC soustruh, 2 vřetena + 3 revolverové hlavy — vysoce produkční, série)
- MASTURN 32 (CNC soustruh ≤ø320mm, větší a jednodušší díly, menší série)
- Soustruhy se překrývají — volba závisí na průměru, složitosti a sérii.
- MCV 750 (CNC frézka 3-osá)
- MILLTAP 700 5AX (CNC frézka 5-osá, složitější tvary)
- TAJMAC H40 (CNC frézka 4-osá horizontální)
- VS20 (sloupová vrtačka — upíchnutí z druhé strany / odjehlení)
- MECHANIK (ruční práce — srážení, začištění)
- KONTROLA (výstupní kontrola)

PRAVIDLA:
- Strojní čas = celkový čas na stroji per kus (řez, přejezdy, výměny nástrojů, upínání kusu). NE setup stroje.
- Jednoduché díly = málo operací. NEPŘIDÁVEJ zbytečné operace.
- Kooperace se NEPOČÍTÁ.
- Rotační díly ze soustruhu → většinou následuje VS20 (upíchnutí z druhé strany, odjehlení).
- Více upnutí na frézce = více operací na tom samém stroji.

JSON formát:
{
  "material": "1.0503",
  "stock": {"shape": "round_bar|flat_bar|square_bar|hexagonal_bar|plate|tube", "diameter_mm": null, "width_mm": null, "height_mm": null, "length_mm": null},
  "operations": [
    {"category": "SAW|LATHE|MILL|DRILL|MANUAL|QC", "machine": "...", "operation_time_min": 0.0, "setup_time_min": 0, "manning_pct": 100, "num_operations": 1}
  ]
}
```

---

## JSONL Format (per sample)

```json
{
  "messages": [
    {"role": "system", "content": "<system prompt above>"},
    {"role": "user", "content": [
      {"type": "image_url", "image_url": {"url": "data:image/png;base64,...", "detail": "high"}},
      {"type": "text", "text": "Analyzuj výkres a navrhni technologický postup."}
    ]},
    {"role": "assistant", "content": "{\"material\": \"1.0570\", \"stock\": {...}, \"operations\": [...]}"}
  ]
}
```

Model se učí: **Vidím výkres → poznám materiál, polotovar, a kolik času na jakém stroji to zabere.**

---

## GT Computation Pipeline

### Postup

1. **Eligible parts:** `parts.file_id IS NOT NULL` + `≥3 VP` + `NOT LIKE 'DRE%'`
2. **Per VP:** group operations by machine category → sum times/setups, avg manning
3. **Across VPs:** trimmed_mean_10 per category → final GT
4. **Clamping:** manning 30–120%, setup max 360 min
5. **Filters:** skip if no_material, no_saw, time_too_high

### Normalizace strojů

| Input | → Output |
|-------|----------|
| MILLTAP 700 5AX + WH3 | MILLTAP 700 5AX |
| MILLTAP 700 + WH3 | MILLTAP 700 5AX |
| FV20 (klasická fréza) | MCV 750 |
| VS20 (vrtačka) | VS20 |
| NZX 2000 | NZX 2000 (samostatný) |

---

## Soubory

| Soubor | Účel |
|--------|------|
| `scripts/generate_ft_v2_data.py` | **Hlavní pipeline** — GT výpočet + JSONL generátor |
| `data/ft_v2_training.jsonl` | Training JSONL (1,017 samples, 955 MB) |
| `data/ft_v2_training_meta.json` | Metadata (categories, machines, counts) |
| `data/ft_v2_training_preview.json` | Preview prvních 20 samples (bez obrázků) |
| `scripts/test_ft_v2_prompt.py` | Test script — few-shot/FT inference + porovnání s GT |
| `data/ft_v2_ground_truth.json` | Ground truth pro test díly |

### Jak generovat data

```bash
python scripts/generate_ft_v2_data.py              # full generation
python scripts/generate_ft_v2_data.py --dry-run     # only stats, no JSONL
python scripts/generate_ft_v2_data.py --validate    # validate existing JSONL
```

---

## Estimated Cost

| Položka | Cena |
|---------|------|
| FT Training (1,017 samples × 2 epochs) | ~$126–150 |
| Inference per call | ~$0.05–0.10 (1 image + JSON) |

---

## Baseline (bez FT) vs Expected (po FT)

| Metrika | Baseline (few-shot) | Expected (po FT) |
|---------|:---:|:---:|
| MAPE celkový čas | 33% | < 15% |
| Konzistence | Nestabilní (temp=0.2) | Stabilní |
| Materiál detekce | Nespolehlivá | Naučená z 1,017 příkladů |
| Volba stroje | Přibližná | Naučená z produkce |

---

## Version History

- 2026-02-19 v3: FT job na GPT-4.1, 1,017 samples, opravený prompt (material, NLX, NZX, strojní čas)
- 2026-02-17 v2: Prompt design, GT metodika per-VP/per-category, baseline test MAPE 33%
- 2026-02-17 v1: Initial draft — data analýza, training sample format
