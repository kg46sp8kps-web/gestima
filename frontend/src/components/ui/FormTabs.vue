<template>
  <div class="form-tabs" :class="{ 'form-tabs-vertical': vertical }">
    <!-- Tab navigation -->
    <div class="tabs-nav" role="tablist">
      <button
        v-for="(tab, index) in tabs"
        :key="getTabKey(tab, index)"
        :class="[
          'tab-button',
          {
            active: modelValue === index,
            disabled: isTabDisabled(tab)
          }
        ]"
        :disabled="isTabDisabled(tab)"
        role="tab"
        :aria-selected="modelValue === index"
        :aria-controls="`tab-panel-${index}`"
        @click="selectTab(index)"
      >
        <!-- Tab icon -->
        <span v-if="getTabIcon(tab)" class="tab-icon">
          {{ getTabIcon(tab) }}
        </span>

        <!-- Tab label -->
        <span class="tab-label">{{ getTabLabel(tab) }}</span>

        <!-- Tab badge -->
        <span v-if="getTabBadge(tab)" class="tab-badge">
          {{ getTabBadge(tab) }}
        </span>
      </button>
    </div>

    <!-- Tab content panels -->
    <div class="tabs-content">
      <template v-for="(tab, index) in tabs" :key="getTabKey(tab, index)">
        <div
          v-if="keepAlive || modelValue === index"
          v-show="modelValue === index"
          :id="`tab-panel-${index}`"
          class="tab-panel"
          :class="{ active: modelValue === index }"
          role="tabpanel"
          :aria-hidden="modelValue !== index"
        >
          <slot :name="`tab-${index}`" :tab="tab" :index="index" :active="modelValue === index">
            <!-- Default slot fallback - use if named slots not provided -->
            <slot v-if="modelValue === index" :tab="tab" :index="index"></slot>
          </slot>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * FormTabs - Tab layout component for forms and multi-section views
 *
 * Usage:
 * ```vue
 * <FormTabs v-model="activeTab" :tabs="['Základní', 'Materiál', 'Operace']">
 *   <template #tab-0>Basic info content</template>
 *   <template #tab-1>Material content</template>
 *   <template #tab-2>Operations content</template>
 * </FormTabs>
 * ```
 *
 * Or with object tabs:
 * ```vue
 * <FormTabs
 *   v-model="activeTab"
 *   :tabs="[
 *     { label: 'Základní' },
 *     { label: 'Materiál', badge: 3 },
 *     { label: 'Operace', disabled: true }
 *   ]"
 * >
 * ```
 *
 * Note: For icons, use Lucide Vue components directly in tab labels or custom slots.
 */

export interface TabItem {
  label: string;
  icon?: string;
  badge?: string | number;
  disabled?: boolean;
  key?: string;
}

type Tab = string | TabItem;

interface Props {
  modelValue: number;
  tabs: Tab[];
  vertical?: boolean;
  keepAlive?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  vertical: false,
  keepAlive: true
});

const emit = defineEmits<{
  'update:modelValue': [index: number];
  'tab-change': [index: number, tab: Tab];
}>();

// === METHODS ===

const getTabKey = (tab: Tab, index: number): string => {
  if (typeof tab === 'object' && tab.key) {
    return tab.key;
  }
  return `tab-${index}`;
};

const getTabLabel = (tab: Tab): string => {
  return typeof tab === 'string' ? tab : tab.label;
};

const getTabIcon = (tab: Tab): string | undefined => {
  return typeof tab === 'object' ? tab.icon : undefined;
};

const getTabBadge = (tab: Tab): string | number | undefined => {
  return typeof tab === 'object' ? tab.badge : undefined;
};

const isTabDisabled = (tab: Tab): boolean => {
  return typeof tab === 'object' ? !!tab.disabled : false;
};

const selectTab = (index: number) => {
  const tab = props.tabs[index];
  if (tab && index !== props.modelValue && !isTabDisabled(tab)) {
    emit('update:modelValue', index);
    emit('tab-change', index, tab);
  }
};
</script>

<style scoped>
/* === CONTAINER === */
.form-tabs {
  display: flex;
  flex-direction: column;
  height: 100%;
  container-type: inline-size;
}

.form-tabs-vertical {
  flex-direction: row;
}

/* === TAB NAVIGATION === */
.tabs-nav {
  display: flex;
  gap: var(--space-1);
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-subtle);
  padding: 0 var(--space-4);
  flex-shrink: 0;
  overflow-x: auto;
  scrollbar-width: thin;
}

.form-tabs-vertical .tabs-nav {
  flex-direction: column;
  border-bottom: none;
  border-right: 1px solid var(--border-default);
  padding: var(--space-4) 0;
  min-width: 180px;
  overflow-x: visible;
  overflow-y: auto;
}

/* === TAB BUTTON === */
.tab-button {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  position: relative;
  white-space: nowrap;
  transition: var(--transition-fast);
}

.tab-button:hover:not(.disabled) {
  color: var(--text-primary);
  background: var(--state-hover);
}

.tab-button.active {
  color: var(--brand);
}

/* Active indicator (horizontal) */
.tab-button.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--brand);
  border-radius: 1px 1px 0 0;
}

/* Active indicator (vertical) */
.form-tabs-vertical .tab-button.active::after {
  bottom: auto;
  top: 0;
  left: auto;
  right: -1px;
  width: 2px;
  height: 100%;
  border-radius: 0 1px 1px 0;
}

.tab-button.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* === TAB ICON === */
.tab-icon {
  font-size: var(--text-sm);
  line-height: 1;
}

/* === TAB BADGE === */
.tab-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 var(--space-1);
  border-radius: var(--radius-full);
  background: var(--brand);
  color: white;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.tab-button:not(.active) .tab-badge {
  background: var(--bg-muted);
  color: var(--text-secondary);
}

/* === TAB CONTENT === */
.tabs-content {
  flex: 1;
  overflow: auto;
  position: relative;
}

.tab-panel {
  padding: var(--space-5);
  height: 100%;
}

/* Hide inactive panels but keep them mounted */
.tab-panel:not(.active) {
  position: absolute;
  visibility: hidden;
  pointer-events: none;
}

/* === RESPONSIVE === */
@container (max-width: 768px) {
  .form-tabs-vertical {
    flex-direction: column;
  }

  .form-tabs-vertical .tabs-nav {
    flex-direction: row;
    border-right: none;
    border-bottom: 1px solid var(--border-default);
    min-width: auto;
    padding: 0 var(--space-4);
    overflow-x: auto;
  }

  .form-tabs-vertical .tab-button.active::after {
    bottom: -1px;
    top: auto;
    left: 0;
    right: 0;
    width: auto;
    height: 2px;
    border-radius: 1px 1px 0 0;
  }
}
</style>
