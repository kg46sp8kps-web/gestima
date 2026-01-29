# GESTIMA: ULTIMATE ROAD TO BETA

> **Vytvořeno:** 2026-01-29
> **Verze:** 1.0
> **Status:** SINGLE SOURCE OF TRUTH pro cestu k BETA release
> **Autor:** Roy (IT Crowd Mode) - "Have you tried turning it off and on again?"

---

## EXECUTIVE SUMMARY

### Co dokumentace TVRDÍ vs. REALITA

| Oblast | Dokumentace | Realita | Gap |
|--------|-------------|---------|-----|
| **Vue Frontend** | 75% hotovo | **15-20%** | 55-60% |
| **Navigace** | Funguje | **BROKEN** - header jen na Dashboard | CRITICAL |
| **Parts CRUD** | ✅ | ⚠️ Material tab = placeholder | 40% |
| **Operations** | ✅ | ❌ Modul NEEXISTUJE | 100% |
| **Materials** | ❌ | ❌ 30 řádků placeholder | 100% |
| **Backend** | 100% | ✅ 100% | 0% - OK! |
| **Testy** | 286 unit | ✅ 286 passing | 0% - OK! |

### Klíčové problémy

```
🔴 CRITICAL: Navigace NEFUNGUJE
   - AppHeader existuje ale JEN na Dashboard
   - Uživatel se ZASEKNE po opuštění dashboardu
   - Musí ručně měnit URL

🔴 CRITICAL: Klíčové moduly NEEXISTUJÍ
   - PartOperationsModule.vue = ???
   - PartMaterialModule.vue = 30 řádků placeholder
   - PartPricingModule.vue = ???

🟡 MEDIUM: Backend cleanup
   - 4 long functions (>80 LOC)
   - 10 debug print() statements
   - Float→Decimal migration pending

🟢 GOOD: Co funguje
   - Backend API kompletní (87+ endpoints)
   - Auth/JWT/RBAC funguje
   - Unit testy passing (286)
   - Build funguje (60.67 KB)
```

---

## ROAD TO BETA: 4 MILESTONES

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│   MILESTONE 0: NAVIGATION FIX              🚨 BLOKUJÍCÍ                │
│   "Uživatel se může pohybovat"              ~4 hodiny                   │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   MILESTONE 1: CORE FLOW                   💰 BUSINESS VALUE           │
│   "Díl → Materiál → Operace → Cena"         ~16 hodin                  │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   MILESTONE 2: SUPPORTING FEATURES         📦 COMPLETENESS             │
│   "WorkCenters, Admin, Settings"            ~12 hodin                  │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   MILESTONE 3: QUALITY & DEPLOY            🚀 PRODUCTION               │
│   "Testy, cleanup, nasazení"                ~16 hodin                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

TOTAL: ~48 hodin = 6 pracovních dnů = 2 týdny part-time
```

---

## MILESTONE 0: NAVIGATION FIX ✅ COMPLETED

**Status:** ✅ HOTOVO (2026-01-29)
**Effort:** ~2 hodiny (rychlejší než odhadováno!)
**Výstup:** Uživatel se dostane odkudkoliv kamkoliv

### Co bylo implementováno:
- ✅ **App.vue** - Global layout with conditional header/footer
- ✅ **AppHeader.vue** - Hamburger menu navigation (logo, search, favorites, user, menu)
- ✅ **AppFooter.vue** - 3-column layout with "Be lazy..." motto
- ✅ **WindowsView.vue** - Fixed to work within global chrome

### Problém

```
AKTUÁLNÍ STAV:

  Dashboard ──────────────→ Parts List
     ✅                         ❌
  (má header)              (ŽÁDNÝ header!)
                                  │
                                  ↓
                           Part Detail
                               ❌
                          (ŽÁDNÝ header!)
                                  │
                          Jak se vrátit?
                               🔒
                          UVĚZNĚN!
```

### Řešení

**Upravit `App.vue` - přidat globální layout:**

```vue
<!-- frontend/src/App.vue -->
<template>
  <div id="app" :class="{ 'is-login': isLoginPage }">
    <!-- Header všude kromě login -->
    <AppHeader v-if="!isLoginPage" />

    <main class="main-content" :class="{ 'with-header': !isLoginPage }">
      <RouterView />
    </main>

    <!-- Footer všude kromě login -->
    <AppFooter v-if="!isLoginPage" />

    <!-- Global toast notifications -->
    <ToastContainer />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useDarkMode } from '@/composables/useDarkMode'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
