<script setup lang="ts">
import { ClipboardList } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
</script>

<template>
  <div class="module-placeholder">
    <h2>
      <ClipboardList :size="ICON_SIZE.LARGE" class="inline-icon" />
      Batch Sets
    </h2>
    <p>Batch Sets module will go here</p>
    <p class="hint">This is a placeholder - integrate later</p>
  </div>
</template>

<style scoped>
.module-placeholder {
  padding: 2rem;
  text-align: center;
}

.module-placeholder h2 {
  margin: 0 0 1rem 0;
  color: var(--t1);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.inline-icon {
  display: inline-block;
}

.module-placeholder p {
  margin: 0.5rem 0;
  color: var(--t3);
}

.hint {
  font-size: var(--fs);
  color: var(--t3);
  font-style: italic;
}
</style>
