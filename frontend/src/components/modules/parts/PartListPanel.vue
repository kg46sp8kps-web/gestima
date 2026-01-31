<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { usePartsStore } from '@/stores/parts'
import type { Part } from '@/types/part'
import type { LinkingGroup } from '@/stores/windows'

interface Props {
  linkingGroup?: LinkingGroup
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'select-part': [part: Part]
  'create-new': []
}>()

const partsStore = usePartsStore()
const searchQuery = ref('')
const selectedPartId = ref<number | null>(null)

const filteredParts = computed(() => {
  let list = [...partsStore.parts]

  // Sort by part_number (numeric if possible)
  list.sort((a, b) => {
    const aNum = parseInt(a.part_number)
    const bNum = parseInt(b.part_number)
    if (!isNaN(aNum) && !isNaN(bNum)) {
      return aNum - bNum
    }
    return a.part_number.localeCompare(b.part_number)
  })

  // Filter by search query
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    list = list.filter(p =>
      p.part_number.toLowerCase().includes(query) ||
      p.name.toLowerCase().includes(query)
    )
  }

  return list
})

const isLoading = computed(() => partsStore.loading)
const hasParts = computed(() => partsStore.parts.length > 0)

function selectPart(part: Part) {
  selectedPartId.value = part.id
  emit('select-part', part)
}

function handleCreate() {
  emit('create-new')
}

onMounted(async () => {
  await partsStore.fetchParts()
})

// Expose method for parent to set selection
defineExpose({
  setSelection(partId: number | null) {
    selectedPartId.value = partId
  }
})
</script>

<template>
  <div class="part-list-panel">
    <!-- Header -->
    <div class="list-header">
      <h3>Díly</h3>
      <button @click="handleCreate" class="btn-create">
        ➕ Nový
      </button>
    </div>

    <!-- Search Bar -->
    <input
      v-model="searchQuery"
      type="text"
      placeholder="Filtrovat díly..."
      class="search-input"
    />

    <!-- Loading State -->
    <div v-if="isLoading" class="loading-list">
      <div class="spinner"></div>
      <p>Načítám díly...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="!hasParts" class="empty-list">
      <div class="empty-icon">📦</div>
      <p>Žádné díly</p>
    </div>

    <!-- Parts List -->
    <div v-else class="parts-list">
      <div
        v-for="part in filteredParts"
        :key="part.id"
        @click="selectPart(part)"
        :class="{ active: selectedPartId === part.id }"
        class="part-item"
      >
        <span class="part-number">{{ part.part_number }}</span>
        <span class="part-name">{{ part.name }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Copy relevant styles from PartMainModule.vue LEFT PANEL section */
.part-list-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  height: 100%;
  overflow: hidden;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.list-header h3 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.btn-create {
  padding: var(--space-1) var(--space-2);
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: var(--transition-fast);
}

.btn-create:hover {
  background: var(--color-primary-hover);
}

.search-input {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--bg-input);
  color: var(--text-base);
}

.search-input:focus {
  outline: none;
  background: var(--state-focus-bg);
  border-color: var(--state-focus-border);
}

.loading-list {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-8);
  color: var(--text-secondary);
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border-default);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-list {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-8);
  color: var(--text-tertiary);
  text-align: center;
}

.empty-list .empty-icon {
  font-size: var(--text-2xl);
}

.empty-list p {
  font-size: var(--text-sm);
}

.parts-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.part-item {
  padding: var(--space-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: var(--transition-fast);
  background: var(--bg-surface);
}

.part-item:hover {
  background: var(--state-hover);
  border-color: var(--border-strong);
}

.part-item.active {
  background: var(--state-selected);
  border-color: var(--color-primary);
}

.part-item .part-number {
  display: block;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-primary);
  margin-bottom: var(--space-1);
}

.part-item .part-name {
  display: block;
  font-size: var(--text-sm);
  color: var(--text-base);
}
</style>
