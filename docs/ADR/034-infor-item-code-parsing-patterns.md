# ADR-034: Infor Item Code Parsing Patterns

**Status:** Implemented
**Date:** 2026-02-03
**Context:** Material import from Infor CloudSuite Industrial (SyteLine)

---

## Problem

Infor Item codes contain structured information about materials:
- Material norm (W.Nr)
- Stock shape
- Dimensions
- Surface treatment

**Example:** `1.0503-HR016x016-T`

The parser must extract all components reliably for MaterialItem creation.

---

## Decision

**Item Code is MASTER source.** Description is FALLBACK only.

### Priority Order

1. **Item code** (MASTER) - structured, reliable format
2. **Description** (FALLBACK) - free text, Czech/English mix

---

## Item Code Format

```
{W.Nr}-{SHAPE}{dimensions}-{SURFACE}
```

| Component | Pattern | Example |
|-----------|---------|---------|
| W.Nr | `1.xxxx`, `2.xxxx`, `3.xxxx` | `1.0503` |
| Shape | `KR`, `HR`, `OK`, `DE`, `TR` | `HR` |
| Dimensions | varies by shape | `016x016` |
| Surface | `T`, `V`, `P`, `O`, `F`, `B`, etc. | `T` |

---

## Shape Codes

| Code | Shape | GESTIMA Enum | Dimensions |
|------|-------|--------------|------------|
| **KR** | Round bar (kulatina) | `ROUND_BAR` | diameter |
| **HR** | Square/Flat bar | `SQUARE_BAR` / `FLAT_BAR` | width × thickness |
| **OK** | Hexagonal bar (šestihran) | `HEXAGONAL_BAR` | SW (width) |
| **DE** | Plate (deska/plech) | `PLATE` | thickness-width(-length) |
| **TR** | Tube (trubka) | `TUBE` | diameter × wall / width × height × wall |

### HR Disambiguation

HR can be SQUARE_BAR or FLAT_BAR:
- `HR010x010` → width=10, thickness=10 → **SQUARE_BAR**
- `HR020x003` → width=20, thickness=3 → **FLAT_BAR**

```python
if width == thickness:
    return StockShape.SQUARE_BAR
else:
    return StockShape.FLAT_BAR
```

---

## Dimension Parsing Patterns

### Pattern 1: Round Bar (KR)

```
{W.Nr}-KR{diameter}-{SURF}
{W.Nr}-KR{diameter}.000-{SURF}
```

| Example | diameter |
|---------|----------|
| `1.0503-KR016-T` | 16 |
| `1.0503-KR020.000-B` | 20 |

**Regex:** `-KR(\d+)(?:\.\d+)?-?`

### Pattern 2: Square/Flat Bar (HR)

```
{W.Nr}-HR{width}x{thickness}-{SURF}
```

| Example | width | thickness | Shape |
|---------|-------|-----------|-------|
| `1.0503-HR010x010-T` | 10 | 10 | SQUARE_BAR |
| `1.0503-HR020x003-P` | 20 | 3 | FLAT_BAR |

**Regex:** `-HR(\d+)(?:\.\d+)?[xX]+(\d+)(?:\.\d+)?(?:-|$)`

### Pattern 3: Hexagonal Bar (OK)

```
{W.Nr}-OK{SW}-{SURF}
{W.Nr}-OK{SW}.000-{SURF}
```

| Example | width (SW) |
|---------|------------|
| `1.0503-OK017-T` | 17 |
| `1.0503-OK019.000-V` | 19 |

SW = Schlüsselweite (across flats). Stored as `width`.

**Regex:** `-OK(\d+)(?:\.\d+)?-?`

### Pattern 4: Plate (DE)

```
{W.Nr}-DE{thickness}-{width}-{SURF}
{W.Nr}-DE{thickness}-{width}-{length}-{SURF}
```

| Example | thickness | width | length |
|---------|-----------|-------|--------|
| `3.3547-DE010-042-F` | 10 | 42 | - |
| `3.3547-DE010-038-066-L` | 10 | 38 | 66 |

**Regex:** `-DE(\d+)-(\d+)(?:-(\d+))?(?:-[A-Z]+)?$`

### Pattern 5a: Round Tube (TR - 2 dimensions)

```
{W.Nr}-TR{diameter}x{wall}-{SURF}
{W.Nr}-TR{diameter}.000x{wall}-{SURF}
```

