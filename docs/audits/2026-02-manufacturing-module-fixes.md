# Manufacturing Module - Missing Features Checklist

**Zdroj:** PartMainModule.vue
**Cíl:** ManufacturingItemsModule.vue
**Status:** 🔴 Incomplete (7 critical issues)

---

## 🔴 CRITICAL MISSING FEATURES

### 1. **handleSelectPart** (řádek 91) - INCOMPLETE
**Current:**
```typescript
function handleSelectPart(part: Part) {
  selectedPart.value = part
}
```

**Missing:**
- ❌ Window context update (`contextStore.setContext`)
- ❌ Event emission (`emit('select-part', ...)`)

**Fix:**
```typescript
function handleSelectPart(part: Part) {
  selectedPart.value = part

  // Update window context
  if (props.linkingGroup) {
    contextStore.setContext(
      props.linkingGroup,
      part.id,
      part.part_number,
      part.article_number
    )
  }

  // Emit event for parent
  emit('select-part', part.part_number)
}
```

---

### 2. **refreshPart** - NOT IMPLEMENTED ❌
**Location:** After line 155 (after openDrawingWindow)

**Missing:**
- ❌ Ability to reload selected part after changes

**Add:**
```typescript
async function refreshPart() {
  if (!selectedPart.value) return

  // Reload only the selected part from API
  // Don't update store to avoid triggering list re-render and scroll reset
  const updatedPart = await getPart(selectedPart.value.part_number)
  selectedPart.value = updatedPart
}
```

**Required import:**
```typescript
import { getPart } from '@/api/parts'
```

**Template binding:**
```vue
<CustomizableModule
  v-else
  :config="manufacturingItemsDetailConfig"
  :context="widgetContext"
  :orientation="layoutMode"
  @widget-action="handleWidgetAction"
  @refresh="refreshPart"  <!-- ADD THIS -->
/>
```

---

### 3. **watch(props.partNumber)** - NOT IMPLEMENTED ❌
**Location:** After line 62 (after onMounted)

**Missing:**
- ❌ External part selection (when prop changes)
- ❌ Auto-select part on mount if partNumber provided

**Add:**
```typescript
// Watch prop changes (for external part selection)
watch(() => props.partNumber, (newPartNumber) => {
  if (newPartNumber) {
    const part = partsStore.parts.find(p => p.part_number === newPartNumber)
    if (part) {
      handleSelectPart(part)
      listPanelRef.value?.setSelection(part.id)
    }
  }
})

// Also update onMounted to auto-select:
onMounted(async () => {
  const stored = localStorage.getItem('manufacturingItemsPanelSize')
  if (stored) {
    const size = parseInt(stored, 10)
    if (!isNaN(size) && size >= 250 && size <= 1000) {
      panelSize.value = size
    }
  }

  // Load parts
  await partsStore.fetchParts()

  // ADD THIS: Auto-select if partNumber prop provided
  if (props.partNumber) {
    const part = partsStore.parts.find(p => p.part_number === props.partNumber)
    if (part) {
      handleSelectPart(part)
      listPanelRef.value?.setSelection(part.id)
    }
  }
})
```

**Required import:**
```typescript
import { watch } from 'vue'  // Add to existing import
```

---

### 4. **Props Interface** - INCOMPLETE
**Current:**
```typescript
interface Props {
  linkingGroup?: LinkingGroup
}
```

**Missing:**
- ❌ `partNumber?: string` - for external selection

**Fix:**
```typescript
interface Props {
  partNumber?: string
  linkingGroup?: LinkingGroup
}

const props = withDefaults(defineProps<Props>(), {
  partNumber: undefined,  // ADD THIS
  linkingGroup: null
})
```

---

### 5. **Emits Definition** - NOT DEFINED ❌
**Location:** After Props interface (around line 35)

**Missing:**
- ❌ Event emission definition

**Add:**
```typescript
const emit = defineEmits<{
  'select-part': [partNumber: string]
}>()
```

---

### 6. **contextStore Import** - NOT IMPORTED ❌
**Location:** Line 16 (imports section)

**Missing:**
- ❌ Window context store import

**Add:**
```typescript
import { useWindowContextStore } from '@/stores/windowContext'
```

**And in script:**
```typescript
const contextStore = useWindowContextStore()  // After windowsStore
```

---

### 7. **handleWidgetAction** - INCOMPLETE
**Current:** (line 160-191)
```typescript
case 'edit':
  console.log('Edit not implemented yet')
  break
```

**Missing:**
- ❌ Edit modal implementation

**Options:**
- A) Reuse PartInfoEdit widget (editable mode)
- B) Create separate EditManufacturingItemModal
- C) Inline editing in info widget

