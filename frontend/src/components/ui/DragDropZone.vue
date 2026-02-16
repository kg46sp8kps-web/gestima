<script setup lang="ts">
/**
 * DragDropZone - Reusable drag & drop file upload component
 *
 * Features:
 * - Drag & drop area with visual feedback
 * - Click to browse fallback
 * - File type validation (accept prop)
 * - File size validation (maxSize prop)
 * - Loading state with progress
 * - Error state with user-friendly messages
 * - Preview state (slot for custom preview)
 * - Keyboard accessible (tab to zone, enter to browse)
 *
 * Design system compliant:
 * - Uses --color-success for active state
 * - Uses --color-danger for error state
 * - Uses --space-* for padding/margins
 * - Uses --text-* for typography
 */

import { ref, computed } from 'vue'
import { AlertTriangle, FileText, Upload } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  modelValue: File | null
  accept?: string
  maxSize?: number // bytes (default 10MB)
  label?: string
  disabled?: boolean
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  accept: 'application/pdf',
  maxSize: 10 * 1024 * 1024, // 10MB
  label: 'Drag PDF here or click to browse',
  disabled: false,
  loading: false
})

const emit = defineEmits<{
  'update:modelValue': [file: File | null]
  'upload': [file: File]
  'error': [message: string]
}>()

// State
const isDragging = ref(false)
const errorMessage = ref<string | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)

// Computed
const hasFile = computed(() => props.modelValue !== null)
const fileName = computed(() => props.modelValue?.name || '')
const fileSize = computed(() => {
  if (!props.modelValue) return ''
  const kb = props.modelValue.size / 1024
  if (kb < 1024) return `${kb.toFixed(1)} KB`
  return `${(kb / 1024).toFixed(1)} MB`
})

// Validate file
function validateFile(file: File): string | null {
  // Check file type
  if (props.accept && !props.accept.includes(file.type)) {
    return `Invalid file type. Expected: ${props.accept}`
  }

  // Check file size
  if (file.size > props.maxSize) {
    const maxMB = (props.maxSize / (1024 * 1024)).toFixed(1)
    return `File too large. Maximum size: ${maxMB} MB`
  }

  return null
}

// Handle file selection
function handleFile(file: File | null) {
  if (!file) return

  errorMessage.value = null

  const error = validateFile(file)
  if (error) {
    errorMessage.value = error
    emit('error', error)
    return
  }

  emit('update:modelValue', file)
  emit('upload', file)
}

// Drag & drop handlers
function onDragEnter(e: DragEvent) {
  if (props.disabled || props.loading) return
  e.preventDefault()
  isDragging.value = true
}

function onDragOver(e: DragEvent) {
  if (props.disabled || props.loading) return
  e.preventDefault()
}

function onDragLeave(e: DragEvent) {
  if (props.disabled || props.loading) return
  e.preventDefault()
  isDragging.value = false
}

function onDrop(e: DragEvent) {
  if (props.disabled || props.loading) return
  e.preventDefault()
  isDragging.value = false

  const files = e.dataTransfer?.files
  if (files && files.length > 0 && files[0]) {
    handleFile(files[0])
  }
}

// Click to browse
function onClick() {
  if (props.disabled || props.loading) return
  fileInputRef.value?.click()
}

function onFileInput(e: Event) {
  const target = e.target as HTMLInputElement
  const files = target.files
  if (files && files.length > 0 && files[0]) {
    handleFile(files[0])
  }
  // Reset input value to allow re-upload of same file
  target.value = ''
}

// Keyboard accessibility
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault()
    onClick()
  }
}

// Remove file
function removeFile() {
  emit('update:modelValue', null)
  errorMessage.value = null
}
</script>

<template>
  <div class="drag-drop-zone">
    <!-- Drop zone -->
    <div
      class="drop-area"
      :class="{
        'is-dragging': isDragging,
        'has-file': hasFile,
        'has-error': errorMessage,
        'is-disabled': disabled,
        'is-loading': loading
      }"
      @dragenter="onDragEnter"
      @dragover="onDragOver"
      @dragleave="onDragLeave"
      @drop="onDrop"
      @click="onClick"
      @keydown="onKeydown"
      tabindex="0"
      role="button"
      :aria-label="label"
    >
      <!-- Hidden file input -->
      <input
        ref="fileInputRef"
        type="file"
        :accept="accept"
        @change="onFileInput"
        style="display: none"
      />

      <!-- Loading state -->
      <div v-if="loading" class="state-content">
        <div class="spinner"></div>
        <p class="state-label">Uploading...</p>
      </div>

      <!-- Error state -->
      <div v-else-if="errorMessage" class="state-content">
        <span class="state-icon error">
          <AlertTriangle :size="ICON_SIZE.HERO" :stroke-width="2" />
        </span>
        <p class="state-label error">{{ errorMessage }}</p>
        <button type="button" @click.stop="removeFile" class="btn-remove">
          Try again
        </button>
      </div>

      <!-- Success state (file selected) -->
      <div v-else-if="hasFile" class="state-content">
        <span class="state-icon success">
          <FileText :size="ICON_SIZE.HERO" :stroke-width="2" />
        </span>
        <p class="state-label success">{{ fileName }}</p>
        <p class="file-size">{{ fileSize }}</p>
        <button type="button" @click.stop="removeFile" class="btn-remove">
          Remove
        </button>
      </div>

      <!-- Idle state (empty) -->
      <div v-else class="state-content">
        <span class="state-icon">
          <Upload :size="ICON_SIZE.HERO" :stroke-width="2" />
        </span>
        <p class="state-label">{{ label }}</p>
        <p class="state-hint">Max size: {{ (maxSize / (1024 * 1024)).toFixed(1) }} MB</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.drag-drop-zone {
  width: 100%;
}

.drop-area {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 150px;
  padding: var(--space-6);
  border: 2px dashed var(--border-default);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  cursor: pointer;
  transition: var(--transition-normal);
}

.drop-area:hover:not(.is-disabled):not(.is-loading) {
  border-color: var(--color-success);
  background: var(--state-hover);
}

.drop-area:focus {
  outline: none;
  border-color: var(--state-focus-border);
  box-shadow: 0 0 0 3px var(--brand-subtle);
}

.drop-area.is-dragging {
  border-color: var(--color-success);
  background: var(--color-success-light);
  border-style: solid;
}

.drop-area.has-error {
  border-color: var(--color-danger);
  background: rgba(244, 63, 94, 0.05);
}

.drop-area.is-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.drop-area.is-loading {
  cursor: wait;
}

/* State content */
.state-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  text-align: center;
}

.state-icon {
  opacity: 0.8;
  display: flex;
  align-items: center;
  justify-content: center;
}

.state-icon.success {
  color: var(--color-success);
}

.state-icon.error {
  color: var(--color-danger);
}

.state-label {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-body);
}

.state-label.success {
  color: var(--color-success);
}

.state-label.error {
  color: var(--color-danger);
}

.state-hint {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.file-size {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

.btn-remove {
  margin-top: var(--space-2);
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-danger);
  background: transparent;
  border: 1px solid var(--color-danger);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: var(--transition-fast);
}

.btn-remove:hover {
  color: white;
  background: var(--color-danger);
}

/* Spinner animation */
.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid var(--border-default);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
