<script setup lang="ts">
/**
 * QuoteFromRequestPanel - V2 Wizard Coordinator
 * 3-step flow: Upload → Review → Progress/Result
 */
import { ref, computed } from 'vue'
import { useQuotesStore } from '@/stores/quotes'
import { useWindowsStore } from '@/stores/windows'
import type { QuoteFromRequestCreateV2 } from '@/types/quote'
import QuoteRequestUploadStep from './QuoteRequestUploadStep.vue'
import type { FileWithType } from './QuoteRequestUploadStep.vue'
import QuoteRequestReviewStep from './QuoteRequestReviewStep.vue'
import QuoteRequestProgressStep from './QuoteRequestProgressStep.vue'

const quotesStore = useQuotesStore()
const windowsStore = useWindowsStore()

type WizardStep = 'upload' | 'review' | 'progress'
const step = ref<WizardStep>('upload')
const drawingFiles = ref<File[]>([])

const reviewV2 = computed(() => quotesStore.aiReviewV2)
const creationResult = computed(() => quotesStore.creationResult)
const isCreating = computed(() => quotesStore.creatingQuoteV2)
const isParsing = computed(() => quotesStore.aiParsingV2)

async function handleAnalyze(typedFiles: FileWithType[]) {
  const requestFiles = typedFiles.filter(f => f.type === 'request').map(f => f.file)
  const drawings = typedFiles.filter(f => f.type === 'drawing').map(f => f.file)
  drawingFiles.value = drawings
  try {
    await quotesStore.parseQuoteRequestV2(requestFiles, drawings)
    step.value = 'review'
  } catch {
    // Error handled in store — stay on upload step
  }
}

function handleBack() {
  quotesStore.clearAiReviewV2()
  step.value = 'upload'
}

async function handleConfirm(data: QuoteFromRequestCreateV2, files: File[]) {
  step.value = 'progress'
  try {
    await quotesStore.createQuoteFromRequestV2(data, files)
  } catch {
    // Error handled in store — stay on progress step (shows error via toast)
  }
}

function handleOpenQuote(quoteNumber: string) {
  quotesStore.clearAiReviewV2()
  windowsStore.closeWindow('quote-from-request')
  const quote = quotesStore.quotes.find(q => q.quote_number === quoteNumber)
  if (quote) {
    quotesStore.fetchQuote(quoteNumber)
  }
}
</script>

<template>
  <div class="panel">
    <!-- Step 1: Upload -->
    <div v-if="isParsing" class="loading">
      <div class="spinner"></div>
      <p>AI analyzuje PDF poptavku a vykresy...</p>
      <p class="hint">Paralelni analyza vsech vykresu. Trva 15-60 sekund.</p>
    </div>

    <QuoteRequestUploadStep
      v-if="step === 'upload' && !isParsing"
      @analyze="handleAnalyze"
    />

    <!-- Step 2: Review -->
    <QuoteRequestReviewStep
      v-if="step === 'review' && reviewV2"
      :review="reviewV2"
      :drawing-files="drawingFiles"
      @back="handleBack"
      @confirm="handleConfirm"
    />

    <!-- Step 3: Progress / Result -->
    <QuoteRequestProgressStep
      v-if="step === 'progress'"
      :loading="isCreating"
      :result="creationResult"
      @open-quote="handleOpenQuote"
    />
  </div>
</template>

<style scoped>
.panel { width: 100%; height: 100%; overflow-y: auto; padding: 12px; background: var(--base); }
.loading { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 400px; padding: 24px; gap: var(--pad); color: var(--t2); }
.loading p { margin: 0; font-size: var(--fs); }
.hint { font-size: var(--fs); color: var(--t3); }
</style>
