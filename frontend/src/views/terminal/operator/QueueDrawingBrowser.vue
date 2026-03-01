<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useSwipeNavigation } from '@/composables/useSwipeNavigation'
import type { MachinePlanItem } from '@/types/workshop'
import { apiClient } from '@/api/client'

const props = defineProps<{
  items: MachinePlanItem[]
}>()

const emit = defineEmits<{
  'go-to-job': [job: string, oper: string]
}>()

const currentIndex = ref(0)
const containerRef = ref<HTMLElement | null>(null)

// Deduplicate by article — show only first operation per DerJobItem
const uniqueItems = computed(() => {
  const seen = new Set<string>()
  return props.items.filter(item => {
    const art = item.DerJobItem
    if (!art) return true // keep items without article (will show placeholder)
    if (seen.has(art)) return false
    seen.add(art)
    return true
  })
})

// PDF file ID cache: article → { fileId, loading }
const pdfCache = ref<Map<string, { fileId: number | null; loading: boolean }>>(new Map())

const currentItem = computed(() => uniqueItems.value[currentIndex.value] ?? null)
const total = computed(() => uniqueItems.value.length)

// Resolve PDF file ID for an article
async function resolvePdf(article: string) {
  if (pdfCache.value.has(article)) return
  pdfCache.value.set(article, { fileId: null, loading: true })
  try {
    const { data } = await apiClient.get<{ files: { id: number; mime_type: string }[] }>(
      `/files/by-article/${encodeURIComponent(article)}`,
    )
    const pdf = data.files?.find(f => f.mime_type === 'application/pdf')
    pdfCache.value.set(article, { fileId: pdf?.id ?? null, loading: false })
  } catch {
    pdfCache.value.set(article, { fileId: null, loading: false })
  }
}

// Preload current + adjacent
function preloadAround(idx: number) {
  const items = uniqueItems.value
  const indices = [idx, idx - 1, idx + 1].filter(i => i >= 0 && i < items.length)
  for (const i of indices) {
    const art = items[i]?.DerJobItem
    if (art) resolvePdf(art)
  }
}

watch(currentIndex, (idx) => preloadAround(idx), { immediate: true })
watch(() => uniqueItems.value.length, () => {
  if (currentIndex.value >= uniqueItems.value.length) {
    currentIndex.value = Math.max(0, uniqueItems.value.length - 1)
  }
  preloadAround(currentIndex.value)
})

// Current PDF state
const currentPdf = computed(() => {
  const art = currentItem.value?.DerJobItem
  if (!art) return { fileId: null, loading: false }
  return pdfCache.value.get(art) ?? { fileId: null, loading: false }
})

// Navigation
function goNext() {
  if (currentIndex.value < total.value - 1) currentIndex.value++
}
function goPrev() {
  if (currentIndex.value > 0) currentIndex.value--
}

// Swipe
useSwipeNavigation(containerRef, {
  onSwipeLeft: goNext,
  onSwipeRight: goPrev,
})

// Keyboard navigation
function onKey(e: KeyboardEvent) {
  if (e.key === 'ArrowLeft') goPrev()
  else if (e.key === 'ArrowRight') goNext()
}

// Tier helpers
function tierIcon(item: MachinePlanItem): 'hot' | 'urgent' | null {
  if (item.IsHot || item.Tier === 'hot') return 'hot'
  if (item.Tier === 'urgent') return 'urgent'
  return null
}
</script>