**Recommended: Inline editing (simplest)**
Update `widgetContext` to enable editing:
```typescript
const widgetContext = computed(() => ({
  'manufacturing-item-info': {
    item: selectedPart.value,
    editable: true  // ADD THIS
  },
  // ...
}))
```

Then in widget handle save action (already done in PartInfoEdit pattern).

---

## 🟢 ALREADY CORRECT

✅ Split-pane layout (lines 235-346)
✅ Panel resize logic (lines 99-128)
✅ localStorage persistence (lines 51-58, 121)
✅ Window actions (lines 131-155)
✅ Layout mode switching (lines 79-88)
✅ Widget action routing (lines 160-191) - partially

---

## 📝 COPY-PASTE FIXES (All in one)

**Step 1:** Add missing imports (line ~16)
```typescript
import { watch } from 'vue'
import { useWindowContextStore } from '@/stores/windowContext'
import { getPart } from '@/api/parts'
```

**Step 2:** Add missing stores (line ~37)
```typescript
const contextStore = useWindowContextStore()
```

**Step 3:** Update Props (line ~28)
```typescript
interface Props {
  partNumber?: string
  linkingGroup?: LinkingGroup
}

const props = withDefaults(defineProps<Props>(), {
  partNumber: undefined,
  linkingGroup: null
})
```

**Step 4:** Add emits (line ~35)
```typescript
const emit = defineEmits<{
  'select-part': [partNumber: string]
}>()
```

**Step 5:** Fix handleSelectPart (line ~91)
```typescript
function handleSelectPart(part: Part) {
  selectedPart.value = part

  // Update window context
  if (props.linkingGroup) {
    contextStore.setContext(
      props.linkingGroup,
      part.id,
      part.part_number,
      part.article_number
    )
  }

  // Emit event
  emit('select-part', part.part_number)
}
```

**Step 6:** Add refreshPart (after line ~155)
```typescript
async function refreshPart() {
  if (!selectedPart.value) return
  const updatedPart = await getPart(selectedPart.value.part_number)
  selectedPart.value = updatedPart
}
```

**Step 7:** Update onMounted (line ~51)
```typescript
onMounted(async () => {
  const stored = localStorage.getItem('manufacturingItemsPanelSize')
  if (stored) {
    const size = parseInt(stored, 10)
    if (!isNaN(size) && size >= 250 && size <= 1000) {
      panelSize.value = size
    }
  }

  await partsStore.fetchParts()

  // Auto-select if partNumber prop provided
  if (props.partNumber) {
    const part = partsStore.parts.find(p => p.part_number === props.partNumber)
    if (part) {
      handleSelectPart(part)
      listPanelRef.value?.setSelection(part.id)
    }
  }
})
```

**Step 8:** Add watcher (after onMounted, line ~63)
```typescript
// Watch prop changes (for external part selection)
watch(() => props.partNumber, (newPartNumber) => {
  if (newPartNumber) {
    const part = partsStore.parts.find(p => p.part_number === newPartNumber)
    if (part) {
      handleSelectPart(part)
      listPanelRef.value?.setSelection(part.id)
    }
  }
})
```

**Step 9:** Add refresh binding in template (line ~227)
```vue
<CustomizableModule
  v-else
  :config="manufacturingItemsDetailConfig"
  :context="widgetContext"
  :orientation="layoutMode"
  @widget-action="handleWidgetAction"
  @refresh="refreshPart"
/>
```

---

## ✅ VERIFICATION CHECKLIST

After applying fixes, verify:

- [ ] Selecting part updates window context (check Window Manager)
- [ ] Selecting part emits event (check parent component)
- [ ] partNumber prop auto-selects part on mount
- [ ] External partNumber change updates selection
- [ ] Refresh action reloads part data
- [ ] All window actions work (Material, Operations, Pricing, Drawing)
- [ ] Panel resize persists in localStorage
- [ ] Layout mode switch works (vertical/horizontal)

---

## 🎨 CSS/LAYOUT ISSUES

**Problem:** "zarovnání je těžké"

**Root cause:** Duplicated CSS from PartMainModule

**Solution:** Extract to shared CSS module

Create `frontend/src/assets/css/modules/_split-pane.css` with:
```css
/* Already exists - reuse it! */
/* Check if ManufacturingItemsModule uses it */
```

**Or use shared component:**
```vue
<SplitPaneLayout
  :left-size="panelSize"
  :orientation="layoutMode"
  @resize="handleResize"
>
  <template #left>
    <PartListPanel ... />
  </template>
  <template #right>
    <CustomizableModule ... />
  </template>
</SplitPaneLayout>
```

This eliminates CSS duplication entirely.

---

## 🚀 NEXT STEPS

1. Apply copy-paste fixes above
2. Test all functionality
3. Extract SplitPaneLayout component (for future modules)
4. Document in MODULE-CREATION-GUIDE.md

**Estimated time with checklist:** 15 minutes (vs 3 hours trial & error)
