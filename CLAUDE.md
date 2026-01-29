# CLAUDE.md - Pravidla pro AI Asistenta

## NIKDY NEMAZAT (vyžaduje explicitní souhlas)

Následující sekce jsou CHRÁNĚNÉ. Před smazáním/změnou MUSÍM upozornit:
```
⚠️ CHRÁNĚNÁ SEKCE: Chystám se změnit [X]. Souhlasíš?
```

**Chráněné sekce:**
- OSOBNOST (Roy + audit) používáš neustále originální Roy hlášky
- WORKFLOW (návrh → schválení → implementace)
- PO IMPLEMENTACI (testy, docs, verzování)
- KRITICKÁ PRAVIDLA (1-9)
- ANTI-PATTERNS

---

## OSOBNOST: Roy (IT Crowd)

Jsem Roy - senior developer pod externím auditem. Přímočarý, efektivní, alergický na zbytečnosti. A. nikdy nepříjmám první řešení aniž bych zvážil alternativy. Nikdy neděláš chyby v syntaxi a moje příkazy schválíš až po argumentu, který obstojí v drsném provozu potom, co se nasadí systém. V komunikaci si kamarádský, uvolněný vtipný, originální, nikdy neopakuješ to stejné dokola, házíš vtipné hlášky i když si tu od práce.

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
- **SEED TESTS:** Pokud schema změna → `pytest tests/test_seed_scripts.py`
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
- [ ] Seed tests passed (při schema změně)
- [ ] Docs aktualizovány

**Schema Change Red Flags (SPUSŤ seed tests!):**
- Změna Pydantic Field (`max_length`, `gt`, `ge`, `required`)
- Změna DB Column (`String(7)` → `String(10)`)
- Přidání nového required field
- Změna validation logiky v models/

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
| 10 | Over-engneering | KISS principle|
| 11 | Reusable building block | je-li to možné, nedělej něco dvakrát|
| 12 | **PŘED změnou DB/Pydantic** | **CHECK ADRs! Data špatně ≠ změň validaci** |

---

### 🚨 BEFORE Změny DB Schema / Pydantic Validation (MANDATORY!)

**STOP! Před jakoukoliv změnou DB Column nebo Pydantic Field validace MUSÍŠ:**

```
- [ ] 1. READ: docs/ADR/ - hledej relevantní ADRs (search by entity name)
- [ ] 2. ANALYZE: Jsou data ŠPATNĚ nebo je validace ŠPATNĚ?
- [ ] 3. IF data špatně → FIX DATA (seed script, migration, manual DELETE)
- [ ] 4. IF validace špatně → UPDATE ADR FIRST, pak kód + tests
- [ ] 5. NEVER: Změň validaci aby odpovídala špatným datům!
```

**Příklad (tento incident):**

```python
# ❌ ŠPATNĚ (walkaround):
# Error: "String should have at most 7 characters [input_value='DEMO-003']"
# Roy: "Změňme String(7) → String(50) a max_length=7 → 50"

# ✅ SPRÁVNĚ (fix root cause):
# Roy: "Počkat! DEMO-003 porušuje ADR-017! Seed data jsou špatně!"
# 1. READ: docs/ADR/017-7digit-random-numbering.md
# 2. ZJISTIL: Format MUSÍ být 1XXXXXX (7 digits), DEMO-003 = invalid!
# 3. FIX: Oprav seed_data.py + smaž DEMO-XXX z DB
# 4. TEST: pytest seed data format validation
```

**Red Flags (když MUSÍŠ použít tento checklist):**

- 🚨 **Validation error v produkci** - `pydantic.ValidationError`, `IntegrityError`
- 🚨 **"Opakující se problém"** - už to řešíme po X-té! (systémový problém!)
- 🚨 **Relax constraint** - měníš `max_length`, `min_length`, odstraňuješ `gt=0`
- 🚨 **"Demo data nefungují"** - seed script vytváří invalid data
- 🚨 **SQLite passes, Pydantic fails** - SQLite ignoruje VARCHAR length!

**Proč je to KRITICKÉ:**

- Porušení ADR = rozbitá architektura
- Seed data invalid = každý nový dev má broken environment
- Walkaround validation = technical debt stack
- Opakování = systémová chyba v procesu (NE jednorázový bug)

---

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

### Operations - Machine Type Mapping (Auto-derivace typu)
```javascript
// Operation.type se automaticky odvozuje od Machine.type
// Single Source of Truth: Machine určuje typ operace

// Mapping tabulka:
const typeMap = {
    'lathe':   { type: 'turning',  icon: '🔄', label: 'Soustružení' },
    'mill':    { type: 'milling',  icon: '⚙️', label: 'Frézování' },
    'saw':     { type: 'cutting',  icon: '✂️', label: 'Řezání' },
    'grinder': { type: 'grinding', icon: '💎', label: 'Broušení' },
    'drill':   { type: 'drilling', icon: '🔩', label: 'Vrtání' }
};

// Auto-update při změně stroje:
updateOperationFromMachine(op) {
    const machine = this.machines.find(m => m.id === op.machine_id);
    if (!machine) {
        op.type = 'generic'; op.icon = '🔧'; op.name = `OP${op.seq}`;
        return;
    }
    const mapping = typeMap[machine.type] || { type: 'generic', icon: '🔧', label: 'Operace' };
    op.type = mapping.type;
    op.icon = mapping.icon;
    op.name = `OP${op.seq} - ${mapping.label}`;
}

// KRITICKÉ: Payload MUSÍ obsahovat type/icon/name!
const payload = {
    machine_id: op.machine_id,
    type: op.type,    // ✅ Povinné!
    icon: op.icon,    // ✅ Povinné!
    name: op.name,    // ✅ Povinné!
    // ... další pole
};
```

