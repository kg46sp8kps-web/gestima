# PLÁN: Oprava Waterline 2D Viewer - Zigzag Artifacts

**Datum:** 2026-02-07
**Problém:** Waterline kontura se zobrazuje jako zigzag, i když surová data jsou hladká
**Root cause:** Každá kontura (outer/inner) má vlastní škálování → deformace aspect ratio

---

## Analýza problému

### Co funguje ✅
- Backend endpoint `/api/feature-recognition-batch/step-waterline-2d/{filename}` vrací validní data
- Waterline extrakce z `batch_combined_results.json` produkuje hladké kontury (0-2% zigzag points)
- SVG rendering zobrazuje oba kontury (outer=modrá, inner=červená)

### Co nefunguje ❌
- **Visual artifact:** Kontura vypadá jako zuby pily místo hladkého profilu
- **Root cause:** `contourToPath()` funkce počítá `minR/maxR` SAMOSTATNĚ pro každou konturu
  - Outer contour má např. r ∈ [13.5, 27.5] → scaleY = 480 / 14
  - Inner contour má např. r ∈ [9.5, 9.5] → scaleY = 480 / 0 = ∞ (pak fallback na 1)
  - **Důsledek:** Stejný 1mm skok na outer vypadá jinak než na inner → aspect ratio porušen

### Důkaz
```typescript
// Waterline2DViewer.vue, lines 147-158
const allZ = contour.map(p => p[0])  // ← Každá kontura má VLASTNÍ min/max
const allR = contour.map(p => p[1])
const minZ = Math.min(...allZ)
const maxZ = Math.max(...allZ)
const minR = Math.min(...allR)       // ← Tady je problém!
const maxR = Math.max(...allR)

const rangeZ = maxZ - minZ || 1
const rangeR = maxR - minR || 1      // ← Outer: 14mm, Inner: 0mm

const scaleX = (svgWidth - 2 * margin) / rangeZ   // ← Různé škálování!
const scaleY = (svgHeight - 2 * margin) / rangeR  // ← Různé škálování!
```

---

## Řešení

### Varianta A: Unified Scaling (DOPORUČENO)
**Princip:** Vypočítat JEDEN společný bounding box pro OBJE kontury najednou

**Implementace:**
1. Přidat computed property `globalBounds`:
   ```typescript
   const globalBounds = computed(() => {
     if (!waterlineData.value) return null

     const allPoints = [
       ...waterlineData.value.outer_contour,
       ...waterlineData.value.inner_contour
     ]

     const allZ = allPoints.map(p => p[0])
     const allR = allPoints.map(p => p[1])

     return {
       minZ: Math.min(...allZ),
       maxZ: Math.max(...allZ),
       minR: Math.min(...allR),
       maxR: Math.max(...allR)
     }
   })
   ```

2. Upravit `contourToPath()` aby přijímal `bounds` parametr:
   ```typescript
   function contourToPath(contour: number[][], bounds: any): string {
     const rangeZ = bounds.maxZ - bounds.minZ || 1
     const rangeR = bounds.maxR - bounds.minR || 1

     const scaleX = (svgWidth - 2 * margin) / rangeZ
     const scaleY = (svgHeight - 2 * margin) / rangeR

     return contour.map(([z, r]) => {
       const x = margin + (z - bounds.minZ) * scaleX
       const y = svgHeight - margin - (r - bounds.minR) * scaleY
       return `${x},${y}`
     }).join(' ')
   }
   ```

3. Update computed properties:
   ```typescript
   const outerContourPath = computed(() => {
     if (!waterlineData.value || !globalBounds.value) return ''
     return contourToPath(waterlineData.value.outer_contour, globalBounds.value)
   })

   const innerContourPath = computed(() => {
     if (!waterlineData.value || !globalBounds.value) return ''
     return contourToPath(waterlineData.value.inner_contour, globalBounds.value)
   })
   ```

**Výhody:**
- ✅ Zachová aspect ratio (1mm v R = 1mm v Z vizuálně)
- ✅ Outer a inner kontura ve správném měřítku vůči sobě
- ✅ Minimální změna kódu (~10 řádků)

**Nevýhody:**
- ⚠️ Pokud inner contour je malá/prázdná, viewport se zbytečně zvětší

---

### Varianta B: Aspect Ratio Lock
**Princip:** Vynucovat `scaleX === scaleY` (jednotkový aspect ratio)

**Implementace:**
```typescript
const rangeZ = maxZ - minZ || 1
const rangeR = maxR - minR || 1

const scaleX = (svgWidth - 2 * margin) / rangeZ
const scaleY_candidate = (svgHeight - 2 * margin) / rangeR

// Force 1:1 aspect ratio
const scale = Math.min(scaleX, scaleY_candidate)
const scaleX_final = scale
const scaleY_final = scale
```

**Výhody:**
- ✅ Garantuje 1:1 aspect ratio
- ✅ Každá kontura může mít vlastní bounds (flexibilnější)

**Nevýhody:**
- ❌ Může vyplývat prázdné místo v SVG viewportu
- ❌ Složitější centrování

---

### Varianta C: Separate SVG viewBox per contour
**Princip:** Každá kontura má vlastní `<svg>` s vlastním viewBox

**Neimplementovat** — rozdělené grafy = ztráta kontextu (uživatel neuvidí vztah outer↔inner)

---

## Doporučení

**✅ Použít Variantu A (Unified Scaling)**

**Důvod:** ROT díly VŽDY mají inner + outer konturu, která reprezentuje JEDEN díl. Unified scaling zachová jejich geometrický vztah.

---

## Implementační checklist

- [ ] Přidat `globalBounds` computed property (sloučit outer+inner body)
- [ ] Upravit `contourToPath(contour, bounds)` signature
- [ ] Update `outerContourPath` computed (předat bounds)
- [ ] Update `innerContourPath` computed (předat bounds)
- [ ] Update `getOperationPath()` funkci (pokud používá contourToPath)
- [ ] Test na 3+ ROT dílech (různé aspect ratio)
- [ ] Verify že operace highlight správně mapuje na konturu

---

## Testovací soubory

```
✅ 10383459_7f06bbe6.stp        (178 points, 0% zigzag)
✅ JR 810671.ipt.step           (176 points, 2.3% zigzag)
✅ PDM-249322_03.stp            (ROT part)
```

---

## Odhadovaný čas

- **Implementace:** 5 min (7 řádků změn)
- **Testing:** 10 min (3 ROT díly + screenshot check)
- **Total:** 15 min

---

## Po implementaci

1. Screenshot PŘED/PO pro user verification
2. Update CLAUDE.local.md s poznámkou "Waterline 2D scaling bug fixed"
3. Commit: `fix(visualization): unified scaling for waterline contours (ADR-TBD)`

---

**Status:** READY TO IMPLEMENT (čeká na user approval)
