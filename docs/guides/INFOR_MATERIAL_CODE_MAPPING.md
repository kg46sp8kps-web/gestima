# Infor Material Code Mapping — Reference

**Source:** Analýza 3189 materiálů z Infor SLItems (FamilyCode = 'Materiál')

---

## Item Code Format

```
{W.Nr}-{SHAPE}{dimensions}-{SURFACE}
1.0036-HR005x005-T

Plasty:
{MATERIAL}-{GF##}-{SHAPE}{dimensions}-{SURFACE}
PA66-GF30-KR030.000-L
```

---

## Shape Codes

| Code | % | Gestima Enum | Poznámka |
|------|---|--------------|---------|
| DE | 39.5% | `PLATE` | |
| KR | 27.9% | `ROUND_BAR` | |
| HR | 24.5% | `SQUARE_BAR` / `FLAT_BAR` | stejné rozměry = SQUARE, různé = FLAT |
| TR | 4.6% | `TUBE` | |
| OK | 2.9% | `HEXAGONAL_BAR` | |
| L, J, U, UPE, SP | <1% | profily | nízká priorita |

---

## Surface Treatment Codes

### Kovy (metals)

| Code | Meaning |
|------|---------|
| T | cold_drawn (tažená) |
| V | hot_rolled (válená) |
| O | peeled (loupaná) |
| F | milled (frézovaná) |
| Vs | cold_rolled |
| S / Sv | welded (svařovaná) |

### Plasty (plastics) — suffix po rozměrech

**Výrobní metoda:**

| Code | Meaning |
|------|---------|
| P | Lisovaný (pressed/extruded) |
| L | Litý (cast) |

**Barva (poslední suffix):**

| Code | Meaning |
|------|---------|
| B | Černý (black) |
| N | Natur (natural) |
| G | Šedivý (grey) |

Uloženo jako kombinace: `L/N` = litý natur, `P/B` = lisovaný černý.

---

## W.Nr / Material Code → MaterialGroup

### Kovy (W.Nr prefix)

| Prefix | Typ |
|--------|-----|
| 1.0xxx | Ocel konstrukční |
| 1.1xxx | Ocel automatová |
| 1.2xxx | Ocel nástrojová |
| 1.4xxx | Nerez |
| 2.0xxx | Měď a slitiny |
| 2.1xxx | Speciální slitiny mědi |
| 3.xxxx | Hliník a slitiny |

### Plasty (textový kód v w_nr)

| Kód | Materiál |
|-----|---------|
| POM-C | Polyacetal kopolymer |
| POM-H | Polyacetal homopolymer |
| PA6 | Polyamid 6 |
| PA66 | Polyamid 66 |
| PA66-GF30 | PA66 + 30% sklo |
| PE500 | Polyethylen PE-HD 500 |
| UHMW-PE | Ultra-high molecular weight PE |
| PEEK | Polyéteréterketón |
| PEEK-GF30 | PEEK + 30% sklo |
| PTFE | Teflon |

Lookup přes MaterialNorm tabulku (w_nr → MaterialGroup) — NE přes prefix přímý mapping.

---

## Plastic Item Code Examples

```
POM-C-DE010-028-L-N       → POM-C,  deska tl.10 šíře 28,  litý natur
PA6-KR050.000-P-B          → PA6,    kulatina D50,         lisovaný černý
PE500-DE030-65-750-N       → PE500,  deska tl.30 šíře 65 délka 750, natur
PEEK-GF30-DE050-000-L      → PEEK GF30, deska tl.50,      litý
UHMW-PE-DE040-000-L-B      → UHMW-PE, deska tl.40,        litý černý
```

---

## Ignore Patterns

```
výpalky:  /^\d+-vypalek$/
odlitky:  /^\d+-odlitek$/
odpady:   /^\d{6}(-[A-Z])?$/
M-kódy:   /^M-\d{4}-\d{3}-\d{3}$/
```

---

## Parser Coverage

- Phase 1 (done): DE, KR, HR, TR, OK + surface T/V/O/F/Vs — pokrytí ~84%
- Phase 2 (pending): L, U, UPE, J profily — ~14%
- Phase 3 (done): Plasty s GF, barvy, výrobní metoda — ~0.2%
