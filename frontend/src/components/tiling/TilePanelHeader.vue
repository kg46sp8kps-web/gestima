<script setup lang="ts">
import { ref, computed, nextTick, onUnmounted } from 'vue'
import { Maximize2Icon, Minimize2Icon, XIcon, PanelTopIcon, PanelLeftIcon } from 'lucide-vue-next'
import { useWorkspaceStore } from '@/stores/workspace'
import { useQuoteLayoutStore } from '@/stores/quoteLayout'
import { MODULE_REGISTRY } from '@/types/workspace'
import type { LeafNode, ContextGroup } from '@/types/workspace'
import { ICON_SIZE_SM } from '@/config/design'

interface Props {
  node: LeafNode
  maximized: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'maximize': []
  'close': []
  'drag-start': []
  'open-module-picker': []
}>()

const ws = useWorkspaceStore()
const quoteLayout = useQuoteLayoutStore()
const moduleDef = computed(() => MODULE_REGISTRY[props.node.module])

// ─── Ctx group picker ───
const pickerOpen = ref(false)

const GROUPS: ContextGroup[] = ['ca', 'cb', 'cc', 'cd']
const GROUP_LABELS: Record<ContextGroup, string> = { ca: 'A', cb: 'B', cc: 'C', cd: 'D' }
const GROUP_COLORS: Record<ContextGroup, string> = {
  ca: 'var(--la)',
  cb: 'var(--lb)',
  cc: 'var(--link-group-blue)',
  cd: 'var(--link-group-yellow)',
}

function closePicker() {
  pickerOpen.value = false
}

function openPicker() {
  pickerOpen.value = true
  // Add once-listener AFTER current click event cycle — prevents immediate self-close
  nextTick(() => {
    document.addEventListener('click', closePicker, { once: true })
  })
}

function selectCtx(ctx: ContextGroup) {
  ws.setLeafCtx(props.node.id, ctx)
  pickerOpen.value = false
}

// Safety cleanup if component unmounts while picker is open
onUnmounted(() => document.removeEventListener('click', closePicker))

// Timer handle for deferred startDrag — cleared in dragend if drag is cancelled instantly
let dragTimer: ReturnType<typeof setTimeout> | null = null

/**
 * Creates a scaled-down ghost image of the panel — matches tiling-preview-v3 exactly.
 * Ghost is placed off-screen at -9999px with z-index:99999 so the browser can render it
 * for setDragImage capture. The wrapper is physically sized (w×h), inner clone is scaled.
 */
function createDragGhost(pnl: HTMLElement): HTMLElement {
  const rect = pnl.getBoundingClientRect()
  const maxW = 200, maxH = 140
  const scale = Math.min(maxW / rect.width, maxH / rect.height, 0.45)
  const w = Math.round(rect.width * scale)
  const h = Math.round(rect.height * scale)

  const ghost = document.createElement('div')
  ghost.style.cssText = [
    'position:fixed', 'top:-9999px', 'left:-9999px', 'z-index:99999',
    `width:${w}px`, `height:${h}px`,
    'overflow:hidden', 'border-radius:6px',
    'border:1px solid rgba(229,57,53,0.3)',
    'box-shadow:0 8px 24px rgba(0,0,0,0.5)',
    'pointer-events:none',
  ].join(';')

  const inner = pnl.cloneNode(true) as HTMLElement
  inner.style.cssText = [
    `width:${rect.width}px`, `height:${rect.height}px`,
    `transform:scale(${scale})`, 'transform-origin:top left',
    'opacity:1', 'pointer-events:none',
  ].join(';')
  inner.querySelectorAll('.drop-zones').forEach(el => el.remove())
  inner.classList.add('instant')
  ghost.appendChild(inner)
  document.body.appendChild(ghost)
  return ghost
}

function onDragStart(e: DragEvent) {
  if (e.dataTransfer) {
    e.dataTransfer.setData('text/plain', props.node.id)
    e.dataTransfer.effectAllowed = 'move'
    const pnl = (e.currentTarget as HTMLElement).parentElement
    if (pnl) {
      const ghost = createDragGhost(pnl)
      e.dataTransfer.setDragImage(ghost, ghost.offsetWidth / 2, 14)
      // Defer state changes exactly like v3: setTimeout(0) ensures the drag gesture is
      // fully captured by the browser BEFORE we apply pointer-events:none to the source
      // panel and show drop zones. Without this deferral the reactive DOM update (via
      // microtask) can interfere with drag initialisation in Chrome.
      dragTimer = setTimeout(() => {
        dragTimer = null
        ws.startDrag(props.node.id, props.node.module)
        // Double rAF for ghost removal — browser needs 2 paint frames after setDragImage
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            if (ghost.parentNode) ghost.parentNode.removeChild(ghost)
          })
        })
      }, 0)
    }
  }
  emit('drag-start')
}

