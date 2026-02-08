# Jak vytvořit Ground Truth Dataset

## Účel

Ground truth = **manuálně ověřené rozměry z PDF výkresů**, které použijeme jako referenci pro měření accuracy AI extrakce.

---

## Co potřebujeme pro každý díl

### 1. Critical Dimensions (povinné)
- `max_diameter` - největší průměr dílu [mm]
- `total_length` - celková délka dílu [mm]
- `bore_diameter` - průměr díry (pokud je) [mm]
- `bore_depth` - hloubka díry [mm]

### 2. Outer Contour (volitelné, ale užitečné)
- Seznam bodů `[{r, z}, ...]` kde:
  - `r` = radius (průměr/2) [mm]
  - `z` = poloha na ose [mm]
- Min. 3 body: začátek, střed, konec
- Ideálně: všechny step changes (změny průměru)

### 3. Features (volitelné)
- Důležité prvky: holes, threads, chamfers, grooves
- Pro každý feature:
  - `type` - druh (hole, thread_od, chamfer, ...)
  - `diameter` - průměr [mm]
  - `depth` nebo `length` - délka/hloubka [mm]
  - `tolerance` - H7, h6, ... (pokud je na výkresu)

---

## Příklad: PDM-249322_03

### PDF výkres říká:
- Max průměr: Ø55 mm (příruba)
- Celková délka: 89 mm
- Díra: Ø19 H7, hloubka 50 mm
- Hlavní tělo: Ø27.5 mm
- Závit: M30×2

### Ground truth zápis:

```json
{
  "filename": "PDM-249322_03.stp",
  "verified_by": "manual_inspection",
  "critical_dimensions": {
    "max_diameter": 55.0,
    "total_length": 89.0,
    "bore_diameter": 19.0,
    "bore_depth": 50.0
  },
  "outer_contour": [
    {"r": 30.0, "z": 0.0, "note": "Závit M30 na čele"},
    {"r": 27.5, "z": 1.0, "note": "Hlavní tělo"},
    {"r": 27.5, "z": 48.0, "note": "Konec těla"},
    {"r": 55.0, "z": 49.0, "note": "Příruba Ø55"},
    {"r": 55.0, "z": 89.0, "note": "Konec příruby"}
  ],
  "features": [
    {
      "type": "hole",
      "diameter": 19.0,
      "depth": 50.0,
      "tolerance": "H7"
    },
    {
      "type": "thread_od",
      "spec": "M30×2",
      "diameter": 30.0,
      "pitch": 2.0,
      "length": 6.0
    }
  ]
}
```

---

## Jak to udělat rychle (5 dílů = 15 minut)

### Pro každý díl:
1. Otevři PDF výkres
2. Najdi **hlavní kótování:**
   - Největší průměr (obvykle největší číslo s Ø)
   - Celková délka (vzdálenost mezi čely)
   - Díra (pokud je) - průměr + hloubka
3. Zapsat do JSON

### Minimální varianta (rychlá):
```json
{
  "filename": "xyz.stp",
  "verified_by": "quick_manual",
  "critical_dimensions": {
    "max_diameter": 55.0,
    "total_length": 89.0,
    "bore_diameter": 19.0
  }
}
```

**To stačí!** Outer contour a features jsou bonus.

---

## Doporučené díly pro ground truth (priorita)

1. ✅ **PDM-249322_03.stp** - DONE (reference file)
2. **JR 810665.ipt.step** - Bug #1 (inner/outer swap)
3. **JR 810671.ipt.step** - Bug #3 (wrong length)
4. **10383459_7f06bbe6.stp** - Jeden z "realistic values"
5. **0304663_D00043519_000.1_3D.stp** - Prismatic part

---

## Kam to zapsat

### Soubor: `docs/testing/ground_truth.json`

```json
{
  "dataset": [
    {
      "filename": "PDM-249322_03.stp",
      "verified_by": "manual_inspection",
      "critical_dimensions": {...}
    },
    {
      "filename": "JR 810665.ipt.step",
      "verified_by": "manual_inspection",
      "critical_dimensions": {...}
    }
  ]
}
```

---

## Až to budeš mít hotové

1. Ulož do `docs/testing/ground_truth.json`
2. Spusť: `python scripts/test_geometry_extraction_accuracy.py`
3. Výsledek: `docs/testing/accuracy_report.md` s čísly

---

## Potřebuji pomoc?

- Otevři PDF v prohlížeči
- Screenshot hlavní kótování
- Pošli mi, já to přepíšu do JSON
