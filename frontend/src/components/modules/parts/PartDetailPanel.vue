<script setup lang="ts">
import { ref } from 'vue'
import type { Part } from '@/types/part'
import type { LinkingGroup } from '@/stores/windows'
import DrawingsManagementModal from './DrawingsManagementModal.vue'
import { Package, Settings, DollarSign, FileText } from 'lucide-vue-next'

interface Props {
  part: Part
  linkingGroup?: LinkingGroup
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'open-material': []
  'open-operations': []
  'open-pricing': []
  'open-drawing': [drawingId?: number]
  'refresh': []
}>()


// Drawings management modal
const showDrawingsModal = ref(false)

function handleDrawingButtonClick() {
  // Check if part has any drawings
  if (props.part.drawing_path) {
    // Has drawing = open primary drawing window
    emit('open-drawing')
  } else {
    // No drawing = open modal for upload
    showDrawingsModal.value = true
  }
}

function handleDrawingButtonRightClick(event: MouseEvent) {
  event.preventDefault()
  // Right-click = always open modal for management
  showDrawingsModal.value = true
}

function handleOpenDrawing(drawingId?: number) {
  emit('open-drawing', drawingId)
  showDrawingsModal.value = false
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString('cs-CZ')
}
</script>

<template>
  <div class="part-detail-panel">
    <!-- Compact Header -->
    <div class="part-header-compact">
      <div class="header-item">
        <span class="header-label">Artikl:</span>
        <span class="header-value">{{ part.article_number || '—' }}</span>
      </div>
      <div class="header-item">
        <span class="header-label">Výkres:</span>
        <span class="header-value">{{ part.drawing_path || '—' }}</span>
      </div>
      <div class="header-item">
        <span class="header-label">Název:</span>
        <span class="header-value">{{ part.name }}</span>
      </div>
      <div class="header-item">
        <span class="header-label">Revize:</span>
        <span class="header-value">{{ part.customer_revision || '—' }}</span>
      </div>
      <div class="header-item full-width" v-if="part.notes">
        <span class="header-label">Poznámky:</span>
        <span class="header-value">{{ part.notes }}</span>
      </div>
      <div class="header-item">
        <span class="article-number-badge">{{ part.article_number || part.part_number }}</span>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="actions-grid">
      <button class="action-button" @click="emit('open-material')">
        <Package :size="32" class="action-icon" />
        <span class="action-label">Materiál</span>
      </button>
      <button class="action-button" @click="emit('open-operations')">
        <Settings :size="32" class="action-icon" />
        <span class="action-label">Operace</span>
      </button>
      <button class="action-button" @click="emit('open-pricing')">
        <DollarSign :size="32" class="action-icon" />
        <span class="action-label">Ceny</span>
      </button>
      <button
        class="action-button"
        @click="handleDrawingButtonClick"
        @contextmenu="handleDrawingButtonRightClick"
        title="Klikni = otevři výkres | Pravé tlačítko = správa výkresů"
      >
        <FileText :size="32" class="action-icon" />
        <span class="action-label">Výkres</span>
      </button>
    </div>

    <!-- Drawings Management Modal -->
    <DrawingsManagementModal
      v-model="showDrawingsModal"
      :part-number="part.part_number"
      @refresh="emit('refresh')"
      @open-drawing="handleOpenDrawing"
    />
  </div>
</template>

<style scoped>
/* Copy relevant styles from PartMainModule.vue DETAIL section */
.part-detail-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

/* Compact Header Grid */
.part-header-compact {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
}

.header-item {
  display: flex;
  gap: var(--space-2);
  align-items: baseline;
}

.header-item.full-width {
  grid-column: 1 / -1;
}

.header-label {
  font-weight: var(--font-medium);
  color: var(--text-secondary);
  white-space: nowrap;
}

.header-value {
  color: var(--text-body);
}

.article-number-badge {
  padding: var(--space-1) var(--space-2);
  background: var(--color-primary);
  color: white;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  justify-self: end;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
}

.action-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-4);
  background: var(--bg-surface);
  border: 2px solid var(--border-default);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: var(--transition-normal);
}

.action-button:hover {
  border-color: var(--color-primary);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.action-icon {
  color: var(--color-primary);
}

.action-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-body);
}

</style>
