<template>
  <div class="material-parser-input">
    <div class="parser-field">
      <Input
        v-model="parserText"
        label="Rychlý vstup materiálu"
        placeholder="Např: D20 1.4301 100mm (stiskněte Enter)"
        :disabled="disabled || parsing"
        @keyup.enter="handleParse"
      />
    </div>

    <!-- Parse result preview -->
    <div v-if="parseResult && parseResult.confidence >= 0.4" class="parse-preview">
      <div class="preview-header">
        <span class="preview-label">Rozpoznáno:</span>
        <div class="confidence-bar">
          <div
            v-for="i in 3"
            :key="i"
            class="confidence-segment"
            :class="getSegmentClass(i)"
          ></div>
        </div>
      </div>
      <div class="preview-values">
        <span v-if="parseResult.material_norm" class="preview-item">
          W.Nr. {{ parseResult.material_norm }}
        </span>
        <span v-if="parseResult.shape" class="preview-item">
          {{ formatShape(parseResult.shape) }}
        </span>
        <span v-if="parseResult.diameter" class="preview-item">
          Ø{{ parseResult.diameter }}mm
        </span>
        <span v-if="parseResult.width" class="preview-item">
          {{ parseResult.width }}mm
        </span>
        <span v-if="parseResult.height" class="preview-item">
          ×{{ parseResult.height }}mm
        </span>
        <span v-if="parseResult.length" class="preview-item">
          L{{ parseResult.length }}mm
        </span>
        <span v-if="parseResult.wall_thickness" class="preview-item">
          t{{ parseResult.wall_thickness }}mm
        </span>
      </div>
    </div>

    <!-- Low confidence warning -->
    <div v-else-if="parseResult && parseResult.confidence < 0.4" class="parse-warning">
      Nepodařilo se rozpoznat materiál. Zkuste jiný formát nebo vyplňte pole ručně.
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useMaterialsStore } from '@/stores/materials'
import { parseMaterialDescription } from '@/api/materials'
import type { MaterialParseResult, StockShape } from '@/types/material'
import Input from '@/components/ui/Input.vue'

// Debounce helper
function debounce<T extends (...args: any[]) => any>(fn: T, delay: number) {
  let timeoutId: ReturnType<typeof setTimeout> | null = null
  return function (this: any, ...args: Parameters<T>) {
    if (timeoutId) clearTimeout(timeoutId)
    timeoutId = setTimeout(() => fn.apply(this, args), delay)
  }
}

interface Props {
  disabled?: boolean
  materialStandard?: string | null
}

interface Emits {
  (e: 'parsed', result: MaterialParseResult): void
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  materialStandard: null
})

const emit = defineEmits<Emits>()

const materialsStore = useMaterialsStore()

// Local state
const parserText = ref('')
const previewResult = ref<MaterialParseResult | null>(null)  // Local preview (NOT confirmed)

// Computed
const parsing = computed(() => materialsStore.parsingMaterial)
const parseResult = computed(() => previewResult.value || materialsStore.parseResult)

const confidenceClass = computed(() => {
  if (!parseResult.value) return ''
  const confidence = parseResult.value.confidence
  if (confidence >= 0.8) return 'confidence-high'
  if (confidence >= 0.6) return 'confidence-medium'
  return 'confidence-low'
})

// Methods
async function handleParse() {
  if (!parserText.value.trim() || props.disabled) return

  // Parse and update store (confirmed action)
  await materialsStore.parseMaterial(parserText.value)
  previewResult.value = null  // Clear preview after confirmation

  // ONLY emit on Enter (confirm action)
  const result = materialsStore.parseResult
  if (result && result.confidence >= 0.4) {
    console.log('[MaterialParserInput] Emitting parsed event (Enter pressed)')
    emit('parsed', result)
  }
}

// Real-time parsing (debounced) - ONLY for LOCAL preview, does NOT touch store
const debouncedParse = debounce(async () => {
  if (!parserText.value.trim()) {
    previewResult.value = null
    return
  }
  // Parse for LOCAL preview only - call API directly, bypass store
  try {
    const result = await parseMaterialDescription(parserText.value)
    previewResult.value = result
    console.log('[MaterialParserInput] Preview only (debounced), no store update')
  } catch (error) {
    console.error('Preview parse error:', error)
    previewResult.value = null
  }
}, 500)

// Watch text changes for real-time preview (NOT confirmation)
watch(parserText, (newValue) => {
  if (!newValue || newValue.trim() === '') {
    // Clear everything when text is deleted
    previewResult.value = null
    materialsStore.clearParseResult()
  } else {
    debouncedParse()
  }
})

function formatShape(shape: StockShape): string {
  return materialsStore.formatShape(shape)
}

// Confidence segment helper
function getSegmentClass(segmentIndex: number): string {
  if (!parseResult.value) return 'segment-inactive'

  const confidence = parseResult.value.confidence
  const segmentsToFill = Math.ceil(confidence * 3) // 0-3 segments filled

  if (segmentIndex <= segmentsToFill) {
    if (confidence >= 0.8) return 'segment-high'
    if (confidence >= 0.6) return 'segment-medium'
    return 'segment-low'
  }
  return 'segment-inactive'
}

// Expose for parent
defineExpose({
  clear: () => {
    parserText.value = ''
    previewResult.value = null
    materialsStore.clearParseResult()
  }
})
</script>

<style scoped>
.material-parser-input {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

/* Parser field */
.parser-field {
  width: 100%;
}

/* Parse preview */
.parse-preview {
  padding: var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2);
}

.preview-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-body);
}

.confidence-bar {
  display: flex;
  gap: 2px;
  width: 60px;
}

.confidence-segment {
  flex: 1;
  height: 4px;
  border-radius: var(--radius-sm);
  background: var(--border-default);
  transition: all var(--transition-normal) var(--ease-out);
}

.confidence-segment.segment-low {
  background: var(--status-error);
  box-shadow: 0 0 4px var(--status-error);
}

.confidence-segment.segment-medium {
  background: var(--palette-warning);
  box-shadow: 0 0 4px var(--palette-warning);
}

.confidence-segment.segment-high {
  background: var(--palette-success);
  box-shadow: 0 0 4px var(--palette-success);
}

.confidence-segment.segment-inactive {
  background: var(--border-default);
}

.preview-values {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.preview-item {
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  font-family: var(--font-mono);
  color: var(--text-body);
}

/* Parse warning */
.parse-warning {
  padding: var(--space-3);
  background: rgba(217, 119, 6, 0.15);
  border: 1px solid var(--palette-warning);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  color: var(--text-body);
}
</style>
