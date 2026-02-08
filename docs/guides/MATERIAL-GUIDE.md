# Material System - Kompletni Prirucka

**Verze:** 2.0 | **Datum:** 2026-02-08

---

## Prehled

Materialovy system GESTIMA resit automaticke prirazovani materialovych kategorii a cen podle normy polotovaru.

### Architektura (3 vrstvy)

```
MaterialNorm (prevodni tabulka)     → W.Nr/EN/CSN/AISI → MaterialGroup
     ↓
MaterialGroup (kategorie)           → hustota, nazev (napr. "Ocel konstrukční")
     ↓                                  8-digit kód: 20910000-20910008
MaterialItem (konkretni polotovar)  → rozmery, cena, shape
     ↓
MaterialPriceCategory (ceny)        → cenove tabulky podle vaha tiers
                                       8-digit kód: 20900000-20900042
```

**DŮLEŽITÉ:** Používají se **8-digit kódy** dle ADR-017:
- MaterialPriceCategory: `20900000-20900042` (43 kategorií)
- MaterialGroup: `20910000-20910008` (9 skupin)

**ADRs:** [ADR-011](ADR/011-material-hierarchy.md), [ADR-014](ADR/014-material-price-tiers.md), [ADR-015](ADR/015-material-norm-mapping.md)

---

## 1. MaterialNorm - Prevodni tabulka

### Co to je

Prevod mezinarodniho oznaceni materialu na interni kategorii:

| W.Nr | EN ISO | CSN | AISI | → MaterialGroup |
|------|--------|-----|------|-----------------|
| 1.0503 | C45 | 12050 | 1045 | Ocel konstrukcni (C45) |
| 1.4301 | X5CrNi18-10 | 17240 | 304 | Nerez (304) |

**Pravidla:**
- Min. 1 sloupec musi byt vyplnen
- Case-insensitive (c45 = C45)
- OR logika pres vsechny 4 sloupce

### Admin konzole

**URL:** `/admin/material-norms`
**Opravneni:** Admin only

**Funkce:**
- Pridani/uprava norem
- Vyhledavani (300ms debounce)
- Optimistic locking pro soubehy

### Seed data (~22 beznych norem)

```bash
python scripts/seed_material_norms.py
```

---

## 2. MaterialGroup - Kategorie (9 skupin)

### Seed Script: `scripts/seed_material_groups.py`

**CANONICAL SOURCE - Jediný platný seed pro MaterialGroup!**

| Code (8-digit) | Nazev | Hustota (kg/dm³) |
|----------------|-------|------------------|
| 20910000 | Hliník | 2.70 |
| 20910001 | Měď | 8.90 |
| 20910002 | Mosaz | 8.50 |
| 20910003 | Ocel automatová | 7.85 |
| 20910004 | Ocel konstrukční | 7.85 |
| 20910005 | Ocel legovaná | 7.85 |
| 20910006 | Ocel nástrojová | 7.85 |
| 20910007 | Nerez | 7.90 |
| 20910008 | Plasty | 1.20 |

**Spuštění:**
```bash
python scripts/seed_material_groups.py
```

---

## 3. MaterialPriceCategory - Cenové kategorie (43 kategorií)

### Seed Script: `scripts/seed_price_categories.py`

**CANONICAL SOURCE - Jediný platný seed pro MaterialPriceCategory!**

**43 kategorií podle materiálu a tvaru (20900000-20900042):**

| Materiál | Počet tvarů | Kódy | Příklad |
|----------|-------------|------|---------|
| Hliník | 6 | 20900000-20900005 | deska, tyč kruhová, tyč plochá, tyč čtvercová, trubka, tyč šestihranná |
| Mosaz | 4 | 20900006-20900009 | tyč kruhová, tyč plochá, tyč čtvercová, trubka |
| Měď | 6 | 20900010-20900015 | deska, tyč kruhová, tyč plochá, tyč čtvercová, trubka, tyč šestihranná |
| Nerez | 6 | 20900016-20900021 | deska, tyč kruhová, tyč plochá, tyč čtvercová, trubka, tyč šestihranná |
| **Ocel automatová** | 3 | **20900022-20900024** | **tyč kruhová, tyč plochá, tyč čtvercová** |
| **Ocel konstrukční** | 6 | **20900025-20900030** | **deska, tyč kruhová, tyč plochá, tyč čtvercová, trubka, tyč šestihranná** |
| **Ocel legovaná** | 3 | **20900031-20900033** | **tyč kruhová, tyč plochá, tyč čtvercová** |
| **Ocel nástrojová** | 4 | **20900034-20900037** | **deska, tyč kruhová, tyč plochá, tyč čtvercová** |
| Plasty | 5 | 20900038-20900042 | deska, tyč kruhová, tyč plochá, tyč čtvercová, tyč šestihranná |

**Spuštění:**
```bash
# NEJPRVE seed MaterialGroups!
python scripts/seed_material_groups.py

# PAK seed PriceCategories (vyžaduje groups)
python scripts/seed_price_categories.py
```

