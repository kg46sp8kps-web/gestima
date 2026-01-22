# GESTIMA - Shrnutí Session #1

**Datum:** 2026-01-22  
**Téma:** Inicializace projektu + UI v1.0 (finální design)  
**Status:** ✅ UI Design LOCKED

---

## ✅ CO JSME UDĚLALI

### 1. **Projekt Setup**
- ✅ FastAPI aplikace běží (`uvicorn app.gestima_app:app --reload`)
- ✅ SQLite databáze s WAL mode
- ✅ Modely (Part, Operation, Feature, Batch, Machine)
- ✅ Routery (API endpoints hotové)
- ✅ Services (time_calculator, price_calculator připravené)

### 2. **Part Model (Díl)**
- ✅ `part_number` - UNIQUE constraint (nemůžeš vytvořit dva díly se stejným číslem)
- ✅ `part_number` - povinné pole
- ✅ `name` - volitelné
- ✅ `material_name` - volitelné (jen označení typu oceli)
- ✅ `material_group` - povinné (vychází se z toho pro řezné podmínky)
- ✅ Polotovar - dynamické pole podle typu:
  - Tyč/Trubka/Odlitek: Ø + Délka
  - Trubka: + Vnitřní průměr
  - Přířez: d × š × v (3 rozměry)
  - Plech: d × š × tloušťka
- ❌ Finální rozměry ODSTRANĚNY (podle požadavku)

### 3. **UI - Formulář pro nový díl**
- ✅ `/parts/new` - formulář funguje
- ✅ Alpine.js logika
- ✅ Dynamické pole podle typu polotovaru
- ✅ Validace duplicitního čísla výkresu
- ✅ Toast notifikace
- ✅ Přesměrování na editaci po vytvoření

### 4. **UI - Editace dílu (v1.0 FINÁLNÍ) 🔒**
- ✅ `/parts/{id}/edit` - stránka existuje
- ✅ Layout: levý panel (320px sticky) + pravý panel (flex: 1)
- ✅ **Levý panel (ribbony):**
  - ✅ Základní údaje dílu (collapsible)
  - ✅ Cenový přehled (collapsible, připravený na data)
  - ✅ Tlačítko "Zpět na seznam"
- ✅ **Pravý panel (ribbony):**
  - ✅ Čas na kus (STICKY ribbon, collapsible, font 0.85rem)
  - ✅ Operace (RIBBON, collapsible, scrollovatelné)
  - ✅ Jednotlivé operace rozbalovací (kliknutím na header)
  - ✅ Mode buttons (LOW/MID/HIGH) s `@click.stop`
- ✅ **Všechny ribbon headery:**
  - ✅ Sjednocená výška (min-height: 38px, padding: 0.5rem 0.8rem)
  - ✅ Stejný font size (0.85rem)
- ✅ **DESIGN LOCKED** - Guesstimator CSS v1.0
- ✅ Responsivní layout (80% šířka, min 1200px, max 2400px)

### 5. **API Endpoints**
- ✅ `POST /api/parts/` - vytvořit díl (s kontrolou duplicity)
- ✅ `GET /api/parts/` - seznam dílů
- ✅ `GET /api/parts/{id}` - detail dílu
- ✅ `GET /api/operations/part/{part_id}` - operace dílu
- ✅ `POST /api/operations/` - vytvořit operaci
- ✅ `POST /api/operations/{id}/change-mode` - změnit LOW/MID/HIGH
- ✅ `GET /api/batches/part/{part_id}` - dávky dílu

---

## ❌ CO JEŠTĚ CHYBÍ

### **UI**
- ✅ Implementovat Guesstimator CSS (variables, components, operations)
- ✅ Upravit HTML podle tvého designu
- ✅ Správné třídy na komponentách
- ✅ Operation card design
- ✅ Mode buttons (LOW/MID/HIGH) se správným stylem
- ⚠️ Cenový ribbon se správným stylem (struktura je, data chybí)
- ⚠️ Price bar (horizontální stacked bar) - připraveno, chybí data z kalkulace

