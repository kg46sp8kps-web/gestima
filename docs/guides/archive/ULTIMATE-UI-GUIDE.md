# ULTIMATE UI GUIDE - Finální Stavební Kameny

**Verze:** 1.0 FINAL
**Datum:** 2026-02-02
**Status:** 🔒 **PRODUCTION LOCKED** - Žádné změny!

**Cíl:** Vytvořit jakékoliv UI za **MAX 30 MINUT** včetně debuggingu.

---

## 🎯 FILOZOFIE: Copy-Paste > Coding

```
Screenshot → Claude.ai → Copy-paste template → Done
   (2 min)      (5 min)         (3 min)      (20 min debug/polish)
```

**PRAVIDLA:**
1. ✅ **VŽDY** použij existující komponentu
2. ✅ **VŽDY** copy-paste template
3. ✅ **NIKDY** nepis CSS od nuly
4. ✅ **NIKDY** neřeš spacing ručně - použij design tokens

---

## 📦 STAVEBNÍ KAMENY (Building Blocks)

### Level 1: Design Tokens (Použij VŽDY)

```css
/* SPACING - 4pt grid */
--space-1: 4px
--space-2: 6px   ← BASE gap
--space-3: 8px   ← BASE padding
--space-4: 12px
--space-5: 16px
--space-6: 20px

/* TEXT SIZES */
--text-xs: 10px
--text-sm: 11px
--text-base: 12px ← BASE
--text-lg: 13px
--text-xl: 14px

/* COLORS */
--color-primary: #991b1b (red)
--color-success: #059669 (green)
--color-danger: #f43f5e (pink)
--color-info: #2563eb (blue)

--text-primary: #ffffff (headings)
--text-body: #f5f5f5 (body text)
--text-secondary: #a3a3a3 (labels)

--bg-base: #0a0a0a (app background)
--bg-surface: #141414 (cards, panels)
--bg-raised: #1a1a1a (elevated)

--border-default: #2a2a2a
--border-strong: #404040
```

**POUŽITÍ:**
```css
/* ❌ ŠPATNĚ */
padding: 8px;
font-size: 12px;
color: #f5f5f5;

/* ✅ SPRÁVNĚ */
padding: var(--space-3);
font-size: var(--text-base);
color: var(--text-body);
```

---

### Level 2: Base Components (Copy-Paste Ready)

**Lokace:** `frontend/src/components/base/`

#### BaseButton.vue
```vue
<BaseButton variant="primary" size="md" @click="save">
  Save
</BaseButton>

<!-- Variants: primary, secondary, danger, success, ghost -->
<!-- Sizes: sm, md, lg -->
<!-- Props: loading, disabled, icon, iconRight -->
```

#### BaseCard.vue
```vue
<BaseCard padding="md">
  <template #header>Title</template>
  <p>Content</p>
  <template #footer>Footer</template>
</BaseCard>

<!-- Padding: none, sm, md, lg -->
<!-- Automaticky fluid (height: 100%) -->
<!-- NIKDY se neusekne -->
```

#### BaseInput.vue (TODO - vytvořit)
```vue
<BaseInput
  v-model="name"
  label="Part Name"
  placeholder="Enter name..."
  :error="errors.name"
/>
```

#### BaseDialog.vue (TODO - vytvořit)
```vue
<BaseDialog v-model:open="showDialog" title="Confirm">
  <p>Are you sure?</p>
  <template #footer>
    <BaseButton @click="showDialog = false">Cancel</BaseButton>
    <BaseButton variant="danger" @click="confirm">Delete</BaseButton>
  </template>
</BaseDialog>
```

#### BaseTable.vue (TODO - vytvořit)
```vue
<BaseTable
  :columns="columns"
  :data="items"
  :loading="loading"
  @row-click="handleSelect"
/>
```

---

### Level 3: Widget Templates

**GOLDEN RULE:** Widget = Header (optional) + Content (fluid) + Footer (optional)

```vue
<template>
  <div class="widget-root">
    <!-- Optional: Header -->
    <div v-if="showHeader" class="widget-header">
      <h3>Widget Title</h3>
    </div>

    <!-- Content - KRITICKÉ: flex: 1 -->
    <div class="widget-content">
      <!-- Empty state -->
      <div v-if="!data" class="empty-state">
        <Icon :size="48" />
        <p>No data</p>
      </div>

      <!-- Actual content -->
      <div v-else>
        <!-- Your UI here -->
      </div>
    </div>

    <!-- Optional: Footer -->
    <div v-if="showFooter" class="widget-footer">
      <BaseButton>Action</BaseButton>
    </div>
  </div>
</template>

<style scoped>
.widget-root {
  height: 100%; /* KRITICKÉ - vždy 100% */
  display: flex;
  flex-direction: column;
  padding: var(--space-3); /* Jednotný padding */
}

.widget-header {
  flex-shrink: 0; /* KRITICKÉ - header se neshrinkne */
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border-default);
}

.widget-content {
  flex: 1; /* KRITICKÉ - zabere zbytek prostoru */
  overflow: auto; /* KRITICKÉ - auto scroll */
  /* ŽÁDNÝ padding zde - už je na .widget-root */
}

.widget-footer {
  flex-shrink: 0; /* KRITICKÉ - footer se neshrinkne */
  padding-top: var(--space-2);
  border-top: 1px solid var(--border-default);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: var(--space-2);
  color: var(--text-tertiary);
}
</style>
```

