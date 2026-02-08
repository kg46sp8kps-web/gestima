<script setup lang="ts">
import { computed } from 'vue'
import type { Pagination } from './DataTable.vue'

interface Props {
  pagination: Pagination
  dataLength: number
  perPageOptions?: number[]
}

const props = withDefaults(defineProps<Props>(), {
  perPageOptions: () => [10, 25, 50, 100]
})

const emit = defineEmits<{
  'page-change': [page: number]
  'per-page-change': [perPage: number]
}>()

const currentPage = computed(() => props.pagination.page)
const totalPages = computed(() =>
  Math.ceil(props.pagination.total / props.pagination.perPage)
)
const hasPreviousPage = computed(() => currentPage.value > 1)
const hasNextPage = computed(() => currentPage.value < totalPages.value)
const paginationStart = computed(() =>
  (props.pagination.page - 1) * props.pagination.perPage + 1
)
const paginationEnd = computed(() =>
  Math.min(
    props.pagination.page * props.pagination.perPage,
    props.pagination.total
  )
)

function goToPage(page: number) {
  if (page >= 1 && page <= totalPages.value) {
    emit('page-change', page)
  }
}

function handlePerPageChange(event: Event) {
  const target = event.target as HTMLSelectElement
  emit('per-page-change', parseInt(target.value, 10))
}
</script>

<template>
  <div v-if="dataLength > 0" class="data-table-pagination">
    <div class="pagination-info">
      Zobrazeno {{ paginationStart }}-{{ paginationEnd }} z {{ pagination.total }}
    </div>

    <div class="pagination-controls">
      <button
        class="pagination-btn"
        :disabled="!hasPreviousPage"
        @click="goToPage(currentPage - 1)"
      >
        ‹ Předchozí
      </button>

      <span class="pagination-current">
        Strana {{ currentPage }} z {{ totalPages }}
      </span>

      <button
        class="pagination-btn"
        :disabled="!hasNextPage"
        @click="goToPage(currentPage + 1)"
      >
        Další ›
      </button>
    </div>

    <div class="pagination-per-page">
      <label>
        Na stránku:
        <select :value="pagination.perPage" @change="handlePerPageChange">
          <option v-for="option in perPageOptions" :key="option" :value="option">
            {{ option }}
          </option>
        </select>
      </label>
    </div>
  </div>
</template>

<style scoped>
.data-table-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4);
  border-top: 1px solid var(--border-default);
  background: var(--bg-subtle);
  flex-wrap: wrap;
}

.pagination-info {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.pagination-btn {
  padding: var(--space-2) var(--space-4);
  background: var(--bg-raised);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  color: var(--text-primary);
  cursor: pointer;
  transition: var(--transition-fast);
}

.pagination-btn:hover:not(:disabled) {
  background: var(--state-hover);
  border-color: var(--border-strong);
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-current {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  min-width: 100px;
  text-align: center;
}

.pagination-per-page {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.pagination-per-page select {
  margin-left: var(--space-2);
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--bg-raised);
  color: var(--text-primary);
  font-size: var(--text-sm);
}

@media (max-width: 768px) {
  .data-table-pagination {
    flex-direction: column;
    gap: var(--space-3);
  }

  .pagination-info,
  .pagination-per-page {
    width: 100%;
    text-align: center;
  }
}
</style>
