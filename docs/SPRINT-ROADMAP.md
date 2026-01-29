# GESTIMA Vue SPA - Sprint Roadmap

> **Vytvořeno:** 2026-01-29
> **Stav:** REALISTICKÁ ANALÝZA po hloubkovém auditu
> **Backend:** 100% hotový
> **Frontend Vue:** ~15-20% hotový (NE 75% jak dokumentace tvrdila)

---

## EXECUTIVE SUMMARY

### Co máme
- ✅ **Backend kompletní:** 14 modelů, 87+ endpoints, services, auth
- ✅ **Vue struktura:** Router, stores, API clients, základní komponenty
- ✅ **Testy:** 286 unit testů (100% pass)
- ✅ **Build:** 60.67 KB gzipped

### Co NEMÁME (kritické)
- ❌ **Navigace:** AppHeader pouze na Dashboardu - uživatel se zasekne
- ❌ **PartMaterialModule:** Placeholder (30 řádků, jen text)
- ❌ **PartOperationsModule:** Neexistuje!
- ❌ **PartPricingModule:** Neexistuje!
- ❌ **Admin/MasterData:** Placeholder (TODO text)
- ❌ **WorkCenters:** Placeholder
- ❌ **Settings:** Placeholder

### Klíčové číslo
```
Dokumentace tvrdí: 75% hotovo
Realita:           15-20% hotovo
Gap:               55-60% práce před námi
```

---

## SPRINT ROADMAP

```
┌─────────────────────────────────────────────────────────────┐
│  SPRINT 0: FOUNDATION FIX (BLOKUJÍCÍ)           ~4h        │
│  "Bez navigace není aplikace"                              │
├─────────────────────────────────────────────────────────────┤
│  SPRINT 1: CORE PARTS FLOW                      ~12h       │
│  "Díl → Materiál → Operace → Cena"                         │
├─────────────────────────────────────────────────────────────┤
│  SPRINT 2: SUPPORTING FEATURES                  ~8h        │
│  "WorkCenters, Settings"                                   │
├─────────────────────────────────────────────────────────────┤
│  SPRINT 3: ADMIN & DATA                         ~8h        │
│  "Master Data management"                                  │
├─────────────────────────────────────────────────────────────┤
│  SPRINT 4: POLISH & DEPLOY                      ~8h        │
│  "E2E testy, integrace, production"                        │
└─────────────────────────────────────────────────────────────┘

TOTAL ESTIMATE: ~40h (1 týden full-time nebo 2 týdny part-time)
```

---

## SPRINT 0: FOUNDATION FIX 🚨
**Priorita:** BLOKUJÍCÍ
**Odhad:** 4 hodiny
**Cíl:** Uživatel se může pohybovat po aplikaci

### Deliverables

| # | Task | Soubor | Čas |
|---|------|--------|-----|
| 0.1 | Layout wrapper s AppHeader/Footer | `App.vue` nebo `DefaultLayout.vue` | 1h |
| 0.2 | Podmínka: skrýt header na /login | Router meta nebo v-if | 0.5h |
| 0.3 | Ověřit všechny routes mají navigaci | Manual test | 0.5h |
| 0.4 | Breadcrumbs nebo "← Zpět" konzistentně | Všechny views | 1h |
| 0.5 | Smoke test: proklikání celé app | Manual E2E | 1h |

### Acceptance Criteria
```
✅ Z JAKÉKOLIV stránky se dostanu na Dashboard
✅ Z JAKÉKOLIV stránky se dostanu na Parts List
✅ Header viditelný všude kromě Login
✅ Logout funguje z jakékoliv stránky
```

### Technický návrh
```vue
<!-- App.vue -->
<template>
  <div id="app">
    <!-- Header všude kromě login -->
    <AppHeader v-if="!isLoginPage" />

    <main class="main-content">
      <RouterView />
    </main>

    <!-- Footer všude kromě login -->
    <AppFooter v-if="!isLoginPage" />

    <ToastContainer />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const isLoginPage = computed(() => route.name === 'login')
</script>
```

---