function onDragEnd() {
  // Cancel pending startDrag if drag was aborted before setTimeout fired
  if (dragTimer !== null) {
    clearTimeout(dragTimer)
    dragTimer = null
  }
  ws.endDrag()
}
</script>

<template>
  <div
    class="ph"
    draggable="true"
    @dragstart="onDragStart"
    @dragend="onDragEnd"
  >
    <!-- Module title — click opens ctx group picker (only for ctx-aware modules) -->
    <div class="pht" data-testid="panel-header-title" @click.stop="moduleDef.usesCtx ? openPicker() : undefined">
      <span class="ph-label">{{ moduleDef.label }}</span>
      <!-- Ctx group picker — hidden until pht is clicked -->
      <div v-if="pickerOpen" class="ph-ctx-picker" data-testid="panel-ctx-picker" @click.stop>
        <button
          v-for="g in GROUPS"
          :key="g"
          class="ph-ctx-opt"
          :class="{ active: node.ctx === g }"
          :data-testid="`panel-ctx-opt-${g}`"
          @click.stop="selectCtx(g)"
        >
          <span class="ph-ctx-swatch" :style="{ background: GROUP_COLORS[g] }" />
          Skupina {{ GROUP_LABELS[g] }}
        </button>
      </div>
    </div>

    <div class="phf" />

    <!-- Quotes: layout toggle -->
    <button
      v-if="node.module === 'quotes'"
      class="pc"
      :title="quoteLayout.getMode(node.id) === 'vertical' ? 'Přepnout na horizontální' : 'Přepnout na vertikální'"
      data-testid="quote-layout-toggle"
      @click.stop="quoteLayout.toggle(node.id)"
    >
      <PanelTopIcon v-if="quoteLayout.getMode(node.id) === 'vertical'" :size="ICON_SIZE_SM - 2" />
      <PanelLeftIcon v-else :size="ICON_SIZE_SM - 2" />
    </button>

    <!-- Controls -->
    <button
      class="pc"
      :title="maximized ? 'Obnovit' : 'Maximalizovat'"
      data-testid="panel-maximize"
      @click.stop="emit('maximize')"
    >
      <Maximize2Icon v-if="!maximized" :size="ICON_SIZE_SM - 2" />
      <Minimize2Icon v-else :size="ICON_SIZE_SM - 2" />
    </button>
    <button
      class="pc x"
      title="Zavřít panel"
      data-testid="panel-close"
      @click.stop="emit('close')"
    >
      <XIcon :size="ICON_SIZE_SM - 2" />
    </button>
  </div>
</template>

<style scoped>
.ph {
  height: 28px;
  background: rgba(255,255,255,0.025);
  border-bottom: 1px solid var(--b1);
  display: flex;
  align-items: center;
  padding: 0 var(--pad);
  gap: 4px;
  flex-shrink: 0;
  user-select: none;
  cursor: grab;
}
.ph:active { cursor: grabbing; }

.pht {
  position: relative;
  display: flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: var(--rs);
  transition: background 0.08s;
}
.pht:hover { background: var(--b1); }

.ph-label {
  font-size: var(--fsm);
  font-weight: 600;
  color: var(--t3);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  pointer-events: none;
}

.ph-ctx-picker {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  background: var(--raised);
  border: 1px solid var(--b3);
  border-radius: var(--r);
  padding: 4px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  z-index: 200;
  min-width: 120px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.5);
}
.ph-ctx-opt {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 8px;
  border-radius: var(--rs);
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: var(--fsm);
  color: var(--t2);
  font-family: var(--font);
  transition: background 0.06s;
  white-space: nowrap;
}
.ph-ctx-opt:hover { background: var(--b2); color: var(--t1); }
.ph-ctx-opt.active { background: var(--b2); font-weight: 600; color: var(--t1); }
.ph-ctx-swatch {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  flex-shrink: 0;
}

.phf { flex: 1; }

.pc {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 2px;
  color: var(--t4);
  cursor: pointer;
  transition: all 0.06s;
  font-family: var(--font);
}
.pc:hover { background: var(--b1); color: var(--t1); }
.pc.x:hover { background: rgba(248,113,113,0.12); color: var(--err); }
.pc:focus-visible { outline: 2px solid rgba(255,255,255,0.5); outline-offset: 1px; }
</style>
