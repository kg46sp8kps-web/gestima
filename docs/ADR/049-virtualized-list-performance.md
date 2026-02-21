# ADR-049: Virtualized List Performance Pattern

**Status:** ACCEPTED — MANDATORY pro všechny list moduly
**Datum:** 2026-02-20
**Kontext:** PartListPanel vs MaterialItemsListPanel performance analysis

---

## Problém

Moduly s DataTable komponentou (MaterialItemsListPanel, FileListPanel) měly:
- **Otevírání:** 0.5–1s čekání (backend vrací vše bez limitu + eager JOIN)
- **Zavírání:** 5–10s (Vue unmountuje 4000 DOM nodů synchronně)
- **Re-otevření:** 0.5–1s (žádný cache, vždy nový fetch)

PartListPanel (18 000 položek) se otevíral **okamžitě**. Rozdíl byl v architektuře.

---

## Root Cause Analysis

### ❌ Špatný pattern (DataTable)

```
Backend: SELECT * FROM items (bez LIMIT) + selectinload(group, price_category)
→ 4000 rows × 3 eager-loaded objekty = velký JSON payload
→ Frontend: DataTable renderuje 4000 <tr> jako Vue komponenty
→ Unmount: Vue teardown 4000 DOM nodů = 5–10s blokování UI
→ Re-open: žádný cache, vždy nový API call
```

### ✅ Správný pattern (Virtualizer)

```
Backend: SELECT * FROM items LIMIT 200 OFFSET 0 (first load fast)
→ Frontend: TanStack Virtual = jen ~30 DOM nodů v každý moment
→ Unmount: 30 DOM nodů = okamžité
→ Re-open: data v store (cache), žádný fetch = <10ms
```

---

## Mandatory Pattern pro všechny list moduly

### 1. Backend — vždy skip/limit, nikdy selectinload pro list endpoint

```python
# ✅ SPRÁVNĚ
@router.get("/items", response_model=XxxListResponse)
async def get_items(skip: int = 0, limit: int = 200, db=...):
    base_query = select(Item).where(Item.deleted_at.is_(None))
    count = await db.scalar(select(func.count()).select_from(base_query.subquery()))
    items = await db.scalars(base_query.order_by(Item.code).offset(skip).limit(limit))
    return XxxListResponse(items=items.all(), total=count)

# ❌ ZAKÁZÁNO — bez limitu + eager load
@router.get("/items")
async def get_items(db=...):
    result = await db.execute(
        select(Item).options(selectinload(Item.group))  # ← ZAKÁZÁNO pro list
    )
    return result.scalars().all()  # ← ZAKÁZÁNO bez limitu
```

Response model vždy `{ items: [...], total: N }` — nikdy plain array.

### 2. Store — identický pattern jako parts.ts

```typescript
// ✅ POVINNÉ FLAGY (stejné jako parts store)
const items = ref<Xxx[]>([])
const itemsTotal = ref(0)
const itemsLoaded = ref(false)
const loadingItems = ref(false)
const loadingMoreItems = ref(false)

// Identické computed jako parts store
const initialLoading = computed(() => loadingItems.value && items.value.length === 0)
const hasItems = computed(() => items.value.length > 0)
const hasMore = computed(() => items.value.length < itemsTotal.value)

// First load — 200 rows
async function fetchItems(): Promise<void> {
  if (itemsLoaded.value) return  // ← cache guard, re-open je okamžité
  loadingItems.value = true
  try {
    const response = await api.getItems({ skip: 0, limit: 200 })
    items.value = response.items
    itemsTotal.value = response.total
    itemsLoaded.value = true
  } finally {
    loadingItems.value = false
  }
}

// Batch 50 — na scroll
async function fetchMoreItems(): Promise<void> {
  if (loadingMoreItems.value || !hasMore.value) return
  loadingMoreItems.value = true
  try {
    const response = await api.getItems({ skip: items.value.length, limit: 50 })
    items.value.push(...response.items)
  } finally {
    loadingMoreItems.value = false
  }
}

// Reset při logout
itemsLoaded.value = false
```

### 3. ListPanel — TanStack Virtual, NIKDY DataTable pro velké listy

