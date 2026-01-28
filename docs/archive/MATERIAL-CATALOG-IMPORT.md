# Material Catalog Import - Pracovní Dokumentace

**Datum:** 2026-01-27
**Status:** ⏸️ ODLOŽENO (priorita: nízká, vrátíme se později)
**Důvod odkladu:** Zdržuje vývoj, potřebujeme řešit povrchy a další funkcionalitu

---

## 📋 Přehled

Import materiálového katalogu z Excel souboru `data/materialy_export_import.xlsx` (4181 řádků) do databáze jako MaterialItems s auto-generovanými 7-digit material_numbers (2XXXXXX).

### Aktuální stav parseru

**✅ Parsovatelné: 3322 položek (79.5% pokrytí)**
**⊘ Přeskočené: 859 položek**

---

## 🎯 Co bylo implementováno

### 1. Parser materiálových kódů

**Soubor:** `scripts/analyze_material_codes.py`

**Podporované formáty:**

| Typ | Formát | Příklad | Tvar | Počet |
|-----|--------|---------|------|-------|
| **Ocel - tyče kruhové** | `[W.Nr]-KR[DDD].000-[STAV]` | `1.0503-KR050.000-O` | ROUND_BAR | ~800× |
| **Ocel - tyče ploché/čtvercové** | `[W.Nr]-HR[WWW]x[TTT]-[STAV]` | `1.0036-HR015x005-T` | FLAT_BAR / SQUARE_BAR | ~600× |
| **Ocel - trubky** | `[W.Nr]-TR[DDD]x[WWW]-[STAV]` | `1.4301-TR010x002-S` | TUBE | ~120× |
| **Ocel - šestihrany** | `[W.Nr]-OK[DDD].000-[STAV]` | `1.0503-OK017.000-T` | HEXAGONAL_BAR | ~86× |
| **Ocel - 3D bloky** | `[W.Nr]-HR[TTT]-[WWW]-[LLL]-BLOK` | `1.0036-HR080-220-275-BLOK` | BLOCK | ~9× |
| **Ocel - přířezy** | `[W.Nr]-KR[DDD].000-[LLL]-[STAV]` | `1.0503-KR140.000-015-O` | ROUND_BAR + length | ~19× |
| **Ocel - tyče s délkou** | `[W.Nr]-HR[WWW]x[TTT]-[STAV]-/[LLL]` | `1.2842-HR015x001.5-B-/500` | FLAT_BAR + length | ~10× |
| **Hliník - 3D bloky** | `3.xxxx-DE[TTT]-[WWW]-[LLL]-[STAV]` | `3.3547-DE012-082-102-F` | BLOCK | ~556× |
| **Hliník - 2D pásy** | `3.xxxx-DE[TTT]-[WWW]-[STAV]` | `3.3547-DE012-066-L` | FLAT_BAR | ~634× |
| **Litina - tyče** | `GG250-KR[DDD].000-L` | `GG250-KR050.000-L` | ROUND_BAR | ~25× |
| **Plasty - tyče** | `[PLAST]-KR[DDD].000-[STAV]-[BARVA]` | `PA6-KR080.000-P-B` | ROUND_BAR | ~80× |
| **Plasty - desky** | `[PLAST]-DE[TTT]-000-[STAV]-[BARVA]` | `PA6-DE010-000-P-B` | PLATE | ~10× |
| **Plasty - pásy** | `[PLAST]-DE[TTT]-[WWW]-[STAV]-[BARVA]` | `POM-C-DE016-014-L-B` | FLAT_BAR | ~98× |
| **Plasty - 3D bloky** | `[PLAST]-DE[TTT]-[WWW]-[LLL]-[BARVA]` | `PE500-DE012-190-303-B` | BLOCK | ~15× |

**Stavy materiálů:**
- T = Tažený (drawn)
- V = Válcovaný (rolled)
- O = Žíhaný (annealed)
- P = Lisovaný (pressed)
- L = Litý (cast)
- F = Frézovaný (milled)
- B = Broušený (ground)
- S = Svařovaný (welded)

