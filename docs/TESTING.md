# GESTIMA - Testování

## 📋 Přehled testů

### Testovací soubory

| Soubor | Počet testů | Pokrytí |
|--------|-------------|---------|
| test_authentication.py | 27 | Auth + RBAC + role hierarchy |
| test_backup.py | 10 | Backup/restore/list/cleanup |
| test_rate_limiting.py | 9 | Rate limiter + config |
| test_pricing.py | 9 | Cenová kalkulace polotovarů |
| test_conditions.py | ? | Řezné podmínky |
| test_error_handling.py | 6 | Transaction error handling |

### Kritické testy (označené `@pytest.mark.critical`)

Tyto testy **MUSÍ** vždy procházet před nasazením. Pokrývají:
- Výpočty cen (materiál, strojní čas)
- Výpočty časů operací
- Kalkulace dávek
- Authentication & Authorization
- Backup & Restore

---

## 🧪 Testy cenové kalkulace

**Soubor:** `tests/test_pricing.py`

### Pokryté scénáře:

#### 1. **Tyč (rod)** - `test_material_cost_rod_steel`
- Vstup: ø50 × 100mm, konstrukcní ocel
- Vzorec: `π × r² × délka`
- Kontrola: objem, hmotnost, cena

#### 2. **Trubka (tube)** - `test_material_cost_tube`
- Vstup: ø50/40 × 100mm (vnější/vnitřní), konstrukcní ocel
- Vzorec: `π × (r_outer² - r_inner²) × délka`
- Kontrola: objem dutiny, hmotnost, cena

#### 3. **Přířez (billet)** - `test_material_cost_billet`
- Vstup: 100×50×30mm, konstrukcní ocel
- Vzorec: `délka × šířka × výška`
- Kontrola: objem kvádru, hmotnost, cena

#### 4. **Plech (sheet)** - `test_material_cost_sheet`
- Vstup: 1000×500×5mm, konstrukcní ocel
- Vzorec: `délka × šířka × tloušťka`
- Kontrola: objem, hmotnost, cena

#### 5. **Odlitek (casting)** - `test_material_cost_casting`
- Vstup: ø80 × 150mm, litina
- Vzorec: `π × r² × délka` (jako tyč)
- Kontrola: objem, hmotnost z DB hustoty

#### 6. **Nerez (stainless)** - `test_material_cost_stainless`
- Vstup: ø50 × 100mm, nerez austenitická
- Kontrola: jiná hustota (7.90) a cena (120 Kč/kg)

#### 7. **Nulové rozměry** - `test_material_cost_zero_dimensions`
- Vstup: ø0 × 0mm
- Očekávaný výsledek: `volume=0, weight=0, cost=0`

#### 8. **Neexistující materiál** - `test_material_cost_invalid_material`
- Vstup: neznámý materiál
- Očekávaný výsledek: fallback hodnoty (density=7.85, price=30)

#### 9. **Strojní čas** - `test_machining_cost_basic`
- Vstup: 5 min, 1200 Kč/hod
- Vzorec: `(čas_min / 60) × hodinová_sazba`

---

## 🚀 Spuštění testů

### Všechny testy:
```bash
pytest tests/test_pricing.py -v
```

### Jen kritické testy:
```bash
pytest tests/test_pricing.py -v -m critical
```

### S pokrytím kódu:
```bash
pytest tests/test_pricing.py --cov=app/services/price_calculator --cov-report=term-missing
```

---

## ✅ Očekávaný výsledek

```
============================= test session starts ==============================
tests/test_pricing.py::test_material_cost_rod_steel PASSED               [ 11%]
tests/test_pricing.py::test_material_cost_tube PASSED                    [ 22%]
tests/test_pricing.py::test_material_cost_billet PASSED                  [ 33%]
tests/test_pricing.py::test_material_cost_sheet PASSED                   [ 44%]
tests/test_pricing.py::test_material_cost_casting PASSED                 [ 55%]
tests/test_pricing.py::test_material_cost_stainless PASSED               [ 66%]
tests/test_pricing.py::test_material_cost_zero_dimensions PASSED         [ 77%]
tests/test_pricing.py::test_material_cost_invalid_material PASSED        [ 88%]
tests/test_pricing.py::test_machining_cost_basic PASSED                  [100%]

============================== 9 passed in 0.08s
```

---

## 📝 Pravidla pro testy

### 1. **Kritické funkce MUSÍ mít testy**
- Výpočty cen (materiál, strojní čas)
- Výpočty časů operací
- Kalkulace dávek
- Validace vstupů

### 2. **Nepoužívat hardcoded hodnoty z DB**
```python
# ❌ ŠPATNĚ - hardcoded cena
expected_cost = weight * 30  # Co když se cena změní v DB?

# ✅ SPRÁVNĚ - použít vrácený výsledek
expected_cost = weight * result.price_per_kg
```

### 3. **Testovat edge cases**
- Nulové hodnoty
- Záporné hodnoty (pokud jsou validovány)
- Neexistující data (fallback)
- Maximální hodnoty

### 4. **Tolerance pro float porovnání**
```python
# ✅ SPRÁVNĚ - tolerance pro zaokrouhlení
assert abs(result.weight_kg - expected_weight) < 0.01

# Nebo pomocí pytest.approx
assert result.cost == pytest.approx(expected_cost, rel=0.01)
```

---

## 🔧 Přidání nového testu

1. Vytvoř test funkci s prefixem `test_`
2. Označ kritické testy: `@pytest.mark.critical`
3. Označ business logiku: `@pytest.mark.business`
4. Pro async funkce: `@pytest.mark.asyncio`
5. Dokumentuj co test dělá (docstring)

```python
@pytest.mark.business
@pytest.mark.critical
@pytest.mark.asyncio
async def test_material_cost_new_type():
    """KRITICKÝ TEST: Popis co test dělá"""
    result = await calculate_material_cost(...)
    
    # Assertions
    assert result.volume_mm3 > 0
    assert result.cost > 0
```

---

**Poslední aktualizace:** 2026-01-23  
**Pokrytí:** 9 testů pro cenovou kalkulaci polotovarů