---

### Level 4: Layout Patterns

#### Pattern 1: Info Grid (key-value pairs)

```vue
<div class="info-grid">
  <div class="info-field">
    <span class="label">Part Number:</span>
    <span class="value">{{ part.part_number }}</span>
  </div>
  <div class="info-field">
    <span class="label">Name:</span>
    <span class="value">{{ part.name }}</span>
  </div>
</div>

<style scoped>
.info-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.info-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
}

.value {
  font-size: var(--text-base);
  color: var(--text-body);
}

/* Container query for horizontal layout on wide widgets */
@container widget (min-width: 400px) {
  .info-field {
    flex-direction: row;
    align-items: baseline;
    gap: var(--space-2);
  }

  .label {
    min-width: 120px;
    flex-shrink: 0;
  }

  .value {
    flex: 1;
  }
}
</style>
```

#### Pattern 2: Action Grid (buttons)

```vue
<div class="action-grid">
  <BaseButton
    v-for="action in actions"
    :key="action.id"
    :variant="action.variant"
    :icon="action.icon"
    @click="handleAction(action.id)"
  >
    {{ action.label }}
  </BaseButton>
</div>

<style scoped>
.action-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.action-grid button {
  flex: 1 1 calc(33.333% - var(--space-2)); /* 3 columns */
  min-width: 80px; /* Prevent too narrow */
}

/* Responsive */
@container widget (max-width: 400px) {
  .action-grid button {
    flex: 1 1 calc(50% - var(--space-2)); /* 2 columns */
  }
}

@container widget (max-width: 250px) {
  .action-grid button {
    flex: 1 1 100%; /* 1 column */
  }
}
</style>
```

#### Pattern 3: List with Selection

```vue
<div class="list-container">
  <div
    v-for="item in items"
    :key="item.id"
    class="list-item"
    :class="{ selected: item.id === selectedId }"
    @click="handleSelect(item)"
  >
    <span class="item-title">{{ item.title }}</span>
    <span class="item-subtitle">{{ item.subtitle }}</span>
  </div>
</div>

<style scoped>
.list-container {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.list-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: var(--transition-fast);
}

.list-item:hover {
  background: var(--state-hover);
}

.list-item.selected {
  background: var(--state-selected);
  border-color: var(--color-primary);
}

.item-title {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

.item-subtitle {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}
</style>
```

---

## 🚀 WORKFLOW: 30 MINUT NA OKNO

### Krok 1: Mockup (5 min)

**Nástroje:**
- Excalidraw (online)
- Papír + tužka
- Figma (pokud umíš)

**Vytvoř:**
1. Základní layout (kde jsou widgety)
2. Popisy widgetů (co zobrazují, jaké akce)
3. Screenshot

### Krok 2: Claude.ai Generování (10 min)

**Prompt template:**

```
[Upload screenshot mockupu]

Vytvoř Vue 3 <script setup> komponentu podle tohoto designu.

REQUIREMENTS:
✅ TypeScript
✅ Použij Base komponenty (BaseButton, BaseCard z /components/base/)
✅ Použij design tokens (var(--space-3), var(--text-body), atd.)
✅ Container queries (NE media queries)
✅ Fluid layout (height: 100%, flex: 1)
✅ Empty states
✅ Max 200 LOC

ANTI-PATTERNS (NIKDY):
❌ Hardcoded heights (height: 80px)
❌ Hardcoded colors (#ff0000)
❌ Hardcoded spacing (padding: 8px)
❌ Media queries (@media)
❌ CSS Grid s fixed sizes
❌ Scroll v widgetu (už je v WidgetWrapper)

STRUKTURA:
```vue
<script setup lang="ts">
import { computed } from 'vue'
import BaseButton from '@/components/base/BaseButton.vue'
// ...

interface Props {
  context?: {
    data?: YourType | null
  }
}

const props = defineProps<Props>()
</script>

<template>
  <div class="widget-root">
    <div v-if="!context?.data" class="empty-state">...</div>
    <div v-else>...</div>
  </div>
</template>

<style scoped>
.widget-root {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: var(--space-3);
}
</style>
```

Return COMPLETE .vue file ready to copy-paste.
```

