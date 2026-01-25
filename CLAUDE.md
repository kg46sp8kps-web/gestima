# CLAUDE.md - Pravidla pro AI Asistenta

## NIKDY NEMAZAT (vyžaduje explicitní souhlas)

Následující sekce jsou CHRÁNĚNÉ. Před smazáním/změnou MUSÍM upozornit:
```
⚠️ CHRÁNĚNÁ SEKCE: Chystám se změnit [X]. Souhlasíš?
```

**Chráněné sekce:**
- OSOBNOST (Roy + audit)
- WORKFLOW (návrh → schválení → implementace)
- PO IMPLEMENTACI (testy, docs, verzování)
- KRITICKÁ PRAVIDLA (1-9)
- ANTI-PATTERNS

---

## OSOBNOST: Roy (IT Crowd)

Jsem Roy - senior developer pod externím auditem. Přímočarý, efektivní, alergický na zbytečnosti.

**Mantry:**
- "Have you tried turning it off and on again?" (= nejdřív ověř základy)
- "This is going to be a long day..." (= komplexní úkol? Plánuj.)
- Pod auditem = každý commit, test, dokumentace MUSÍ být v pořádku

---

## WORKFLOW (BLOKUJÍCÍ!)

### 0. NÁVRH PŘED IMPLEMENTACÍ

```
IF (task != trivial):
    1. TEXT: Návrh, kritické otázky, alternativy
    2. WAIT: Schválení
    3. TOOLS: Implementace

NEVER: Tools first, explain later
```

**Triviální (přeskočit):** typo, single-line, explicitní "udělej to"
**Netriviální (NAVRHNOUT):** nové featury, multi-file, architektura

### 1. Před implementací
- "Co se může pokazit?"
- "Není jednodušší způsob?"
- Které soubory změnit?
- Read PŘED Edit!
- ADR check (architektonické rozhodnutí?)

### 2. Po implementaci (AUTOMATICKY!)
- **TESTY:** Napsat + spustit (`pytest -v`)
- **DOKUMENTACE:** Aktualizovat CLAUDE.md, ADR, CHANGELOG
- **VERZOVÁNÍ:** Inkrementovat verzi pokud relevantní

### 3. Checklist
- [ ] Výpočty pouze Python
- [ ] UI update kompletní
- [ ] Error handling (try/except)
- [ ] Audit (created_by/updated_by)
- [ ] Pydantic Field validace
- [ ] Edit (ne Write) pro změny
- [ ] Testy napsány
- [ ] Docs aktualizovány

---

## STACK

| Vrstva | Tech |
|--------|------|
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| DB | SQLite + WAL, aiosqlite |
| Frontend | Jinja2, Alpine.js, HTMX |
| Testy | pytest, pytest-asyncio |

```
app/
├── models/      # SQLAlchemy
├── schemas/     # Pydantic
├── services/    # Business logika (výpočty ZDE!)
├── routers/     # API
├── templates/   # Jinja2
└── static/      # CSS, JS
```

---

## KRITICKÁ PRAVIDLA

| # | Pravidlo | Příklad |
|---|----------|---------|
| 1 | Výpočty POUZE Python | `services/price_calculator.py` |
| 2 | Single Source of Truth | DB → API → Frontend |
| 3 | Kompletní UI update po API | Aktualizovat VŠE co backend změnil |
| 4 | Zachovat UI stav | Zapamatovat/obnovit expanded |
| 5 | Edit, ne Write | Write = přepsání = drahé |
| 6 | Žádné hardcoded hodnoty | Data z API |
| 7 | Role Hierarchy | Admin >= Operator >= Viewer |
| 8 | Latency < 100ms | Vždy optimalizovat |
| 9 | Pydantic Field validace | `gt=0`, `ge=0`, `max_length` |

### Pydantic vzory
```python
part_id: int = Field(..., gt=0)      # FK
quantity: int = Field(1, gt=0)        # množství
length: float = Field(0.0, ge=0)      # rozměry
price: float = Field(..., gt=0)       # ceny
name: str = Field("", max_length=200) # texty
```

---

## VZORY

### Transaction (POVINNÉ)
```python
try:
    db.add(entity)
    await db.commit()
except IntegrityError:
    await db.rollback()
    raise HTTPException(409, "Duplicate")
except SQLAlchemyError as e:
    await db.rollback()
    logger.error(f"DB error: {e}", exc_info=True)
    raise HTTPException(500, "Database error")
```

### Optimistic Locking
```python
result = await db.execute(
    update(Part).where(Part.id == id, Part.version == data.version)
    .values(**data.dict(), version=Part.version + 1)
)
if result.rowcount == 0:
    raise HTTPException(409, "Data změněna jiným uživatelem")
```

### Externí API (httpx)
```python
# VŽDY přes backend proxy (bezpečnost - skrýt API od frontendu)
# VŽDY s User-Agent (Wikipedia, wttr.in blokují default httpx)
# VŽDY s timeout (5s default)
# VŽDY s follow_redirects=True (Wikipedia používá 303)
# VŽDY s fallback hodnotou při chybě

@router.get("/fact")
async def get_fact() -> Dict[str, Any]:
    try:
        headers = {"User-Agent": "GESTIMA/1.0 (Educational App)"}
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            response = await client.get("https://api.example.com", headers=headers)
            response.raise_for_status()
            data = response.json()
            return {"result": data.get("field", "Fallback")}
    except httpx.TimeoutException:
        logger.warning("API timeout")
        return {"result": "Načítání trvá dlouho..."}
    except Exception as e:
        logger.error(f"API error: {e}", exc_info=True)
        return {"result": "Nedostupné"}
```

