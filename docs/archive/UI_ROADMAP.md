# GESTIMA - UI ROADMAP v1.0

**Status:** 🚧 IN PROGRESS
**Datum:** 2026-01-24
**Účel:** Plán implementace kompletního uživatelského rozhraní

---

## 📋 SOUČASNÝ STAV

### ✅ CO MÁME (Backend + Částečné UI)

**Backend (API) - HOTOVO:**
- ✅ Authentication API (`POST /api/auth/login`, `/logout`, `/me`)
- ✅ RBAC (Admin/Operator/Viewer) s role hierarchy
- ✅ Parts CRUD (GET/POST/PUT/DELETE `/api/parts`)
- ✅ Operations CRUD + change-mode endpoint
- ✅ Features CRUD (backend hotovo, UI chybí)
- ✅ Batches CRUD (backend hotovo, UI částečné)
- ✅ Data endpoints (materials, stock-price, cutting-conditions)

**Frontend (Templates) - ČÁSTEČNÉ:**
- ✅ [base.html](app/templates/base.html) - layout, navbar, footer
- ✅ [index.html](app/templates/index.html) - Dashboard (seznam posledních 20 dílů)
- ✅ [parts/list.html](app/templates/parts/list.html) - Seznam všech dílů
- ✅ [parts/new.html](app/templates/parts/new.html) - Formulář pro vytvoření dílu (včetně live ceny polotovaru)
- ✅ [parts/edit.html](app/templates/parts/edit.html) - Editace dílu:
  - ✅ Základní údaje (Ribbon)
  - ✅ Materiál & polotovar + live cena (Ribbon)
  - ✅ Operace (přidání, změna režimu LOW/MID/HIGH)
  - ✅ Cenový přehled (Batches - pouze zobrazení)

**CSS Design - HOTOVO:**
- ✅ [docs/UI_REFERENCE.md](docs/UI_REFERENCE.md) - kompletní design guide
- ✅ `/app/static/css/gestima.css` - implementované CSS (dark theme, ribbons, buttons)

---

### ❌ CO CHYBÍ (Kritické bloky)

| Komponenta | Status | Důvod blokování | Priorita |
|------------|--------|-----------------|----------|
| **Login UI** | ❌ CHYBÍ | Nelze se přihlásit, app je nechráněná | **P0 - BLOCKER** |
| **Auth ochrana** | ❌ CHYBÍ | Pages nejsou chráněné `Depends(get_current_user)` | **P0 - BLOCKER** |
| **Features UI** | ❌ CHYBÍ | Nelze přidávat prvky operací → výpočty nefungují | **P0 - BLOCKER** |
| **Batches UI** | ⚠️ ČÁSTEČNÉ | Zobrazení funguje, chybí vytváření nabídek | **P1 - KRITICKÉ** |
| **Navbar User Info** | ❌ CHYBÍ | Nezobrazuje přihlášeného uživatele + Logout | **P1 - KRITICKÉ** |

---

## 🛣️ ROADMAP - Implementační fáze

### **FÁZE 0: Login & Authentication UI** ⭐ NEJVYŠŠÍ PRIORITA

**Cíl:** Uživatel se může přihlásit a používat aplikaci bezpečně.

#### Úkoly:

**1. Login stránka**
- [ ] Vytvořit `app/templates/auth/login.html`
  - Formulář: username + password
  - Použít UI design z [UI_REFERENCE.md](UI_REFERENCE.md) (dark theme, flat buttons)
  - Alpine.js pro AJAX submit na `POST /api/auth/login`
  - Toast notifikace při chybě/úspěchu
  - Redirect na `/` po úspěšném přihlášení

**2. Pages router - přidat route**
- [ ] Upravit [app/routers/pages_router.py](app/routers/pages_router.py):
  ```python
  @router.get("/login", response_class=HTMLResponse)
  async def login_page(request: Request):
      return templates.TemplateResponse("auth/login.html", {"request": request})
  ```

**3. Ochrana stránek**
- [ ] Přidat `Depends(get_current_user)` do všech protected routes:
  - `GET /` (index)
  - `GET /parts`
  - `GET /parts/new`
  - `GET /parts/{id}/edit`

**4. Exception handler - redirect**
- [ ] V [app/gestima_app.py](app/gestima_app.py) přidat handler pro 401:
  ```python
  @app.exception_handler(HTTPException)
  async def http_exception_handler(request: Request, exc: HTTPException):
      if exc.status_code == 401:
          # Pokud je HTML request → redirect na /login
          if "text/html" in request.headers.get("accept", ""):
              return RedirectResponse(url="/login?redirect=" + str(request.url))
      raise exc
  ```

