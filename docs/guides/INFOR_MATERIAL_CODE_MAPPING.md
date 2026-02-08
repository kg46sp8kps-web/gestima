# INFOR Material Code Mapping - Kompletní Reference

**Version:** 1.0
**Date:** 2026-02-03
**Source:** Analýza 3189 materiálů z Infor SLItems (FamilyCode = 'Materiál')

---

## 📋 Item Code Structure

### Standard Metal Format:
```
{W.Nr}-{SHAPE}{dimensions}-{SURFACE}
1.0036-HR005x005-T
│      │  │       └─ Surface treatment (optional)
│      │  └─────────── Dimensions (mm)
│      └────────────── Shape code
└───────────────────── Material norm (W.Nr)
```

### Plastic with Glass Fiber:
```
{MATERIAL}-{GF##}-{SHAPE}{dimensions}-{SURFACE}
PA66-GF30-KR030.000-L
│    │    │  │       └─ Surface treatment
│    │    │  └─────────── Dimensions
│    │    └────────────── Shape code
│    └─────────────────── Glass Fiber %
└──────────────────────── Plastic material
```

---

## 🔸 SHAPE CODES (Tvary)

### Standard Shapes (používané v parseru):

| Code | Count | % | Czech Name | English Name | Gestima Enum | Priority |
|------|-------|---|------------|--------------|--------------|----------|
| **DE** | 1085 | 39.5% | Deska/Plech | Plate/Sheet | `PLATE` | HIGH |
| **KR** | 766 | 27.9% | Tyč kruhová (Kulatina) | Round Bar | `ROUND_BAR` | HIGH |
| **HR** | 672 | 24.5% | Tyč čtvercová/plochá | Square/Flat Bar | `SQUARE_BAR` / `FLAT_BAR` | HIGH |
| **TR** | 127 | 4.6% | Trubka | Tube | `TUBE` | HIGH |
| **OK** | 81 | 2.9% | Tyč šestihranná | Hexagonal Bar | `HEXAGONAL_BAR` | HIGH |
| **L** | 12 | 0.4% | Úhelník (L-profil) | Angle (L-profile) | `ANGLE` | MEDIUM |
| **J** | 2 | 0.1% | Jekl (čtyřhran svařovaný) | Square Tube | `SQUARE_TUBE` | LOW |
| **U** | 1 | 0.0% | U profil | U Channel | `U_CHANNEL` | LOW |
| **UPE** | 1 | 0.0% | UPE profil | UPE Beam | `UPE_BEAM` | LOW |
| **SP** | 1 | 0.0% | Speciální profil | Special Profile | `SPECIAL_PROFILE` | LOW |

### Shape Detection Logic:

```python
# HR shape disambiguation:
# - HR with same dimensions (005x005) → SQUARE_BAR
# - HR with different dimensions (008x004) → FLAT_BAR

def detect_hr_shape(dimensions: str) -> StockShape:
    if 'x' in dimensions:
        parts = dimensions.split('x')
        if len(parts) == 2:
            w, h = parts[0], parts[1]
            if w == h:
                return StockShape.SQUARE_BAR
            else:
                return StockShape.FLAT_BAR
    return StockShape.FLAT_BAR  # default
```

---

## 🎨 SURFACE TREATMENT CODES (Povrchová úprava)

### Active Surface Treatments:

| Code | Count | % | Czech Name | English Name | Storage Field | Notes |
|------|-------|---|------------|--------------|---------------|-------|
| **T** | 863 | 44.2% | Tažená | Cold Drawn | `surface_treatment` | Nejčastější |
| **V** | 340 | 17.4% | Válená | Hot Rolled | `surface_treatment` | |
| **P** | 334 | 17.1% | ? | ? | `surface_treatment` | TBD význam |
| **L** | 168 | 8.6% | ? | ? | `surface_treatment` | TBD význam |
| **O** | 126 | 6.4% | Loupaná | Peeled | `surface_treatment` | |
| **F** | 56 | 2.9% | Frézovaná | Milled | `surface_treatment` | |
| **S** | 27 | 1.4% | Svařovaná? | Welded? | `surface_treatment` | |
| **Sv** | 11 | 0.6% | Svařovaná | Welded | `surface_treatment` | |
| **Vs** | 10 | 0.5% | Válcovaná za studena | Cold Rolled | `surface_treatment` | |
| **BLOK** | 7 | 0.4% | Blok | Block | `surface_treatment` | Speciální |
| **B** | 6 | 0.3% | ? | ? | `surface_treatment` | TBD význam |
| **Pl** | 3 | 0.2% | Plechový | Sheet Metal | `surface_treatment` | |
| **St** | 1 | 0.1% | ? | ? | `surface_treatment` | |
| **EP** | 1 | 0.1% | ? | ? | `surface_treatment` | |
| **vypalek** | 1 | 0.1% | Výpalek | Blank | `surface_treatment` | Error? |

### Surface Treatment Mapping:

```python
SURFACE_TREATMENT_MAP = {
    'T': 'cold_drawn',        # Tažená
    'V': 'hot_rolled',        # Válená
    'O': 'peeled',            # Loupaná
    'F': 'milled',            # Frézovaná
    'S': 'welded',            # Svařovaná
    'Sv': 'welded',           # Svařovaná
    'Vs': 'cold_rolled',      # Válcovaná za studena
    'BLOK': 'block',          # Blok
    'Pl': 'sheet_metal',      # Plechový
    # TBD:
    'P': 'unknown_p',
    'L': 'unknown_l',
    'B': 'unknown_b',
    'St': 'unknown_st',
    'EP': 'unknown_ep',
}
```

