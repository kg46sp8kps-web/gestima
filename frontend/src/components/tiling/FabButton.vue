<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { Plus } from 'lucide-vue-next'
import type { WorkspaceType } from '@/types/workspace'

const emit = defineEmits<{
  'switch-workspace': [workspace: WorkspaceType]
}>()

const isOpen = ref(false)
const isVisible = ref(false)

const workspaces: { key: WorkspaceType; label: string; shortcut?: string; dotColor: string }[] = [
  { key: 'timevision', label: 'TimeVision', shortcut: '⌘6', dotColor: 'var(--red)' },
  { key: 'manufacturing', label: 'Výroba', shortcut: '⌘7', dotColor: 'var(--red)' },
  { key: 'partners', label: 'Partneři', shortcut: '⌘8', dotColor: 'var(--t3)' },
  { key: 'quotes', label: 'Nabídky', shortcut: '⌘9', dotColor: 'var(--ok)' },
  { key: 'materials', label: 'Materiály', dotColor: 'var(--t3)' },
  { key: 'accounting', label: 'Účetnictví', dotColor: 'var(--t3)' },
  { key: 'files', label: 'Soubory', dotColor: 'var(--t3)' },
  { key: 'admin', label: 'Správa', dotColor: 'var(--t3)' },
]

function togglePicker() {
  isOpen.value = !isOpen.value
}

function closePicker() {
  isOpen.value = false
}

function selectWorkspace(key: WorkspaceType) {
  emit('switch-workspace', key)
  closePicker()
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && isOpen.value) {
    closePicker()
  }
}

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
  setTimeout(() => {
    isVisible.value = true
  }, 500)
})

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <!-- FAB -->
  <button
    class="fab"
    :class="{ visible: isVisible }"
    @click="togglePicker"
    data-testid="fab-button"
    title="Přidat modul"
  >
    <Plus :size="15" />
  </button>

  <!-- Module Picker -->
  <div
    class="module-picker"
    :class="{ open: isOpen }"
    data-testid="module-picker"
  >
    <div class="picker-header">Přidat modul</div>
    <button
      v-for="ws in workspaces"
      :key="ws.key"
      class="picker-item"
      @click="selectWorkspace(ws.key)"
      :data-testid="`fab-ws-${ws.key}`"
    >
      <span class="ws-dot" :style="{ background: ws.dotColor }"></span>
      {{ ws.label }}
      <span v-if="ws.shortcut" class="ws-shortcut">{{ ws.shortcut }}</span>
    </button>
  </div>

  <!-- Backdrop -->
  <div v-if="isOpen" class="fab-backdrop" @click="closePicker"></div>
</template>

<style scoped>
/* ── FAB Button ── */
.fab {
  position: fixed;
  bottom: 30px;
  right: 11px;
  width: 33px;
  height: 33px;
  border-radius: 50%;
  background: var(--red);
  color: var(--t1);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
  box-shadow:
    0 3px 14px rgba(229, 57, 53, 0.35),
    0 0 30px rgba(229, 57, 53, 0.1);
  opacity: 0;
  transform: scale(0.5);
  pointer-events: none;
  transition:
    background 0.15s ease,
    transform 0.15s ease,
    box-shadow 0.15s ease;
}

.fab.visible {
  animation: fab-entrance 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) 0s forwards;
  pointer-events: auto;
}

.fab:hover {
  background: rgba(229, 57, 53, 0.7);
  transform: scale(1.08);
  box-shadow:
    0 4px 20px rgba(229, 57, 53, 0.5),
    0 0 40px rgba(229, 57, 53, 0.15);
}

.fab:focus-visible {
  outline: 2px solid rgba(255,255,255,0.5);
  outline-offset: 2px;
}

@keyframes fab-entrance {
  from {
    opacity: 0;
    transform: scale(0.5);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* ── Module Picker Popup ── */
.module-picker {
  position: fixed;
  bottom: 68px;
  right: 11px;
  width: 190px;
  background: color-mix(in srgb, var(--surface) 88%, transparent);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.10);
  border-radius: 7px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
  z-index: 25;
  overflow: hidden;
  transform-origin: bottom right;
  transition: all 0.15s ease;
  opacity: 0;
  transform: scale(0.92) translateY(4px);
  pointer-events: none;
}

.module-picker.open {
  opacity: 1;
  transform: scale(1) translateY(0);
  pointer-events: auto;
}

/* ── Picker Header ── */
.picker-header {
  padding: 5px 9px;
  font-size: var(--fsl);
  font-weight: 600;
  color: var(--t4);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  background: color-mix(in srgb, var(--raised) 92%, transparent);
}

/* ── Picker Items ── */
.picker-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 9px;
  font-size: var(--fs);
  color: var(--t3);
  cursor: pointer;
  width: 100%;
  text-align: left;
  border: none;
  background: none;
  transition:
    background 0.1s ease,
    color 0.1s ease;
}

.picker-item:hover {
  background: rgba(255, 255, 255, 0.06);
  color: var(--t1);
}

.picker-item:focus-visible {
  outline: 2px solid rgba(255,255,255,0.5);
  outline-offset: -2px;
}

/* ── Workspace Dot ── */
.ws-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* ── Shortcut Label ── */
.ws-shortcut {
  font-family: var(--mono);
  font-size: var(--fsl);
  color: var(--t4);
  margin-left: auto;
}

/* ── Backdrop ── */
.fab-backdrop {
  position: fixed;
  inset: 0;
  z-index: 19;
}
</style>
