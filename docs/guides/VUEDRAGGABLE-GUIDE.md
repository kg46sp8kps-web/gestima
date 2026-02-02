# VueDraggable Best Practices

**Version:** 1.0
**Last Updated:** 2026-02-01
**Use Case:** Clean drag & drop for Vue 3 lists

---

## 📦 Installation

```bash
npm install vuedraggable@next
```

**Why `@next`?** Vue 3 compatibility (uses Sortable.js under the hood)

---

## ✅ Recommended Configuration

### Template

```vue
<template>
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
      <div class="item-wrapper">
        <YourComponent :item="item" />
      </div>
    </template>
  </draggable>
</template>
```

### Script Setup

```typescript
import draggable from 'vuedraggable'
import { ref, watch, computed } from 'vue'

// Local copy for v-model (VueDraggable mutates this)
const localItems = ref<Item[]>([])

// Sync with store/props
watch(() => props.items, (newItems) => {
  localItems.value = [...newItems]
}, { immediate: true })

// Handle drop
async function handleDragEnd() {
  // Renumber or reorder as needed
  localItems.value.forEach((item, index) => {
    item.order = (index + 1) * 10
  })

  // Save to backend
  await store.updateOrder(localItems.value)
}
```

### CSS - CRITICAL FOR CLEAN UX

```css
/* Ghost = invisible placeholder (creates gap) */
.ghost {
  opacity: 0;              /* INVISIBLE */
  min-height: 100px;       /* Creates visible GAP */
  margin: var(--space-4) 0;
}

/* Chosen = when you grab the item */
.chosen {
  cursor: grabbing !important;
}

/* Drag = the item you're dragging */
.drag {
  opacity: 1 !important;   /* VISIBLE - what you see while dragging */
  cursor: grabbing !important;
}
```

**KEY INSIGHT:**
❌ Don't make `.ghost` visible (creates duplicate visual)
✅ Make `.ghost` invisible but keep `min-height` (creates gap)
✅ Make `.drag` fully visible (what user sees while dragging)

---

## 🚫 What NOT to Do

### ❌ DON'T: Custom HTML5 Drag & Drop

```vue
<!-- AVOID THIS - 100+ LOC of complex event handlers -->
<div
  draggable="true"
  @dragstart="handleDragStart"
  @dragover="handleDragOver"
  @dragend="handleDragEnd"
  @drop="handleDrop"
>
```

**Problems:**
- 100+ LOC of complex logic
- Cross-browser issues
- Ghost image positioning bugs
- Hard to get drop zone right
- Touch support requires more work

### ❌ DON'T: Visible Ghost

```css
/* BAD - creates duplicate visual */
.ghost {
  opacity: 0.5;
  background: blue;
  border: 2px dashed red;
}
```

**Result:** User sees TWO items (dragged item + ghost placeholder) = confusing UX

---

## ✅ Best Practices

### 1. **Keep Ghost Invisible**
```css
.ghost {
  opacity: 0;              /* Invisible */
  min-height: 100px;       /* But creates gap */
}
```

### 2. **Simple Props**
Don't overcomplicate with `swap-threshold`, `invert-swap`, etc.
Basic config works best:
```vue
:animation="300"
direction="vertical"
```

### 3. **Sync Pattern**
Always use local copy + watch for syncing:
```typescript
const localItems = ref([])
watch(storeItems, (newItems) => {
  localItems.value = [...newItems]
}, { immediate: true })
```

### 4. **Renumbering Logic**
Use 10-20-30 sequence for easier insertions:
```typescript
localItems.value.forEach((item, index) => {
  item.seq = (index + 1) * 10
})
```

---

## 🎯 Real World Example

**Location:** `frontend/src/components/modules/operations/OperationsDetailPanel.vue`

**What it does:**
- Drag & drop reordering of operations
- Auto-renumber sequence 10-20-30
- Smooth 300ms animation
- Clean UX: only dragged item visible + gap

**Key takeaways:**
- Started with custom HTML5 D&D (420 LOC, buggy)
- Switched to VueDraggable (373 LOC, perfect UX)
- Saved 47 LOC (-11%)
- Zero bugs, better UX

---

## 📚 References

- **VueDraggable:** https://github.com/SortableJS/vue.draggable.next
- **Sortable.js:** https://sortablejs.github.io/Sortable/
- **Implementation:** `frontend/src/components/modules/operations/OperationsDetailPanel.vue`

---

**Rule:** Always prefer VueDraggable over custom drag & drop. It's battle-tested, accessible, and works perfectly.