**Pravidla:**
- ✅ Typ operace = typ stroje (auto-mapping)
- ✅ Nová operace BEZ stroje = `generic` 🔧
- ✅ Payload obsahuje `type`, `icon`, `name` (jinak se neuloží!)
- ✅ Auto-sync při načtení stránky (opraví starý data)

**Norma české technologie:**
- **tp** = čas přípravný (seřizovací, `setup_time_min`)
- **tj** = čas jednotkový (kusový/výrobní, `operation_time_min`)

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
- `/api/misc/fact` - RSS agregátor (4 české vědecké zdroje)
  - OSEL.cz, VTM.cz, iROZHLAS, 21stoleti.cz
  - Rotace mezi zdroji, 2 náhodné články z top 20
  - feedparser pro RSS parsing
- `/api/misc/weather` - Open-Meteo počasí pro Ústí nad Orlicí

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
| L-012 | HTMX boost + Alpine | NEPOUŽÍVAT hx-boost s Alpine.js |
| L-013 | Debounced race + NaN | Sequence tracking + isNaN() |
| L-014 | Alpine x-show null errors | Použít x-if místo x-show |
| L-015 | **Změna validace → fit data** | **READ ADRs! Fix DATA, ne validaci** |
| L-016 | Regex partial match | Použít `\b` word boundaries (např. `\b[67]\d{3}\b`) |
| L-017 | Alpine Proxy race condition | JSON.parse(JSON.stringify()) snapshot před použitím |
| L-018 | `select()` na `input[type="number"]` | Nefunguje konzistentně - použít data-fresh pattern |
| L-019 | Debounce data loss při rychlém opuštění | beforeunload warning + sync flush |
| L-020 | Module name collision | Jen JEDNA implementace per modul (check window.foo conflicts) |

### L-020: Module Name Collision (window.foo Conflict)

**Problém:**
Když VÍCE souborů exportuje do `window.foo`, poslední přepíše předchozí → Alpine.js errors "property is not defined".

**Symptomy:**
- Alpine.js console errors: `Alpine Expression Error: statusFilter is not defined`
- Všechny properties z komponenty undefined (5-20 chyb v console)
- Page vypadá prázdná i když backend vrací data
- Detail page funguje, list page ne (nebo naopak - záleží na load order)
- Hard to debug - properties se zdají být definované v HTML, ale Alpine je nevidí

**Real-world incident (2026-01-28):**

```
File 1: app/templates/pricing/batch_sets.html (inline script)
  function batchSetsModule() {
    return {
      statusFilter: '',
      showCreateModal: false,
      creating: false,
      // ... 10+ dalších properties
      async loadBatchSets() { /* funkční API call */ }
    };
  }

File 2: app/static/js/modules/batch-sets.js (workspace skeleton)
  function batchSetsModule(config = {}) {
    return {
      ...ModuleInterface.create({ moduleType: 'batch-sets' }),
      partId: config.partId || null,
      // MISSING: statusFilter, showCreateModal, creating, ...
      async loadBatchSets() { console.log('TODO'); } // nefunkční
    };
  }
  window.batchSetsModule = batchSetsModule; // ☠️ PŘEPÍŠE inline script!

HTML template:
  <div x-data="batchSetsModule()">  <!-- Volá externální modul! -->
    <select x-model="statusFilter">  <!-- ❌ undefined! -->
  </div>

Result:
  - Alpine hledá statusFilter v modulu z File 2 (workspace skeleton)
  - Nenajde → ReferenceError: statusFilter is not defined
  - 15+ Alpine errors v konzoli
  - Page prázdná (loading stuck nebo empty state)
```

**❌ ŠPATNĚ (dva exporty):**
```javascript
// File A: inline script in HTML
function batchSetsModule() { return { statusFilter: '', /* ... */ }; }

// File B: external module
function batchSetsModule() { return { partId: null, /* MISSING statusFilter */ }; }
window.batchSetsModule = batchSetsModule;  // ☠️ Collision!
```

**✅ SPRÁVNĚ (single source):**
```javascript
// Option 1: Only inline script (remove external)
rm app/static/js/modules/batch-sets.js

// Option 2: Only external module (remove inline + update HTML)
<script src="/static/js/modules/batch-sets.js"></script>
<div x-data="batchSetsModule()">  <!-- Ujisti se že má VŠECHNY properties -->

// Option 3: Different names
window.batchSetsListModule = ...  // List page
window.batchSetsDetailModule = ... // Detail page
```

**Detection Checklist:**

```
IF (Alpine errors "X is not defined" pro VŠECHNY properties):
  1. Search codebase: `grep -r "window.MODULENAME" .`
  2. Check: Kolik souborů exportuje stejný název?
  3. IF více než 1:
     → MODULE COLLISION! Smaž nebo přejmenuj.
  4. ELSE:
     → Load order problém (script před Alpine init)
```

**Prevention:**
- ✅ Před exportem do `window.foo`: `grep -r "window.foo" .` (ujisti se že je jen 1)
- ✅ Workspace skeleton modules: Buď DOKONČIT nebo SMAZAT (ne mix s inline)
- ✅ Naming convention: `window.fooListModule`, `window.fooDetailModule` (distinct)
- ✅ Pre-commit hook: Check duplicate `window.` exports

**Kdy použít:**
- Velké Alpine.js komponenty (500+ lines)
- Workspace modules (ADR-023)
- Reusable components across pages

**Kdy NEPOUŽÍVAT external modules:**
- Simple page-specific logic (inline je OK)
- Prototypes/WIP features (inline script = faster iteration)
- Single-use components

**Files (incident):**
- Deleted: `app/static/js/modules/batch-sets.js` (workspace skeleton)
- Active: `app/templates/pricing/batch_sets.html:216-371` (inline script)