**5. Navbar - přidat User Info + Logout**
- [ ] Upravit [app/templates/base.html](app/templates/base.html):
  - Navbar right: `{{ user.username }} ({{ user.role }}) | Logout`
  - Logout button → `POST /api/auth/logout` → redirect na `/login`
  - Alpine.js state pro current user (`GET /api/auth/me`)

**6. Login redirect flow**
- [ ] Po přihlášení: redirect na původní URL (query param `?redirect=`)

#### Kritéria úspěchu:
- ✅ Nelze přistoupit na `/` bez přihlášení → redirect na `/login`
- ✅ Po přihlášení uvidím dashboard + v navbaru své jméno
- ✅ Logout button funguje → odhlásí a přesměruje na `/login`

---

### **FÁZE 1: Seznam dílů (Parts List)**

**Cíl:** Přehledný seznam všech dílů s filtrováním a řazením.

#### Současný stav:
- ✅ [parts/list.html](app/templates/parts/list.html) existuje
- ✅ Zobrazuje díly v tabulce (číslo, název, materiál)
- ⚠️ Chybí: filtry, řazení, akce (edit, delete)

#### Úkoly:

**1. Vylepšit tabulku dílů**
- [ ] Přidat sloupce:
  - `part_number` (klikatelný → edit)
  - `name`
  - `material_group` + `material_name`
  - `stock_type` (ikona: 🔵 Tyč, ⭕ Trubka, ...)
  - `updated_at` (poslední úprava)
  - Akce: 🔧 Edit | 🗑️ Smazat

**2. Filtry + Search**
- [ ] Vyhledávací pole (part_number, name)
- [ ] Filtr podle materiálu (dropdown)
- [ ] Filtr podle stock_type (checkboxy)
- [ ] HTMX: live update při změně filtru (`hx-get="/parts" hx-trigger="change"`)

**3. Řazení**
- [ ] Klikatelné column headery (řadit podle sloupce)
- [ ] Default: `ORDER BY updated_at DESC`

**4. Delete funkce**
- [ ] Tlačítko 🗑️ → Confirmation dialog
- [ ] `DELETE /api/parts/{id}` (soft delete)
- [ ] HTMX: odstranit řádek z tabulky bez reload

**5. Prázdný stav**
- [ ] Pokud žádné díly: velký button "➕ Vytvořit první díl"

#### Kritéria úspěchu:
- ✅ Seznam zobrazuje všechny díly s kompletními informacemi
- ✅ Vyhledávání funguje (part_number nebo name)
- ✅ Lze smazat díl (s potvrzením)
- ✅ Klik na díl → otevře editaci

---

### **FÁZE 2: Edit dílu - Features UI** ⚠️ BLOCKER PRO VÝPOČTY

**Cíl:** Umožnit přidávání prvků (features) k operacím → spustit výpočty časů a cen.