**Claude.ai vygeneruje:**
- Kompletní .vue soubor
- S TypeScript types
- S design tokens
- S container queries
- Ready to use

**Copy-paste → Done!**

### Krok 3: Layout Config (3 min)

**Copy-paste template:**

```typescript
// frontend/src/config/layouts/my-module-detail.ts

import type { ModuleLayoutConfig } from '@/types/widget'

export const myModuleDetailConfig: ModuleLayoutConfig = {
  moduleKey: 'my-module-detail',
  cols: 12,
  rowHeight: 60,

  widgets: [
    {
      id: 'my-info-widget',
      type: 'info-card',
      title: 'Informace',
      component: 'MyInfoWidget',
      minWidth: 3,
      minHeight: 3,
      defaultWidth: 6,
      defaultHeight: 5,
      resizable: true,
      removable: false,
      required: true
    },
    {
      id: 'my-actions-widget',
      type: 'action-bar',
      title: 'Akce',
      component: 'MyActionsWidget',
      minWidth: 3,
      minHeight: 2,
      defaultWidth: 6,
      defaultHeight: 3,
      resizable: true,
      removable: false,
      required: true
    }
  ],

  defaultLayouts: {
    compact: [
      { i: 'my-info-widget', x: 0, y: 0, w: 12, h: 5 },
      { i: 'my-actions-widget', x: 0, y: 5, w: 12, h: 3 }
    ],
    comfortable: [
      { i: 'my-info-widget', x: 0, y: 0, w: 6, h: 5 },
      { i: 'my-actions-widget', x: 6, y: 0, w: 6, h: 3 }
    ]
  }
}
```

### Krok 4: Main Module (2 min)

**Copy-paste template:**

```vue
<script setup lang="ts">
import { ref, computed } from 'vue'
import CustomizableModule from '@/components/layout/CustomizableModule.vue'
import { myModuleDetailConfig } from '@/config/layouts/my-module-detail'
import type { MyDataType } from '@/types/...'

const selectedItem = ref<MyDataType | null>(null)

const widgetContext = computed(() => ({
  'my-info-widget': {
    data: selectedItem.value
  },
  'my-actions-widget': {
    itemId: selectedItem.value?.id,
    disabled: !selectedItem.value
  }
}))

function handleWidgetAction(widgetId: string, action: string, payload?: any) {
  if (action === 'edit') {
    // Handle edit
  }
  // ... other actions
}
</script>

<template>
  <CustomizableModule
    :config="myModuleDetailConfig"
    :context="widgetContext"
    @widget-action="handleWidgetAction"
  />
</template>
```

### Krok 5: Debug & Polish (10 min)

#### A) Aktivuj CSS Debug Overlay

```vue
<!-- Add to App.vue -->
<CssDebugOverlay v-if="import.meta.env.DEV" />
```

**Použití:**
1. Stiskni `Ctrl+Shift+D` → Debug mode
2. Klikni na "useknutý" widget → Zobrazí problémy
3. Oprav podle návrhů

**Časté problémy:**

| Problém | Příčina | Fix |
|---------|---------|-----|
| Widget useknutý | `overflow: hidden` + content přetéká | `overflow: auto` |
| Widget malý | Fixed height | `height: 100%; flex: 1` |
| Velký spacing | Hardcoded padding | `padding: var(--space-3)` |
| Špatné zarovnání | Chybí flex | `display: flex; flex-direction: column` |

#### B) Screenshot → Claude.ai Fix

```
[Upload screenshot aktuálního UI]

Problém: Widget má useknutý spodek

Oprav CSS podle těchto pravidel:
- height: 100% na root
- flex: 1 na content
- overflow: auto na scrollable části
- Žádné fixed heights

Vrať jen CSS fix (ne celý soubor).
```

Claude vrátí:
```css
.widget-content {
  flex: 1;
  overflow: auto;
}
```

Copy-paste → Done!

---

## 🛡️ CSS ANTI-PATTERN CHECKLIST

**Před commitom zkontroluj:**

```bash
# Search for anti-patterns
grep -r "height: [0-9]" frontend/src/components/widgets/
grep -r "min-height: [0-9]" frontend/src/components/widgets/
grep -r "padding: [0-9]" frontend/src/components/widgets/
grep -r "@media" frontend/src/components/widgets/
```

**Pokud najdeš:**
- ❌ `height: 80px` → Replace: `height: 100%` nebo `flex: 1`
- ❌ `padding: 8px` → Replace: `padding: var(--space-3)`
- ❌ `@media (max-width: 400px)` → Replace: `@container widget (max-width: 400px)`

---

## 📚 COMPONENT LIBRARY (Use These!)

### Existing (Ready to use)

