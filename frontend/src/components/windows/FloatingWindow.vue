<script setup lang="ts">
/**
 * FloatingWindow - Draggable, resizable window component
 * Features: Drag titlebar, resize from corners, minimize/maximize/close
 */

import { ref, computed } from 'vue'
import { useWindowsStore, type WindowState, type LinkingGroup } from '@/stores/windows'
import { useWindowContextStore } from '@/stores/windowContext'
import { Link } from 'lucide-vue-next'

interface Props {
  window: WindowState
}

const props = defineProps<Props>()
const store = useWindowsStore()
const contextStore = useWindowContextStore()

// Drag state
const isDragging = ref(false)
const dragStartX = ref(0)
const dragStartY = ref(0)
const dragStartWinX = ref(0)
const dragStartWinY = ref(0)

// Resize state
const isResizing = ref(false)
const resizeStartX = ref(0)
const resizeStartY = ref(0)
const resizeStartWidth = ref(0)
const resizeStartHeight = ref(0)

// Color dropdown state
const showColorDropdown = ref(false)

// Window style
const windowStyle = computed(() => {
  if (props.window.maximized) {
    return {
      left: '0',
      top: '56px',
      width: '100vw',
      height: 'calc(100vh - 88px)', // 56px header + 32px footer
      zIndex: props.window.zIndex
    }
  }

  return {
    left: `${props.window.x}px`,
    top: `${props.window.y}px`,
    width: `${props.window.width}px`,
    height: `${props.window.height}px`,
    zIndex: props.window.zIndex
  }
})

// Snap threshold (pixels)
const SNAP_THRESHOLD = 15

// Min window dimensions (read from CSS variable)
const getMinWidth = () => {
  const cssValue = getComputedStyle(document.documentElement)
    .getPropertyValue('--density-window-min-width')
    .trim()
  return cssValue ? parseInt(cssValue, 10) : 300
}
const MIN_HEIGHT = 200

// Drag handlers
function startDrag(event: MouseEvent) {
  if (props.window.maximized) return

  isDragging.value = true
  dragStartX.value = event.clientX
  dragStartY.value = event.clientY
  dragStartWinX.value = props.window.x
  dragStartWinY.value = props.window.y

  store.bringToFront(props.window.id)

  document.addEventListener('mousemove', onDragMove)
  document.addEventListener('mouseup', onDragEnd)
}

function onDragMove(event: MouseEvent) {
  if (!isDragging.value) return

  const deltaX = event.clientX - dragStartX.value
  const deltaY = event.clientY - dragStartY.value

  let newX = dragStartWinX.value + deltaX
  let newY = dragStartWinY.value + deltaY

  // Apply screen boundaries (prevent dragging outside)
  const headerHeight = 56  // CHANGED: Fixed header height
  const footerHeight = 32  // CHANGED: Sticky footer height
  const minX = 0
  const minY = headerHeight
  const maxX = window.innerWidth - props.window.width
  const maxY = window.innerHeight - footerHeight - props.window.height  // CHANGED: Respect footer

  newX = Math.max(minX, Math.min(newX, maxX))
  newY = Math.max(minY, Math.min(newY, maxY))

  // Apply snapping to other windows and screen edges
  const snapped = applySnapping(newX, newY, props.window.width, props.window.height)
  newX = snapped.x
  newY = snapped.y

  store.updateWindowPosition(props.window.id, newX, newY)
}

