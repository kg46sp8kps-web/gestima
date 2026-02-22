<script setup lang="ts">
/**
 * Quotes List Module - Split-pane coordinator
 *
 * LEFT: QuoteListPanel (320px resizable)
 * RIGHT: QuoteHeader + QuoteDetailPanel
 *
 * Refactored: uses useResizeHandle composable (eliminates inline resize logic)
 */

import { ref, computed, onMounted } from 'vue'
import { useQuotesStore } from '@/stores/quotes'
import { usePartLayoutSettings } from '@/composables/usePartLayoutSettings'
import { useResizeHandle } from '@/composables/useResizeHandle'
import type { Quote, QuoteWithItems } from '@/types/quote'

import QuoteListPanel from './quotes/QuoteListPanel.vue'
import QuoteHeader from './quotes/QuoteHeader.vue'
import QuoteDetailPanel from './quotes/QuoteDetailPanel.vue'

interface Props {
  inline?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  inline: false
})

const quotesStore = useQuotesStore()
const selectedQuote = ref<QuoteWithItems | null>(null)

// Layout + resize
const { layoutMode } = usePartLayoutSettings('quotes-list')
const { size: panelSize, isDragging, startResize } = useResizeHandle({
  storageKey: 'quotesListPanelSize',
  defaultSize: 320,
  minSize: 250,
  maxSize: 600,
  vertical: true,
})

async function handleSelectQuote(quote: Quote) {
  await quotesStore.fetchQuote(quote.quote_number)
  selectedQuote.value = quotesStore.currentQuote
}

function handleQuoteUpdated() {
  quotesStore.fetchQuotes()
  if (selectedQuote.value) {
    quotesStore.fetchQuote(selectedQuote.value.quote_number)
      .then((quote) => {
        selectedQuote.value = quote
      })
  }
}

function handleQuoteDeleted() {
  selectedQuote.value = null
  quotesStore.fetchQuotes()
}

const panelStyle = computed(() => {
  const size = `${panelSize.value}px`
  return layoutMode.value === 'vertical'
    ? { width: size }
    : { height: size }
})

const resizeCursor = computed(() =>
  layoutMode.value === 'vertical' ? 'col-resize' : 'row-resize'
)

onMounted(() => {
  if (!quotesStore.loaded) {
    quotesStore.fetchQuotes()
  }
})
</script>

<template>
  <div
    class="split-layout"
    :class="`layout-${layoutMode}`"
  >
    <!-- LEFT PANEL: Quote List (resizable) -->
    <div class="left-panel" :style="panelStyle">
      <QuoteListPanel
        :selected-quote="selectedQuote"
        @select-quote="handleSelectQuote"
      />
    </div>

    <!-- RESIZE HANDLE -->
    <div
      class="resize-handle"
      :class="{ dragging: isDragging }"
      :style="{ cursor: resizeCursor }"
      @mousedown="startResize"
    ></div>

    <!-- RIGHT PANEL: Header + Detail -->
    <div class="right-panel">
      <QuoteHeader
        :quote="selectedQuote"
        @updated="handleQuoteUpdated"
        @deleted="handleQuoteDeleted"
      />
      <QuoteDetailPanel
        :quote="selectedQuote"
        @updated="handleQuoteUpdated"
        @deleted="handleQuoteDeleted"
      />
    </div>
  </div>
</template>

<style scoped>
.split-layout { display: flex; gap: 0; height: 100%; overflow: hidden; }
.layout-horizontal { flex-direction: column; }
.layout-vertical { flex-direction: row; }
.left-panel, .right-panel { min-width: 0; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
.left-panel { flex-shrink: 0; padding: var(--pad); }
.right-panel { flex: 1; overflow: hidden; }
.resize-handle { flex-shrink: 0; background: var(--b2); transition: background 100ms; position: relative; z-index: 10; }
.layout-vertical .resize-handle { width: 4px; cursor: col-resize; }
.layout-horizontal .resize-handle { height: 4px; cursor: row-resize; }
.resize-handle:hover, .resize-handle.dragging { background: var(--red); }
</style>
