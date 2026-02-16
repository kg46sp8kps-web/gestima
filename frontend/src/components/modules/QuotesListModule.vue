<script setup lang="ts">
/**
 * Quotes List Module - Split-pane coordinator
 *
 * LEFT: QuoteListPanel (320px resizable)
 * RIGHT: QuoteHeader + QuoteDetailPanel
 */

import { ref, computed, onMounted } from 'vue'
import { useQuotesStore } from '@/stores/quotes'
import { usePartLayoutSettings } from '@/composables/usePartLayoutSettings'
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

// Layout settings
const { layoutMode } = usePartLayoutSettings('quotes-list')

// Panel size state
const panelSize = ref(320)
const isDragging = ref(false)

async function handleSelectQuote(quote: Quote) {
  // Fetch full quote with items
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

// Resize handler
function startResize(event: MouseEvent) {
  event.preventDefault()
  isDragging.value = true

  const isVertical = layoutMode.value === 'vertical'
  const startPos = isVertical ? event.clientX : event.clientY
  const startSize = panelSize.value

  const handleMove = (e: MouseEvent) => {
    const currentPos = isVertical ? e.clientX : e.clientY
    const delta = currentPos - startPos
    const newSize = Math.max(250, Math.min(600, startSize + delta))
    panelSize.value = newSize
  }

  const handleUp = () => {
    isDragging.value = false
    localStorage.setItem('quotesListPanelSize', String(panelSize.value))
    document.removeEventListener('mousemove', handleMove)
    document.removeEventListener('mouseup', handleUp)
  }

  document.addEventListener('mousemove', handleMove)
  document.addEventListener('mouseup', handleUp)
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
  // Load saved panel size
  const stored = localStorage.getItem('quotesListPanelSize')
  if (stored) {
    const size = parseInt(stored, 10)
    if (!isNaN(size) && size >= 250 && size <= 600) {
      panelSize.value = size
    }
  }

  quotesStore.fetchQuotes()
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
/* === SPLIT LAYOUT === */
.split-layout {
  display: flex;
  gap: 0;
  height: 100%;
  overflow: hidden;
}

.layout-horizontal {
  flex-direction: column;
}

.layout-vertical {
  flex-direction: row;
}

/* === PANELS === */
.left-panel,
.right-panel {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.left-panel {
  flex-shrink: 0; /* KRITICKÉ: panel má fixed size */
  padding: var(--space-3);
}

.right-panel {
  flex: 1; /* KRITICKÉ: zabere zbytek prostoru */
  overflow: hidden;
}

/* === RESIZE HANDLE === */
.resize-handle {
  flex-shrink: 0;
  background: var(--border-default);
  transition: background var(--duration-fast);
  position: relative;
  z-index: 10;
}

.layout-vertical .resize-handle {
  width: 4px;
  cursor: col-resize;
}

.layout-horizontal .resize-handle {
  height: 4px;
  cursor: row-resize;
}

.resize-handle:hover,
.resize-handle.dragging {
  background: var(--color-primary);
}
</style>