function applySnapping(x: number, y: number, width: number, height: number) {
  const snapThreshold = SNAP_THRESHOLD
  let snappedX = x
  let snappedY = y

  // Snap to screen edges
  if (Math.abs(x) < snapThreshold) snappedX = 0
  if (Math.abs(y - 56) < snapThreshold) snappedY = 56 // Header offset
  if (Math.abs(x + width - window.innerWidth) < snapThreshold) {
    snappedX = window.innerWidth - width
  }
  if (Math.abs(y + height - window.innerHeight) < snapThreshold) {
    snappedY = window.innerHeight - height
  }

  // Snap to other windows
  const otherWindows = store.windows.filter(w => w.id !== props.window.id && !w.minimized)

  for (const other of otherWindows) {
    // Snap left edge to other's right edge
    if (Math.abs(x - (other.x + other.width)) < snapThreshold) {
      snappedX = other.x + other.width
    }

    // Snap right edge to other's left edge
    if (Math.abs((x + width) - other.x) < snapThreshold) {
      snappedX = other.x - width
    }

    // Snap top edge to other's bottom edge
    if (Math.abs(y - (other.y + other.height)) < snapThreshold) {
      snappedY = other.y + other.height
    }

    // Snap bottom edge to other's top edge
    if (Math.abs((y + height) - other.y) < snapThreshold) {
      snappedY = other.y - height
    }
  }

  return { x: snappedX, y: snappedY }
}

function onDragEnd() {
  isDragging.value = false
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('mouseup', onDragEnd)
}

// Resize handlers
function startResize(event: MouseEvent) {
  if (props.window.maximized) return

  event.stopPropagation()
  isResizing.value = true
  resizeStartX.value = event.clientX
  resizeStartY.value = event.clientY
  resizeStartWidth.value = props.window.width
  resizeStartHeight.value = props.window.height

  store.bringToFront(props.window.id)

  document.addEventListener('mousemove', onResizeMove)
  document.addEventListener('mouseup', onResizeEnd)
}

function onResizeMove(event: MouseEvent) {
  if (!isResizing.value) return

  const deltaX = event.clientX - resizeStartX.value
  const deltaY = event.clientY - resizeStartY.value

  let newWidth = Math.max(getMinWidth(), resizeStartWidth.value + deltaX)
  let newHeight = Math.max(MIN_HEIGHT, resizeStartHeight.value + deltaY)

  // Apply screen boundaries (prevent resizing outside)
  const footerHeight = 32  // CHANGED: Sticky footer height
  const maxWidth = window.innerWidth - props.window.x
  const maxHeight = window.innerHeight - footerHeight - props.window.y  // CHANGED: Respect footer

  newWidth = Math.min(newWidth, maxWidth)
  newHeight = Math.min(newHeight, maxHeight)

  // Apply snapping to resize (right and bottom edges)
  const snapped = applyResizeSnapping(
    props.window.x,
    props.window.y,
    newWidth,
    newHeight
  )
  newWidth = snapped.width
  newHeight = snapped.height

  store.updateWindowSize(props.window.id, newWidth, newHeight)
}

function applyResizeSnapping(x: number, y: number, width: number, height: number) {
  const snapThreshold = SNAP_THRESHOLD
  let snappedWidth = width
  let snappedHeight = height

  // Snap right edge to screen edge
  const rightEdge = x + width
  if (Math.abs(rightEdge - window.innerWidth) < snapThreshold) {
    snappedWidth = window.innerWidth - x
  }

  // Snap bottom edge to screen edge
  const bottomEdge = y + height
  if (Math.abs(bottomEdge - window.innerHeight) < snapThreshold) {
    snappedHeight = window.innerHeight - y
  }

  // Snap to other windows
  const otherWindows = store.windows.filter(w => w.id !== props.window.id && !w.minimized)

  for (const other of otherWindows) {
    // Snap right edge to other's left edge
    if (Math.abs(rightEdge - other.x) < snapThreshold) {
      snappedWidth = other.x - x
    }

    // Snap right edge to other's right edge
    if (Math.abs(rightEdge - (other.x + other.width)) < snapThreshold) {
      snappedWidth = (other.x + other.width) - x
    }

    // Snap bottom edge to other's top edge
    if (Math.abs(bottomEdge - other.y) < snapThreshold) {
      snappedHeight = other.y - y
    }

    // Snap bottom edge to other's bottom edge
    if (Math.abs(bottomEdge - (other.y + other.height)) < snapThreshold) {
      snappedHeight = (other.y + other.height) - y
    }
  }

  return { width: snappedWidth, height: snappedHeight }
}