import ToastContainer from '@/components/ui/ToastContainer.vue'

const route = useRoute()
const { isDark } = useDarkMode()

const isLoginPage = computed(() => route.name === 'login')
</script>

<style>
.main-content {
  flex: 1;
  overflow: auto;
}

.main-content.with-header {
  /* Adjust for fixed header if needed */
}
</style>
```

### Tasklist

| # | Task | Čas | Soubor |
|---|------|-----|--------|
| 0.1 | Upravit App.vue - přidat AppHeader/Footer | 1h | `App.vue` |
| 0.2 | Odstranit duplicate header z DashboardView | 30m | `DashboardView.vue` |
| 0.3 | Sjednotit CSS pro main-content | 30m | `App.vue` + views |
| 0.4 | Test: proklikání všech routes | 1h | Manual |
| 0.5 | Fix: případné CSS konflikty | 1h | Various |

### Acceptance Criteria

```bash
✅ Z /parts se dostanu na Dashboard (klik na logo)
✅ Z /parts/:id se dostanu na /parts (← Zpět nebo menu)
✅ Z jakékoliv stránky vidím header s navigací
✅ Logout funguje z jakékoliv stránky
✅ Žádné console errors
```

### Verification

```bash
# Po dokončení:
npm run dev
# Proklikat: / → /parts → /parts/new → vytvořit → /parts/:id → /work-centers → /settings → /
# Všude musí být header!
```

---

## MILESTONE 1: CORE FLOW 💰

**Status:** HIGHEST BUSINESS VALUE
**Effort:** 16 hodin
**Výstup:** Kompletní workflow: Díl → Materiál → Operace → Kalkulace ceny

### Co chybí

| Komponenta | Stav | Potřeba |
|------------|------|---------|
| **PartOperationsModule** | ❓ Neexistuje nebo nefunkční | CRUD operací |
| **PartMaterialModule** | ❌ 30 řádků placeholder | CRUD materiálů |
| **PartPricingModule** | ❓ Neověřeno | Zobrazení kalkulace |
| **materials.ts store** | ❌ Prázdný | Actions pro MaterialInput |

### 1.1 PartOperationsModule (4h)

**Backend API (existuje):**
- `GET /api/parts/{part_number}/operations`
- `POST /api/parts/{part_number}/operations`
- `PUT /api/operations/{id}`
- `DELETE /api/operations/{id}`

**Frontend implementace:**

```vue
<template>
  <div class="operations-module">
    <!-- Header -->
    <div class="module-header">
      <h3>Operace</h3>
      <button class="btn btn-primary btn-sm" @click="openCreateForm">
        + Přidat operaci
      </button>
    </div>

    <!-- Tabulka operací -->
    <DataTable
      :data="operations"
      :columns="columns"
      :loading="loading"
      empty-message="Žádné operace. Přidejte první operaci."
    >
      <template #cell-actions="{ row }">
        <button @click="editOperation(row)" title="Upravit">✏️</button>
        <button @click="confirmDelete(row)" title="Smazat">🗑️</button>
      </template>
    </DataTable>

    <!-- Edit/Create Modal -->
    <Modal v-model="showForm" :title="isEditing ? 'Upravit operaci' : 'Nová operace'">
      <form @submit.prevent="saveOperation">
        <div class="form-group">
          <label>Pořadí (seq)</label>
          <input v-model.number="form.seq" type="number" min="1" required />
        </div>

        <div class="form-group">
          <label>Název</label>
          <input v-model="form.name" type="text" required />
        </div>

        <div class="form-group">
          <label>Pracoviště</label>
          <select v-model="form.work_center_id">
            <option :value="null">-- Vyberte --</option>
            <option v-for="wc in workCenters" :key="wc.id" :value="wc.id">
              {{ wc.name }}
            </option>
          </select>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>tp (přípravný čas) [min]</label>
            <input v-model.number="form.setup_time_min" type="number" min="0" step="0.1" />
          </div>
          <div class="form-group">
            <label>tj (kusový čas) [min]</label>
            <input v-model.number="form.operation_time_min" type="number" min="0" step="0.01" />
          </div>
        </div>

        <div class="form-group">
          <label>
            <input type="checkbox" v-model="form.is_coop" />
            Kooperace
          </label>
        </div>

        <template v-if="form.is_coop">
          <div class="form-row">
            <div class="form-group">
              <label>Cena kooperace [Kč]</label>
              <input v-model.number="form.coop_price" type="number" min="0" />
            </div>
            <div class="form-group">
              <label>Min. cena [Kč]</label>
              <input v-model.number="form.coop_min_price" type="number" min="0" />
            </div>
            <div class="form-group">
              <label>Dodací dny</label>
              <input v-model.number="form.coop_days" type="number" min="0" />
            </div>
          </div>
        </template>

        <div class="form-actions">
          <button type="button" class="btn btn-secondary" @click="closeForm">Zrušit</button>
          <button type="submit" class="btn btn-primary" :disabled="saving">
            {{ saving ? 'Ukládám...' : 'Uložit' }}
          </button>
        </div>
      </form>
    </Modal>
  </div>
