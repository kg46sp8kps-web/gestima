<script setup lang="ts">
/**
 * CssDebugOverlay - Visual CSS debugging tool
 *
 * Řeší problémy:
 * - "Widget má useknutý spodek" → height overflow
 * - "Nevím kde je problém se spacingem" → visual spacing ruler
 * - "Widget se nescrolluje" → overflow detection
 *
 * Použití:
 * 1. Přidej <CssDebugOverlay /> do App.vue
 * 2. Stiskni Ctrl+Shift+D (debug mode)
 * 3. Klikni na element → zobrazí debug info
 *
 * @example
 * ```vue
 * <template>
 *   <div id="app">
 *     <RouterView />
 *     <CssDebugOverlay v-if="isDev" />
 *   </div>
 * </template>
 * ```
 */

import { ref, onMounted, onUnmounted, computed } from 'vue'

const isActive = ref(false)
const selectedElement = ref<HTMLElement | null>(null)
const debugInfo = ref<any>(null)
const mousePos = ref({ x: 0, y: 0 })

function toggleDebugMode(event: KeyboardEvent) {
  // Ctrl+Shift+D
  if (event.ctrlKey && event.shiftKey && event.key === 'D') {
    event.preventDefault()
    isActive.value = !isActive.value

    if (isActive.value) {
      document.body.classList.add('css-debug-active')
    } else {
      document.body.classList.remove('css-debug-active')
      selectedElement.value = null
    }
  }

  // Escape to exit
  if (event.key === 'Escape' && isActive.value) {
    isActive.value = false
    document.body.classList.remove('css-debug-active')
    selectedElement.value = null
  }
}

function handleClick(event: MouseEvent) {
  if (!isActive.value) return

  event.preventDefault()
  event.stopPropagation()

  const target = event.target as HTMLElement
  selectedElement.value = target

  // Gather debug info
  const computed = window.getComputedStyle(target)
  const rect = target.getBoundingClientRect()

  debugInfo.value = {
    tag: target.tagName.toLowerCase(),
    classes: Array.from(target.classList),
    dimensions: {
      width: rect.width,
      height: rect.height,
      offsetHeight: target.offsetHeight,
      scrollHeight: target.scrollHeight
    },
    computed: {
      display: computed.display,
      position: computed.position,
      overflow: computed.overflow,
      overflowY: computed.overflowY,
      height: computed.height,
      minHeight: computed.minHeight,
      maxHeight: computed.maxHeight,
      flex: computed.flex,
      flexGrow: computed.flexGrow,
      flexShrink: computed.flexShrink,
      flexBasis: computed.flexBasis,
      padding: computed.padding,
      margin: computed.margin
    },
    issues: detectIssues(target, computed)
  }
}

function detectIssues(element: HTMLElement, computed: CSSStyleDeclaration) {
  const issues: string[] = []

  // Issue 1: Useknutý obsah (overflow hidden but content overflows)
  if (element.scrollHeight > element.offsetHeight && computed.overflow === 'hidden') {
    issues.push('🔴 OVERFLOW: Content is clipped! (scrollHeight > offsetHeight)')
  }

  // Issue 2: Fixed height (anti-pattern)
  if (computed.height && !computed.height.includes('%') && !computed.height.includes('auto')) {
    issues.push(`🟡 FIXED HEIGHT: height: ${computed.height} (use height: 100% or flex: 1)`)
  }

  // Issue 3: Min-height without height
  if (computed.minHeight !== '0px' && computed.height === 'auto') {
    issues.push(`🟡 MIN-HEIGHT without height: ${computed.minHeight}`)
  }

  // Issue 4: No flex on parent
  const parent = element.parentElement
  if (parent && computed.height === '100%') {
    const parentComputed = window.getComputedStyle(parent)
    if (parentComputed.display !== 'flex' && parentComputed.height === 'auto') {
      issues.push('🔴 HEIGHT 100% but parent has no height or flex!')
    }
  }

  // Issue 5: Excessive padding
  const paddingTop = parseInt(computed.paddingTop)
  const paddingBottom = parseInt(computed.paddingBottom)
  if (paddingTop + paddingBottom > 40) {
    issues.push(`🟡 EXCESSIVE PADDING: ${paddingTop + paddingBottom}px total`)
  }

  if (issues.length === 0) {
    issues.push('✅ No obvious issues detected')
  }

  return issues
}

function handleMouseMove(event: MouseEvent) {
  if (!isActive.value) return
  mousePos.value = { x: event.clientX, y: event.clientY }
}

const elementPath = computed(() => {
  if (!selectedElement.value) return ''

  const path: string[] = []
  let el: HTMLElement | null = selectedElement.value

  while (el && el !== document.body) {
    const tag = el.tagName.toLowerCase()
    const classes = el.classList.length > 0 ? `.${Array.from(el.classList).join('.')}` : ''
    path.unshift(`${tag}${classes}`)
    el = el.parentElement
  }

  return path.join(' > ')
})

onMounted(() => {
  window.addEventListener('keydown', toggleDebugMode)
  window.addEventListener('click', handleClick, true)
  window.addEventListener('mousemove', handleMouseMove)
})

onUnmounted(() => {
  window.removeEventListener('keydown', toggleDebugMode)
  window.removeEventListener('click', handleClick, true)
  window.removeEventListener('mousemove', handleMouseMove)
  document.body.classList.remove('css-debug-active')
})
</script>