## SPRINT 1: CORE PARTS FLOW
**Priorita:** HIGH
**Odhad:** 12 hodin
**Cíl:** Kompletní CRUD pro díly včetně materiálu, operací a kalkulace

### Deliverables

| # | Task | Soubor | Čas |
|---|------|--------|-----|
| 1.1 | **PartOperationsModule** - CRUD operací | `PartOperationsModule.vue` | 4h |
| 1.2 | **PartMaterialModule** - CRUD materiálů | `PartMaterialModule.vue` | 4h |
| 1.3 | **PartPricingModule** - zobrazení kalkulace | `PartPricingModule.vue` | 2h |
| 1.4 | Materials store - actions | `stores/materials.ts` | 1h |
| 1.5 | Integration test - celý flow | Manual + unit | 1h |

### 1.1 PartOperationsModule (4h)

**Backend API (už existuje):**
- `GET /api/parts/{part_number}/operations`
- `POST /api/parts/{part_number}/operations`
- `PUT /api/operations/{id}`
- `DELETE /api/operations/{id}`

**Frontend potřebuje:**
```vue
<template>
  <div class="operations-module">
    <!-- Tabulka operací -->
    <DataTable :data="operations" :columns="columns">
      <template #actions="{ row }">
        <button @click="editOperation(row)">✏️</button>
        <button @click="deleteOperation(row.id)">🗑️</button>
      </template>
    </DataTable>

    <!-- Přidat operaci -->
    <button @click="showAddForm = true">+ Přidat operaci</button>

    <!-- Modal pro edit/create -->
    <Modal v-model="showForm">
      <OperationForm
        :operation="editingOperation"
        :work-centers="workCenters"
        @save="saveOperation"
        @cancel="closeForm"
      />
    </Modal>
  </div>
</template>
```

**Pole operace:**
- seq (pořadí)
- name (název)
- work_center_id (pracoviště - select)
- setup_time_min (tp - přípravný čas)
- operation_time_min (tj - kusový čas)
- is_coop (kooperace checkbox)
- coop_price, coop_min_price, coop_days (pokud is_coop)

### 1.2 PartMaterialModule (4h)

**Backend API (už existuje):**
- `GET /api/material-inputs?part_id={id}`
- `POST /api/material-inputs`
- `PUT /api/material-inputs/{id}`
- `DELETE /api/material-inputs/{id}`
- `POST /api/material-inputs/{id}/operations/{op_id}` (link)

**Frontend potřebuje:**
```vue
<template>
  <div class="material-module">
    <!-- Seznam materiálů -->
    <div v-for="input in materialInputs" :key="input.id" class="material-card">
      <div class="material-info">
        <span class="shape-icon">{{ shapeIcon(input.stock_shape) }}</span>
        <span>{{ input.material_category?.name }}</span>
        <span>{{ formatDimensions(input) }}</span>
        <span>{{ input.quantity }}x</span>
      </div>
      <div class="material-actions">
        <button @click="edit(input)">✏️</button>
        <button @click="remove(input.id)">🗑️</button>
      </div>
    </div>

    <!-- Přidat materiál -->
    <button @click="showAddForm = true">+ Přidat materiál</button>

    <!-- Form modal -->
    <Modal v-model="showForm">
      <MaterialInputForm
        :input="editingInput"
        :categories="categories"
        :operations="partOperations"
        @save="save"
      />
    </Modal>
  </div>
</template>
```

**Pole MaterialInput:**
- price_category_id (select z kategorií)
- material_item_id (volitelné - konkrétní položka)
- stock_shape: CYLINDER | BOX | TUBE | SHEET
- stock_diameter, stock_length (pro CYLINDER)
- stock_width, stock_height, stock_length (pro BOX)
- quantity (počet kusů)
- linked_operations[] (M:N checkboxy)

### 1.3 PartPricingModule (2h)

**Backend API (už existuje):**
- `GET /api/parts/{part_number}/pricing`
- `POST /api/parts/{part_number}/batches` (vytvořit batch)

