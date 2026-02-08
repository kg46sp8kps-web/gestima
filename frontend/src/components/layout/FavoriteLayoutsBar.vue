<script setup lang="ts">
import Tooltip from '@/components/ui/Tooltip.vue'

interface Layout {
  id: string
  name: string
}

interface Props {
  layouts: Layout[]
  activeId: string | null
}

interface Emits {
  (e: 'load', layoutId: string): void
}

defineProps<Props>()
const emit = defineEmits<Emits>()
</script>

<template>
  <div v-if="layouts.length > 0" class="favorite-layouts">
    <Tooltip
      v-for="fav in layouts"
      :key="fav.id"
      :text="fav.name"
      :delay="750"
    >
      <button
        class="favorite-btn"
        :class="{ 'is-active': activeId === fav.id }"
        @click="emit('load', fav.id)"
      >
        {{ fav.name }}
      </button>
    </Tooltip>
  </div>
</template>

<style scoped>
.favorite-layouts {
  display: flex;
  gap: var(--space-2);
}

.favorite-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 80px;
  height: 32px;
  padding: 0 var(--space-3);
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.favorite-btn:hover {
  background: var(--state-hover);
  border-color: var(--border-strong);
}

.favorite-btn.is-active {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}
</style>