### **Funkce**
- ❌ Přidání kroků (features) k operaci
- ❌ Formulář pro geometrii kroků (Ds, Df, length...)
- ❌ Výpočet času z geometrie (time_calculator)
- ❌ Kalkulace cen (price_calculator)
- ❌ Vytvoření dávek (100ks, 200ks, 1000ks)
- ❌ Editace operace (název, stroj, seřízení)
- ❌ Smazání operace/dílu

### **Backend**
- ❌ Načtení strojů z DB/Excel
- ❌ Načtení řezných podmínek
- ❌ Implementace `time_calculator.py`
- ❌ Implementace `price_calculator.py`
- ❌ Vytvoření testovacích dat (fixture)

---

## 🗂️ STRUKTURA PROJEKTU

```
/Users/lofas/Documents/__App/Gestima/
├── app/
│   ├── models/          # ✅ Hotové (Part, Operation, Feature, Batch, Machine)
│   ├── routers/         # ✅ API endpoints hotové
│   ├── services/        # ⚠️ Prázdné (time_calculator, price_calculator)
│   ├── templates/
│   │   ├── base.html    # ✅ Layout
│   │   ├── parts/
│   │   │   ├── new.html # ✅ Funguje
│   │   │   └── edit.html # ⚠️ Funkční, ale špatný design
│   ├── static/
│   │   ├── css/
│   │   │   ├── gestima.css      # ✅ Main import file
│   │   │   ├── variables.css    # ✅ Guesstimator colors/variables
│   │   │   ├── base.css         # ✅ Base styles + watermark
│   │   │   ├── layout.css       # ✅ Split layout (left/right panels)
│   │   │   ├── components.css   # ✅ Ribbons, buttons, forms
│   │   │   └── operations.css   # ✅ Operation cards, mode buttons
│   │   ├── img/
│   │   │   └── logo.png         # ✅ KOVO RYBKA logo
│   │   └── js/
│   │       └── gestima.js  # ✅ Toast notifikace
│   ├── database.py      # ✅ SQLite + WAL mode
│   └── gestima_app.py   # ✅ FastAPI app
├── Docs/
│   ├── GESTIMA_1.0_SPEC.md  # ✅ Kompletní specifikace
│   ├── LESSONS.md           # ✅ Poučení z chyb
│   ├── UI_REFERENCE.md      # ✅ NOVĚ - CSS reference z Guesstimator
│   ├── SESSION_SUMMARY.md   # ✅ NOVĚ - tento soubor
│   └── ADR/
│       └── 003-integer-id-vs-uuid.md  # ✅ Integer ID je OK
├── gestima.db           # ✅ Databáze vytvořena
└── .cursorrules         # ✅ Pravidla pro Cursor
```

---

## 📋 DŮLEŽITÉ INFO

### **ID vs Číslo výkresu**
- **ID** - auto-increment integer (1, 2, 3...) - TECHNICKÝ klíč
- **part_number** - číslo výkresu (9007, 15005518FMG...) - BUSINESS klíč
- **UUID NENÍ** implementované - podle ADR-003 není potřeba

### **Materiál**
- `material_group` - povinné (vychází se z toho)
- `material_name` - volitelné (jen lidsky čitelné označení)

### **Tech Stack**
- Backend: FastAPI + SQLAlchemy + SQLite
- Frontend: Jinja2 + HTMX + Alpine.js (ŽÁDNÝ React!)
- CSS: Guesstimator style (dark theme)

---

## 🎨 DESIGN SYSTEM v1.0 (LOCKED)

### **CSS Architecture**
```
gestima.css (main)
├── @import 'variables.css'    # Barvy, font sizes
├── @import 'base.css'          # Body, watermark (0.079 opacity), main-content
├── @import 'layout.css'        # Split layout, sticky panels, scrollable content
├── @import 'components.css'    # Ribbons, buttons, forms, toast
└── @import 'operations.css'    # Operation cards, mode buttons
```

