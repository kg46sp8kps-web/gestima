# Vue SPA - Generic-First Architecture (ADR-025)

**Datum:** 2026-01-29
**Status:** 📋 **PROPOSED** - Návrh pro implementaci
**Context:** MaterialInput refactor (ADR-024 backend) + Vue SPA migration
**Princip:** NO FAT COMPONENTS (CLAUDE.md Rule #14, L-036)

---

## 🎯 Problém

Při návrhu Vue SPA frontendu pro MaterialInput (ADR-024) jsme původně navrhli:

```
❌ BAD: PartMaterialModule.vue (1196 LOC)
- Fat, context-specific module
- Tightly coupled to Part
- Cannot reuse for Inventory, MaterialItems, Stock management
- Violates LEAN principle (Part model is lean, why UI fat?)
```

**Zjištění:** "Pokud komponenta nemůže být použita v Inventory search (v4.0), je příliš specifická!"

---

## ✅ Řešení: Generic-First Architecture

### Architektura

```
/components/shared/           (Generic building blocks)
├── SearchBar.vue             Universal search input
├── FilterPanel.vue           Generic filters (by category, status, etc.)
└── CategorySelector.vue      Type selector (parts/materials/products)

/components/materials/        (Material-specific reusable components)
├── MaterialParserInput.vue   AI parser "D20 C45 100mm" (~150 LOC)
├── MaterialDimensionFields.vue  Dynamic dims by shape (~200 LOC)
├── MaterialCategorySelect.vue   Filtered categories by shape (~100 LOC)
├── MaterialCard.vue          Display card (grid/sidebar/compact) (~150 LOC)
└── MaterialManager.vue       Generic material CRUD (~300 LOC)
                              → Accepts filter: { part_id?, operation_id?, in_stock? }
                              → Reusable everywhere!

/components/shared/           (Generic display components)
├── ItemCard.vue              Generic card (parts/materials/products)
├── ItemGrid.vue              Generic grid layout
└── ItemList.vue              Generic list layout

/configs/                     (Type-specific configs, NOT components!)
├── partConfig.ts             { fields, icon, route, displayName, ... }
├── materialConfig.ts         { fields, icon, route, displayName, ... }
└── productConfig.ts          { fields, icon, route, displayName, ... }

/views/workspace/modules/     (Thin context wrappers ~50 LOC each!)
├── PartMaterialPanel.vue     <MaterialManager :filter="{ part_id }" />
├── OperationMaterialPanel.vue  <MaterialManager :filter="{ operation_id }" />
└── StockMaterialPanel.vue    <MaterialManager :filter="{ in_stock: true }" />
```

---

## 🔧 Komponenty - Detailní Specifikace

### 1. MaterialParserInput.vue (~150 LOC)

**Props:**
```typescript
interface Props {
  modelValue: string
  placeholder?: string
  debounce?: number  // Default: 400ms
}
```

**Emits:**
```typescript
{
  'update:modelValue': [value: string]
  'parsed': [result: MaterialParseResult]
  'apply': [result: MaterialParseResult]
}
```

**Features:**
- AI parsing: "D20 C45 100mm" → { shape, diameter, length, material }
- Debounced API call (400ms)
- Confidence badges (✅ HIGH / ⚠️ MEDIUM / ❌ LOW)
- Purple gradient styling (replicate from Alpine.js)
- "Použít" / "Zrušit" buttons
- Loading state

**Použití:**
```vue
<MaterialParserInput
  v-model="quickInput"
  @apply="applyParsedValues"
/>
```

**Reusable pro:**
- Part material form
- MaterialItems admin
- Inventory quick add
- Stock management

---

### 2. MaterialDimensionFields.vue (~200 LOC)

**Props:**
```typescript
interface Props {
  stockShape: StockShape
  modelValue: {
    stock_diameter?: number
    stock_length?: number
    stock_width?: number
    stock_height?: number
    stock_wall_thickness?: number
  }
  readonly?: boolean
}
```

**Features:**
- **Dynamic fields** based on stock_shape:
  - `round_bar`: ⌀ + délka
  - `tube`: ⌀ vnější + tl. stěny + délka
  - `square_bar`: strana + délka
  - `flat_bar`, `plate`: délka + šířka + výška
  - `hexagonal_bar`, `casting`, `forging`: ⌀ + délka
- **Fresh input pattern** (useFreshInput composable)
- Auto-focus first field
- Validation (min 0, max reasonable values)
- Unit labels (mm)

**Použití:**
```vue
<MaterialDimensionFields
  :stock-shape="form.stock_shape"
  v-model="form.dimensions"
/>
```

---

### 3. MaterialCategorySelect.vue (~100 LOC)

**Props:**
```typescript
interface Props {
  stockShape: StockShape | null
  modelValue: number | null
  categories: MaterialPriceCategory[]
}
```

**Features:**
- **Filtered categories** by stock_shape
- Mapping logic (replicated from Alpine.js):
  - `round_bar` → KRUHOVA, BRONZ
  - `square_bar` → CTVEREC
  - `plate` → DESKY
  - `tube` → TRUBKA
  - etc.
- Display: "S235 - Konstrukční ocel"
- Empty state handling

**Použití:**
```vue
<MaterialCategorySelect
  :stock-shape="form.stock_shape"
  v-model="form.price_category_id"
  :categories="allCategories"
/>
```

---

### 4. MaterialCard.vue (~150 LOC)

**Props:**
```typescript
interface Props {
  material: MaterialInputWithOperations
  mode?: 'grid' | 'sidebar' | 'compact' | 'inline'
  readonly?: boolean
  showActions?: boolean
  showOperations?: boolean
}
```

**Modes:**

1. **Grid** (default - full card):
   ```
   ┌─────────────────────────────┐
   │ Kulatina ⌀20 × 100 mm       │
   │ C45, 1 ks                    │
   │ 🔗 Operace: OP1, OP2        │
   │ [Edit] [Delete]             │
   └─────────────────────────────┘
   ```

2. **Sidebar** (compact vertical):
   ```
   ┌──────────────┐
   │ 🔩 Kulatina  │
   │    ⌀20×100   │
   │    C45       │
   └──────────────┘
   ```

3. **Compact** (single line badge):
   ```
   [🔩 Kulatina ⌀20×100]
   ```

4. **Inline** (text only):
   ```
   Materiál: Kulatina ⌀20 × 100 mm (C45)
   ```

**Použití:**
```vue
<MaterialCard
  :material="item"
  mode="grid"
  @edit="handleEdit"
  @delete="handleDelete"
/>
```

---

### 5. MaterialManager.vue (~300 LOC)

**Props:**
```typescript
interface Props {
  filter?: {
    part_id?: number
    operation_id?: number
    in_stock?: boolean
    // Future: product_id, order_id, ...
  }
  mode?: 'full' | 'compact'
  readonly?: boolean
}
```

**Features:**
- Load materials (filtered by props)
- Add material form (with parser)
- Materials list (using MaterialCard)
- Edit/Delete operations
- Stock cost display (sum)
- Operation linking (if part context)
- Empty state

**Structure:**
```vue
<template>
  <div class="material-manager">
    <!-- Parser section (if not readonly) -->
    <MaterialParserInput
      v-if="!readonly"
      @apply="handleParsedMaterial"
    />

    <!-- Add material form -->
    <div v-if="showAddForm" class="add-form">
      <MaterialCategorySelect />
      <MaterialDimensionFields />
      <button @click="createMaterial">Přidat</button>
    </div>

    <!-- Materials list -->
    <div class="materials-list">
      <MaterialCard
        v-for="mat in materials"
        :material="mat"
        @edit="editMaterial"
        @delete="deleteMaterial"
      />
    </div>

    <!-- Stock cost (if part context) -->
    <div v-if="filter.part_id" class="stock-cost">
      Materiál celkem: {{ totalCost }} Kč
    </div>
  </div>
</template>
```

**Použití:**
```vue
<!-- Part context -->
<MaterialManager :filter="{ part_id: 123 }" />

<!-- Operation context -->
<MaterialManager :filter="{ operation_id: 456 }" />

<!-- Inventory context (v4.0) -->
<MaterialManager :filter="{ in_stock: true }" />
```

---

### 6. Thin Context Wrappers (~50 LOC each)

#### PartMaterialPanel.vue
```vue
<script setup lang="ts">
import MaterialManager from '@/components/materials/MaterialManager.vue'
import { computed } from 'vue'

interface Props {
  partId: number | null
  partNumber: string
  inline?: boolean
}

const props = defineProps<Props>()

const filter = computed(() => ({
  part_id: props.partId || undefined
}))
</script>

<template>
  <div class="part-material-panel">
    <MaterialManager
      v-if="partId"
      :filter="filter"
      mode="full"
    />
    <div v-else class="empty">
      Vyberte díl pro správu materiálů
    </div>
  </div>
</template>
```

#### OperationMaterialPanel.vue
```vue
<script setup lang="ts">
import MaterialManager from '@/components/materials/MaterialManager.vue'

interface Props {
  operationId: number | null
}

const props = defineProps<Props>()
const filter = computed(() => ({ operation_id: props.operationId }))
</script>

<template>
  <MaterialManager
    v-if="operationId"
    :filter="filter"
    mode="compact"
    readonly
  />
</template>
```

---

## 🎨 Generic Display Components

### ItemCard.vue (Universal)

**Props:**
```typescript
interface Props {
  item: any  // Part | MaterialInput | Product | InventoryItem
  config: ItemConfig  // partConfig | materialConfig | productConfig
  mode?: 'grid' | 'list' | 'compact'
}

interface ItemConfig {
  type: string  // 'part' | 'material' | 'product'
  icon: string  // '📦' | '🔩' | '🏭'
  displayName: (item: any) => string
  summary: (item: any) => string
  route: (item: any) => RouteLocationRaw
  actions?: Array<{ label: string, icon: string, handler: (item: any) => void }>
}
```

**Použití:**
```vue
<!-- Parts -->
<ItemCard :item="part" :config="partConfig" />

<!-- Materials -->
<ItemCard :item="material" :config="materialConfig" />

<!-- Products (v3.0) -->
<ItemCard :item="product" :config="productConfig" />
```

---

## 📋 Type Configs (NOT Components!)

### partConfig.ts
```typescript
export const partConfig: ItemConfig = {
  type: 'part',
  icon: '📦',
  displayName: (part: Part) => part.name,
  summary: (part: Part) => `${part.part_number} • ${part.notes || 'Bez poznámek'}`,
  route: (part: Part) => ({ name: 'part-detail', params: { partNumber: part.part_number } }),
  actions: [
    { label: 'Edit', icon: '✏️', handler: (part) => router.push(...) },
    { label: 'Duplicate', icon: '📋', handler: (part) => duplicatePart(part) }
  ]
}
```

### materialConfig.ts
```typescript
export const materialConfig: ItemConfig = {
  type: 'material',
  icon: '🔩',
  displayName: (mat: MaterialInput) => getMaterialSummary(mat),  // "Kulatina ⌀20×100"
  summary: (mat: MaterialInput) => `${mat.quantity} ks • Seq ${mat.seq}`,
  route: (mat: MaterialInput) => ({ name: 'material-detail', params: { id: mat.id } }),
  actions: [
    { label: 'Edit', icon: '✏️', handler: (mat) => editMaterial(mat) },
    { label: 'Delete', icon: '🗑️', handler: (mat) => deleteMaterial(mat) }
  ]
}
```

---

## 🔮 Budoucí Použití (Inventory v4.0)

### Inventory View (Unified Search)
```vue
<script setup lang="ts">
import SearchBar from '@/components/shared/SearchBar.vue'
import FilterPanel from '@/components/shared/FilterPanel.vue'
import CategorySelector from '@/components/shared/CategorySelector.vue'
import ItemGrid from '@/components/shared/ItemGrid.vue'
import { partConfig, materialConfig, productConfig } from '@/configs'

const searchQuery = ref('')
const selectedCategory = ref<'parts' | 'materials' | 'products'>('parts')
const searchResults = ref([])

const currentConfig = computed(() => {
  switch (selectedCategory.value) {
    case 'parts': return partConfig
    case 'materials': return materialConfig
    case 'products': return productConfig
  }
})

async function search() {
  // Single unified search API
  const results = await searchInventory(searchQuery.value, selectedCategory.value)
  searchResults.value = results
}
</script>

<template>
  <div class="inventory-view">
    <!-- Universal search -->
    <SearchBar
      v-model="searchQuery"
      placeholder="Hledat díly, materiály, výrobky..."
      @search="search"
    />

    <!-- Generic filters -->
    <FilterPanel>
      <CategorySelector
        v-model="selectedCategory"
        :categories="['parts', 'materials', 'products']"
      />
    </FilterPanel>

    <!-- Generic grid with type-specific config -->
    <ItemGrid
      :items="searchResults"
      :config="currentConfig"
      @select="handleSelect"
    />
  </div>
</template>
```

**Výhoda:** Žádný nový kód! Všechny komponenty reusable, jen nová konfigurace.

---

## 📊 LOC Comparison

### ❌ Fat Approach (původní návrh)
```
PartMaterialModule.vue        1196 LOC  (1000+ non-reusable)
InventoryMaterialPanel.vue     800 LOC  (duplicate logic)
MaterialItemsManager.vue       900 LOC  (duplicate logic)
────────────────────────────────────
TOTAL:                        2896 LOC  (mostly duplicate)
```

### ✅ Generic Approach (tento návrh)
```
MaterialParserInput.vue        150 LOC  (reusable)
MaterialDimensionFields.vue    200 LOC  (reusable)
MaterialCategorySelect.vue     100 LOC  (reusable)
MaterialCard.vue               150 LOC  (reusable)
MaterialManager.vue            300 LOC  (reusable)
────────────────────────────────────
Generic components:            900 LOC

PartMaterialPanel.vue           50 LOC  (thin wrapper)
OperationMaterialPanel.vue      50 LOC  (thin wrapper)
StockMaterialPanel.vue          50 LOC  (thin wrapper)
────────────────────────────────────
Context wrappers:              150 LOC

ItemCard.vue                   150 LOC  (universal)
ItemGrid.vue                   100 LOC  (universal)
ItemList.vue                   100 LOC  (universal)
────────────────────────────────────
Display components:            350 LOC

partConfig.ts                   50 LOC  (config, not code)
materialConfig.ts               50 LOC  (config, not code)
────────────────────────────────────
Configs:                       100 LOC

────────────────────────────────────
TOTAL:                        1500 LOC  (all reusable!)
```

**Savings:**
- **48% less code** (1500 vs 2896 LOC)
- **100% reusable** (vs ~30% reusable)
- **Consistent UX** across all contexts
- **Future-proof** for Inventory v4.0, Tech DB v5.0

---

## 🚀 Implementation Plan

### Phase 1: Generic Material Components (~2-3 days)
1. ✅ MaterialInput types (done)
2. ✅ MaterialInput API client (done)
3. ✅ Materials store extended (done)
4. ✅ useFreshInput composable (done)
5. ⏳ MaterialParserInput.vue
6. ⏳ MaterialDimensionFields.vue
7. ⏳ MaterialCategorySelect.vue
8. ⏳ MaterialCard.vue
9. ⏳ MaterialManager.vue

### Phase 2: Thin Context Wrappers (~1 day)
1. ⏳ PartMaterialPanel.vue
2. ⏳ Integrate into PartDetailView.vue
3. ⏳ Test part material flow

### Phase 3: Generic Display Components (~2 days)
1. ⏳ ItemCard.vue (universal)
2. ⏳ ItemGrid.vue
3. ⏳ ItemList.vue
4. ⏳ partConfig.ts
5. ⏳ materialConfig.ts

### Phase 4: Testing & Documentation (~1 day)
1. ⏳ Unit tests (Vitest)
2. ⏳ Component tests (Vue Test Utils)
3. ⏳ Update CHANGELOG.md
4. ⏳ Update ADR-024 (mark frontend complete)
5. ⏳ Create component docs (Storybook?)

**Total estimate:** 6-7 days

---

## ✅ Benefits

### Technical
- ✅ **DRY principle** - No duplicate code
- ✅ **LEAN architecture** - Thin wrappers, fat reusables
- ✅ **Testable** - Small, focused components
- ✅ **Maintainable** - Fix bug once, works everywhere
- ✅ **Type-safe** - Full TypeScript support

### Business
- ✅ **Faster development** - New contexts = just configs
- ✅ **Consistent UX** - Same look & feel everywhere
- ✅ **Future-proof** - Ready for Inventory v4.0, Tech DB v5.0
- ✅ **Reduced tech debt** - Less code to maintain

### User Experience
- ✅ **Familiar interface** - Learn once, use everywhere
- ✅ **Predictable behavior** - Same interactions across contexts
- ✅ **Faster workflows** - Same patterns for parts/materials/products

---

## 🚨 Anti-Patterns to Avoid

### L-036: Fat context-specific components
❌ **NEVER:**
```vue
<!-- DON'T: 1000-line context-specific monster -->
<PartMaterialModule.vue>  (1196 LOC, non-reusable)
```

✅ **ALWAYS:**
```vue
<!-- DO: Generic manager + thin wrapper -->
<MaterialManager.vue>     (300 LOC, reusable)
<PartMaterialPanel.vue>   (50 LOC, thin wrapper)
```

### Test: "Can it be used in Inventory search?"
- If NO → Too specific, redesign!
- If YES → Good generic design ✅

---

## 📚 Related Documents

- [CLAUDE.md](../CLAUDE.md) - Rule #14: NO FAT COMPONENTS
- [ADR-024: MaterialInput Refactor](ADR/024-material-input-refactor.md) - Backend
- VISION.md (removed, git history) - v4.0 Inventory, v5.0 Tech DB
- [L-036: Fat Components Anti-Pattern](../CLAUDE.md#l-036)

---

## 📝 Notes

**Lesson Learned (2026-01-29):**
> "We almost built a 1000-line PartMaterialModule. Then asked: 'Can we use this for Inventory?' Answer: No. Redesigned to generic-first. Now it works everywhere!"

**Principle:**
> "If a component can't be used in Inventory search (v4.0), it's too specific!"

**Mantra:**
> "Generic building blocks + thin wrappers = LEAN architecture"

---

**Status:** 📋 PROPOSED
**Next:** Implement Phase 1 (generic material components)
**Owner:** Claude + User collaboration
**Last Updated:** 2026-01-29 22:50