**Frontend potřebuje:**
```vue
<template>
  <div class="pricing-module">
    <!-- Batch selector -->
    <div class="batch-selector">
      <label>Série:</label>
      <input v-model.number="batchSize" type="number" min="1" />
      <button @click="calculatePrice">Vypočítat</button>
    </div>

    <!-- Price breakdown -->
    <div v-if="pricing" class="price-breakdown">
      <div class="price-row">
        <span>Materiál:</span>
        <span>{{ formatCurrency(pricing.material_cost) }}</span>
      </div>
      <div class="price-row">
        <span>Práce:</span>
        <span>{{ formatCurrency(pricing.labor_cost) }}</span>
      </div>
      <div class="price-row">
        <span>Kooperace:</span>
        <span>{{ formatCurrency(pricing.coop_cost) }}</span>
      </div>
      <div class="price-row total">
        <span>CELKEM:</span>
        <span>{{ formatCurrency(pricing.total_price) }}</span>
      </div>
      <div class="price-row per-piece">
        <span>Cena/ks:</span>
        <span>{{ formatCurrency(pricing.price_per_piece) }}</span>
      </div>
    </div>
  </div>
</template>
```

### Acceptance Criteria Sprint 1
```
✅ Mohu přidat/editovat/smazat operaci na dílu
✅ Mohu přidat/editovat/smazat materiál na dílu
✅ Mohu propojit materiál s operacemi (M:N)
✅ Vidím kalkulaci ceny pro zadanou sérii
✅ Všechna data se ukládají do DB přes API
```

---

## SPRINT 2: SUPPORTING FEATURES
**Priorita:** MEDIUM
**Odhad:** 8 hodin
**Cíl:** WorkCenters a Settings fungují

### Deliverables

| # | Task | Soubor | Čas |
|---|------|--------|-----|
| 2.1 | WorkCentersListView - reálný obsah | `WorkCentersListView.vue` | 2h |
| 2.2 | WorkCenterEditView - formulář | `WorkCenterEditView.vue` | 2h |
| 2.3 | WorkCenters store | `stores/workCenters.ts` | 1h |
| 2.4 | SettingsView - user preferences | `SettingsView.vue` | 2h |
| 2.5 | Dark mode persistence | `useDarkMode.ts` | 1h |

### WorkCenter Model (backend existuje)
```typescript
interface WorkCenter {
  id: number
  work_center_number: string  // WCXXXXXX
  name: string
  type: 'lathe' | 'mill' | 'saw' | 'grinder' | 'drill' | 'manual'
  hourly_rate: number
  efficiency: number  // 0.0 - 1.0
  is_active: boolean
}
```

### Acceptance Criteria Sprint 2
```
✅ Vidím seznam pracovišť
✅ Mohu přidat/editovat/smazat pracoviště
✅ V operacích mohu vybrat pracoviště ze selectu
✅ Settings: změna hesla, jazyk, dark mode
✅ Dark mode se pamatuje po refreshi
```

---

## SPRINT 3: ADMIN & DATA
**Priorita:** MEDIUM
**Odhad:** 8 hodin
**Cíl:** Admin může spravovat číselníky

### Deliverables

| # | Task | Soubor | Čas |
|---|------|--------|-----|
| 3.1 | MaterialGroupsTab - CRUD | `MasterDataView.vue` | 2h |
| 3.2 | MaterialCategoriesTab - CRUD | `MasterDataView.vue` | 2h |
| 3.3 | MaterialItemsTab - CRUD | `MasterDataView.vue` | 2h |
| 3.4 | MaterialNormsTab - import/CRUD | `MasterDataView.vue` | 2h |

### Admin API Endpoints (backend existuje)
```
GET/POST /api/admin/material-groups
GET/POST /api/admin/material-categories
GET/POST /api/admin/material-items
GET/POST /api/admin/material-norms
DELETE /api/admin/{entity}/{id}
```

### Acceptance Criteria Sprint 3
```
✅ Admin vidí 4 tabs v Master Data
✅ Každý tab má tabulku s daty
✅ CRUD pro všechny entity
✅ Validace na unikátní kódy
✅ Soft delete s potvrzením
```

---

## SPRINT 4: POLISH & DEPLOY
**Priorita:** LOW (ale nutné pro produkci)
**Odhad:** 8 hodin
**Cíl:** Production-ready aplikace