<template>
  <div class="qdb" ref="containerRef">
    <!-- PDF area -->
    <div class="qdb-viewer" @keydown="onKey" tabindex="0">
      <!-- Loading -->
      <div v-if="currentPdf.loading" class="qdb-msg">Hledám výkres...</div>

      <!-- No article -->
      <div v-else-if="!currentItem?.DerJobItem" class="qdb-msg qdb-msg--dim">
        Bez artiklu
      </div>

      <!-- No PDF found -->
      <div v-else-if="currentPdf.fileId === null" class="qdb-msg qdb-msg--dim">
        Výkres nenalezen<br>
        <span class="qdb-msg-article">{{ currentItem.DerJobItem }}</span>
      </div>

      <!-- PDF iframe -->
      <iframe
        v-else
        :key="currentPdf.fileId"
        :src="`/api/files/${currentPdf.fileId}/preview`"
        class="qdb-pdf"
      />

      <!-- Invisible tap zones — OVER iframe, always present -->
      <div
        v-if="currentIndex > 0"
        class="qdb-tap qdb-tap--left"
        @click.stop="goPrev"
        @touchend.stop.prevent="goPrev"
      />
      <div
        v-if="currentIndex < total - 1"
        class="qdb-tap qdb-tap--right"
        @click.stop="goNext"
        @touchend.stop.prevent="goNext"
      />
    </div>

    <!-- Position indicator -->
    <div class="qdb-position">{{ currentIndex + 1 }} / {{ total }}</div>

    <!-- Info bar -->
    <div
      v-if="currentItem"
      :class="['qdb-info', {
        'qdb-info--hot': tierIcon(currentItem) === 'hot',
        'qdb-info--urgent': tierIcon(currentItem) === 'urgent',
      }]"
      @click="emit('go-to-job', currentItem.Job, currentItem.OperNum)"
    >
      <div class="qdb-info-left">
        <!-- Tier icon -->
        <span v-if="tierIcon(currentItem) === 'hot'" class="qdb-tier qdb-tier--hot">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M12 23c-3.6 0-7-2.4-7-7 0-3.3 2.3-5.8 4-7.5.5-.5 1.5-.2 1.5.5v2.2c0 .4.5.6.8.3C13.4 9.5 15 6.5 15 4c0-.7.8-1 1.3-.5C18.7 6 21 9.5 21 13c0 5.5-4 10-9 10z"/></svg>
        </span>
        <span v-else-if="tierIcon(currentItem) === 'urgent'" class="qdb-tier qdb-tier--urgent">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
        </span>

        <!-- Position -->
        <span class="qdb-pos">#{{ currentIndex + 1 }}</span>

        <!-- Article -->
        <span v-if="currentItem.DerJobItem" class="qdb-article">{{ currentItem.DerJobItem }}</span>

        <!-- Job / Op -->
        <span class="qdb-job">{{ currentItem.Job }} / Op {{ currentItem.OperNum }}</span>
      </div>

      <!-- Chevron -->
      <svg class="qdb-chevron" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="9 6 15 12 9 18"/>
      </svg>
    </div>
  </div>
</template>

<style scoped>
.qdb {
  display: flex;
  flex-direction: column;
  /* Height comes from parent flex (flex:1 on .queue-drawings) */
  min-height: 0;
  background: var(--ground, #181a1f);
  overflow: hidden;
  user-select: none;
  -webkit-user-select: none;
}

/* PDF viewer area */
.qdb-viewer {
  flex: 1;
  min-height: 0;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.qdb-pdf {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border: none;
  background: rgba(255, 255, 255, 0.95);
}

/* Invisible tap zones — overlay on top of iframe */
.qdb-tap {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 25%;
  z-index: 10;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.qdb-tap--left {
  left: 0;
}
.qdb-tap--right {
  right: 0;
}

/* Messages */
.qdb-msg {
  color: var(--t3);
  font-size: 15px;
  text-align: center;
  padding: 20px;
  z-index: 1;
}
.qdb-msg--dim {
  color: var(--t4);
}
.qdb-msg-article {
  font-size: 13px;
  color: var(--t4);
  margin-top: 4px;
  display: inline-block;
}

/* Position indicator */
.qdb-position {
  text-align: center;
  font-size: 12px;
  font-weight: 500;
  color: var(--t4);
  padding: 6px 0;
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}

/* Info bar */
.qdb-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--b2);
  background: rgba(255, 255, 255, 0.03);
  cursor: pointer;
  flex-shrink: 0;
  -webkit-tap-highlight-color: transparent;
}
.qdb-info:active {
  background: rgba(255, 255, 255, 0.06);
}
.qdb-info--hot {
  border-top: 2px solid var(--red, #ef5350);
  background: color-mix(in srgb, var(--red, #ef5350) 6%, transparent);
}
.qdb-info--urgent {
  border-top: 2px solid var(--amber, #ff9800);
}

.qdb-info-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  overflow: hidden;
}

.qdb-tier {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}
.qdb-tier--hot {
  color: var(--red, #ef5350);
  animation: pulse-hot 1.5s ease-in-out infinite;
}
.qdb-tier--urgent {
  color: var(--amber, #ff9800);
}
@keyframes pulse-hot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.qdb-pos {
  font-size: 14px;
  font-weight: 600;
  color: var(--t2);
  flex-shrink: 0;
}

.qdb-article {
  font-size: 14px;
  font-weight: 500;
  color: var(--t1);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.qdb-job {
  font-size: 13px;
  color: var(--t3);
  white-space: nowrap;
  flex-shrink: 0;
}

.qdb-chevron {
  color: var(--t4);
  flex-shrink: 0;
}
</style>