function onResizeEnd() {
  isResizing.value = false
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', onResizeEnd)
}

// Linking group colors (CSS classes instead of emoji)
type LinkingGroupKey = Exclude<LinkingGroup, null> | 'null'
const linkingGroupColors: Record<LinkingGroupKey, string> = {
  red: '#ef4444',
  blue: '#3b82f6',
  green: '#10b981',
  yellow: '#f59e0b',
  null: '#6b7280'
}

// Computed
const linkingGroupColor = computed(() => {
  return linkingGroupColors[props.window.linkingGroup || 'null']
})

// Window title with linked article_number
const displayTitle = computed(() => {
  if (!props.window.linkingGroup) {
    return props.window.title
  }

  // Get context for this linking group
  const context = contextStore.getContext(props.window.linkingGroup)

  if (!context.articleNumber) {
    return props.window.title
  }

  // Extract module name from title (e.g., "Operations - 10001234" -> "Operations")
  const parts = props.window.title.split(' - ')
  const moduleName = parts[0]

  return moduleName
})

// Window actions
function handleClose() {
  store.closeWindow(props.window.id)
}

function handleMinimize() {
  store.minimizeWindow(props.window.id)
}

function handleMaximize() {
  store.maximizeWindow(props.window.id)
}

function handleFocus() {
  store.bringToFront(props.window.id)
}

function toggleColorDropdown() {
  showColorDropdown.value = !showColorDropdown.value
}

function setLinkingGroup(group: LinkingGroup) {
  store.setWindowLinkingGroup(props.window.id, group)
  showColorDropdown.value = false
}

// Color options with hex colors
const colorOptions = [
  { value: 'red' as LinkingGroup, color: '#ef4444', label: 'Red' },
  { value: 'blue' as LinkingGroup, color: '#3b82f6', label: 'Blue' },
  { value: 'green' as LinkingGroup, color: '#10b981', label: 'Green' },
  { value: 'yellow' as LinkingGroup, color: '#f59e0b', label: 'Yellow' },
  { value: null as LinkingGroup, color: '#6b7280', label: 'Unlinked' }
]
</script>

<template>
  <div
    class="floating-window"
    :class="{
      'is-dragging': isDragging,
      'is-resizing': isResizing,
      'is-maximized': window.maximized
    }"
    :style="windowStyle"
    @mousedown="handleFocus"
  >
    <!-- Titlebar -->
    <div class="window-titlebar" @mousedown="startDrag">
      <div class="window-title-row">
        <!-- Color dropdown on dot -->
        <div class="color-dropdown-wrapper">
          <button
            class="linking-dot clickable"
            @click.stop="toggleColorDropdown"
            title="Click to change linking group"
          >
            <span class="color-dot" :style="{ backgroundColor: linkingGroupColor }"></span>
          </button>
          <Transition name="dropdown-fade">
            <div v-if="showColorDropdown" class="color-dropdown" @click.stop>
              <button
                v-for="opt in colorOptions"
                :key="opt.value || 'none'"
                class="color-option"
                :class="{ 'is-active': window.linkingGroup === opt.value }"
                @click="setLinkingGroup(opt.value)"
              >
                <span class="color-dot" :style="{ backgroundColor: opt.color }"></span>
                <span class="option-label">{{ opt.label }}</span>
              </button>
            </div>
          </Transition>
        </div>
        <span class="window-title">
          {{ displayTitle }}
          <span v-if="window.linkingGroup && contextStore.getContext(window.linkingGroup).articleNumber" class="linked-part">
            (<Link :size="12" :stroke-width="2" class="link-icon-inline" />
            {{ contextStore.getContext(window.linkingGroup).articleNumber }})
          </span>
        </span>
      </div>
      <div class="window-controls">
        <button class="btn-control btn-minimize" @click.stop="handleMinimize" title="Minimize">
          −
        </button>
        <button class="btn-control btn-maximize" @click.stop="handleMaximize" title="Maximize">
          {{ window.maximized ? '⤢' : '□' }}
        </button>
        <button class="btn-control btn-close" @click.stop="handleClose" title="Close">
          ×
        </button>
      </div>
    </div>

    <!-- Content -->
    <div class="window-content">
      <slot></slot>
    </div>

    <!-- Resize handle (bottom-right corner) -->
    <div
      v-if="!window.maximized"
      class="resize-handle"
      @mousedown="startResize"
    ></div>
  </div>
