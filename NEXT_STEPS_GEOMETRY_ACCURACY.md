# NEXT STEPS: Geometry Extraction Accuracy Testing

## Co jsme vytvořili

✅ **Test infrastruktura:**
- `scripts/test_geometry_extraction_accuracy.py` - Batch testing script
- `docs/testing/ground_truth_template.json` - Template pro ground truth
- `docs/testing/HOW_TO_CREATE_GROUND_TRUTH.md` - Návod na vytvoření ground truth

## Co potřebuješ udělat (15-30 minut)

### KROK 1: Vytvořit Ground Truth (5 dílů minimum)

Otevři PDF výkresy a zapiš základní rozměry do `docs/testing/ground_truth.json`:

```json
{
  "dataset": [
    {
      "filename": "PDM-249322_03.stp",
      "verified_by": "manual",
      "critical_dimensions": {
        "max_diameter": 55.0,
        "total_length": 89.0,
        "bore_diameter": 19.0
      }
    },
    {
      "filename": "JR 810665.ipt.step",
      "verified_by": "manual",
      "critical_dimensions": {
        "max_diameter": 12.0,
        "total_length": 87.8,
        "bore_diameter": 6.9
      }
    }
  ]
}
```

**Doporučené díly:**
1. PDM-249322_03.stp (reference)
2. JR 810665.ipt.step
3. JR 810671.ipt.step
4. 10383459_7f06bbe6.stp
5. 0304663_D00043519_000.1_3D.stp

**Stačí:** max_diameter, total_length, bore_diameter (pokud je)

---

### KROK 2: Spustit batch test

```bash
# Backend MUSÍ běžet!
python gestima.py run

# V novém terminálu:
python scripts/test_geometry_extraction_accuracy.py
```

**Output:**
- `docs/testing/extraction_results.json` - detailed results
- `docs/testing/accuracy_report.md` - summary s accuracy %

---

### KROK 3: Analyze results

Otevři `docs/testing/accuracy_report.md`:

**Pokud accuracy < 95%:**
1. Najdi soubory s nejnižší accuracy
2. Zkontroluj co AI extrahovala špatně
3. Identifikuj pattern (např. "vždy chybí závity")
4. Vylepši prompt v `app/services/geometry_extractor.py`
5. Opakuj KROK 2

**Pokud accuracy ≥ 95%:**
1. Freeze prompt (commit)
2. Přejít na Phase 2: Time calculation calibration
3. Collect shop floor data

---

## Alternativní test (rychlejší)

Pokud nechceš vytvářet ground truth ručně, můžeme udělat:

### VISUAL INSPECTION TEST

1. Spustit batch test BEZ ground truth
2. Pro každý díl:
   - Zobrazit AI extrakt v browseru (Interactive SVG)
   - Otevřít PDF vedle
   - Zhodnotit: "looks correct" vs "wrong"
3. Změřit % correct

**Výhoda:** Faster (5 min per file vs 2 min)
**Nevýhoda:** Subjektivní (ale stále lepší než žádné měření)

---

## Proč to dělám takhle

**Audit finding:** "NO measurement = NO accuracy baseline"

Nemůžeš říct "AI extrakce je přesná" bez dat.

**Data-driven approach:**
1. Measure current accuracy
2. Identify failures
3. Fix specific issues
4. Re-measure
5. Repeat until 95%

**NE:** "Změním prompt, snad to pomůže" (guess & hope)

---

## Až budeš hotový

Pošli mi:
- `docs/testing/accuracy_report.md` (summary)
- Screenshot nejhoršího fail case
- "Co teď?" → Pokračovat na prompt optimization

---

## Nebo můžu udělat JÁ (s tvou pomocí)

Pokud chceš, můžu:
1. Spustit API test přes backend endpoint
2. Zobrazit výsledky v browseru (Interactive SVG viewer)
3. Ty řekneš "correct" / "wrong" pro 10 dílů
4. Spočítám accuracy

**Tvoje volba:**
- A) Udělám ground truth ručně (15 min) → přesné měření
- B) Visual inspection společně (5 min) → rychlé měření
- C) Něco jiného → navrhni

**Já počkám na tvůj input.**