#### Současný stav:
- ✅ [parts/edit.html](app/templates/parts/edit.html) - operace fungují
- ❌ V místě features je placeholder: *"📝 Kroky operace (zatím neimplementováno)"* ([edit.html:262](app/templates/parts/edit.html#L262))

#### Úkoly:

**1. Features komponenta (rozbalovací seznam)**
- [ ] Při rozbalení operace zobrazit seznam prvků:
  ```html
  <div class="features-section" x-show="expanded">
      <div class="feature-list">
          <template x-for="feat in operation.features">
              <div class="feature-item">
                  📏 Díra Ø12 x 50mm | tp: 2.5 min
                  <button @click="deleteFeature(feat.id)">🗑️</button>
              </div>
          </template>
      </div>
      <button @click="addFeature(op.id)" class="btn-add-feature">
          + Přidat prvek
      </button>
  </div>
  ```

**2. Formulář pro přidání prvku**
- [ ] Modal/Inline formulář:
  - Typ prvku: `<select>` (díra, závit, drážka, povrch, ...)
  - Průměr: `<input type="number">` (pokud relevantní)
  - Délka/Hloubka: `<input type="number">`
  - Počet: `<input type="number" default="1">`
  - Výpočet: Backend automaticky spočítá `t_p` (čas na prvek)

**3. Backend endpoint**
- [ ] `POST /api/features/` - vytvořit prvek
  - Input: `operation_id`, `feature_type`, `diameter`, `length`, `count`
  - Output: Feature object s vypočítaným `t_p`
  - Přepočítat `operation_time_min` celé operace
  - Vrátit: updated feature + updated operation

**4. Live update časů**
- [ ] Po přidání/smazání prvku:
  - Aktualizovat `operation.operation_time_min`
  - Aktualizovat `totalTime` (součet všech operací)
  - Aktualizovat všechny batches (ceny se změní)

**5. Typy prvků (Feature types)**
- [ ] Implementovat podle [GESTIMA_1.0_SPEC.md](GESTIMA_1.0_SPEC.md):
  - `hole` - Díra (Ø, hloubka)
  - `thread` - Závit (Ø, délka, stoupání)
  - `groove` - Drážka (šířka, hloubka, délka)
  - `surface` - Povrch (průměr, délka - např. soustružení plochy)
  - `contour` - Obrys (frézování tvaru)

#### Kritéria úspěchu:
- ✅ Lze přidat prvek k operaci (např. "Díra Ø12 x 50mm")
- ✅ Backend automaticky spočítá `t_p` (čas vrtání)
- ✅ `operation_time_min` se aktualizuje po přidání prvku
- ✅ `totalTime` v ribbonu "⏱️ Čas na kus" se aktualizuje
- ✅ Ceny v batches se přepočítají automaticky

---

### **FÁZE 3: Batches UI - Vytváření nabídek**

**Cíl:** Vytvořit nabídky pro různé množství (1ks, 10ks, 100ks, ...).

#### Současný stav:
- ✅ Cenový přehled (Ribbon) zobrazuje existující batches
- ❌ Nelze vytvářet nové batches přes UI

#### Úkoly:

**1. Formulář pro vytvoření batch**
- [ ] V ribbonu "📊 Cenový přehled" přidat button:
  ```html
  <button @click="showBatchForm = true" class="btn-add-batch">
      + Přidat cenovou nabídku
  </button>
  ```

**2. Inline formulář**
- [ ] Pole:
  - Množství: `<input type="number" placeholder="např. 100">`
  - Tlačítka:
    - `💾 Vypočítat` → `POST /api/batches/`
    - `❌ Zrušit`

**3. Backend endpoint**
- [ ] `POST /api/batches/` - vytvořit batch:
  - Input: `part_id`, `quantity`
  - Backend spočítá:
    - `t_piece` (čas na kus = součet operation_time_min)
    - `t_setup` (součet setup_time_min)
    - `material_cost` (cena polotovaru)
    - `machining_cost` (stroj * čas)
    - `total_cost`
    - `unit_cost` (cena za kus)
  - Vrátí: Batch object

**4. Zobrazení v tabulce**
- [ ] Aktualizovat seznam batches po vytvoření
- [ ] Formát:
  ```
  100 ks | 320 Kč/ks
  ```

**5. Delete batch**
- [ ] Button 🗑️ u každé nabídky
- [ ] `DELETE /api/batches/{id}`

**6. Price Bar (pokročilé - optional)**
- [ ] Vizuální rozdělení ceny (materiál | obrábění | seřízení):
  ```html
  <div class="price-bar">
      <div class="bar-segment mat" style="width: 30%"></div>
      <div class="bar-segment mach" style="width: 50%"></div>
      <div class="bar-segment setup" style="width: 20%"></div>
  </div>
  ```
  (viz [UI_REFERENCE.md:288-329](UI_REFERENCE.md#L288-L329))

#### Kritéria úspěchu:
- ✅ Lze vytvořit nabídku pro konkrétní množství (např. 100ks)
- ✅ Backend automaticky spočítá jednotkovou cenu
- ✅ Nabídka se zobrazí v cenovém přehledu
- ✅ Lze smazat nabídku

---

### **FÁZE 4: Batch Freeze (Zmrazení cen)** - Pokročilé

**Cíl:** Zmrazit cenu nabídky (snapshot) aby se neměnila při změně materiálů/strojů.

#### Kontext:
- Podle [ADR-012](ADR/012-minimal-snapshot.md) - Minimal Snapshot implementován
- Backend: `POST /api/batches/{id}/freeze` - existuje
- UI: chybí tlačítko "🔒 Zmrazit cenu"

#### Úkoly:

**1. Freeze button**
- [ ] U každé nabídky v cenovém přehledu:
  ```html
  <button @click="freezeBatch(batch.id)" x-show="!batch.is_frozen">
      🔒 Zmrazit
  </button>
  <span x-show="batch.is_frozen" class="frozen-badge">
      🔒 Zmrazeno
  </span>
  ```

**2. Vizuální indikace**
- [ ] Zmrazená nabídka má jiný background (např. `--accent-blue` tint)
- [ ] Tooltip: "Cena je zmrazená k datu X"

**3. Immutability**
- [ ] Zmrazenou nabídku nelze editovat
- [ ] Tlačítko Edit je disabled pokud `is_frozen === true`

**4. Clone batch (optional)**
- [ ] Tlačítko "📋 Klonovat" u zmrazené nabídky
- [ ] `POST /api/batches/{id}/clone` → vytvoří novou nabídku s aktuálními cenami

#### Kritéria úspěchu:
- ✅ Lze zmrazit nabídku (cena se nezmění při změně materiálu)
- ✅ Zmrazená nabídka má vizuální indikaci (🔒)
- ✅ Zmrazenou nabídku nelze editovat

---

### **FÁZE 5: Dashboard vylepšení** - Nice to have

**Cíl:** Užitečný přehled pro rychlou orientaci.

#### Současný stav:
- ✅ Dashboard zobrazuje posledních 20 dílů
- ⚠️ Statistiky jsou hardcoded: *"Rozpracovaných: 0"*, *"Kalkulovaných: 0"*

#### Úkoly:

**1. Skutečné statistiky**
- [ ] Počítat z DB:
  - Celkem dílů (`COUNT(*)`)
  - Rozpracovaných (díly s operacemi, ale bez batches)
  - Kalkulovaných (díly s batches)

**2. Quick actions**
- [ ] Widget "⚡ Rychlé akce":
  - ➕ Nový díl
  - 📊 Zobrazit všechny díly
  - 📁 Exportovat nabídky (future)

**3. Poslední aktivity**
- [ ] Timeline:
  ```
  10:35 | Jan Novák vytvořil díl #15005518FMG
  09:20 | Petr Svoboda změnil operaci OP20 na dílu #12345
  ```

---

## 📊 TIMELINE - Odhad priorit

| Fáze | Komponenta | Priorita | Závislosti | Estimated |
|------|------------|----------|------------|-----------|
| **0** | Login & Auth UI | **P0 - BLOCKER** | - | 3-4h |
| **1** | Parts List | **P1** | Fáze 0 | 2h |
| **2** | Features UI | **P0 - BLOCKER** | Fáze 0 | 4-5h |
| **3** | Batches UI | **P1** | Fáze 2 | 2h |
| **4** | Batch Freeze | **P2** | Fáze 3 | 1h |
| **5** | Dashboard | **P3** | Fáze 1 | 1-2h |

**CELKEM:** ~13-16 hodin čisté implementace

---

## 🎯 NEXT STEPS - Co dělat TEĎ

### 1. Manuální test současného stavu
```bash
cd /Users/lofas/Documents/__App_Claude/Gestima
python3 gestima.py run
# Otevřít: http://localhost:8000
```

**Prozkoumat:**
- Funguje Dashboard?
- Funguje vytvoření dílu? (parts/new)
- Funguje editace dílu? (parts/{id}/edit)
- Zobrazuje se live cena polotovaru?
- Funguje přidání operace?
- Co se stane když kliknu na mode button (LOW/MID/HIGH)?

### 2. Vytvořit admin uživatele
```bash
python3 gestima.py create-admin
# Username: admin
# Password: ***
```

### 3. Začít s Fází 0 - Login UI
- Vytvořit `app/templates/auth/login.html`
- Implementovat auth flow
- Otestovat přihlášení

---

## 📝 POZNÁMKY

**Design konzistence:**
- Všechny komponenty používat z [UI_REFERENCE.md](UI_REFERENCE.md)
- Dark theme barvy (`--bg-primary`, `--accent-red`, ...)
- Ribbon layout pro sekce
- Flat buttons (`.btn-flat`)
- Toast notifikace pro feedback

**Alpine.js patterns:**
- State v `x-data="componentName()"`
- API volání v metodách (ne inline)
- Debouncing pro live updates (300-500ms)
- Error handling s toast notifikacemi

**HTMX usage:**
- Pro části stránky které se mění (list fragments)
- `hx-boost="true"` v base.html pro SPA-like navigation
- Partial updates (ne full page reload)

**Důležité:**
- Vždy aktualizovat celý stav po API změně (operace + features + batches + totalTime)
- Zachovat UI stav při update (expanded/collapsed ribbons)
- Validace na frontendu I backendu (never trust client)

---

**Verze:** 1.0
**Status:** 🚧 PLANNING
**Poslední update:** 2026-01-24
**Autor:** Claude Code + Lofas (diskuse)