</template>
```

**Store: `stores/operations.ts`** (pokud neexistuje - vytvořit nebo rozšířit)

### 1.2 PartMaterialModule (4h)

**Backend API (existuje - ADR-024):**
- `GET /api/material-inputs?part_id={id}`
- `POST /api/material-inputs`
- `PUT /api/material-inputs/{id}`
- `DELETE /api/material-inputs/{id}`
- `POST /api/material-inputs/{id}/operations/{op_id}` (link)
- `DELETE /api/material-inputs/{id}/operations/{op_id}` (unlink)

**Klíčové pole MaterialInput:**
```typescript
interface MaterialInput {
  id: number
  part_id: number
  price_category_id: number  // FK - povinné
  material_item_id?: number  // FK - volitelné
  stock_shape: 'CYLINDER' | 'BOX' | 'TUBE' | 'SHEET'
  stock_diameter?: number    // pro CYLINDER, TUBE
  stock_length?: number      // pro všechny
  stock_width?: number       // pro BOX, SHEET
  stock_height?: number      // pro BOX
  stock_wall_thickness?: number  // pro TUBE
  quantity: number           // počet kusů na 1 díl
  linked_operations: Operation[]  // M:N
}
```

**Store: `stores/materials.ts`** - NUTNO IMPLEMENTOVAT

```typescript
export const useMaterialsStore = defineStore('materials', () => {
  const materialInputs = ref<MaterialInput[]>([])
  const categories = ref<MaterialPriceCategory[]>([])
  const loading = ref(false)

  async function fetchMaterialInputs(partId: number) {
    loading.value = true
    try {
      const response = await materialInputsApi.getByPartId(partId)
      materialInputs.value = response.data
    } finally {
      loading.value = false
    }
  }

  async function createMaterialInput(data: MaterialInputCreate) {
    const response = await materialInputsApi.create(data)
    materialInputs.value.push(response.data)
    return response.data
  }

  async function updateMaterialInput(id: number, data: MaterialInputUpdate) {
    const response = await materialInputsApi.update(id, data)
    const index = materialInputs.value.findIndex(m => m.id === id)
    if (index !== -1) materialInputs.value[index] = response.data
    return response.data
  }

  async function deleteMaterialInput(id: number) {
    await materialInputsApi.delete(id)
    materialInputs.value = materialInputs.value.filter(m => m.id !== id)
  }

  async function linkToOperation(materialInputId: number, operationId: number) {
    await materialInputsApi.linkOperation(materialInputId, operationId)
    await fetchMaterialInputs(/* partId */)
  }

  // ... další actions

  return {
    materialInputs,
    categories,
    loading,
    fetchMaterialInputs,
    createMaterialInput,
    updateMaterialInput,
    deleteMaterialInput,
    linkToOperation
  }
})
```

### 1.3 PartPricingModule (2h)

**Backend API (existuje):**
- `GET /api/parts/{part_number}/pricing?batch_size=100`
- `POST /api/parts/{part_number}/batches`

**Implementace:** Zobrazení kalkulace, výběr série, breakdown ceny

### 1.4 Ověřit existující moduly (2h)

Před implementací zjistit skutečný stav:
```bash
# Co existuje?
ls -la frontend/src/views/workspace/modules/
ls -la frontend/src/components/modules/

