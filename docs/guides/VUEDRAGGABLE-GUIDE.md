# VueDraggable — Gestima Pattern

**Package:** `vuedraggable@next` (Vue 3 + Sortable.js)
**Real implementation:** `frontend/src/components/modules/operations/OperationsDetailPanel.vue`

---

## Pattern

```vue
<draggable
  v-model="localItems"
  @end="handleDragEnd"
  item-key="id"
  :animation="300"
  direction="vertical"
  ghost-class="ghost"
  chosen-class="chosen"
  drag-class="drag"
>
  <template #item="{ element: item }">
    <YourComponent :item="item" />
  </template>
</draggable>
```

```typescript
const localItems = ref<Item[]>([])

// ALWAYS local copy + watch — VueDraggable mutates the array
watch(() => props.items, (v) => { localItems.value = [...v] }, { immediate: true })

async function handleDragEnd() {
  localItems.value.forEach((item, i) => { item.seq = (i + 1) * 10 })
  await store.updateOrder(localItems.value)
}
```

---

## CSS — kritické

```css
/* Ghost = neviditelný placeholder, vytváří vizuální mezeru */
.ghost  { opacity: 0; min-height: 100px; }

/* Drag = tažený prvek — musí být viditelný */
.drag   { opacity: 1 !important; cursor: grabbing !important; }

/* Chosen = při chycení */
.chosen { cursor: grabbing !important; }
```

**Klíčové:** `.ghost` musí být `opacity: 0` (neviditelný), jinak uživatel vidí duplikát. `min-height` zachová vizuální mezeru.

---

## Gotchas

- `v-model` musí být lokální kopie (`ref([...])`), ne přímý store state — Sortable.js mutuje pole
- `item-key` je povinný (unikátní ID každého prvku)
- Sekvence 10-20-30 (násobky 10) pro snadné vkládání bez renumberingu všeho
- `@end` event — ne `@change` — pro ukládání po dokončení drag
- Nepřidávej `swap-threshold`, `invert-swap` — základní config stačí
