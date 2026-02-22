<template>
  <div class="spinner-container" :class="{ inline }">
    <div class="spinner" :style="{ width: size, height: size }"></div>
    <span v-if="text" class="spinner-text">{{ text }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  size?: string
  text?: string
  inline?: boolean
}>(), {
  size: '24px',
  text: '',
  inline: false
})
</script>

<style scoped>
.spinner-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.spinner-container.inline {
  flex-direction: row;
}

.spinner {
  border: 3px solid var(--b2);
  border-top: 3px solid var(--red);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.spinner-text {
  color: var(--t3);
  font-size: 16px;
}
</style>