✅ `CustomizableModule.vue` - Universal module template
✅ `GridLayoutArea.vue` - GridStack wrapper
✅ `WidgetWrapper.vue` - Widget chrome
✅ `InfoCard.vue` - Generic info display
✅ `ActionBar.vue` - Action buttons
✅ `BaseButton.vue` - Button with variants
✅ `BaseCard.vue` - Card container
✅ `CssDebugOverlay.vue` - CSS debugger

### TODO (Vytvořit podle potřeby)

⏳ `BaseInput.vue` - Form input
⏳ `BaseDialog.vue` - Modal dialog
⏳ `BaseTable.vue` - Data table
⏳ `BaseSelect.vue` - Dropdown
⏳ `BaseCheckbox.vue` - Checkbox
⏳ `BaseBadge.vue` - Status badge
⏳ `BaseToast.vue` - Toast notifications

**RULE:** Vytvoř jen když potřebuješ 3× (Rule of Three)

---

## 🎨 VISUAL DEBUGGING WORKFLOW

### Problém: "Widget se nezobrazuje jak chci"

**Řešení: Screenshot → Claude.ai Visual Fix**

1. Screenshot aktuálního UI
2. Screenshot expected UI (nebo mockup)
3. Prompt:

```
[Upload obě screenshots]

CURRENT: [první screenshot]
EXPECTED: [druhý screenshot]

Oprav CSS aby CURRENT vypadal jako EXPECTED.

Pravidla:
- Použij design tokens (var(--space-X))
- Fluid layout (height: 100%)
- Container queries

Vrať jen CSS diff.
```

Claude vrátí:
```css
/* Change this: */
.action-grid {
  gap: 12px; /* ❌ */
}

/* To this: */
.action-grid {
  gap: var(--space-3); /* ✅ */
}
```

---

## 📋 30-MIN CHECKLIST

**Před začátkem:**
- [ ] Mockup narýsován (5 min)
- [ ] Screenshot vytvořen

**Implementace:**
- [ ] Widget 1 vygenerován Claude.ai (5 min)
- [ ] Widget 2 vygenerován Claude.ai (5 min)
- [ ] Layout config vytvořen (3 min)
- [ ] Main module vytvořen (2 min)

**Testing:**
- [ ] CSS Debug zapnut (Ctrl+Shift+D)
- [ ] Žádné "useknuté" widgety
- [ ] Responsive funguje (resize window)
- [ ] Drag & drop funguje
- [ ] Empty states zobrazují se

**Anti-pattern check:**
- [ ] Žádné `height: XXpx`
- [ ] Žádné hardcoded colors
- [ ] Žádné hardcoded spacing
- [ ] Jen container queries (ne @media)

**Done!** ✅

---

## 🔒 PRODUCTION RULES (LOCKED)

**THESE NEVER CHANGE:**

1. **Design tokens only** - Žádné hardcoded hodnoty
2. **Fluid layouts** - height: 100%, flex: 1
3. **Container queries** - Ne @media
4. **Empty states** - Vždy zobraz prázdný stav
5. **< 200 LOC per widget** - Malé komponenty
6. **Base components first** - Použij existující
7. **Copy-paste templates** - Ne coding od nuly

---

## 🚀 QUICK START

**Vytvořit nový modul:**

```bash
# 1. Nakresli mockup (5 min)
# 2. Screenshot → Claude.ai (10 min)
# 3. Copy-paste layout config (3 min)
# 4. Copy-paste main module (2 min)
# 5. Debug (10 min)

# Total: 30 min
```

**Fix CSS problém:**

```bash
# 1. Ctrl+Shift+D (zapni CSS debug)
# 2. Klikni na problémový element
# 3. Čti "Issues" sekci
# 4. Oprav podle návrhů
# 5. Hotovo

# Total: 2 min
```

---

## 📞 TROUBLESHOOTING

### "Claude.ai vygeneroval špatný kód"

**Fix:**
```
Tento kód porušuje pravidla:
[paste kód]

Oprav podle ULTIMATE UI GUIDE:
- Použij design tokens
- height: 100% místo fixed heights
- Container queries místo media queries

Vrať opravený kód.
```

### "Nevím jak nakreslit mockup"

**Použij Excalidraw:**
1. https://excalidraw.com
2. Nakresli obdélníky (widgety)
3. Přidej text (popisky)
4. Screenshot
5. Done

### "Widget má useknutý spodek"

**Fix:**
1. `Ctrl+Shift+D` → Debug mode
2. Klikni na widget
3. Čti "Issues"
4. Pravděpodobně: `overflow: hidden` → změň na `overflow: auto`

---

**END OF GUIDE** 🔒

**Toto je finální verze. Žádné další změny.**

Vše co potřebuješ je zde. **Max 30 min na okno. Guaranteed.**