<template>
  <!-- Debug indicator -->
  <div v-if="isActive" class="debug-indicator">
    🔍 CSS Debug Mode (Esc to exit)
  </div>

  <!-- Spacing ruler (shows on hover) -->
  <div v-if="isActive" class="spacing-ruler" :style="{ left: mousePos.x + 'px', top: mousePos.y + 'px' }">
    <div class="ruler-line ruler-line--x"></div>
    <div class="ruler-line ruler-line--y"></div>
  </div>

  <!-- Debug panel -->
  <Teleport to="body">
    <div v-if="isActive && debugInfo" class="debug-panel">
      <div class="debug-panel__header">
        <h3>CSS Debug Info</h3>
        <button @click="selectedElement = null; debugInfo = null">✕</button>
      </div>

      <div class="debug-panel__content">
        <!-- Element path -->
        <div class="debug-section">
          <h4>Element Path</h4>
          <code class="debug-path">{{ elementPath }}</code>
        </div>

        <!-- Issues -->
        <div class="debug-section">
          <h4>Issues</h4>
          <ul class="debug-issues">
            <li v-for="(issue, i) in debugInfo.issues" :key="i">{{ issue }}</li>
          </ul>
        </div>

        <!-- Dimensions -->
        <div class="debug-section">
          <h4>Dimensions</h4>
          <table class="debug-table">
            <tr>
              <td>Width:</td>
              <td>{{ Math.round(debugInfo.dimensions.width) }}px</td>
            </tr>
            <tr>
              <td>Height:</td>
              <td>{{ Math.round(debugInfo.dimensions.height) }}px</td>
            </tr>
            <tr>
              <td>Offset Height:</td>
              <td>{{ debugInfo.dimensions.offsetHeight }}px</td>
            </tr>
            <tr :class="{ 'warning': debugInfo.dimensions.scrollHeight > debugInfo.dimensions.offsetHeight }">
              <td>Scroll Height:</td>
              <td>{{ debugInfo.dimensions.scrollHeight }}px</td>
            </tr>
          </table>
        </div>

        <!-- Computed styles -->
        <div class="debug-section">
          <h4>Computed Styles</h4>
          <table class="debug-table">
            <tr>
              <td>display:</td>
              <td><code>{{ debugInfo.computed.display }}</code></td>
            </tr>
            <tr>
              <td>overflow:</td>
              <td><code>{{ debugInfo.computed.overflow }}</code></td>
            </tr>
            <tr>
              <td>height:</td>
              <td><code>{{ debugInfo.computed.height }}</code></td>
            </tr>
            <tr>
              <td>flex:</td>
              <td><code>{{ debugInfo.computed.flex }}</code></td>
            </tr>
            <tr>
              <td>padding:</td>
              <td><code>{{ debugInfo.computed.padding }}</code></td>
            </tr>
          </table>
        </div>

        <!-- Quick fixes -->
        <div class="debug-section">
          <h4>Quick Fixes</h4>
          <div class="debug-fixes">
            <button @click="copyToClipboard('height: 100%; display: flex; flex-direction: column;')">
              📋 Copy fluid layout CSS
            </button>
            <button @click="copyToClipboard('overflow: auto;')">
              📋 Copy overflow fix
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style>
/* Global debug mode styles */
body.css-debug-active * {
  outline: 1px solid rgba(255, 0, 0, 0.2) !important;
}

body.css-debug-active *:hover {
  outline: 2px solid rgba(255, 0, 0, 0.6) !important;
  cursor: crosshair !important;
}
</style>

<style scoped>
.debug-indicator {
  position: fixed;
  top: 10px;
  right: 10px;
  padding: var(--space-2) var(--space-4);
  background: var(--color-danger);
  color: white;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  z-index: 999999;
  pointer-events: none;
}

.spacing-ruler {
  position: fixed;
  pointer-events: none;
  z-index: 999998;
}

.ruler-line {
  position: absolute;
  background: rgba(37, 99, 235, 0.5);
}

.ruler-line--x {
  width: 100vw;
  height: 1px;
  left: -50vw;
  top: 0;
}

.ruler-line--y {
  width: 1px;
  height: 100vh;
  left: 0;
  top: -50vh;
}

.debug-panel {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 500px;
  max-height: 80vh;
  background: var(--bg-surface);
  border: 2px solid var(--color-danger);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  z-index: 999999;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.debug-panel__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3);
  background: var(--color-danger);
  color: white;
  border-bottom: 1px solid var(--border-default);
}

.debug-panel__header h3 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: white;
}

.debug-panel__header button {
  background: transparent;
  border: none;
  color: white;
  font-size: var(--text-xl);
  cursor: pointer;
  padding: var(--space-1);
}

.debug-panel__content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4);
}

.debug-section {
  margin-bottom: var(--space-4);
}

.debug-section h4 {
  margin: 0 0 var(--space-2) 0;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.debug-path {
  display: block;
  padding: var(--space-2);
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  word-break: break-all;
  color: var(--text-body);
}

.debug-issues {
  list-style: none;
  padding: 0;
  margin: 0;
}

.debug-issues li {
  padding: var(--space-2);
  margin-bottom: var(--space-1);
  background: var(--bg-input);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
}

.debug-table {
  width: 100%;
  font-size: var(--text-xs);
  border-collapse: collapse;
}

.debug-table tr {
  border-bottom: 1px solid var(--border-default);
}

.debug-table tr.warning {
  background: rgba(217, 119, 6, 0.1);
}

.debug-table td {
  padding: var(--space-1) var(--space-2);
}

.debug-table td:first-child {
  font-weight: var(--font-medium);
  color: var(--text-secondary);
  width: 40%;
}

.debug-table code {
  font-family: var(--font-mono);
  color: var(--color-info);
}

.debug-fixes {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.debug-fixes button {
  padding: var(--space-2) var(--space-3);
  background: var(--color-info);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  cursor: pointer;
  transition: var(--transition-fast);
}

.debug-fixes button:hover {
  background: var(--color-info-hover);
}
</style>

<script lang="ts">
function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text)
  alert('Copied to clipboard: ' + text)
}
</script>