### Deliverables

| # | Task | Čas |
|---|------|-----|
| 4.1 | E2E testy (Playwright) - happy paths | 3h |
| 4.2 | FastAPI static file serving | 1h |
| 4.3 | Environment config (dev/staging/prod) | 1h |
| 4.4 | Error boundaries a fallbacks | 1h |
| 4.5 | Performance audit (Lighthouse) | 1h |
| 4.6 | Dokumentace aktualizace | 1h |

### E2E Test Scenarios
```typescript
// tests/e2e/happy-path.spec.ts
test('Complete part creation flow', async ({ page }) => {
  // Login
  await page.goto('/login')
  await page.fill('[data-testid="username"]', 'demo')
  await page.fill('[data-testid="password"]', 'demo123')
  await page.click('[data-testid="login-button"]')

  // Navigate to parts
  await page.click('text=Díly')
  await expect(page).toHaveURL('/parts')

  // Create part
  await page.click('[data-testid="create-part-button"]')
  await page.fill('[data-testid="part-name-input"]', 'Test Part')
  await page.click('[data-testid="save-button"]')

  // Verify redirect to detail
  await expect(page).toHaveURL(/\/parts\/\d+/)

  // Add operation
  await page.click('text=Operace')
  await page.click('text=+ Přidat operaci')
  // ...
})
```

### Acceptance Criteria Sprint 4
```
✅ E2E testy procházejí
✅ Vue app servována z FastAPI
✅ Lighthouse score > 90
✅ Žádné console errors
✅ Dokumentace odpovídá realitě
```

---

## TIMELINE VIZUALIZACE

```
TÝDEN 1
├── Po: Sprint 0 (4h) - Layout fix
├── Út: Sprint 1.1 (4h) - Operations module
├── St: Sprint 1.2 (4h) - Materials module
├── Čt: Sprint 1.3-1.5 (4h) - Pricing + integration
└── Pá: Buffer / Bug fixes

TÝDEN 2
├── Po: Sprint 2.1-2.2 (4h) - WorkCenters
├── Út: Sprint 2.3-2.5 (4h) - Settings
├── St: Sprint 3.1-3.2 (4h) - Admin tabs 1-2
├── Čt: Sprint 3.3-3.4 (4h) - Admin tabs 3-4
└── Pá: Sprint 4 (8h) - Polish & Deploy

CELKEM: 10 pracovních dnů = 2 týdny
```

---

## RIZIKA A MITIGACE

| Riziko | Pravděpodobnost | Dopad | Mitigace |
|--------|-----------------|-------|----------|
| API nekompatibilita | Nízká | Vysoký | Backend už existuje a je otestovaný |
| Store complexity | Střední | Střední | Použít existující patterns z parts store |
| CSS conflicts | Střední | Nízký | Design system už existuje |
| Time overrun | Vysoká | Střední | Buffer den každý týden |

---

## DEFINICE HOTOVO (DoD)

Pro KAŽDÝ sprint:
- [ ] Kód napsán a funguje
- [ ] Unit testy přidány (kde relevantní)
- [ ] Manual test proklikáním
- [ ] Žádné console errors
- [ ] Responsive (desktop 1200px+)
- [ ] Dokumentace aktualizována

---

## QUICK WINS (Můžeme udělat HNED)

Pokud chceš vidět rychlý progres, Sprint 0 je **4 hodiny práce** a dramaticky zlepší UX:

```bash
# Po Sprint 0 bude:
✅ Header na všech stránkách
✅ Navigace funguje
✅ Uživatel se nezasekne
```

**Doporučení:** Začni Sprint 0 DNES.

---

## POZNÁMKY

- Všechny odhady jsou konzervativní (přidáno 20% buffer)
- Backend je 100% ready - nemusíme nic měnit
- 286 unit testů zajišťuje stabilitu
- Design system existuje - jen ho použít

---

*Dokument vytvořen: 2026-01-29*
*Autor: Roy (IT Crowd Mode)*
*Status: APPROVED FOR EXECUTION*