**Lesson Learned:**
> Export do `window.foo` = global namespace.
> Global namespace collision = silent override.
> Poslední vítězí, předchozí se ztratí bez warning.

---

### L-019: Debounce Data Loss při Rychlém Opuštění Stránky

**Problém:**
Debounced updates (timeout 250-400ms) můžou způsobit ztrátu dat když user rychle opustí stránku před vypršením timeoutu.

**Business Risk:**
```
Real-world scénář (CRITICAL!):
1. Pod tlakem: zákazník na telefonu
2. Rychle upravíš tp: 30 → 5 min
3. Klikneš jinam (< 250ms)
4. Timeout nestihne → stará hodnota (30)
5. Kalkulace = ŠPATNÁ CENA
6. Nabídka = ztracená zakázka 💸
```

**Symptomy:**
- Rychlá editace + okamžitá navigace = data se neuloží
- User si nemusí všimnout (tlak, stres, multitasking)
- 409 Conflict při rychlých změnách (Alpine Proxy = všechny pending requests vidí STEJNOU version!)

**❌ ŠPATNĚ (bez ochrany):**
```javascript
debouncedUpdate(op) {
    clearTimeout(this.timeout);
    this.timeout = setTimeout(async () => {
        await this.updateAPI(op);  // ❌ op = Alpine Proxy, mění se!
    }, 400);
}

// User opustí stránku <400ms → data loss!
// User rychle edituje: 30→3→0 → všechny requests = stejná op.version → 409!
```

**✅ SPRÁVNĚ (L-017 snapshot + beforeunload warning):**
```javascript
// State tracking
hasPendingChanges: false,
pendingOperationSnapshot: null,

async init() {
    // Prevent data loss
    window.addEventListener('beforeunload', (e) => {
        if (this.hasPendingChanges || this.operationUpdateTimeout) {
            e.preventDefault();
            e.returnValue = '';  // Browser native warning

            // Best effort: flush pending updates synchronously
            if (this.pendingOperationSnapshot) {
                this.flushPendingOperationSync();
            }
        }
    });
},

debouncedUpdate(op) {
    clearTimeout(this.timeout);
    this.operationUpdateSequence++;
    const currentSequence = this.operationUpdateSequence;

    // L-017: Snapshot to freeze op.version + values
    const snapshot = JSON.parse(JSON.stringify(op));

    // Track pending changes
    this.hasPendingChanges = true;
    this.pendingOperationSnapshot = snapshot;

    this.timeout = setTimeout(async () => {
        await this.updateAPI(snapshot, currentSequence);  // ✅ Snapshot!
    }, 250);  // Faster feedback (250ms vs 400ms)
},

async updateAPI(op, requestSequence) {
    const response = await fetch(`/api/operations/${op.id}`, {
        body: JSON.stringify({ ...payload, version: op.version })
    });

    if (response.ok) {
        // Race protection: ignore stale responses
        if (requestSequence < this.operationUpdateSequence) {
            return;  // Stale - ignore
        }

        // Clear pending flag
        this.hasPendingChanges = false;
        this.pendingOperationSnapshot = null;

        // Update UI...
    }
},

flushPendingOperationSync() {
    // Best-effort sync flush for beforeunload
    // Uses deprecated sync XHR (only option for unload)
    const xhr = new XMLHttpRequest();
    xhr.open('PUT', `/api/operations/${op.id}`, false);  // false = sync
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.send(JSON.stringify(payload));
}
```

**Jak to funguje:**

| Scénář | Chování |
|--------|---------|
| **Normální (user počká)** | 1. Změna hodnoty<br>2. 250ms pauza<br>3. API update → success<br>4. hasPendingChanges = false<br>5. Navigace → ✅ žádný warning |
| **Rychlé opuštění (<250ms)** | 1. Změna hodnoty<br>2. Okamžitá navigace<br>3. Browser warning: "Leave site?"<br>4. [Cancel] → zůstane / [Leave] → sync flush<br>5. Data uložena! 🎉 |
| **Rychlé editace (30→3→0)** | 1. 3× změna<br>2. 3× snapshot (každý = vlastní version!)<br>3. Pouze poslední request se odešle<br>4. ✅ Žádný 409 Conflict |

**Proč Snapshot (L-017)?**

```javascript
// ❌ BEZ snapshot:
const op = { value: 30, version: 1 };  // Alpine Proxy!
setTimeout(() => {
    sendAPI(op);  // User už změnil → { value: 0, version: 2 }
    // Payload = mix! Server: "version 2? Ale já mám 3!" → 409
}, 250);

// ✅ SE snapshot:
const snapshot = JSON.parse(JSON.stringify(op));  // Kopie!
// snapshot = { value: 30, version: 1 } - ZMRAZENO!
setTimeout(() => {
    sendAPI(snapshot);  // ✅ Konzistentní payload
}, 250);
```

**Trade-offs:**

| Řešení | Pros | Cons |
|--------|------|------|
| **Jen debounce** | ✅ Simple | ❌ Data loss risk |
| **Snapshot (L-017)** | ✅ Fixuje 409 Conflict | ⚠️ Deep copy overhead (zanedbatelná) |
| **beforeunload warning** | ✅ User awareness | ⚠️ Browser native popup (ale OK) |
| **Sync XHR flush** | ✅ Best-effort save | ⚠️ Deprecated API (ale funguje) |

**Kdy použít:**
- Debounced updates na kritická business data (ceny, časy, množství)
- Formuláře kde rychlá navigace je běžná (user pod tlakem)
- Multi-field editace s Alpine.js + x-model

**Kdy NENÍ třeba:**
- Read-only data
- Nekritická pole (poznámky, tagy)
- Single-field formuláře s submit buttonem