**Výhody této struktury:**
- Generic názvy (Hliník = všechny 3xxx-6xxx série)
- 4 typy ocelí (automatová, konstrukční, legovaná, nástrojová)
- Separované tvary (SQUARE_BAR ≠ FLAT_BAR)
- 8-digit kódy dle ADR-017

---

## 4. MaterialItem - Polotovary

### Struktura zaznamu

```python
MaterialItem:
    material_number: str    # 7-digit (2XXXXXX)
    code: str               # "1.0503-KR050.000-O"
    name: str               # "C45 D50 - tyc kruhova"
    shape: StockShape       # ROUND_BAR, FLAT_BAR, ...
    diameter: float         # mm (pro ROUND_BAR)
    width: float            # mm (pro FLAT_BAR)
    thickness: float        # mm
    material_group_id: FK   # → MaterialGroup
    price_category_id: FK   # → MaterialPriceCategory
```

### Tvary (StockShape enum)

- `ROUND_BAR` - kruhova tyc
- `FLAT_BAR` - plocha tyc
- `SQUARE_BAR` - ctvercova tyc
- `HEXAGONAL_BAR` - sestihran
- `TUBE` - trubka
- `PLATE` - deska
- `BLOCK` - 3D blok

---

## 5. Smart Lookup (Inteligentni vyhledavani)

### Jak to funguje

Uzivatel zada: `"1.4404 D21"` (potrebuje prumer 21mm)

System:
1. Extrahuje: material_code=1.4404, shape=ROUND_BAR, diameter=21
2. Najde MaterialGroup pres MaterialNorm
3. Smart Lookup: filtruje items kde diameter >= 21 (UPWARD ONLY!)
4. Vybere nejblizsi: MaterialItem "1.4404 D25" (diff=4mm)

```
Zadano: D21 → Nalezeno: D25 (vetsi o 4mm)
Zadano: D21 → NENALEZENO: D20 (mensi = nelze pouzit!)
```

**ADR:** [ADR-019](ADR/019-material-catalog-smart-lookup.md)

---

## 6. Import katalogu

### Status: ODLOZENO

Import z Excel (~4181 radku) odlozen. Parser podporuje 79.5% formatu.

**Soubory:**
- `scripts/analyze_material_codes.py` - analyza
- `scripts/import_material_catalog.py` - import (nerealizovany)

**Podporovane formaty:**
- Ocel: `1.0503-KR050.000-O`, `1.0036-HR015x005-T`
- Hlinik: `3.3547-DE012-082-102-F`
- Plasty: `PA6-KR080.000-P-B`
- Litina: `GG250-KR050.000-L`

**Preskocene (~859):**
- Vypalky, profily (L, U), odlitky, specialni tolerance

---

## 7. API Reference

### Endpointy

```
GET    /admin/material-norms              # Admin stranka
GET    /api/material-groups               # List kategorii
GET    /api/material-norms/search?q=      # Vyhledavani
POST   /api/material-norms                # Vytvorit
PUT    /api/material-norms/{id}           # Upravit
DELETE /api/material-norms/{id}           # Soft delete

GET    /api/materials/items               # List polotovaru
GET    /api/materials/items/{id}          # Detail
GET    /api/materials/parse?text=         # Parse + smart lookup
```

### Service funkce

```python
from app.services.material_mapping import auto_assign_group

group = await auto_assign_group(db, norm_code="C45")
# → MaterialGroup(name="Ocel konstrukcni (C45)", density=7.85)
```

---

## 8. Troubleshooting

### "Neznama norma: {kod}"

1. Zkontrolujte preklepy (system je case-insensitive)
2. Overtte existenci v Admin konzoli
3. Pridejte normu pokud chybi

### Optimistic locking error

"Norma byla zmenena jinym uzivatelem"

→ Obnovte stranku (F5) a zkuste znovu

### Parser nerozpoznal format

Zkontrolujte `temp/all_unrecognized.txt` pro seznam nepodporovanych formatu.

---

## 9. Odkazy

**ADRs:**
- [ADR-011: Material Hierarchy](ADR/011-material-hierarchy.md)
- [ADR-014: Material Price Tiers](ADR/014-material-price-tiers.md)
- [ADR-015: Material Norm Mapping](ADR/015-material-norm-mapping.md)
- [ADR-016: Material Parser Strategy](ADR/016-material-parser-strategy.md)
- [ADR-019: Smart Lookup](ADR/019-material-catalog-smart-lookup.md)

**Kod:**
- `app/models/material.py` - DB modely (MaterialGroup, MaterialPriceCategory, MaterialItem, MaterialNorm)
- `app/services/material_mapping.py` - business logika
- **`scripts/seed_material_groups.py`** - **CANONICAL seed pro MaterialGroup (9 skupin)**
- **`scripts/seed_price_categories.py`** - **CANONICAL seed pro MaterialPriceCategory (43 kategorií)**
- `scripts/seed_material_norms_complete.py` - seed pro MaterialNorm (83 norem)

---

**Verze:** 2.0 | **Autor:** GESTIMA Team | **Updated:** 2026-02-08
