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
  gap: 12px;
  padding: 12px;
  border-top: 1px solid var(--b2);
  background: var(--ground);
  flex-wrap: wrap;
  container-type: inline-size;
}

.pagination-info {
  font-size: var(--fs);
  color: var(--t3);
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: var(--pad);
}

.pagination-btn {
  padding: 6px 12px;
  background: var(--raised);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  font-size: var(--fs);
  color: var(--t1);
  cursor: pointer;
  transition: all 100ms var(--ease);
}

.pagination-btn:hover:not(:disabled) {
  background: var(--b1);
  border-color: var(--b3);
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-current {
  font-size: var(--fs);
  color: var(--t3);
  min-width: 100px;
  text-align: center;
}

.pagination-per-page {
  font-size: var(--fs);
  color: var(--t3);
}

.pagination-per-page select {
  margin-left: 6px;
  padding: 4px 6px;
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  background: var(--raised);
  color: var(--t1);
  font-size: var(--fs);
}

@container (max-width: 768px) {
  .data-table-pagination {
    flex-direction: column;
    gap: var(--pad);
  }

  .pagination-info,
  .pagination-per-page {
    width: 100%;
    text-align: center;
  }
}
</style>