### **Layout System (FINÁLNÍ)**
- **Responsivní:** 80% šířka s pruhy po stranách
- **Minimální:** 1200px (horizontal scrollbar pokud menší)
- **Maximální:** 2400px (pruhy se zvětší na velkých monitorech)
- **Left Panel:** 
  - 320px fixed width
  - `position: sticky; top: 60px`
  - `max-height: calc(100vh - 60px - 1.5rem)`
  - Samostatný scroll
- **Right Panel:**
  - `flex: 1` (zbytek místa)
  - `max-height: calc(100vh - 60px)`
  - **Sticky čas nahoře** (`.right-panel-sticky`)
  - **Scrollovatelný obsah** (`.right-panel-content`)

### **Branding**
- **Logo:** KOVO RYBKA (header, footer, watermark na pozadí)
- **Slogan:** "Be lazy. It's way better than talking to people." (footer)
- **Verze:** v1.0.0 (header badge, footer)
- **Tech Stack:** FastAPI + SQLite + HTMX + Alpine.js (footer)
- **Watermark opacity:** 0.079 (+58% od originálu)

### **Interaktivita**
- **Ribbony:** Všechny collapsible (Alpine.js `x-show`)
  - Levý panel: Základní údaje, Cenový přehled
  - Pravý panel: Čas na kus (sticky), Operace
- **Operace:** Rozbalovací detaily (`x-collapse`, klik na header)
- **Mode buttons:** `@click.stop` (neklikne na celý header)
- **Toast notifikace:** 
  - Pozice: `bottom: 35px` (těsně nad footerem)
  - Zarovnání: zprava (`align-items: flex-end`)
  - Pozadí: 50% opacity + 2px border
  - Barvy: Success (zelená), Error (červená), Info (modrá)
  - Bílý text, backdrop blur
- **Footer:** Grid layout (1fr auto 1fr) - perfektně symetrický

---

## ⏭️ DALŠÍ KROKY (v novém chatu)

### **Priorita 1: Funkčnost operací**
1. **Otestovat přidání operace**
   - Ověřit že API funguje
   - Debugovat console.log výstupy
   - Ověřit že se operace zobrazí v UI

2. **Implementovat features (kroky operace)**
   - Formulář pro geometrii
   - Výpočet času
   - Zobrazení v tabulce

5. **Kalkulace cen**
   - `price_calculator.py`
   - Vytvoření dávek (100ks, 200ks, 1000ks)
   - Zobrazení v cenovém ribbonu

---

## 🐛 KNOWN ISSUES

### **Vyřešeno v této session:**
1. ✅ Duplicitní číslo výkresu → UNIQUE constraint přidán
2. ✅ Layout levá/pravá strana prohozená → opraveno
3. ✅ Design neodpovídá Guesstimator UI → CSS zkopírován a implementován
4. ✅ Responsivní layout → 80% šířka s pruhy po stranách (min 1200px, max 2400px)
5. ✅ Sticky čas se hýbal při scrollu → opraveno (vnitřní scroll v pravém panelu)
6. ✅ Ribbon headery různé výšky → sjednoceno (min-height: 38px, font 0.85rem)
7. ✅ Toast notifikace neviditelné → 50% opacity pozadí, 2px border, bílý text
8. ✅ Toast pozice špatná → bottom: 35px (těsně nad footerem), zarovnání zprava

### **Zbývá implementovat:**
- ⚠️ Přidání operace (API endpoint existuje, potřebuje otestovat)
- ⚠️ Features (kroky operace)
- ⚠️ Kalkulace času a cen

---

## 📞 REFERENCE PRO DALŠÍ SESSION

- **Originální CSS:** `/Users/lofas/Documents/Cursor/Guesstimator/static/css/`
- **UI Reference:** `/Users/lofas/Documents/__App/Gestima/Docs/UI_REFERENCE.md`
- **Specifikace:** `/Users/lofas/Documents/__App/Gestima/Docs/GESTIMA_1.0_SPEC.md`
- **Lessons Learned:** `/Users/lofas/Documents/__App/Gestima/Docs/LESSONS.md`

---

**Konec Session #1** ✅
