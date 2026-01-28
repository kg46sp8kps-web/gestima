# Material System - Kompletni Prirucka

**Verze:** 1.0 | **Datum:** 2026-01-28

---

## Prehled

Materialovy system GESTIMA resit automaticke prirazovani materialovych kategorii a cen podle normy polotovaru.

### Architektura (3 vrstvy)

```
MaterialNorm (prevodni tabulka)     → W.Nr/EN/CSN/AISI → MaterialGroup
     ↓
MaterialGroup (kategorie)           → hustota, nazev (napr. "Ocel C45")
     ↓
MaterialItem (konkretni polotovar)  → rozmery, cena, shape
     ↓
MaterialPriceCategory (ceny)        → cenove tabulky podle vaha tiers
```

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

## 2. MaterialGroup - Kategorie

### Dostupne kategorie (13)

| Code | Nazev | Hustota (kg/dm3) |
|------|-------|------------------|
| 11xxx | Ocel konstrukcni (automatova) | 7.85 |
| C45 | Ocel konstrukcni (C45) | 7.85 |
| 42CrMo4 | Ocel legovana | 7.85 |
| X5CrNi18-10 | Nerez (304) | 7.90 |
| X2CrNiMo17-12-2 | Nerez (316L) | 8.00 |
| 6060 | Hlinik (6060) | 2.70 |
| 7075 | Hlinik (7075 dural) | 2.81 |
| CuZn37 | Mosaz | 8.40 |
| PA6 | Plasty (PA6) | 1.14 |
| POM | Plasty (POM) | 1.42 |

---

## 3. MaterialItem - Polotovary

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

## 4. Smart Lookup (Inteligentni vyhledavani)

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

## 5. Import katalogu

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

## 6. API Reference

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

## 7. Troubleshooting

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

## 8. Odkazy

**ADRs:**
- [ADR-011: Material Hierarchy](ADR/011-material-hierarchy.md)
- [ADR-014: Material Price Tiers](ADR/014-material-price-tiers.md)
- [ADR-015: Material Norm Mapping](ADR/015-material-norm-mapping.md)
- [ADR-016: Material Parser Strategy](ADR/016-material-parser-strategy.md)
- [ADR-019: Smart Lookup](ADR/019-material-catalog-smart-lookup.md)

**Kod:**
- `app/models/material_*.py` - DB modely
- `app/services/material_mapping.py` - business logika
- `scripts/seed_material_norms.py` - seed data

---

**Verze:** 1.0 | **Autor:** GESTIMA Team