| Example | diameter | wall_thickness |
|---------|----------|----------------|
| `1.0039-TR032x002-T` | 32 | 2 |
| `1.0039-TR060.000x003-V` | 60 | 3 |

**Regex:** `-TR(\d+)(?:\.\d+)?[xX]+(\d+)(?:\.\d+)?(?:-|$)`

### Pattern 5b: Rectangular Tube (TR - 3 dimensions)

```
{W.Nr}-TR{width}x{height}x{wall}-{SURF}
```

| Example | width | height (→thickness) | wall_thickness |
|---------|-------|---------------------|----------------|
| `1.0039-TR080x040x02-Sv` | 80 | 40 | 2 |
| `1.0039-TR060x030x03-T` | 60 | 30 | 3 |

Height stored as `thickness` for consistency.

**Regex:** `-TR(\d+)(?:\.\d+)?[xX]+(\d+)(?:\.\d+)?[xX]+(\d+)`

---

## Surface Treatment Codes

| Code | Czech | English | Frequency |
|------|-------|---------|-----------|
| **T** | Tažená | Cold drawn | 44% |
| **V** | Válená | Hot rolled | 17% |
| **P** | Lisovaná | Pressed | 17% |
| **L** | Litá | Cast | 9% |
| **O** | Loupaná | Peeled | 6% |
| **F** | Frézovaná | Milled | 3% |
| **B** | Broušená | Ground | <1% |
| **S** | Svařovaná | Welded | 1% |
| **Sv** | Svařovaná | Welded | <1% |
| **Vs** | Válcovaná za studena | Cold rolled | <1% |
| **BLOK** | Blok | Block | <1% |
| **EP** | Elox Plus | Anodized | <1% |
| **K** | Kovaná | Forged | - |
| **H** | Kalená | Hardened | - |
| **N** | Normalizovaná | Normalized | - |
| **Z** | Pozinkovaná | Galvanized | - |

### Surface Treatment Detection

Surface can appear:
- At end: `1.0503-KR016-T`
- Before tolerance: `1.0503-KR020.000-B-h6`
- After tolerance: `1.0503-KR016.000-f7-B`

**Strategy:** Search for known codes anywhere in Item code, avoiding shape codes (KR, HR, DE, TR, OK).

**Regex:** `-{CODE}(?:-|\.|$)` for each known code

---

## Implementation

### File: `app/services/infor_material_importer_v2.py`

