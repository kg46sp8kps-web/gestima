---
name: cnc-drawing-analysis
description: Analyze CNC machining technical drawings (PDF). Extracts part type (ROT/PRI/COMBINED), dimensions, material, manufacturing operations, and estimates machining time. Use when user uploads a PDF technical drawing for time estimation.
---

# CNC Drawing Analysis Skill

Analyzuješ výrobní výkresy (technické výkresy) z PDF souborů a extraktuješ strukturované informace pro odhad strojního času CNC obrábění.

## Postup

### Krok 1: Konverze PDF na obrázek
Spusť skript pro konverzi PDF na vysokorozlišovací PNG:
```bash
python /skills/cnc-drawing-analysis/scripts/convert_pdf.py /uploads/<filename>.pdf /tmp/drawing.png
```
Skript vytvoří PNG obrázek v 200 DPI — optimální pro čtení kót a razítkových polí.

### Krok 2: Vizuální analýza výkresu
Podívej se na vygenerovaný obrázek (`/tmp/drawing.png`) a analyzuj výkres.

**KRITICKÉ PRAVIDLO — VNĚJŠÍ vs. VNITŘNÍ:**
Typ dílu se určuje VÝHRADNĚ podle VNĚJŠÍHO OBRYSU dílu:
- **PRI** (prizmatický) = vnější obrys je obdélníkový/hranatý (deska, konzola, skříň)
- **ROT** (rotační) = vnější obrys je kruhový/válcový (hřídel, čep, příruba)
- **COMBINED** = válcový vnější obrys + frézované plochy/drážky na povrchu

⚠️ **DÍRY UVNITŘ DÍLU NEJSOU VNĚJŠÍ TVAR!**
Díra ø18 uvnitř obdélníkové destičky → díl je PRI, ne ROT.
Symbol ø na výkresu může znamenat díru — ověř zda jde o vnější průměr nebo vnitřní prvek.

### Krok 3: Extrakce rozměrů
Přečti POUZE zakótované rozměry z výkresu:
- **PRI díl**: délka × šířka × tloušťka (max_diameter_mm = null!)
- **ROT díl**: vnější průměr × délka
- **COMBINED**: jako ROT

### Krok 4: Razítkové pole (Title Block)
Přečti z razítkového pole (obvykle v pravém dolním rohu):
- Materiál (přesně jak je napsáno)
- Číslo dílu / číslo výkresu
- Měřítko, normy

### Krok 5: Manufacturing features
Vypiš POUZE prvky které REÁLNĚ VIDÍŠ zakótované:
- Díry (průměr, počet, průchozí/neprůchozí)
- Závity (M rozměr)
- H7 tolerance díry (vystružování)
- Sražení hran
- Tolerance (POUZE explicitně zakótované)

### Krok 6: Validace
Spusť validační skript:
```bash
python /skills/cnc-drawing-analysis/scripts/validate.py '<JSON_OUTPUT>'
```

### Krok 7: Výstup
Vrať výsledek jako JSON:
```json
{
  "part_type": "PRI",
  "complexity": "medium",
  "max_diameter_mm": null,
  "max_length_mm": 66,
  "max_width_mm": 33,
  "max_height_mm": 6,
  "material_hint": "AlMg4,5Mn",
  "part_number_hint": "D00043519",
  "manufacturing_description": "Obdélníková destička s dírou ø18...",
  "operations": ["frézování", "vrtání", "vystružování"],
  "surface_finish": null,
  "requires_grinding": false
}
```

## Klasifikace komplexity
- **simple** = do 4 prvků, obecné tolerance
- **medium** = 5-10 prvků, H7 díry, závity, ±0.02/0.05
- **complex** = 10+ prvků, IT6 a lepší, 3D kontury, hluboké kapsy

## Operace (vyber relevantní)
- `soustružení` — pro ROT/COMBINED díly
- `frézování` — pro PRI díly (obrys, kapsy, drážky)
- `vrtání` — díry, navrtání
- `vystružování` — H7 díry
- `závitování` — závity M*
- `broušení` — pouze IT5 a lepší tolerance