# Co je v nich?
wc -l frontend/src/views/workspace/modules/*.vue
head -50 frontend/src/views/workspace/modules/PartOperationsModule.vue
```

### 1.5 Integration test (4h)

Kompletní flow test:
1. Vytvořit díl
2. Přidat materiál (CYLINDER, průměr 50, délka 100)
3. Přidat operaci (soustružení, tp=15, tj=2.5)
4. Propojit materiál s operací
5. Zobrazit kalkulaci pro sérii 100ks
6. Ověřit že cena odpovídá vzorci

### Tasklist Milestone 1

| # | Task | Čas | Priorita |
|---|------|-----|----------|
| 1.1 | Audit: zjistit co existuje | 1h | FIRST |
| 1.2 | PartOperationsModule - CRUD | 4h | HIGH |
| 1.3 | materials.ts store | 1h | HIGH |
| 1.4 | PartMaterialModule - CRUD | 4h | HIGH |
| 1.5 | PartPricingModule - display | 2h | HIGH |
| 1.6 | Integration test | 4h | HIGH |

---

## MILESTONE 2: SUPPORTING FEATURES 📦

**Status:** Completeness
**Effort:** 12 hodin
**Výstup:** WorkCenters, Admin panel, Settings fungují

### 2.1 WorkCenters (4h)

**Aktuální stav:** Views existují ale jsou PLACEHOLDER

**Potřeba:**
- WorkCentersListView - tabulka s pracoviśti
- WorkCenterEditView - formulář pro edit/create

**Backend API (existuje):**
- `GET /api/work-centers`
- `POST /api/work-centers`
- `PUT /api/work-centers/{id}`
- `DELETE /api/work-centers/{id}`

### 2.2 Admin MasterData (6h)

**Aktuální stav:** 4 tabs, všechny "TODO"

**Potřeba implementovat:**

| Tab | Entita | Backend | Frontend |
|-----|--------|---------|----------|
| Normy materiálů | MaterialNorm | ✅ | ❌ |
| Skupiny materiálů | MaterialGroup | ✅ | ❌ |
| Cenové kategorie | MaterialPriceCategory | ✅ | ❌ |
| Pracoviště | WorkCenter | ✅ | ❌ (redirect?) |

**Pro každý tab:**
- DataTable s existujícími záznamy
- Tlačítko "+ Přidat"
- Modal s formulářem
- Edit/Delete inline actions

### 2.3 Settings (2h)

**Aktuální stav:** Placeholder

**Potřeba:**
- Změna hesla
- Preference (dark mode, jazyk)
- Uložení do localStorage/API

### Tasklist Milestone 2

| # | Task | Čas |
|---|------|-----|
| 2.1 | WorkCentersListView - DataTable | 2h |
| 2.2 | WorkCenterEditView - Form | 2h |
| 2.3 | MasterData Tab 1-2 (Normy, Skupiny) | 3h |
| 2.4 | MasterData Tab 3-4 (Kategorie, Pracoviště) | 3h |
| 2.5 | SettingsView - Preferences | 2h |

---

## MILESTONE 3: QUALITY & DEPLOY 🚀

**Status:** Production readiness
**Effort:** 16 hodin
**Výstup:** E2E testy, backend cleanup, production deployment

### 3.1 Backend Cleanup (4h)

**Zdroj:** BACKEND-CLEANUP-GUIDE.md

| Task | Soubor | Čas |
|------|--------|-----|
| Nahradit 10x print() → logger.debug() | `material_parser.py` | 30m |
| Odstranit unused imports | Various | 15m |
| Extract copy_material_geometry → service | `parts_router.py` | 2h |
| Update dokumentace | CLAUDE.md, CHANGELOG | 1h |

**Odloženo na v2.0:**
- Float → Decimal migration
- SQLite FK CASCADE fix
- Repository pattern

### 3.2 E2E Tests (6h)

**Framework:** Playwright

**Scénáře:**

```typescript
// tests/e2e/core-flow.spec.ts
test.describe('Core Flow', () => {
  test('Login → Create Part → Add Material → Add Operation → View Pricing', async ({ page }) => {
    // 1. Login
    await page.goto('/login')
    await page.fill('[data-testid="username"]', 'demo')
    await page.fill('[data-testid="password"]', 'demo123')
    await page.click('[data-testid="login-button"]')
    await expect(page).toHaveURL('/')

    // 2. Navigate to parts
    await page.click('text=Díly')
    await expect(page).toHaveURL('/parts')

    // 3. Create part
    await page.click('[data-testid="create-part-button"]')
    await page.fill('[data-testid="part-name-input"]', 'E2E Test Part')
    await page.click('[data-testid="save-button"]')
    await expect(page).toHaveURL(/\/parts\/\d+/)

    // 4. Add material (Tab 2)
    await page.click('text=Materiál')
    await page.click('text=+ Přidat materiál')
    // ... fill form

    // 5. Add operation (Tab 3)
    await page.click('text=Operace')
    await page.click('text=+ Přidat operaci')
    // ... fill form

    // 6. View pricing (Tab 4)
    await page.click('text=Kalkulace')
    await expect(page.locator('[data-testid="total-price"]')).toBeVisible()
  })
})
```

### 3.3 FastAPI Integration (4h)

**Cíl:** Vue SPA servována z FastAPI

```python
# app/main.py
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Mount Vue dist
app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")

# SPA catch-all (MUST be last!)
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # API routes handled by routers
    if full_path.startswith("api/"):
        raise HTTPException(404)
    # Serve Vue index.html for all other routes
    return FileResponse("frontend/dist/index.html")
```

### 3.4 Deployment (2h)

**Checklist:**
- [ ] Environment variables (VITE_API_URL)
- [ ] Production build (`npm run build`)
- [ ] Test build locally
- [ ] Deploy to staging
- [ ] Smoke test na staging
- [ ] Deploy to production

### Tasklist Milestone 3

| # | Task | Čas |
|---|------|-----|
| 3.1 | Backend: print → logger | 30m |
| 3.2 | Backend: extract services (optional) | 2h |
| 3.3 | E2E: Setup Playwright | 1h |
| 3.4 | E2E: Core flow test | 3h |
| 3.5 | E2E: Edge cases | 2h |
| 3.6 | FastAPI: serve Vue | 2h |
| 3.7 | FastAPI: environment config | 1h |
| 3.8 | Deploy: staging test | 1h |
| 3.9 | Deploy: production | 1h |
| 3.10 | Docs: update STATUS, CHANGELOG | 1h |

---

## TIMELINE VISUALIZATION

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          WEEK 1                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  DAY 1 (4h)                                                             │
│  ├── M0: App.vue layout fix                                            │
│  ├── M0: Remove duplicate headers                                       │
│  └── M0: Test all navigation                                           │
│                                                                         │
│  DAY 2 (4h)                                                             │
│  ├── M1: Audit existing modules                                        │
│  └── M1: PartOperationsModule                                          │
│                                                                         │
│  DAY 3 (4h)                                                             │
│  ├── M1: materials.ts store                                            │
│  └── M1: PartMaterialModule                                            │
│                                                                         │
│  DAY 4 (4h)                                                             │
│  ├── M1: PartPricingModule                                             │
│  └── M1: Integration testing                                           │
│                                                                         │
│  DAY 5 (4h)                                                             │
│  ├── M1: Bug fixes                                                     │
│  └── M1: Polish                                                         │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                          WEEK 2                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  DAY 6 (4h)                                                             │
│  ├── M2: WorkCentersListView                                           │
│  └── M2: WorkCenterEditView                                            │
│                                                                         │
│  DAY 7 (4h)                                                             │
│  ├── M2: MasterData tabs 1-2                                           │
│  └── M2: MasterData tabs 3-4                                           │
│                                                                         │
│  DAY 8 (4h)                                                             │
│  ├── M2: SettingsView                                                  │
│  ├── M3: Backend cleanup (prints)                                       │
│  └── M3: Backend cleanup (optional services)                            │
│                                                                         │
│  DAY 9 (4h)                                                             │
│  ├── M3: E2E setup + core flow test                                    │
│  └── M3: E2E edge cases                                                │
│                                                                         │
│  DAY 10 (4h)                                                            │
│  ├── M3: FastAPI integration                                           │
│  ├── M3: Staging deploy + test                                         │
│  └── M3: Production deploy                                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

TOTAL: 10 days × 4h = 40h (2 weeks part-time)
       or 5 days × 8h = 40h (1 week full-time)
```

---

## VERIFICATION PROTOCOL

### Po každém Milestone

```bash
# M0: Navigation
npm run dev
# Proklikat: / → /parts → /parts/:id → /work-centers → /settings → /
# Všude header? ✅

# M1: Core Flow
# Vytvořit díl → přidat materiál → přidat operaci → vidět cenu
# Funguje? ✅

# M2: Supporting
# WorkCenters CRUD funguje? ✅
# Admin tabs mají data? ✅
# Settings se ukládá? ✅

# M3: Quality
pytest tests/         # Backend testy
npm run test          # Frontend unit testy
npx playwright test   # E2E testy
# Vše passing? ✅
```

### Final BETA Checklist

```markdown
## BETA RELEASE CHECKLIST

### Funkčnost
- [ ] Login/Logout funguje
- [ ] Navigace funguje z jakékoliv stránky
- [ ] Parts CRUD kompletní
- [ ] Operations CRUD kompletní
- [ ] Materials CRUD kompletní
- [ ] Pricing zobrazuje správné hodnoty
- [ ] WorkCenters CRUD funguje
- [ ] Admin panel má všechny tabs

### Kvalita
- [ ] 286+ unit testů passing
- [ ] E2E testy passing
- [ ] Bundle < 100KB gzipped
- [ ] Lighthouse > 90
- [ ] Zero console errors
- [ ] Zero TypeScript errors

### Dokumentace
- [ ] STATUS.md aktuální
- [ ] CHANGELOG.md aktuální
- [ ] README aktuální (jak spustit)

### Deployment
- [ ] Vue servováno z FastAPI
- [ ] Environment config funguje
- [ ] Staging otestován
- [ ] Production nasazeno
```

---

## QUICK REFERENCE: Co udělat DNES

**Pokud máš 4 hodiny:**
```
→ MILESTONE 0 kompletně
→ Navigace bude fungovat
→ Můžeš pokračovat kamkoliv
```

**Pokud máš 8 hodin:**
```
→ MILESTONE 0 (4h)
→ MILESTONE 1 audit + Operations (4h)
```

**Pokud máš celý den:**
```
→ MILESTONE 0 + polovina MILESTONE 1
→ Díl → Operace flow bude fungovat
```

---

## DEPENDENCIES DIAGRAM

```
                    MILESTONE 0: Navigation
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
      M1: Parts      M2: WorkCenters  M2: Admin
      M1: Materials  M2: Settings
      M1: Operations
      M1: Pricing
           │
           └───────────────┬───────────────┘
                           │
                           ▼
                    MILESTONE 3: Quality
                           │
                           ▼
                      🎉 BETA RELEASE
```

---

## RISK MITIGATION

| Riziko | Pravděpodobnost | Dopad | Mitigace |
|--------|-----------------|-------|----------|
| API nekompatibilita | Nízká | Vysoký | Backend otestován, 286 testů |
| CSS konflikty | Střední | Střední | Design system existuje |
| Store complexity | Střední | Střední | Kopírovat patterns z parts store |
| Časový skluz | Vysoká | Střední | Buffer 20% v každém milestone |
| Neočekávané bugy | Střední | Střední | E2E testy odhalí před deployem |

---

## SUCCESS METRICS

| Metrika | Before | After | Target |
|---------|--------|-------|--------|
| Navigation works | ❌ 10% | ✅ 100% | 100% |
| Core flow complete | ❌ 15% | ✅ 100% | 100% |
| Supporting features | ❌ 0% | ✅ 100% | 100% |
| E2E tests | 0 | 10+ | 10+ |
| Bundle size | 60KB | <100KB | <100KB |
| Lighthouse | ? | >90 | >90 |

---

## POZNÁMKY

### Co NEDĚLÁME v BETA

- Float → Decimal migration (v2.0)
- SQLite FK CASCADE fix (v2.0)
- Repository pattern refactor (v3.0)
- Mobile responsive (v2.0)
- Multi-language (v3.0)
- Advanced permissions (v2.0)

### Co DĚLÁME v BETA

- ✅ Navigace funguje
- ✅ Core business flow (díl → cena)
- ✅ Admin může spravovat číselníky
- ✅ E2E testy na kritické paths
- ✅ Production deployment

---

**Dokument vytvořen:** 2026-01-29
**Autor:** Roy (IT Crowd Mode)
**Status:** SINGLE SOURCE OF TRUTH

---

> *"Have you tried turning it off and on again?"*
> *→ Clean slate. Fix navigation. Implement flow. Deploy. BETA!*