```python
class MaterialImporter(InforImporterBase[MaterialItem]):

    def parse_shape_from_item_code(self, item_code: str, dims: Dict) -> Optional[StockShape]:
        """Parse shape from Item code (MASTER)"""
        match = re.search(r'-([A-Z]{2})\d', item_code.upper())
        if not match:
            return None

        shape_code = match.group(1)
        shape_map = {
            'KR': StockShape.ROUND_BAR,
            'OK': StockShape.HEXAGONAL_BAR,
            'DE': StockShape.PLATE,
            'TR': StockShape.TUBE,
        }

        if shape_code in shape_map:
            return shape_map[shape_code]

        # HR: disambiguate by dimensions
        if shape_code == 'HR':
            width = dims.get("width")
            thickness = dims.get("thickness")
            if width and thickness and width == thickness:
                return StockShape.SQUARE_BAR
            return StockShape.FLAT_BAR

        return None

    def parse_dimensions_from_item_code(self, item_code: str) -> Dict[str, Optional[float]]:
        """Parse dimensions from Item code (MASTER)"""
        dims = {"diameter": None, "width": None, "thickness": None,
                "wall_thickness": None, "standard_length": None}

        item_upper = item_code.upper()

        # Pattern 1: DE dash-separated
        de_match = re.search(r'-DE(\d+)-(\d+)(?:-(\d+))?(?:-[A-Z]+)?$', item_upper)
        if de_match:
            dims["thickness"] = float(de_match.group(1))
            dims["width"] = float(de_match.group(2))
            if de_match.group(3):
                dims["standard_length"] = float(de_match.group(3))
            return dims

        # Pattern 2a: Rectangular tube (3 dims)
        rect_tube = re.search(r'-TR(\d+)(?:\.\d+)?[xX]+(\d+)(?:\.\d+)?[xX]+(\d+)', item_upper)
        if rect_tube:
            dims["width"] = float(rect_tube.group(1))
            dims["thickness"] = float(rect_tube.group(2))
            dims["wall_thickness"] = float(rect_tube.group(3))
            return dims

        # Pattern 2b: HR/TR with x separator (2 dims)
        x_match = re.search(r'-([A-Z]{2})(\d+)(?:\.\d+)?[xX]+(\d+)(?:\.\d+)?(?:-|$)', item_upper)
        if x_match:
            shape_code = x_match.group(1)
            dim1, dim2 = int(x_match.group(2)), int(x_match.group(3))
            if shape_code == 'HR':
                dims["width"] = float(dim1)
                dims["thickness"] = float(dim1) if dim1 == dim2 else float(dim2)
            elif shape_code == 'TR':
                dims["diameter"] = float(dim1)
                dims["wall_thickness"] = float(dim2)
            return dims

        # Pattern 3: Single dimension (KR, OK, HR simple)
        single = re.search(r'-([A-Z]{2})(\d+)-?', item_upper)
        if single:
            shape_code, dim = single.group(1), int(single.group(2))
            if shape_code == 'KR':
                dims["diameter"] = float(dim)
            elif shape_code == 'OK':
                dims["width"] = float(dim)
            elif shape_code == 'DE':
                dims["thickness"] = float(dim)
            elif shape_code == 'HR':
                dims["width"] = float(dim)

        return dims

    def extract_surface_treatment(self, item_code: str) -> Optional[str]:
        """Extract surface treatment from Item code"""
        item_upper = item_code.upper()

        # Search known codes (longer first)
        for code in sorted(SURFACE_TREATMENT_CODES.keys(), key=len, reverse=True):
            pattern = rf'-{re.escape(code)}(?:-|\.|$)'
            if re.search(pattern, item_upper):
                return code

        # Fallback: 1-2 letter code at end (not shape code)
        shape_codes = {'KR', 'HR', 'DE', 'TR', 'OK'}
        match = re.search(r'-([A-Z]{1,2})$', item_upper)
        if match and match.group(1) not in shape_codes:
            return match.group(1)

        return None
```

---

## Frontend Display

### Staging Table Columns

| Column | Field | Shapes |
|--------|-------|--------|
| Ø | diameter | ROUND_BAR, TUBE (round) |
| WT | wall_thickness | TUBE |
| W | width | SQUARE_BAR, FLAT_BAR, HEX, PLATE, TUBE (rect) |
| T | thickness | FLAT_BAR, PLATE, TUBE (rect height) |
| L | standard_length | PLATE (cut pieces) |

### Surface Treatment Label

```typescript
export function getSurfaceTreatmentLabel(code: string | null): string {
  if (!code) return ''
  const label = SURFACE_TREATMENT_LABELS[code]
  return label ? `${code} - ${label}` : code
}
```

---

## Test Cases

| Item Code | Shape | Ø | WT | W | T | L | Surf |
|-----------|-------|---|----|----|---|---|------|
| `1.0503-KR016-T` | round_bar | 16 | - | - | - | - | T |
| `1.0503-HR010x010-T` | square_bar | - | - | 10 | 10 | - | T |
| `1.0503-HR020x003-P` | flat_bar | - | - | 20 | 3 | - | P |
| `1.0503-OK017-V` | hexagonal_bar | - | - | 17 | - | - | V |
| `3.3547-DE010-042-F` | plate | - | - | 42 | 10 | - | F |
| `3.3547-DE010-038-066-L` | plate | - | - | 38 | 10 | 66 | L |
| `1.0039-TR032x002-T` | tube | 32 | 2 | - | - | - | T |
| `1.0039-TR080x040x02-Sv` | tube | - | 2 | 80 | 40 | - | Sv |
| `1.0503-KR020.000-B-h6` | round_bar | 20 | - | - | - | - | B |

---

## Related ADRs

- [ADR-032: Infor Material Import System](./032-infor-material-import-system.md)
- [ADR-033: Surface Treatment Integration](./033-surface-treatment-integration.md)
- [ADR-016: Material Parser Strategy](./016-material-parser-strategy.md) (quick input)

---

## Files

- `app/services/infor_material_importer_v2.py` - Parser implementation
- `app/routers/infor_router.py` - Test pattern endpoint
- `frontend/src/components/modules/infor/InforMaterialImportPanel.vue` - UI
- `frontend/src/types/infor.ts` - Surface treatment labels
