<template>
  <button
    :class="buttonClasses"
    :disabled="disabled"
    :title="title"
    @click="$emit('click', $event)"
  >
    <component :is="icon" :size="ICON_SIZE.STANDARD" />
  </button>
</template>

<script setup lang="ts">
/**
 * IconButton - Reusable icon-only button component
 *
 * @example
 * <IconButton :icon="Plus" variant="primary" title="Add item" @click="handleAdd" />
 * <IconButton :icon="Trash2" variant="danger" title="Delete" @click="handleDelete" />
 * <IconButton :icon="Edit" title="Edit" @click="handleEdit" />
 */
import { computed, type Component } from 'vue'
import { ICON_SIZE } from '@/config/design'

interface Props {
  icon: Component
  variant?: 'default' | 'primary' | 'danger' | 'success' | 'warning'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  title?: string
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  size: 'md',
  disabled: false,
  title: ''
})

defineEmits<{
  click: [event: MouseEvent]
}>()

const buttonClasses = computed(() => [
  'icon-btn',
  props.variant !== 'default' && `icon-btn-${props.variant}`,
  props.size !== 'md' && `icon-btn-${props.size}`
])
</script>

<style scoped>
/*
 * Styles are defined globally in design-system.css
 * This component uses: .icon-btn, .icon-btn-primary, .icon-btn-danger, etc.
 */
</style>
