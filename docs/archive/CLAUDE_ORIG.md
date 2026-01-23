# CLAUDE.md - Pravidla pro AI Asistenta

## 🎯 Před každým úkolem

1. **Přečti:** [ARCHITECTURE.md](ARCHITECTURE.md) - pochop strukturu
2. **Přečti:** [DB_ARCHITECTURE.md](DB_ARCHITECTURE.md) - pochop data
3. **Přečti:** [FUTURE_STEPS.md](FUTURE_STEPS.md) - co dělat
4. **Přečti:** [LESSONS.md](docs/LESSONS.md) - neudělej stejné chyby
5. **Vždy Read před Edit/Write** - nikdy nepředpokládej obsah

---

## 🔴 NIKDY NEDĚLAT (Kritické)

### 1. Výpočty v JavaScriptu
❌ **ŠPATNĚ:**
```javascript
const time = (Math.PI * diameter * length) / (1000 * vc);
element.textContent = time;
```

✅ **SPRÁVNĚ:**
```javascript
const response = await fetch(`/api/operations/${id}/recalculate`);
const data = await response.json();
element.textContent = data.predicted_time_sec;
```

**Pravidlo:** VŠECHNY výpočty POUZE v Pythonu (services/)

---

### 2. Duplikace logiky
❌ **ŠPATNĚ:** Stejný výpočet v Python + JavaScript
✅ **SPRÁVNĚ:** Python počítá → API vrací → JavaScript zobrazuje

**Pravidlo:** Single Source of Truth (LESSONS L-002)

---

### 3. Částečný update UI
❌ **ŠPATNĚ:**
```javascript
// Aktualizuješ jen čas operace, features zůstanou staré!
updateOperationTime(data.operation.unit_time_min);
```

✅ **SPRÁVNĚ:**
```javascript
// Backend změnil VŠECHNO → frontend aktualizuje VŠECHNO
updateOperationTime(data.operation.unit_time_min);
data.features.forEach(f => {
    updateFeatureTime(f.id, f.predicted_time_sec);
    updateFeatureConditions(f.id, f.vc, f.f, f.ap);
});
updateModeIndicator(data.operation.cutting_mode);
```

**Pravidlo:** Po API volání aktualizovat VŠE co backend změnil (LESSONS L-002)

---

### 4. Ztráta stavu UI
❌ **ŠPATNĚ:**
```javascript
// Přepsat celý HTML → ztratí expanded state
element.innerHTML = newHTML;
```

✅ **SPRÁVNĚ:**
```javascript
// Zapamatovat stav → aktualizovat data → obnovit stav
const wasExpanded = isExpanded(id);
updateData(id, newData);
if (wasExpanded) expand(id);
```

**Pravidlo:** Zachovat expanded, scroll pozice (LESSONS L-003)

---

### 5. Přepsat celý soubor
❌ **ŠPATNĚ:** Write tool pro změnu 3 řádků (→ 7800 tokenů ztráta)
✅ **SPRÁVNĚ:** Edit tool s old_string/new_string

**Pravidlo:** Edit pro změny, Write pouze pro nové soubory (LESSONS L-004)

---

### 6. Hardcoded hodnoty
❌ **ŠPATNĚ:**
```html
<option value="11xxx">Ocel nelegovaná</option>
<option value="12xxx">Ocel legovaná</option>
<!-- 14x opakování... -->
```

✅ **SPRÁVNĚ:**
```javascript
const materials = await fetch('/api/data/materials').then(r => r.json());
```
```html
<template x-for="mat in materials">
    <option :value="mat.code" x-text="mat.name"></option>
</template>
```

**Pravidlo:** Data z DB → API → JavaScript (LESSONS L-008)

---

### 7. Použít x-collapse pro dlouhý obsah
❌ **ŠPATNĚ:** `x-collapse` na sekci s 10+ řádky → oříznutý obsah
✅ **SPRÁVNĚ:** `x-show` bez animace pro dlouhý obsah

**Pravidlo:** `x-collapse` max 3-4 řádky (LESSONS L-009)

---

## ✅ VŽDY DĚLAT

### 1. API First approach
```
User Action → POST /api/... → Backend (calculate + save) → JSON → UI Update
```

### 2. Type hints everywhere
```python
def calculate_time(diameter: float, length: float, vc: float) -> float:
    """Vypočítá čas obrábění."""
    return (math.pi * diameter * length) / (1000 * vc)
```

### 3. Tests pro business logiku
```python
@pytest.mark.critical
async def test_time_calculation():
    """Test výpočtu času soustružení."""
    time = calculate_turning_time(d=50, l=100, vc=200, f=0.2, ap=2)
    assert time == pytest.approx(39.27, rel=0.01)
```

### 4. Error handling
```python
try:
    part = await session.get(Part, part_id)
    if not part:
        raise HTTPException(404, "Díl nenalezen")
except SQLAlchemyError as e:
    raise HTTPException(500, f"DB error: {e}")
```

### 5. Dokumentace (česky)
```python
def calculate_stock_volume(stock_type: str, **dims) -> float:
    """
    Vypočítá objem polotovaru v mm³.

    Args:
        stock_type: Typ polotovaru (tyc/trubka/prizez...)
        **dims: Rozměry (diameter, length, width, height...)

    Returns:
        Objem v mm³

    Raises:
        ValueError: Pokud stock_type není podporován
    """
```

---

## 📝 Workflow pro každý úkol

### 1. Analýza (POVINNÉ)
```
- [ ] Přečíst FUTURE_STEPS.md → co dělat
- [ ] Přečíst LESSONS.md → jak NEudělat chybu
- [ ] Identifikovat soubory k úpravě
- [ ] Přečíst soubory (Read tool)
```

