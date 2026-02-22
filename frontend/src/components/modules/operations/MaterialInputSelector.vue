<template>
  <div class="space-y-2">
    <!-- STATE 1: Empty (no material, no parseResult) -->
    <div v-if="!material && !parseResult">
      <!-- Parser input row - ČERNÝ BACKGROUND -->
      <div class="flex gap-2">
        <input
          v-model="parserInput"
          type="text"
          placeholder="např. '42CrMo4 KR D80 L200' nebo 'X5CrNi18-10 HR 50x200x300'"
          class="flex-1 h-8 px-3 text-xs border rounded
                 bg-[var(--ground)] text-[var(--t1)]
                 border-[var(--b2)]
                 focus:border-[rgba(255,255,255,0.5)] focus:ring-1 focus:ring-[rgba(255,255,255,0.5)]
                 placeholder:text-[var(--t3)]"
          @keyup.enter="parseInput"
        />
        <button
          class="px-3 h-8 text-xs rounded
                 bg-[var(--surface)] text-[var(--t1)]
                 border border-[var(--b2)]
                 hover:bg-[var(--b1)]
                 disabled:opacity-50"
          :disabled="!parserInput.trim() || parsing"
          @click="parseInput"
        >
          {{ parsing ? 'Parsing...' : 'Parse' }}
        </button>
      </div>
      <p v-if="parserError" class="mt-1 text-xs text-[var(--err)]">
        {{ parserError }}
      </p>

      <!-- Manual input (collapsible) -->
      <MaterialManualInput @create="handleManualCreate" />
    </div>

    <!-- STATE 2: Preview (parseResult exists, no confirmed material) -->
    <div
      v-if="!material && parseResult"
      class="border rounded p-3 space-y-3
             bg-[var(--raised)]
             border-[rgba(255,255,255,0.5)]"
      @keyup.enter="handleConfirm"
      tabindex="0"
    >
      <div class="flex items-center gap-2">
        <span class="text-xs font-medium text-[var(--t1)]">Náhled materiálu</span>
        <span
          v-if="parseResult.match_type"
          class="px-1.5 py-0.5 text-[10px] rounded-full"
          :class="matchTypeBadgeClass(parseResult.match_type)"
        >
          {{ parseResult.match_type }}
        </span>
      </div>
      <div class="text-xs text-[var(--t3)]">
        <span class="font-medium text-[var(--t1)]">
          {{ parseResult.item_code || parseResult.w_nr || '—' }}
        </span>
        <span v-if="parseResult.item_description" class="ml-2">{{ parseResult.item_description }}</span>
        <span v-if="parseResult.shape" class="ml-2 text-[var(--t3)]">{{ parseResult.shape }}</span>
        <span v-if="formatDimensions(parseResult) !== '—'" class="ml-2 text-[var(--t3)]">
          {{ formatDimensions(parseResult) }}
        </span>
      </div>
      <div class="flex gap-2 justify-end">
        <button
          class="px-3 h-7 text-xs rounded
                 bg-[var(--surface)] text-[var(--t1)]
                 border border-[var(--b2)]
                 hover:bg-[var(--b1)]"
          @click="handleCancel"
        >
          Zrušit
        </button>
        <button
          class="px-3 h-7 text-xs rounded
                 bg-[var(--red)] text-white
                 hover:bg-[var(--red)]"
          @click="handleConfirm"
        >
          Potvrdit
        </button>
      </div>
    </div>

    <!-- STATE 3: Confirmed Material -->
    <MaterialDisplay
      v-if="material"
      :material="material"
      @remove="handleRemove"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { apiClient } from '@/api/client'
import type { ParsedMaterial } from '@/types/material'
import { formatDimensions, matchTypeBadgeClass } from './materialConstants'
import MaterialManualInput from './MaterialManualInput.vue'
import MaterialDisplay from './MaterialDisplay.vue'

const props = defineProps<{ modelValue: ParsedMaterial | null }>()
const emit = defineEmits<{ 'update:modelValue': [material: ParsedMaterial | null] }>()

const parserInput = ref('')
const parsing = ref(false)
const parserError = ref('')
const parseResult = ref<ParsedMaterial | null>(null)
const material = ref<ParsedMaterial | null>(props.modelValue ? { ...props.modelValue } : null)

watch(() => props.modelValue, (v) => { material.value = v ? { ...v } : null }, { deep: true })

async function parseInput() {
  if (!parserInput.value.trim()) return
  parsing.value = true
  parserError.value = ''
  try {
    const response = await apiClient.post('/materials/parse', { text: parserInput.value.trim() })
    if (response.data && !response.data.error) {
      parseResult.value = response.data
      parserInput.value = ''
    } else {
      parserError.value = response.data?.error || 'Nepodařilo se rozpoznat materiál'
    }
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } } }
    parserError.value = err.response?.data?.detail || 'Chyba při parsování materiálu'
  } finally { parsing.value = false }
}

function handleConfirm() {
  if (!parseResult.value) return
  material.value = { ...parseResult.value }
  parseResult.value = null
  emit('update:modelValue', material.value)
}

function handleCancel() { parseResult.value = null }

function handleManualCreate(mat: ParsedMaterial) {
  material.value = { ...mat }
  emit('update:modelValue', material.value)
}

function handleRemove() {
  material.value = null
  emit('update:modelValue', null)
}
</script>
