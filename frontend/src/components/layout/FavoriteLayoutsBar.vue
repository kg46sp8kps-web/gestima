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
  gap: 6px;
}

.favorite-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 80px;
  height: 32px;
  padding: 0 var(--pad);
  background: transparent;
  border: 1px solid var(--b2);
  border-radius: var(--r);
  color: var(--t1);
  font-size: var(--fs);
  font-weight: 500;
  cursor: pointer;
  transition: all 100ms cubic-bezier(0,0,0.2,1);
}

.favorite-btn:hover {
  background: var(--b1);
  border-color: var(--b3);
}

.favorite-btn.is-active {
  background: var(--red);
  color: white;
  border-color: var(--red);
}
</style>