```vue
<script setup>
import { useVirtualizer } from '@tanstack/vue-virtual'

const ROW_HEIGHT = 30  // --density-row-height
const scrollContainerRef = ref<HTMLElement | null>(null)

const virtualizer = useVirtualizer({
  get count() { return filteredItems.value.length },
  getScrollElement: () => scrollContainerRef.value,
  estimateSize: () => ROW_HEIGHT,
  overscan: 10
})

const virtualRows = computed(() => virtualizer.value.getVirtualItems())
const totalSize = computed(() => virtualizer.value.getTotalSize())

// Infinite scroll trigger
function onScroll() {
  if (!scrollContainerRef.value || !store.hasMore || store.loadingMore) return
  const el = scrollContainerRef.value
  if (el.scrollHeight - el.scrollTop - el.clientHeight < 300) {
    store.fetchMore()
  }
}

// ✅ POVINNÉ — cache guard
onMounted(async () => {
  if (!store.hasItems) await store.fetchItems()
})

// ✅ POVINNÉ — reset filtrů při zavření
onUnmounted(() => {
  searchQuery.value = ''
  // ... reset všech lokálních filtrů
})

// ✅ Spinner jen na první load
const isLoading = computed(() => store.initialLoading)
</script>

<template>
  <!-- Loading POUZE na první load -->
  <div v-if="isLoading" class="loading-container"><Spinner /></div>
  <div v-else-if="filteredItems.length === 0" class="empty-container">Žádné záznamy</div>

  <!-- Virtualizer — NIKDY v-for přes 100+ položek bez virtualizace -->
  <div v-else ref="scrollContainerRef" class="table-container" @scroll.passive="onScroll">
    <div class="vt-header"><!-- sticky header --></div>
    <div class="vt-body" :style="{ height: `${totalSize}px` }">
      <div
        v-for="vRow in virtualRows"
        :key="items[vRow.index]?.id"
        class="vt-row"
        :style="{ height: `${vRow.size}px`, transform: `translateY(${vRow.start}px)` }"
        @click="handleRowClick(items[vRow.index])"
      >
        <!-- cells -->
      </div>
    </div>
  </div>
</template>
```

### 4. Prefetch — po loginu, fire-and-forget

Všechny heavy datasety se načítají na pozadí ihned po loginu:

```typescript
// composables/usePrefetch.ts
async function prefetchAll() {
  await Promise.allSettled([
    store.hasItems ? Promise.resolve() : store.fetchItems(),
    // ... všechny další stores
  ])
}

// LoginView.vue — po auth.login()
void prefetchAll()  // fire-and-forget, neblokuje redirect
```

---

## Referenční implementace

| Soubor | Pattern |
|--------|---------|
| `frontend/src/components/modules/parts/PartListPanel.vue` | ✅ Vzor pro virtualizer + infinite scroll |
| `frontend/src/stores/parts.ts` | ✅ Vzor pro store flagy |
| `frontend/src/components/modules/materials/MaterialItemsListPanel.vue` | ✅ Druhá referenční implementace (2026-02-20) |
| `frontend/src/stores/materials.ts` (`fetchMaterialItems`) | ✅ Vzor pro materials |
| `app/routers/materials_router.py` (`GET /items`) | ✅ Vzor pro backend endpoint |

---

## Pravidla (BLOCKING)

| # | Pravidlo | Porušení |
|---|----------|---------|
| B-1 | `DataTable` **ZAKÁZÁNA** pro listy s >100 potenciálními řádky | Slow unmount |
| B-2 | Backend list endpoint **MUSÍ** mít `skip/limit` default 200 | Timeout |
| B-3 | Backend list endpoint **NESMÍ** mít `selectinload` na relations | N+1 + velký payload |
| B-4 | Backend list endpoint **MUSÍ** vracet `{ items, total }` — nikdy plain array | Nelze paginate |
| B-5 | Store **MUSÍ** mít `initialLoading`, `hasItems`, `hasMore` computed flagy | Blikání spinneru |
| B-6 | Store **MUSÍ** mít `loaded` guard v `fetchItems()` — `if (loaded) return` | Re-fetch na re-open |
| B-7 | `onMounted` **MUSÍ** kontrolovat `if (!store.hasItems)` před fetchem | Zbytečný fetch |
| B-8 | `onUnmounted` **MUSÍ** resetovat lokální filtry | Filtry přetékají mezi sessions |
| B-9 | Spinner (`v-if="initialLoading"`) — nikdy `v-if="loading"` | Bliká při re-fetch |

---

## Performance cíle

| Akce | Cíl | Jak |
|------|-----|-----|
| První otevření | <300ms | Prefetch po loginu |
| Re-otevření | <10ms | Store cache (`loaded` guard) |
| Scroll next batch | <100ms | Batch 50, append |
| Zavření okna | <16ms | Virtualizer = 30 DOM nodů |
| Otevření po prefetch | <1ms | Data jsou v store |