**Barvy plastů:**
- B = Černý (black)
- N = Natur (natural)
- G/GR = Šedý (gray)

---

### 2. Material Groups (kategorie)

**Soubor:** `scripts/import_material_catalog.py`

**Definované skupiny (18 kategorií):**

| Code | Název | Hustota (kg/dm³) | Příklad |
|------|-------|------------------|---------|
| `10xxx` | Ocel konstrukční | 7.85 | 1.0503, 1.0715 |
| `11xxx` | Ocel automatová | 7.85 | 1.1191 |
| `12xxx` | Ocel nástrojová | 7.85 | 1.2842, 1.2379 |
| `13xxx` | Ocel nízkolegovaná | 7.85 | 1.7225 |
| `14xxx` | Nerez | 7.90 | 1.4301, 1.4404 |
| `20xxx` | Měď a slitiny mědi | 8.90 | 2.0401 |
| `21xxx` | Mosaz | 8.40 | 2.1053 |
| `22xxx` | Bronz | 8.80 | 2.0060 |
| `3xxxx` | Hliník | 2.70 | 3.3547, 3.2315 |
| `LITINA-GG` | Litina šedá | 7.20 | GG250 |
| `LITINA-TV` | Litina tvárná | 7.10 | GGG40 |
| `PLAST` | Plasty | 1.14-1.50 | PA6, POM-C, PE, PEEK |

**Plasty (detailně):**
- PA6, PA6G: 1.14 kg/dm³
- PA66: 1.14 kg/dm³
- POM, POM-C: 1.42 kg/dm³
- PE300, PE500, PE1000: 0.95 kg/dm³
- PC: 1.20 kg/dm³
- PEEK, PEEK1000: 1.32 kg/dm³
- PEEK-GF30: 1.50 kg/dm³
- MAPA: 1.14 kg/dm³
- ABS: 1.05 kg/dm³

---

### 3. Price Categories (kombinace materiál + tvar)

**Formát:** `[MATERIAL_FAMILY]-[SHAPE]`

**Příklady:**
- `OCEL-KONS-KRUHOVA` = Ocel konstrukční - kruhová tyč
- `NEREZ-PLOCHA` = Nerez - plochá tyč
- `HLINIK-DESKA` = Hliník - deska
- `LITINA-GG-KRUHOVA` = Litina šedá - kruhová tyč
- `PLAST-KRUHOVA` = Plasty - kruhová tyč

**Vygeneruje se ~40 kombinací** (podle skutečných dat v katalogu).

---

### 4. Přeskočené položky

**859 položek ignorováno, důvody:**

| Kategorie | Počet | Příklad | Důvod |
|-----------|-------|---------|-------|
| Výpalky | ~200× | `0044892-vypalek` | Recyklát, neimportovat |
| System kódy | ~100× | `000-nab-mat`, `000-material_od_zakaznika` | Generické |
| EP povrch | ~50× | `3.3547-nab-EP` | Elektropolovaný hliník - ignorovat |
| Nulové rozměry | ~65× | `HR000x000`, `DE000-000` | Chybějící data |
| Tyče s tolerancemi | ~172× | `KR010.000-B-h6`, `KR045.000-B-f7` | Speciální tolerance |
| Profily (L, U, J) | ~20× | `L050x050x08-Pl`, `UPE120x060-V` | Nestandardní tvary |
| Obdélníkové trubky | ~8× | `TR050x025x02-Sv` | Speciální trubky |
| Odlitky | ~50× | `1071185-odlitek` | Specifické výrobky |
| Speciální kódy | ~100× | `1.4028+QT-KR006-materiál_PBS` | Zákaznické |

**⚠️ TODO pro budoucnost:**
- Profily (L, U, UPE) - vyžaduje nový StockShape nebo custom parsing
- Tyče s tolerancemi (h6, f7, f8) - přidat tolerance pole do DB
- Obdélníkové trubky - vyžaduje width+height pole
- Povrchové úpravy (EP, Vs, Zn, Kl) - vyžaduje surface_treatment tabulku

---

## 🗂️ Datové soubory