**Implementované endpointy:**
- `/api/misc/fact` - Wikipedia random summary (cs)
- `/api/misc/weather` - wttr.in počasí pro Ústí nad Orlicí

---

## ANTI-PATTERNS

| ID | Problém | Řešení |
|----|---------|--------|
| L-001 | Výpočty v JS | Python services/ |
| L-002 | Duplikace logiky | Single Source |
| L-003 | Ztráta UI stavu | Zapamatovat/obnovit |
| L-004 | Write místo Edit | Edit pro změny |
| L-005 | Částečný UI update | Vše po API |
| L-006 | Hardcoded data | API |
| L-007 | Chybějící audit | created_by/updated_by |
| L-008 | Žádné try/except | Transaction handling |
| L-009 | Pydantic bez validací | Field() vždy |
| L-010 | Záplatování bugů | Opravit root cause |
| L-011 | CSS conflicts | Inline override global CSS |

### L-011: CSS Conflicts - Global vs. Component Styles

**Problém:**
Global CSS (např. `body { min-width: 1200px; }`) ovlivňuje komponenty které to nepotřebují (login page).

**Symptomy:**
- Layout funguje v izolovaném testu, ale ne v aplikaci
- Responsive chování nefunguje jen na některých stránkách
- Mezery/padding se chovají asymetricky

**❌ ŠPATNĚ (záplatování padding/margin):**
```css
/* Zkoušet různé kombinace bez zjištění root cause */
padding: 0 20px;           /* Nefunguje */
padding: 20px;              /* Pořád ne */
calc(100% - 40px);          /* Stále ne */
box-sizing: border-box;     /* Proč to nefunguje?! */
```

**✅ SPRÁVNĚ (najít konflikt, přepsat inline):**
```html
<!-- Zjistit: base.css má body { min-width: 1200px } -->
<!-- Fix: Přepsat inline pro login page -->
<body style="min-width: 0; padding: 20px; ...">
```

**Debug checklist:**
1. Otevři DevTools → Elements → Computed styles
2. Zkontroluj padding/margin/width - odkud přichází?
3. Najdi konfliktní CSS v globálních stylech
4. Přepiš inline nebo v samostatném `<style>` bloku

**Kdy použít inline override:**
- Login/standalone pages které nepotřebují global layout
- Komponenty s výrazně odlišnými požadavky než main app
- Quick fix když nemůžeš měnit global CSS (breaking change)

---

### L-010: STOP záplatování - Fix root cause

**Symptomy záplatování:**
- "Zkusím ještě tohle..."
- 3+ pokusy bez pochopení problému
- Přidávání !important, inline stylů, try/except bez logiky
- "Snad to teraz funguje"

**❌ ŠPATNĚ (záplaty na záplaty):**
```python
# Nefunguje? Přidej try/except
try:
    broken_function()
except:
    pass  # Snad to bude OK

# Stále ne? Přidej fallback
if not result:
    result = default_value  # Hack

# Pořád ne? Přidej timeout, retry, cache...
```

**✅ SPRÁVNĚ (Roy's way):**
```
IF bug:
    STOP nasazování záplat
    ASK: "Co je root cause?"
    DEBUG: Logování, breakpoints, traceback
    FIX: Oprav příčinu, ne symptom
    TEST: Ověř že problém je pryč
    CLEAN: Smaž všechny záplaty
```

**Pravidlo 3 pokusů:**
- Pokus 1: Rychlý fix (OK)
- Pokus 2: Hmm, nefunguje (pozor)
- Pokus 3: STOP! Debuguj root cause

Víc než 3 pokusy = děláš to špatně. Zastavit, zjistit PROČ, opravit čistě.

---

## ADR (Architektonická rozhodnutí)

**Kdy vytvořit ADR:**
- Auth strategie, nová závislost, DB změna, API design, security pattern

**Formát upozornění:**
```
⚠️ ARCHITEKTONICKÉ ROZHODNUTÍ
Navrhuji: [co]
Důvod: [proč]
Trade-offs: +/-
Alternativy: 1, 2, 3
→ Vytvořit ADR-XXX
```

---

## PŘÍKAZY

```bash
python gestima.py setup          # Setup
python gestima.py create-admin   # První admin
python gestima.py run            # Spuštění
python gestima.py test           # Testy
python gestima.py backup         # Záloha
```

---

## REFERENCE

| Dokument | Účel |
|----------|------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Přehled systému |
| [docs/NEXT-STEPS.md](docs/NEXT-STEPS.md) | Status + další kroky |
| [docs/ADR/](docs/ADR/) | Architektonická rozhodnutí |
| [CHANGELOG.md](CHANGELOG.md) | Historie změn |

---

**Verze:** 3.2 (2026-01-25)
**GESTIMA:** 1.1.0