### 2. Implementace
```
- [ ] Backend: API endpoint (router + service)
- [ ] Backend: Tests (pytest)
- [ ] Frontend: JavaScript (Alpine.js/HTMX)
- [ ] Frontend: HTML template (Jinja2)
- [ ] Frontend: CSS (gestima.css)
```

### 3. Testování
```
- [ ] pytest -v -m critical
- [ ] Spustit app (uvicorn)
- [ ] Otevřít v prohlížeči
- [ ] Manuální test:
    - Vytvořit díl
    - Přidat operaci
    - Přidat feature
    - Ověřit časy
    - Ověřit ceny
    - Změnit MODE
    - Ověřit live update
```

### 4. Checklist před dokončením
```
- [ ] Jeden zdroj pravdy (Python)
- [ ] UI update po API volání
- [ ] Zachován expanded state
- [ ] Type hints
- [ ] Tests
- [ ] Dokumentace (komentáře)
- [ ] Žádné hardcoded hodnoty
- [ ] Použit Edit (ne Write) pro změny
```

---

## 🎨 Coding Style

### Python (PEP 8 + project style)
```python
# Názvy: snake_case
def calculate_time_sec(diameter: float) -> float:
    pass

# Constants: UPPER_CASE
MAX_RPM = 3000

# Classes: PascalCase
class PartModel(Base):
    pass

# Async všude kde možné
async def get_part(part_id: int) -> Part:
    async with AsyncSession() as session:
        result = await session.execute(select(Part).where(Part.id == part_id))
        return result.scalar_one_or_none()
```

### JavaScript (Alpine.js style)
```javascript
// Alpine.js component
x-data="partEdit({{ part.id }})"

// Event handlers
@click="updatePart()"
@input="updateStockPrice()"

// Reactive binding
x-model="partData.material_group"

// Conditional display
x-show="expanded"
x-text="stockPrice"
```

### HTML (Jinja2 + semantic)
```html
<!-- Semantic structure -->
<div class="ribbon">
    <div class="ribbon-header">
        <div class="ribbon-title">📋 Title</div>
    </div>
    <div class="ribbon-body" x-show="expanded">
        <!-- Content -->
    </div>
</div>

<!-- Jinja2 variables -->
{{ part.part_number }}
{{ part.name or '-' }}

<!-- Jinja2 loops -->
{% for operation in part.operations %}
    <div>{{ operation.sequence }}. {{ operation.operation_type }}</div>
{% endfor %}
```

---

## 🔍 Debugging Checklist

### Backend (Python)
```bash
# Logs
tail -f logs/gestima.log

# SQL queries
# V config.py: DEBUG=True → echo SQL

# Tests
pytest -v -k "test_time" --pdb  # Debug mode
```

### Frontend (Browser)
```javascript
// Console
console.log('data:', data);

// Alpine.js debug
<div x-data="..." x-init="console.log($data)">

// Network tab
// Kontrola API responses (200? JSON správný?)
```

### Časté problémy
| Symptom | Možná příčina | Řešení |
|---------|---------------|--------|
| Čas se nezobrazuje | API nevrací `predicted_time_sec` | Zkontrolovat response JSON |
| Čas se liší po uložení | Výpočet v JS + Python | Smazat JS výpočet, použít API |
| UI se neaktualizuje | Zapomenuté update po API | Aktualizovat VŠE co backend změnil |
| Expanded state zmizel | innerHTML = newHTML | Použít granulární update |
| Dropdown prázdný | Hardcoded options | Načíst z API |

---

## 📚 Reference

### Klíčové soubory
- [ARCHITECTURE.md](ARCHITECTURE.md) - Architektura systému
- [DB_ARCHITECTURE.md](DB_ARCHITECTURE.md) - Databázová struktura
- [FUTURE_STEPS.md](FUTURE_STEPS.md) - Bugy a next steps
- [docs/LESSONS.md](docs/LESSONS.md) - **POVINNÁ ČETBA**
- [docs/ROADMAP.md](docs/ROADMAP.md) - Dlouhodobý plán
- [docs/GESTIMA_1.0_SPEC.md](docs/GESTIMA_1.0_SPEC.md) - Kompletní spec

### ADR (Architecture Decision Records)
- [ADR-001](docs/ADR/001-soft-delete-pattern.md) - Soft delete
- [ADR-002](docs/ADR/002-snapshot-pattern.md) - Snapshots
- [ADR-003](docs/ADR/003-integer-id-vs-uuid.md) - ID strategy

### API Docs (auto-generated)
```
http://localhost:8000/docs        # Swagger UI
http://localhost:8000/redoc       # ReDoc
```

---

## 🚀 Quick Start (pro novou session)

```bash
# 1. Aktivovat venv
source venv/bin/activate

# 2. Spustit app (pokud neběží)
uvicorn app.gestima_app:app --reload

# 3. Otevřít v prohlížeči
open http://localhost:8000

# 4. Přečíst FUTURE_STEPS.md
cat FUTURE_STEPS.md

# 5. Vybrat bug/feature
# 6. Přečíst LESSONS.md
cat docs/LESSONS.md

# 7. Implementovat
# 8. Testovat
pytest -v -m critical
```

---

## ⚡ Pro maximální efektivitu

1. **Paralelizuj:** Read více souborů najednou
2. **Cache:** Pamatuj si strukturu projektu
3. **Heslovitě:** Nepsat romány, jít na věc
4. **Checklist:** Používat před každým commitem
5. **LESSONS.md:** Přečíst POKAŽDÉ před změnou

---

**Verze:** 1.0
**Poslední update:** 2026-01-23
**Účel:** Pravidla pro konzistentní vývoj s AI