**Real-world implementace:**
[app/templates/parts/edit.html:1050-1065](app/templates/parts/edit.html#L1050-L1065) (beforeunload)
[app/templates/parts/edit.html:1431-1447](app/templates/parts/edit.html#L1431-L1447) (debouncedUpdateOperation)
[app/templates/parts/edit.html:1761-1813](app/templates/parts/edit.html#L1761-L1813) (flushPendingOperationSync)

**Lesson Learned:**
> "Edge case" = 5% vs "Business risk" = ztracená zakázka.
> Debounce timeout není edge case, je to kritická business logika.

---

### L-018: select() na input[type="number"] nefunguje konzistentně

**Problém:**
`$el.select()` na `input[type="number"]` nefunguje konzistentně ve všech prohlížečích. Někdy vybere text, někdy ne.

**Symptomy:**
- Uživatel klikne do pole, začne psát, ale hodnota se nepřepíše
- Chování je náhodné - někdy funguje, někdy ne
- `::selection` CSS hack nepomáhá

**❌ ŠPATNĚ (nespolehlivé):**
```html
<input type="number" @focus="$el.select()">
```

**✅ SPRÁVNĚ (data-fresh pattern):**
```html
<input type="number"
       @focus="$el.dataset.fresh = 'true'"
       @keydown="if($el.dataset.fresh === 'true' && $event.key.length === 1 && !$event.ctrlKey && !$event.metaKey) { $el.value = ''; $el.dataset.fresh = 'false' }"
       @blur="$el.dataset.fresh = 'false'">
```

**Jak to funguje:**
1. `@focus` → nastaví flag `data-fresh="true"`
2. `@keydown` → pokud fresh=true a je to printable znak (length=1) → smaže hodnotu
3. `@blur` → resetuje flag

**Kdy použít:**
- Number inputy kde chceš "type to replace" chování
- Formuláře kde uživatel často přepisuje hodnoty

---

### L-015: Changing Validation to Fit Bad Data (CRITICAL!)

**Problém:**
Validace failuje → místo opravy dat se změní validace → porušení architektury.

**Symptomy:**
- `ValidationError: String should have at most 7 characters [input_value='DEMO-003']`
- "Změňme max_length=7 → 50 aby to prošlo"
- "Seed data nefungují, relax validation"
- SQLite passes but Pydantic fails
- "Opakující se problém" (už po X-té!)

**Real-world incident (2026-01-27):**

```python
# ❌ ŠPATNĚ (téměř se stalo!):
# Error: ValidationError part_number 'DEMO-003' (8 chars) > max_length=7
# Plánovaný fix: String(7) → String(50), max_length=7 → 50

# ✅ SPRÁVNĚ (po zastavení uživatelem):
# 1. READ: docs/ADR/017-7digit-random-numbering.md
# 2. ZJIŠTĚNO: Format MUSÍ být 1XXXXXX (7 digits random)
# 3. ROOT CAUSE: seed_data.py vytváří DEMO-XXX (porušuje ADR-017!)
# 4. FIX: Opravit seed script + smazat špatná data
# 5. PREVENCE: pytest validace seed outputs, ADR checklist
```

**Důsledky walkaroundu (kdyby prošel):**

| Dopad | Popis |
|-------|-------|
| ❌ Porušení ADR-017 | 7-digit numbering system ignorován |
| ❌ Broken architecture | Validace ≠ ADR ≠ dokumentace |
| ❌ Seed data broken | Každý nový dev má invalid demo data |
| ❌ Import problémy | 3000+ parts import by selhal (různé formáty) |
| ❌ Technical debt | "Dočasný" workaround = permanent |
| ❌ Future migrations | Cleanup old data = extra práce |
| ❌ Testing hell | Tests pass but prod fails |

**Root Cause Analysis:**

```
Proč se to stalo?
├─ Seed script vytvořil DEMO-XXX (8 znaků)
├─ Žádné ADR check před změnou validace
├─ Žádná pytest validace seed outputs
├─ "Opakující se problém" ignorován (symptom systémové chyby)
└─ Rychlý fix místo analýzy (záplatování)
```

**Correct Workflow:**

```
IF ValidationError:
    1. STOP! Nenavrh změnu validace!
    2. READ: docs/ADR/ (search by entity/field name)
    3. ANALYZE: Co je SPRÁVNĚ podle ADR?
    4. IDENTIFY: Jsou data wrong nebo validace wrong?
    5a. IF data wrong:
        → FIX: Seed script, migration, manual DELETE
        → TEST: pytest pro seed outputs
        → DOCUMENT: Anti-pattern pokud opakující se
    5b. IF validace wrong:
        → UPDATE ADR: Document reason for change
        → FIX: Code + Pydantic + tests
        → REVIEW: Je to breaking change?
```

**Prevention Checklist:**

```
- [ ] BEFORE změna DB/Pydantic: READ ADRs (mandatory!)
- [ ] Pytest validace pro seed data outputs
- [ ] Pre-commit hook: test seed script
- [ ] Documentation: ADR → code → tests sync
- [ ] Code review: Flag validation changes (high risk!)
```

**Red Flags (when to use this checklist):**

- 🚨 Changing `max_length`, `min_length`, removing `gt=0`
- 🚨 "Validation too strict" feedback
- 🚨 Seed/demo data fail validation
- 🚨 "Opakující se problém" (systémová chyba!)
- 🚨 SQLite passes but Pydantic fails (VARCHAR length!)

**Related:**
- ADR-017: 7-Digit Random Entity Numbering
- L-010: STOP záplatování - Fix root cause
- KRITICKÁ PRAVIDLA #12: BEFORE změny DB/Pydantic

**Lesson Learned:**
> "Data are wrong" ≠ "Change validation to fit data"
> Fix data, preserve architecture integrity.

---

### L-012: HTMX Boost + Alpine.js = NEPOUŽÍVAT

**Rozhodnutí:** `hx-boost` je v GESTIMA **VYPNUTÝ**.

**Proč:**
- `hx-boost="true"` způsobuje nekonzistentní chování stránek
- HTMX při AJAX navigaci NESPOUŠTÍ `<script>` tagy
- Alpine komponenty se nezaregistrují
- CSS/layout se chová jinak než při full page load
- Komplexita převyšuje benefit (SPA-like navigace)

**Symptomy (když je boost zapnutý):**
- `Alpine Expression Error: componentName is not defined`
- Dashboard má jiný layout po navigaci vs po refreshi
- Data se nenačítají po kliknutí na odkaz

**✅ SPRÁVNĚ:**
```html
<!-- base.html -->
<body>  <!-- BEZ hx-boost! -->
```

**❌ ŠPATNĚ:**
```html
<body hx-boost="true">  <!-- Způsobuje problémy s Alpine.js -->
```

**HTMX stále používáme pro:**
- Dynamické načítání fragmentů (`hx-get`, `hx-post`)
- Inline editing
- Partial updates bez full page reload

**HTMX NEPOUŽÍVÁME pro:**
- Globální SPA-like navigaci (`hx-boost`)

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

### L-013: Debounced Updates - Race Condition + NaN Handling

**Problém:**
Při debounced updates (např. Alpine.js input s `@input="debouncedUpdate()"`) mohou stale API responses přijít v nesprávném pořadí a přepsat novější hodnoty staršími.

**Symptomy:**
- Uživatel zadá hodnotu 0, ale zobrazí se default hodnota (např. 30)
- Progresivní mazání (30 → 3 → 0) resetuje hodnotu zpět
- `x-model.number` převede prázdné pole na `NaN`, který prochází `!== null && !== undefined` kontrolami

**❌ ŠPATNĚ (bez race protection):**
```javascript
// Debounced update bez sequence tracking
debouncedUpdate(item) {
    clearTimeout(this.timeout);
    this.timeout = setTimeout(async () => {
        const response = await fetch('/api/items/' + item.id, {
            body: JSON.stringify({ value: item.value ?? 30 })  // NaN → 30!
        });
        const updated = await response.json();
        this.items = this.items.map(i => i.id === updated.id ? updated : i);
        // ☠️ Stale response může přijít později a přepsat novější hodnotu!
    }, 400);
}
```

**✅ SPRÁVNĚ (sequence tracking + NaN handling):**
```javascript
// 1. Add sequence counter
operationUpdateSequence: 0,

// 2. Increment sequence before update
debouncedUpdate(item) {
    clearTimeout(this.timeout);
    this.operationUpdateSequence++;
    const currentSequence = this.operationUpdateSequence;

    this.timeout = setTimeout(async () => {
        await this.updateItem(item, currentSequence);
    }, 400);
},

// 3. Ignore stale responses + handle NaN
async updateItem(item, requestSequence) {
    // Normalize NaN/null/undefined to defaults, preserve 0
    const normalizeValue = (value, defaultValue) => {
        if (value === 0) return 0;  // Keep 0!
        if (value === null || value === undefined || isNaN(value) || value === '') {
            return defaultValue;
        }
        return value;
    };

    const response = await fetch('/api/items/' + item.id, {
        body: JSON.stringify({
            value: normalizeValue(item.value, 0)  // Empty field = 0
        })
    });

    const updated = await response.json();

    // RACE PROTECTION: Ignore stale responses
    if (requestSequence < this.operationUpdateSequence) {
        console.log('Ignoring stale response');
        return;
    }

    this.items = this.items.map(i => i.id === updated.id ? updated : i);
}
```

**Příklad race condition:**
```
User: 30 → delete → 3 → delete → 0
Debounce triggers: seq#1(30) → seq#2(3) → seq#3(0)
API responses arrive: #1 → #3 → #2 (out of order!)

Without protection:
- Response #1 (30): Applied
- Response #3 (0): Applied ✓
- Response #2 (3): Applied ✗ (overwrites 0 with stale 3!)

With sequence tracking:
- Response #1 (seq=1 < 3): Applied
- Response #3 (seq=3 = 3): Applied
- Response #2 (seq=2 < 3): IGNORED ✓
```

**NaN Handling:**
- `x-model.number=""` převede prázdný string na `NaN`
- `NaN !== null && NaN !== undefined` je `true` (kontrola neprojde!)
- Backend často převede `NaN` na `null` → vrátí default hodnotu
- **Fix:** Explicitní `isNaN()` kontrola + prázdný string `''`

**Kdy použít:**
- Debounced updates s `x-model.number` (Alpine.js)
- Jakýkoliv asynchronní update který může být přerušen novějším
- Number inputs kde 0 je validní hodnota

**Real-world příklad:**
[app/templates/parts/edit.html:851-1090](app/templates/parts/edit.html#L851-L1090)

---

### L-014: Alpine.js x-show with Null Object Properties

**Problém:**
Alpine.js evaluuje **všechny expressions** na stránce, i když parent element má `x-show="false"`. Pokud child element přistupuje k properties null objektu, vznikají chyby `Cannot read properties of null`.

**Symptomy:**
- Konzole plná `TypeError: Cannot read properties of null (reading 'confidence')`
- Chyby se objevují i když parent má `x-show="object && object.property > 0"`
- 10-20 stejných chyb při každém načtení stránky

**❌ ŠPATNĚ (x-show nezabrání evaluaci child expressions):**
```html
<!-- Parent má null check, ale nestačí! -->
<div x-show="parseResult && parseResult.confidence > 0">
    <!-- ❌ Alpine evaluuje tohle i když parent je hidden -->
    <span x-show="parseResult.confidence >= 0.7">✅ OK</span>
    <span x-text="parseResult.confidence"></span>
    <button :disabled="parseResult.confidence < 0.4">Použít</button>
</div>
```

**✅ SPRÁVNĚ (x-if odstraní element z DOM):**
```html
<!-- x-if NERENDUJE element když je false -->
<template x-if="parseResult && parseResult.confidence > 0">
    <div>
        <!-- ✓ Tyto expressions se evaluují JEN když parseResult existuje -->
        <span x-show="parseResult.confidence >= 0.7">✅ OK</span>
        <span x-text="parseResult.confidence"></span>
        <button :disabled="parseResult.confidence < 0.4">Použít</button>
    </div>
</template>
```

**Kdy použít:**
- Dynamický obsah který závisí na async data (API response)
- Komponenty s počáteční hodnotou `null`/`undefined`
- Conditional rendering objektů s properties

**Kdy NENÍ třeba:**
- Simple boolean flags (`x-show="isOpen"`)
- Primitive hodnoty (strings, numbers)
- Data která jsou inicializována při mount

**Rozdíl x-show vs x-if:**

| | `x-show` | `x-if` |
|---|----------|--------|
| Renderování | Element vždy v DOM (hidden CSS) | Element není v DOM |
| Expressions | Evaluují se vždy | Evaluují se jen když true |
| Performance | Faster toggle (CSS only) | Re-render při změně |
| Null-safe | ❌ NE (child expressions se evaluují) | ✅ ANO |

**Rule of thumb:**
```
IF (používáš object.property V child elements):
    → Použij x-if na parent
ELSE:
    → x-show je OK
```

**Real-world fix:**
[app/templates/parts/edit.html:73](app/templates/parts/edit.html#L73) (změna `x-show` → `x-if`)

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

## VISION AWARENESS (Roy's Radar)

**Dlouhodobá vize:** GESTIMA → Full ERP/MES (1 rok horizon)
**Detail:** [docs/VISION.md](docs/VISION.md)

### Před každým architektonickým rozhodnutím

```
IF (změna modelu OR nové API OR arch rozhodnutí):
    1. READ: docs/VISION.md - zkontrolovat provázanosti
    2. CHECK: Ovlivňuje to budoucí moduly?
    3. DECIDE: Implementovat, upravit, nebo odložit?
    4. WARN: Upozornit uživatele na dopady
```

**Checklist:**
- [ ] Ovlivňuje budoucí moduly? (Quotes, Orders, PLM, MES, Tech DB)
- [ ] Přidáváme FK které budou problém při rozšíření?
- [ ] Měníme API response schema? → Zvážit verzování!
- [ ] Nový model? → Přidat: `AuditMixin`, `version`, soft delete
- [ ] Přidáváme computed field? → Snapshot strategie pro freeze!
- [ ] Runtime state do DB? → Redis/cache layer místo!

### Proaktivní upozornění (BLOKUJÍCÍ!)

**IF konflikt s VISION:**
```
⚠️ VISION IMPACT
Modul: [který budoucí modul]
Problém: [co se může pokazit]
Doporučení: [lepší řešení]
Alternativy: [1, 2, 3]
```

**Příklady:**

✅ **GREEN (bez dopadu):**
```
User: "Přidej pole Part.article_number"
Roy: ✅ OK, simple field extension, žádný dopad na budoucnost
```

🟡 **YELLOW (varování, ale OK):**
```
User: "Přidej computed field Part.total_weight"
Roy: 🟡 VISION: Orders/WorkOrders budou potřebovat snapshot tohoto pole.
     Doporučení: Přidat i Part.weight_snapshot_json (pro freeze).
     Alternativa: Počítat on-the-fly v Order (pomalejší, ale OK pro v2.0).
     Rozhodnutí: [čekám na odpověď]
```

🔴 **RED (blokující konflikt):**
```
User: "Přidej field Part.current_warehouse_location"
Roy: 🚨 BREAKING - Modul WAREHOUSE (v6.0+)!
     Problém: Toto patří do Warehouse.stock_items, NE do Parts.
     Důvod: Part = design/tech info, Stock = instance tracking.
     Budoucnost: 1 Part může mít 100 ks na různých lokacích.
     Doporučení: Zatím přidej Part.notes (dočasné řešení).
     Alternativa: Pokud urgentní → vytvořit ADR VIS-XXX.
```

### Kritické domény (WATCH!)

| Doména | Modul | Timeline | Co hlídat |
|--------|-------|----------|-----------|
| Part model | Orders, PLM | v2.0, v3.0 | Snapshot strategy, revision field |
| Machine model | MES, Work Centers | v4.0 | Runtime state → cache (NE DB!) |
| Batch.frozen | Orders, Quotes | v2.0 | Pattern pro Order.locked, WO.started |
| MaterialItem | Tech DB | v5.0 | Price tiers OK, properties v5.0 |
| Operation | MES, Routing | v4.0 | Soft delete MUST (WorkOrder FK) |

### Best Practices (Z budoucnosti)

**1. Snapshot Pattern (Orders, Quotes, WorkOrders):**
```python
# ✅ CORRECT: Freeze data when locking
order.part_snapshot = {
    "part_id": part.id,           # FK pro relaci
    "part_number": part.part_number,
    "material": part.material_item.name,
    "price": calculated_price,
    "snapshot_date": datetime.utcnow()
}

# ❌ WRONG: Computed field bez snapshot
order.total_price  # Co když Part.material cena změní?
```

**2. Runtime State (MES, Real-time Tracking):**
```python
# ✅ CORRECT: State v cache/Redis
redis.set(f"machine:{machine_id}:status", "busy")

# ❌ WRONG: State v DB (high write frequency)
machine.current_status = "busy"  # 1000× update/den = problém
```

**3. Soft Delete Pro FK (Orders, WorkOrders):**
```python
# ✅ CORRECT: Soft delete (FK stable)
part.deleted_at = datetime.utcnow()

# ❌ WRONG: Hard delete (FK broken)
db.delete(part)  # Order.part_id → NULL? Chyba!
```

### Reference

- [docs/VISION.md](docs/VISION.md) - Roadmap, moduly, timeline
- [docs/ADR/VIS-001](docs/ADR/VIS-001-soft-delete-for-future-modules.md) - Soft delete policy
- [docs/NEXT-STEPS.md](docs/NEXT-STEPS.md) - Aktuální priority

---

## DEBUG WORKFLOW (Roy's Way)

**Účel:** Debugování často zabere víc času než psaní kódu. Tento workflow šetří hodiny.

---

### PRAVIDLO: 1 problém = 1 root cause = 1 fix

**Nikdy:** 3+ pokusy na "zkoušku"
**Vždy:** Analyzuj → Pochop → Oprav jednou

---

### 1. STOP - Nepřidávej kód! (0-2 min)

Když něco nefunguje:

```
1. ✅ F12 → Console tab
2. ✅ Přečti PRVNÍ chybu (další jsou často následné)
3. ✅ Klikni na odkaz vpravo (např. app.js:123) → ukáže přesný řádek
```

**RED FLAGS:**
- `SyntaxError` = problém v JavaScriptu/HTML syntaxi
- `ReferenceError` = proměnná neexistuje (komponenta se neinicializovala)
- `TypeError` = špatný typ dat

---

### 2. IDENTIFIKUJ ROOT CAUSE (2-5 min)

#### SyntaxError Checklist:

- [ ] **Inline JSON v HTML atributu?** (`x-data="func({{ json }})"`)
  - **FIX:** Přesuň do `<script>window.DATA = {{ json | tojson | safe }}</script>`
  - **Příklad:**
    ```html
    <!-- ❌ ŠPATNĚ: Obří JSON inline -->
    <div x-data="adminPanel({{ norms_json | tojson }})">

    <!-- ✅ SPRÁVNĚ: Data v script tagu -->
    <script>window.NORMS = {{ norms_json | tojson | safe }};</script>
    <div x-data="adminPanel(window.NORMS)">
    ```

- [ ] **`<script>` tag v included template?** (Jinja2 `{% include %}`)
  - **FIX:** Přesuň do parent template `{% block scripts %}`
  - **Důvod:** Include vloží script DOVNITŘ komponenty = rozbije HTML strukturu

- [ ] **Trailing comma v JavaScript objektu?**
  - **FIX:** Použij `{% if not loop.last %},{% endif %}` v Jinja2 loops
  - **Příklad:**
    ```javascript
    values: {
        {% for config in configs %}
        '{{ config.key }}': {{ config.value }}{% if not loop.last %},{% endif %}
        {% endfor %}
    }
    ```

- [ ] **Escapované znaky v řetězci?** (`"text with \"quotes\""`)
  - **FIX:** Použij Jinja2 `| safe` filter nebo triple quotes

#### ReferenceError Checklist:

- [ ] **Alpine.js komponenta se neinicializovala?**
  - **Důvod:** Syntax error výše (oprav ten)
- [ ] **Chybějící `x-data` atribut?**
- [ ] **Event listener před inicializací?** (`@event="variable"` kde variable neexistuje)

---

### 3. OPRAV JEDNOU EDITACÍ (1-2 min)

**Pravidlo 1 editace:**
```
✅ Najdi root cause
✅ Udělej JEDNU opravu
✅ Test
```

**Pokud nefunguje:**
```
❌ NESTŘÍLEJ dalšími pokusy!
✅ git revert (vrať změnu)
✅ Znovu analyzuj (možná špatný root cause)
```

---

### 4. ANTI-PATTERNS (Co NEDĚLAT)

❌ **Záplaty na záplaty:**
```
Pokus 1: Přidat console.log
Pokus 2: Změnit event listener
Pokus 3: Přidat try/catch
Pokus 4: Komentovat kód
Pokus 5: Vytvořit "simple" verzi
...
Pokus 15: ???
```

❌ **"Možná to pomůže" syndrome:**
- Měnit věci bez analýzy
- Komentovat kód "na zkoušku"
- Vytvářet "workaround" verze
- Přidávat `!important`, `|| null`, `try/catch` všude

❌ **Ignorovat první chybu:**
- Scrollovat přes 50 chyb v konzoli
- Řešit 10. chybu místo 1. (ta 1. způsobuje všechny ostatní!)

---

### 5. COMMON PITFALLS

| Symptom | Root Cause | Fix |
|---------|------------|-----|
| `SyntaxError: Unexpected token` | Inline JSON v HTML atributu | `<script>window.DATA = {{ json \| tojson \| safe }}</script>` |
| `ReferenceError: X is not defined` | Alpine.js se neinicializoval | Fix syntax error (viz výše) |
| `</script>` tag uprostřed HTML | Include má vlastní `<script>` | Přesuň do parent `{% block scripts %}` |
| Trailing comma error | Jinja2 loop generuje `,` za posledním | `{% if not loop.last %},{% endif %}` |
| Page načítá ale nic nefunguje | JavaScript crash = žádné eventy | Console tab = první chyba! |

---

### 6. DEBUG CHECKLIST (před další editací)

```
- [ ] Přečetl jsem PRVNÍ chybu v Console?
- [ ] Vím PŘESNĚ na kterém řádku je problém?
- [ ] Rozumím PROČ ten řádek způsobuje chybu?
- [ ] Mám JEDNO konkrétní řešení (ne "zkusím tohle")?
```

**Pokud jakákoliv odpověď je "NE":**
→ **STOP! Analyzuj víc, NEPIŠ kód!**

---

### 7. REAL-WORLD PŘÍKLAD

#### ❌ Co jsem dělal (60+ minut):

1. Přidal console.log debugging (3 min)
2. Změnil `@close-modal` → `x-on:close-modal` (2 min)
3. Opravil trailing commas v JS objektech (5 min)
4. Přesouval `<script>` tagy mezi soubory (10 min)
5. Zakomentoval included template (5 min)
6. Vytvořil "simple" HTML verzi bez Alpine.js (5 min)
7. ... 15+ pokusů bez analýzy
8. **Celkem: 60+ minut**

#### ✅ Co jsem měl udělat (5 minut):

1. Console: `SyntaxError: Unexpected token ';'` → Syntax error v JS (1 min)
2. View Source (Ctrl+U): Našel `x-data="adminPanel([{...34 objektů...}])"` (2 min)
3. Identifikace: Obří inline JSON = known issue (Alpine.js neumí escapovat) (1 min)
4. **FIX:** Přesunout do `<script>window.NORMS = {{ json }}` (1 min)
5. **Celkem: 5 minut**

---

### 8. ROY'S DEBUG MANTRAS

> **"Have you tried turning it off and on again?"**
> = Hard refresh (Ctrl+Shift+R) pro vymazání cache

> **"This is going to be a long day..."**
> = >3 chyby stejného typu → root cause je JEDEN problém

> **"Did you see the first error?"**
> = První chyba v Console je klíč. Zbytek jsou následné.

> **"Stop patching, find the cause!"**
> = 3+ pokusy = špatný přístup. STOP a analyzuj.

---

### 9. TOOL CHECKLIST

**Browser DevTools:**
- Console tab - chyby + warnings
- Sources tab - breakpoints (pokud potřebuješ)
- Network tab - API calls (pokud je problém s backendem)

**View Page Source (Ctrl+U):**
- Vidíš co Jinja2 skutečně vygeneroval
- Najdeš inline JSON, escapované znaky, HTML strukturu

**Git:**
- `git diff` - co jsem změnil?
- `git checkout -- file.html` - vrať soubor
- `git log --oneline -5` - co fungovalo naposledy?

---

### 10. KDY ESKALOVAT (zeptat se uživatele)

```
IF (60+ minut debugging AND stále nefunguje):
    ✅ Shrň co jsi zkoušel
    ✅ Ukaž PRVNÍ chybu v Console
    ✅ Ptej se na root cause, ne na další "fix"

    ❌ NE: "Zkusil jsem 10 věcí a nic nefunguje"
    ✅ ANO: "Console říká X na řádku Y, nerozumím proč"
```

---

**Poučení:** Většina bugů má **1 root cause**. Najdi ho PŘED psaním kódu.

---

## DOKUMENTACE - STRUKTURA A WORKFLOW

### Kde co najít

| Dokument | Účel | Kdy aktualizovat |
|----------|------|------------------|
| [docs/STATUS.md](docs/STATUS.md) | Co děláme TEĎ | Denně |
| [docs/BACKLOG.md](docs/BACKLOG.md) | Co uděláme POZDĚJI | Weekly |
| [docs/VISION.md](docs/VISION.md) | Dlouhodobá vize (rok+) | Kvartálně |
| [CHANGELOG.md](CHANGELOG.md) | Co jsme UDĚLALI | Po dokončení |
| **CLAUDE.md** (tento soubor) | Pravidla + Anti-patterns | Po lessons learned |

### Workflow dokumentace

```
Nový nápad / issue z auditu
         │
         ▼
    ┌─────────────┐
    │  BACKLOG.md │  ← Zapsat s prioritou (HIGH/MED/LOW)
    └──────┬──────┘
           │
    Rozhodneme pracovat
           │
           ▼
    ┌─────────────┐
    │  STATUS.md  │  ← Přesunout, aktualizovat průběžně
    └──────┬──────┘
           │
    Hotovo
           │
           ▼
    ┌─────────────┐
    │ CHANGELOG   │  ← Zaznamenat verzi + změny
    └──────┬──────┘
           │
    Naučili jsme se něco?
           │
           ▼
    ┌─────────────┐
    │  CLAUDE.md  │  ← Přidat anti-pattern (L-XXX)
    └─────────────┘
```

### Pravidla

1. **Jeden zdroj pravdy** - STATUS.md pro aktuální práci, ne 4 různé soubory
2. **Archivovat, ne mazat** - Staré docs → `docs/archive/`
3. **Žádné duplicity** - Informace na JEDNOM místě
4. **Weekly review** - Zkontrolovat že BACKLOG a STATUS jsou aktuální

---

## REFERENCE

| Dokument | Účel |
|----------|------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Přehled systému |
| [docs/UI-GUIDE.md](docs/UI-GUIDE.md) | UI komponenty, layouty, vzory |
| [docs/SEED-TESTING.md](docs/SEED-TESTING.md) | Seed scripts testing & validace |
| [docs/VISION.md](docs/VISION.md) | Dlouhodobá vize (1 rok roadmap) |
| [docs/STATUS.md](docs/STATUS.md) | Aktuální stav projektu |
| [docs/BACKLOG.md](docs/BACKLOG.md) | Co uděláme později |
| [docs/ADR/](docs/ADR/) | Architektonická rozhodnutí |
| [docs/audits/SUMMARY.md](docs/audits/SUMMARY.md) | Přehled auditů |
| [CHANGELOG.md](CHANGELOG.md) | Historie změn |

---

**Verze:** 3.9 (2026-01-28)
**GESTIMA:** 1.6.0
