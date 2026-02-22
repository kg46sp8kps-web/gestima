<script setup lang="ts">
interface Props {
  size?: 'sm' | 'md' | 'lg'
  text?: string
  inline?: boolean
}
withDefaults(defineProps<Props>(), {
  size: 'md',
  inline: false,
})
</script>

<template>
  <div :class="['spinner-wrap', `spinner-${size}`, { 'spinner-inline': inline }]">
    <svg class="spinner-svg" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
    </svg>
    <span v-if="text" class="spinner-text">{{ text }}</span>
  </div>
</template>

<style scoped>
.spinner-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--t3);
}
.spinner-inline {
  display: inline-flex;
}
.spinner-svg {
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}
.spinner-sm .spinner-svg { width: 14px; height: 14px; }
.spinner-md .spinner-svg { width: 18px; height: 18px; }
.spinner-lg .spinner-svg { width: 24px; height: 24px; }

.spinner-text {
  font-size: var(--fs);
  color: var(--t3);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
