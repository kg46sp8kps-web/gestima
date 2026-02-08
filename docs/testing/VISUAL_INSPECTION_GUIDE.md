# Visual Inspection Guide

## Co se právě děje

✅ **Batch test běží na všech 37 STEP+PDF souborech**

Script volá AI Vision API pro každý díl a extrahuje:
- Outer/inner contour
- Features (holes, threads, chamfers, etc.)
- Critical dimensions (max_diameter, total_length, bore_diameter)
- SVG vizualizaci profilu

Estimated time: **5-10 minut** (cca 15 sekund per díl × 37)

---

## Co budeš dělat pak

### Krok 1: Otevřít HTML report

Až script doběhne, otevři:

```
file:///Users/lofas/Documents/__App_Claude/Gestima/visual_inspection_report.html
```

(Nebo přes Finder: double-click na `visual_inspection_report.html`)

---

### Krok 2: Review každého dílu (30 sekund per díl)

Pro každý díl uvidíš:

```
┌──────────────────────────────────────────────┐
│ PDM-249322_03.stp                      #1    │
├──────────────────────────────────────────────┤
│ Max Diameter:  55.0 mm                       │
│ Total Length:  89.0 mm                       │
│ Bore Diameter: 19.0 mm                       │
│ Features:      4                             │
├──────────────────────────────────────────────┤
│ [SVG VISUALIZATION]                          │
├──────────────────────────────────────────────┤
│ [✓ CORRECT] [✗ WRONG] [→ SKIP]             │
└──────────────────────────────────────────────┘
```

**Tvůj úkol:**
1. Podívej se na SVG (profile s konturou)
2. Zkontroluj rozměry (max_diameter, length, bore)
3. Klikni:
   - **✓ CORRECT** = rozměry sedí, profil vypadá OK
   - **✗ WRONG** = něco je špatně (chybí features, špatný průměr, atd.)
   - **→ SKIP** = nevíš / nejasné

**Nemusíš porovnávat s PDF výkresem** - jen zhodnoť "looks reasonable" vs "clearly wrong"

---

### Krok 3: Export results

HTML report **automaticky počítá accuracy** jak postupuješ:

```
Progress: 15 / 37 evaluated
Accuracy: 86.7%
```

Evaluace se ukládá do **localStorage** (persist přes refresh).

---

### Krok 4: Analyze results

Až projdeš všech 37 (nebo alespoň 20), podívej se na čísla:

**Pokud accuracy ≥ 90%:**
→ ✅ AI Vision funguje skvěle!
→ Přejít na Phase 2: Time calculation calibration

**Pokud accuracy < 90%:**
→ ⚠️ Identifikovat common failures:
- Chybějí závity?
- Špatné bore diameters?
- Prismatic parts jako rotational?
→ Vylepšit prompt
→ Re-test

---

## Quick Evaluation Tips

**CORRECT** pokud:
- Rozměry jsou ±5% (55mm ± 2.7mm = OK)
- Profil má správný tvar (outer kontura sedí)
- Features count dává smysl (vidíš 3 díry → 3 features = OK)

**WRONG** pokud:
- Dramaticky špatné rozměry (55mm → 8745mm)
- Missing major features (díra Ø20 chybí)
- Prismatic part detected as rotational
- Bore diameter je 0 když díra existuje

**SKIP** pokud:
- Nejsi si jistý
- Komplikovaný díl (multi-feature)
- Need to check PDF first

---

## Expected Outcomes

### Optimistic Scenario (85-95% accuracy)
→ AI Vision funguje, minor fixes potřeba
→ Prompt optimization (1-2 iterace)
→ Ready for time calculation

### Realistic Scenario (70-85% accuracy)
→ AI Vision OK, ale specific edge cases fail
→ Prompt improvements (3-5 iterací)
→ Add validation rules

### Pessimistic Scenario (<70% accuracy)
→ Major issues (wrong pipeline, bad prompt)
→ Redesign prompt structure
→ Consider hybrid approach

---

## Timeline

- **Now:** Batch test running (~10 min)
- **Then:** Your evaluation (~15-20 min for 37 files)
- **Next:** Analyze results + action plan (~5 min)
- **Total:** ~30-35 minutes

---

## Až budeš hotový

Pošli mi:
1. **Final accuracy %** (z HTML reportu)
2. **Top 3 fail cases** (které díly byly nejhorší?)
3. **Common patterns** (co se často děje špatně?)

A já:
1. Analyzuji failures
2. Navrhu prompt improvements
3. Re-testujeme

---

**Status:** ⏳ Waiting for batch test to complete...

Check progress:
```bash
tail -f /private/tmp/claude-501/-Users-lofas-Documents---App-Claude-Gestima/tasks/b05e152.output
```
