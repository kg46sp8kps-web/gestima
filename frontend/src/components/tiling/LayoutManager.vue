<script setup lang="ts">
import { ref } from 'vue'
import { Trash2Icon, StarIcon, EyeIcon, EyeOffIcon, SunIcon, MoonIcon, SparklesIcon } from 'lucide-vue-next'
import { useWorkspaceStore } from '@/stores/workspace'
import { useThemeStore } from '@/stores/theme'
import { useDialog } from '@/composables/useDialog'
import Modal from '@/components/ui/Modal.vue'

defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()

const ws = useWorkspaceStore()
const themeStore = useThemeStore()
const dialog = useDialog()

const savingId = ref<number | null>(null)
const deletingId = ref<number | null>(null)

async function handleSaveCurrent() {
  await ws.saveCurrentLayout()
}

async function handleCreateFromCurrent() {
  const name = window.prompt('Název nového layoutu:')
  if (!name?.trim()) return
  await ws.createFromCurrent(name.trim())
}

async function handleCreateBlank() {
  const name = window.prompt('Název prázdného layoutu:')
  if (!name?.trim()) return
  await ws.createBlankLayout(name.trim())
}

async function handleDelete(id: number, name: string) {
  const confirmed = await dialog.confirm({
    title: 'Smazat layout',
    message: `Opravdu chcete smazat layout „${name}"?`,
    confirmLabel: 'Smazat',
    cancelLabel: 'Zrušit',
  })
  if (!confirmed) return
  deletingId.value = id
  await ws.deleteLayout(id)
  deletingId.value = null
}

async function handleSetDefault(id: number) {
  savingId.value = id
  await ws.setDefaultLayout(id)
  savingId.value = null
}

async function handleToggleHeader(id: number) {
  await ws.toggleHeaderVisibility(id)
}
</script>

<template>
  <Modal :model-value="modelValue" title="Nastavení" size="md" @update:model-value="emit('update:modelValue', $event)">
    <!-- Theme toggle -->
    <div class="lm-theme-row">
      <span class="lm-theme-label">Vzhled</span>
      <div class="lm-theme-toggle">
        <button
          :class="['lm-theme-btn', { active: themeStore.theme === 'dark' }]"
          data-testid="theme-dark-btn"
          @click="themeStore.theme = 'dark'"
        >
          <MoonIcon :size="12" />
          Tmavý
        </button>
        <button
          :class="['lm-theme-btn', { active: themeStore.theme === 'light' }]"
          data-testid="theme-light-btn"
          @click="themeStore.theme = 'light'"
        >
          <SunIcon :size="12" />
          Světlý
        </button>
        <button
          :class="['lm-theme-btn', { active: themeStore.theme === 'corporate' }]"
          data-testid="theme-corporate-btn"
          @click="themeStore.theme = 'corporate'"
        >
          <SparklesIcon :size="12" />
          Moderní
        </button>
      </div>
    </div>

    <!-- Separator -->
    <div class="lm-sep" />

    <!-- Layout toolbar -->
    <div class="lm-toolbar">
      <button
        class="btn-secondary"
        data-testid="layout-create-from-current"
        @click="handleCreateFromCurrent"
      >
        Z aktuálního
      </button>
      <button
        class="btn-secondary"
        data-testid="layout-create-blank"
        @click="handleCreateBlank"
      >
        Čistý
      </button>
      <button
        class="btn-primary"
        :disabled="ws.currentLayoutId === null"
        data-testid="layout-save-current"
        @click="handleSaveCurrent"
      >
        Uložit
      </button>
    </div>

    <!-- Layout list -->
    <div v-if="ws.savedLayouts.length === 0" class="lm-empty">
      Žádné layouty
    </div>
    <table v-else class="ot lm-table">
      <thead>
        <tr>
          <th class="lm-th-name">Název</th>
          <th class="lm-th-center">V headeru</th>
          <th class="lm-th-center">Výchozí</th>
          <th class="lm-th-actions" />
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="layout in ws.savedLayouts"
          :key="layout.id"
          :class="['lm-row', { 'lm-row-active': ws.currentLayoutId === layout.id }]"
          :data-testid="`layout-row-${layout.id}`"
        >
          <td class="lm-td-name">
            <span class="lm-name">{{ layout.name }}</span>
          </td>
          <td class="lm-td-center">
            <button
              class="icon-btn icon-btn-sm"
              :title="layout.show_in_header ? 'Skrýt z headeru' : 'Zobrazit v headeru'"
              :data-testid="`layout-toggle-header-${layout.id}`"
              @click="handleToggleHeader(layout.id)"
            >
              <EyeIcon v-if="layout.show_in_header" :size="14" />
              <EyeOffIcon v-else :size="14" />
            </button>
          </td>
          <td class="lm-td-center">
            <button
              :class="['icon-btn', 'icon-btn-sm', { 'lm-star-active': layout.is_default }]"
              :title="layout.is_default ? 'Výchozí layout' : 'Nastavit jako výchozí'"
              :disabled="layout.is_default || savingId === layout.id"
              :data-testid="`layout-set-default-${layout.id}`"
              @click="handleSetDefault(layout.id)"
            >
              <StarIcon :size="14" />
            </button>
          </td>
          <td class="lm-td-actions">
            <button
              class="icon-btn icon-btn-sm icon-btn-danger"
              title="Smazat layout"
              :disabled="deletingId === layout.id"
              :data-testid="`layout-delete-${layout.id}`"
              @click="handleDelete(layout.id, layout.name)"
            >
              <Trash2Icon :size="14" />
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </Modal>
</template>

<style scoped>
.lm-theme-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.lm-theme-label {
  font-size: var(--fsm);
  font-weight: 600;
  color: var(--t3);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.lm-theme-toggle {
  display: flex;
  gap: 2px;
  background: var(--b1);
  border-radius: var(--rs);
  padding: 2px;
}

.lm-theme-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 22px;
  padding: 0 8px;
  border: none;
  border-radius: calc(var(--rs) - 1px);
  background: transparent;
  color: var(--t3);
  font-family: var(--font);
  font-size: var(--fsm);
  font-weight: 500;
  cursor: pointer;
  transition: all 100ms var(--ease);
}
.lm-theme-btn:hover { color: var(--t2); }
.lm-theme-btn.active {
  background: var(--surface);
  color: var(--t1);
  box-shadow: 0 1px 3px var(--shadow-drop);
}

.lm-sep {
  height: 1px;
  background: var(--b1);
  margin-bottom: 12px;
}

.lm-toolbar {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
}

.lm-empty {
  padding: 20px;
  text-align: center;
  color: var(--t4);
  font-size: var(--fs);
}

/* .lm-table extends global .ot — layout/column overrides only */
.lm-th-center { text-align: center; }

.lm-row {
  border-bottom: 1px solid var(--b1);
  transition: background 80ms var(--ease);
}
.lm-row:hover { background: var(--b1); }
.lm-row-active { background: rgba(255,255,255,0.03); }

.lm-td-name,
.lm-td-center,
.lm-td-actions {
  padding: 6px 8px;
  vertical-align: middle;
}
.lm-td-center { text-align: center; }
.lm-td-actions { text-align: right; }

.lm-name { color: var(--t2); }
.lm-row-active .lm-name { color: var(--t1); font-weight: 500; }

/* star active state — gold color for default layout indicator */
.lm-star-active { color: var(--warn); }
</style>