---

## 🔬 MATERIAL NORM PREFIXES (Materiálové normy)

### W.Nr (Werkstoffnummer) - German Standard:

| Prefix | Range | Material Type | Examples |
|--------|-------|---------------|----------|
| **1.0XXX** | 1.0000-1.0999 | Constructional Steel (Konstrukční ocel) | 1.0036, 1.0503, 1.0715 |
| **1.1XXX** | 1.1000-1.1999 | Free Cutting Steel (Automatová ocel) | 1.1191, 1.1730 |
| **1.2XXX** | 1.2000-1.2999 | Tool Steel (Nástrojová ocel) | 1.2316 |
| **1.4XXX** | 1.4000-1.4999 | Stainless Steel (Nerezová ocel) | 1.4301 |
| **2.0XXX** | 2.0000-2.0999 | Copper Alloys (Měď a slitiny) | 2.0060, 2.0280, 2.0321 |
| **2.1XXX** | 2.1000-2.1999 | Special Copper Alloys | 2.1182 |
| **3.XXXX** | 3.0000-3.9999 | Aluminum Alloys (Hliník a slitiny) | 3.1325, 3.2315, 3.3547 |

### Material Norm Detection:

```python
def detect_material_group_from_wnr(w_nr: str) -> str:
    """Detect material group from W.Nr"""
    if not w_nr or not w_nr.startswith('1.') and not w_nr.startswith('2.') and not w_nr.startswith('3.'):
        return None

    prefix = w_nr[:3]  # e.g., "1.0", "1.1", "1.2"

    MATERIAL_GROUP_MAP = {
        '1.0': 'Constructional Steel',
        '1.1': 'Free Cutting Steel',
        '1.2': 'Tool Steel',
        '1.4': 'Stainless Steel',
        '2.0': 'Copper',
        '2.1': 'Copper Alloys',
        '3.0': 'Aluminum 3000 series',
        '3.1': 'Aluminum 3100 series',
        '3.2': 'Aluminum 3200 series',
        '3.3': 'Aluminum 3300 series',
    }

    return MATERIAL_GROUP_MAP.get(prefix, 'Unknown')
```

---

## 🧪 PLASTIC MATERIALS (Plasty)

### Common Plastics:

| Code | Full Name | Czech Name | Properties |
|------|-----------|------------|------------|
| **PA6** | Polyamide 6 | Polyamid 6 | Engineering plastic |
| **PA66** | Polyamide 66 | Polyamid 66 | Engineering plastic |
| **PEEK** | Polyether Ether Ketone | PEEK | High-performance |
| **POM** | Polyoxymethylene | Polyacetal (Delrin) | Engineering plastic |
| **PTFE** | Polytetrafluoroethylene | Teflon | Low friction |
| **PVC** | Polyvinyl Chloride | PVC | General purpose |
| **PE** | Polyethylene | Polyetylen | General purpose |

### Glass Fiber (GF) Indicator:

- **GF30** = 30% glass fiber reinforcement
- **GF25** = 25% glass fiber reinforcement
- **LFX** = Long fiber reinforced

---

## 🚫 IGNORE PATTERNS (Položky k ignorování)

### Blanks (Výpalky):
```regex
^\d+-vypalek$
```
Example: `0044892-vypalek`

### Castings (Odlitky):
```regex
^\d+-odlitek$
```
Example: `1071185-odlitek`

### Waste Codes (Odpady):
```regex
^\d{6}(-[A-Z])?$
```
Example: `120101`, `120101-N`

### Special M-Codes:
```regex
^M-\d{4}-\d{3}-\d{3}$
```
Example: `M-2016-003-006`

---

## 📊 PARSER IMPLEMENTATION PRIORITY

### Phase 1: Core (83.8% coverage)
- ✅ METAL_FULL: `{W.Nr}-{SHAPE}{dims}-{SURFACE}`
- ✅ Shape codes: DE, KR, HR, TR, OK
- ✅ Surface treatments: T, V, O, F, Vs

### Phase 2: Extended (14.4% coverage)
- ⚠️ Profiles: L, U, UPE, J, SP
- ⚠️ METAL_NO_SURFACE: without surface treatment
- ⚠️ Complex dimensions (L, U profiles)

### Phase 3: Plastics (0.2% coverage)
- ⚠️ PLASTIC_GF_FULL: `{material}-GF##-{SHAPE}{dims}-{SURFACE}`
- ⚠️ PLASTIC_COMPLEX: with color codes

### Phase 4: Edge Cases (1% coverage)
- Ignore blanks, waste, castings
- Handle malformed items

---

## 🎯 SUCCESS METRICS

- **Target Coverage**: 98.5% (all except ignored items)
- **Current Coverage**: 94.5% (Phase 1 only)
- **Missing**: 4% (Profiles + edge cases)

---

## 📝 NOTES

1. **HR Shape Ambiguity**: Must parse dimensions to distinguish SQUARE_BAR vs FLAT_BAR
2. **Surface Treatment TBD**: Codes P, L, B, St, EP need clarification from user
3. **Material Norms**: Already have MaterialNorm table with W.Nr → MaterialGroup lookup
4. **Dimension Formats**:
   - Simple: `005x005` (square), `008x004` (flat)
   - Decimal: `004.000` (round), `001.3` (plate)
   - Complex: `020x020x03` (angle), `010x001.5` (tube wall)
   - Range: `005-130-175` (plate dimensions)

---

**End of Reference Document**