| Soubor | Účel | Řádky |
|--------|------|-------|
| `data/materialy_export_import.xlsx` | **Zdrojový Excel katalog** | 4181 |
| `temp/material_codes_preview.csv` | **Parsovaná data ready pro import** | 3322 |
| `temp/material_codes_summary.json` | Statistiky parsování | - |
| `temp/all_unrecognized.txt` | Kompletní seznam přeskočených | 859 |

---

## 🚀 Spouštění

### 1. Analýza katalogu (dry-run)

```bash
python scripts/analyze_material_codes.py
```

**Výstup:**
- `temp/material_codes_preview.csv` - parsovaná data
- `temp/material_codes_summary.json` - statistiky
- Console output - přehled tvarů, materiálů, stavů

### 2. Preview importu

```bash
python scripts/import_material_catalog.py
```

**Zobrazí:**
- MaterialGroups (18 kategorií)
- PriceCategories (~40 kombinací)
- Ukázka přeskočených položek
- Preview 20 vzorových MaterialItems

### 3. Detailní preview databázových záznamů

```bash
python scripts/preview_material_import.py
```

**Zobrazí:**
- Vzorové MaterialItem záznamy (10×)
- Jaká pole budou naplněna (rozměry, shape, material_number)
- Jaká pole zůstanou NULL (weight_per_meter, standard_length, norms, supplier_code)

### 4. Import do databáze (NEREALIZOVÁNO)

```bash
python scripts/import_material_catalog.py --execute
```

**⚠️ TODO:** Implementovat `execute_import()` funkci.

---

## 📊 Statistiky

### Parsované materiály (TOP 10)

| Materiál | Počet variant | Typ |
|----------|---------------|-----|
| 3.3547 | 997× | Hliník |
| 1.4301 | 203× | Nerez |
| 1.0036 | 200× | Ocel konstrukční |
| 1.0503 | 145× | Ocel konstrukční |
| 3.4365 | 142× | Hliník |
| 3.2315 | 141× | Hliník |
| POM-C | 111× | Plast |
| 1.0570 | 109× | Ocel konstrukční |
| 3.3206 | 106× | Hliník |
| 1.0715 | 78× | Ocel konstrukční |

### Tvary

| Shape | Počet | Poznámka |
|-------|-------|----------|
| FLAT_BAR | 1390× | Ploché tyče, hliníkové pásy, plastové pásy |
| ROUND_BAR | 983× | Kruhové tyče (ocel, nerez, hliník, plasty, litina) |
| BLOCK | 577× | 3D bloky (hliník, ocel, plasty) |
| SQUARE_BAR | 155× | Čtvercové tyče |
| TUBE | 121× | Trubky |
| HEXAGONAL_BAR | 86× | Šestihrany |
| PLATE | 10× | Desky (jen tloušťka, bez šířky) |

---

## ⚙️ Implementační detaily

### MaterialItem databázový záznam

**Naplněná pole (z Excelu + auto-generováno):**
- ✅ `material_number` - 7-digit (2XXXXXX) auto-generováno
- ✅ `code` - původní kód z Excelu (např. `1.0715-KR050.000-O`)
- ✅ `name` - generováno jako `{material} {dimensions} - {shape} {group_name}`
- ✅ `shape` - StockShape enum
- ✅ `diameter` - mm (pro ROUND_BAR, HEXAGONAL_BAR)
- ✅ `width` - mm (pro SQUARE_BAR, FLAT_BAR, BLOCK)
- ✅ `thickness` - mm (pro FLAT_BAR, PLATE, BLOCK)
- ✅ `wall_thickness` - mm (pro TUBE)
- ✅ `material_group_id` - FK → material_groups
- ✅ `price_category_id` - FK → material_price_categories

**NULL pole (doplnit později):**
- ❌ `weight_per_meter` - kg/m (není v Excelu)
- ❌ `standard_length` - mm (není v Excelu, typicky 6000mm)
- ❌ `norms` - "EN 10025, EN 10060" (není v Excelu)
- ❌ `supplier_code` - kód dodavatele (není v Excelu)
- ❌ `supplier` - název dodavatele (není v Excelu)