</template>

<style scoped>
.floating-window {
  position: fixed;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: box-shadow var(--duration-normal) var(--ease-out);
}

.floating-window:hover {
  box-shadow: var(--shadow-xl);
}

.floating-window.is-maximized {
  border-radius: 0;
}

.floating-window.is-dragging,
.floating-window.is-resizing {
  user-select: none;
  transition: none;
}

/* Titlebar */
.window-titlebar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  cursor: move;
  user-select: none;
  backdrop-filter: blur(8px);
}

.is-maximized .window-titlebar {
  cursor: default;
}

.window-title-row {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  flex: 1;
  min-width: 0;
}

.color-dropdown-wrapper {
  position: relative;
}

.linking-dot {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.linking-dot.clickable {
  cursor: pointer;
  padding: var(--space-1);
  border: none;
  background: transparent;
  border-radius: var(--radius-sm);
  transition: background var(--duration-fast) var(--ease-out);
}

.linking-dot.clickable:hover {
  background: var(--state-hover);
}

.color-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 1px solid rgba(0, 0, 0, 0.2);
}

/* Color Dropdown */
.color-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  min-width: 120px;
  background: var(--bg-surface, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  padding: var(--space-1);
  z-index: 10000;
}

.color-option {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  border: none;
  background: transparent;
  color: var(--text-primary);
  font-size: var(--text-base);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out);
  width: 100%;
  text-align: left;
}

.color-option:hover {
  background: var(--bg-primary, #f3f4f6);
}

.color-option.is-active {
  background: var(--accent-subtle, #fee2e2);
  font-weight: 500;
}

.option-label {
  flex: 1;
}

/* Dropdown Transition */
.dropdown-fade-enter-active,
.dropdown-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.dropdown-fade-enter-from,
.dropdown-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.window-title {
  font-weight: 600;
  font-size: var(--text-base);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.linked-part {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
}

.link-icon-inline {
  display: inline-block;
  vertical-align: middle;
}

.window-controls {
  display: flex;
  gap: 0.125rem;
  flex-shrink: 0;
}

.btn-control {
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  color: var(--text-primary);
  font-size: var(--text-xl);
  line-height: 1;
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast) var(--ease-out);
}

.btn-control:hover {
  background: var(--state-hover);
  transform: scale(1.1);
}

.btn-close:hover {
  background: #ef4444;
  color: white;
}

/* Content */
.window-content {
  flex: 1;
  overflow: auto;
  padding: var(--density-window-content-padding, 0.5rem);
}

/* Resize handle */
.resize-handle {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 20px;
  height: 20px;
  cursor: nwse-resize;
  background: linear-gradient(135deg, transparent 50%, var(--border-strong) 50%);
  opacity: 0.3;
  transition: opacity var(--duration-fast) var(--ease-out);
  border-bottom-right-radius: var(--radius-lg);
}

.resize-handle:hover {
  opacity: 0.7;
}

/* Scrollbar */
.window-content::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.window-content::-webkit-scrollbar-track {
  background: transparent;
}

.window-content::-webkit-scrollbar-thumb {
  background: var(--border-light);
  border-radius: 4px;
}

.window-content::-webkit-scrollbar-thumb:hover {
  background: var(--border-focus);
}
</style>
