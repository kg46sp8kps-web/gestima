<script setup lang="ts">
/**
 * Parts List Module - Display and select parts
 *
 * Loads parts from store and displays them in a grid.
 * Can be used standalone or embedded in views.
 */

import { ref, onMounted, computed } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useWindowContextStore } from '@/stores/windowContext'
import type { LinkingGroup } from '@/stores/windows'
import { Package, Calendar } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  standalone?: boolean
  linkingGroup?: LinkingGroup
}

const props = withDefaults(defineProps<Props>(), {
  standalone: false,
  linkingGroup: null
})

const emit = defineEmits<{
  'select-part': [partNumber: string]
}>()

const partsStore = usePartsStore()
const contextStore = useWindowContextStore()

// Computed
const parts = computed(() => partsStore.parts)
const loading = computed(() => partsStore.loading)
const hasParts = computed(() => partsStore.hasParts)

// Load parts on mount
onMounted(async () => {
  if (!hasParts.value) {
    await partsStore.fetchParts()
  }
})

function selectPart(partNumber: string) {
  emit('select-part', partNumber)

  // Update window context if linked
  if (props.linkingGroup) {
    const part = parts.value.find(p => p.part_number === partNumber)
    if (part) {
      contextStore.setContext(props.linkingGroup, part.id, part.part_number, part.article_number)
    }
  }
}

// Format date
function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString('cs-CZ')
}
</script>

<template>
  <div class="parts-list-module">
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>Načítám díly...</p>
    </div>
    <div v-else-if="!hasParts" class="empty">
      <div class="empty-icon">
        <Package :size="ICON_SIZE.HERO" />
      </div>
      <p>Žádné díly k zobrazení</p>
      <p class="hint">Vytvořte první díl pomocí tlačítka "+ Nový díl"</p>
    </div>
    <div v-else class="parts-grid">
      <div
        v-for="part in parts"
        :key="part.part_number"
        class="part-card"
        @click="selectPart(part.part_number)"
        :data-testid="`part-card-${part.part_number}`"
      >
        <div class="part-header">
          <h3 class="part-name">{{ part.name }}</h3>
          <span class="article-number">{{ part.article_number || part.part_number }}</span>
        </div>
        <p v-if="part.notes" class="part-notes">{{ part.notes }}</p>
        <div class="part-meta">
          <span class="meta-item">
            <Calendar :size="ICON_SIZE.SMALL" class="meta-icon" />
            {{ formatDate(part.created_at) }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.parts-list-module {
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* Loading state */
.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: var(--space-10);
  color: var(--text-secondary);
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-default);
  border-top-color: var(--brand);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: var(--space-4);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Empty state */
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: var(--space-10);
  text-align: center;
  color: var(--text-secondary);
}

.empty-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-4);
  opacity: 0.5;
  color: var(--text-secondary);
}

.empty p {
  margin: 0;
  font-size: var(--text-base);
}

.hint {
  margin-top: var(--space-2) !important;
  font-size: var(--text-sm) !important;
  color: var(--text-tertiary);
}

/* Parts grid */
.parts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-4);
  padding: var(--space-4);
  overflow-y: auto;
}

/* Part card */
.part-card {
  padding: var(--space-4);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.part-card:hover {
  border-color: var(--brand);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.part-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.part-name {
  margin: 0;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.article-number {
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  color: var(--brand);
  background: var(--brand-subtle);
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.part-notes {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.part-meta {
  display: flex;
  gap: var(--space-4);
  padding-top: var(--space-2);
  border-top: 1px solid var(--border-subtle);
}

.meta-item {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.meta-icon {
  display: inline-block;
}
</style>