**⚠️ Poznámka:** Pole `length` (pro přířezy a tyče s délkou) je parsováno v CSV, ale **není v DB schématu**. Potřebná migrace nebo použít `standard_length` jinak.

---

## 🔄 Další kroky (když se vrátíme)

### 1. Doplnit chybějící data

- [ ] **Normy (EN, DIN, ČSN, AISI)** - propojit s MaterialNorm tabulkou
- [ ] **Hmotnost na metr** - vypočítat nebo importovat z jiného zdroje
- [ ] **Standardní délky** - nastavit default 6000mm pro tyče
- [ ] **Supplier kódy** - propojit s dodavatelským systémem

### 2. Řešit povrchové úpravy

**Přeskočené suffixy:**
- `-Kl` (klínový) - ignorováno, parsováno jako standardní
- `-Zn` (zinkovaný)
- `-Vs` (válcovaný za studena)
- `-EP` (elektropolovaný) - kompletně přeskočeno pro hliník

**Návrh:** Vytvořit `surface_treatments` tabulku nebo pole v MaterialItem.

### 3. Rozšířit parser pro speciální formáty

- [ ] **Profily** (L, U, UPE, J) - nový StockShape nebo custom geometrie
- [ ] **Tyče s tolerancemi** (h6, f7, f8) - přidat `tolerance` pole
- [ ] **Obdélníkové trubky** (TR050x025x02) - width + height
- [ ] **Speciální délky** - migrace DB pro `length` pole

### 4. Database migrace

```python
# Přidat length field (volitelné)
length = Column(Float, nullable=True)  # mm (pro přířezy, custom délky)
```

### 5. Implementovat import

**Soubor:** `scripts/import_material_catalog.py`

**Funkce `execute_import()` musí:**
1. Generovat 3322× unikátní material_numbers (NumberGenerator service)
2. Vytvořit MaterialGroups (18 záznamů)
3. Vytvořit MaterialPriceCategories (~40 záznamů)
4. Vytvořit MaterialItems (3322 záznamů)
5. Ošetřit duplikáty (code unique constraint)
6. Transakční rollback při chybě
7. Audit (created_by, updated_by)
8. Progress bar (3322 položek = ~10s import)

---

## 📝 Poznámky

### Material Number System (ADR-017)

- **Range:** 2000000-2999999 (7-digit)
- **Generator:** `NumberGenerator` service
- **Formát:** Plain integer (ne 2.000.000, jen 2000000)
- **User-facing:** URL `/api/materials/items/{material_number}`
- **Internal:** `MaterialItem.id` (auto-increment)

### W.Nr. → MaterialNorm mapping

**Parsovaných ~50 unikátních W.Nr. materiálů:**
- 1.0xxx (ocel konstrukční): 1.0036, 1.0503, 1.0570, 1.0715, ...
- 1.1xxx (ocel automatová): 1.1191
- 1.2xxx (ocel nástrojová): 1.2842, 1.2379, ...
- 1.3xxx (ocel nízkolegovaná): 1.7225
- 1.4xxx (nerez): 1.4301, 1.4404, 1.4571, ...
- 2.xxxx (měď, bronz, mosaz): 2.0401, 2.1053, ...
- 3.xxxx (hliník): 3.3547, 3.2315, 3.4365, 3.3206, ...

**TODO:** Doplnit ČSN, EN ISO, AISI normy pro každý W.Nr.

---

## 🎯 Priorita: NÍZKÁ

**Důvod odkladu:**
- Zdržuje vývoj hlavních funkcí
- Potřebujeme řešit povrchové úpravy (komplex)
- Normy vyžadují externí data (EN, ČSN, AISI mapping)
- Import lze dokončit později bez dopadu na jádro systému

**Kdy se vrátit:**
- Po dokončení core funkcí (Parts, Operations, Batches)
- Až budeme potřebovat kompletní materiálový katalog
- Když budeme řešit integraci s dodavateli

---

**Konec dokumentace**
**Autor:** Claude (AI assistant)
**Revize:** 1.0
**Datum:** 2026-01-27
