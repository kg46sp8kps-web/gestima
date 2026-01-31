<script setup lang="ts">
/**
 * FloatingWindow - Draggable, resizable window component
 * Features: Drag titlebar, resize from corners, minimize/maximize/close
 */

import { ref, computed } from 'vue'
import { useWindowsStore, type WindowState, type LinkingGroup } from '@/stores/windows'

interface Props {
  window: WindowState
}

const props = defineProps<Props>()
const store = useWindowsStore()

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
      top: '50px',
      width: '100vw',
      height: 'calc(100vh - 50px)',
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
  const toolbarHeight = 100
  const minX = 0
  const minY = toolbarHeight
  const maxX = window.innerWidth - props.window.width
  const maxY = window.innerHeight - props.window.height

  newX = Math.max(minX, Math.min(newX, maxX))
  newY = Math.max(minY, Math.min(newY, maxY))

  // Apply snapping to other windows and screen edges
  const snapped = applySnapping(newX, newY, props.window.width, props.window.height)
  newX = snapped.x
  newY = snapped.y

  // Check for collision - prevent overlapping
  if (checkCollision(newX, newY, props.window.width, props.window.height)) {
    return // Don't move if would overlap
  }

  store.updateWindowPosition(props.window.id, newX, newY)
}

// Check if position would cause collision with other windows
function checkCollision(x: number, y: number, width: number, height: number): boolean {
  const otherWindows = store.windows.filter(w => w.id !== props.window.id && !w.minimized)

  for (const other of otherWindows) {
    // Check if rectangles overlap
    const overlap = !(
      x + width <= other.x || // This window is left of other
      x >= other.x + other.width || // This window is right of other
      y + height <= other.y || // This window is above other
      y >= other.y + other.height // This window is below other
    )

    if (overlap) {
      return true // Collision detected
    }
  }

  return false // No collision
}

function applySnapping(x: number, y: number, width: number, height: number) {
  const snapThreshold = SNAP_THRESHOLD
  let snappedX = x
  let snappedY = y

  // Snap to screen edges
  if (Math.abs(x) < snapThreshold) snappedX = 0
  if (Math.abs(y - 100) < snapThreshold) snappedY = 100 // Toolbar offset
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
  const maxWidth = window.innerWidth - props.window.x
  const maxHeight = window.innerHeight - props.window.y

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

  // Check for collision - prevent overlapping during resize
  if (checkCollision(props.window.x, props.window.y, newWidth, newHeight)) {
    return // Don't resize if would overlap
  }

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

// Linking group colors
const linkingGroupColors = {
  red: '🔴',
  blue: '🔵',
  green: '🟢',
  yellow: '🟡',
  null: '⚪'
}

// Computed
const linkingGroupDot = computed(() => {
  return linkingGroupColors[props.window.linkingGroup || 'null']
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

// Color options
const colorOptions = [
  { value: 'red' as LinkingGroup, icon: '🔴', label: 'Red' },
  { value: 'blue' as LinkingGroup, icon: '🔵', label: 'Blue' },
  { value: 'green' as LinkingGroup, icon: '🟢', label: 'Green' },
  { value: 'yellow' as LinkingGroup, icon: '🟡', label: 'Yellow' },
  { value: null as LinkingGroup, icon: '⚪', label: 'Unlinked' }
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
          <span
            class="linking-dot clickable"
            @click.stop="toggleColorDropdown"
            title="Click to change linking group"
          >
            {{ linkingGroupDot }}
          </span>
          <Transition name="dropdown-fade">
            <div v-if="showColorDropdown" class="color-dropdown" @click.stop>
              <button
                v-for="opt in colorOptions"
                :key="opt.value || 'none'"
                class="color-option"
                :class="{ 'is-active': window.linkingGroup === opt.value }"
                @click="setLinkingGroup(opt.value)"
              >
                <span class="option-icon">{{ opt.icon }}</span>
                <span class="option-label">{{ opt.label }}</span>
              </button>
            </div>
          </Transition>
        </div>
        <span class="window-title">{{ window.title }}</span>
      </div>
      <div class="window-controls">
        <button class="btn-control btn-minimize" @click="handleMinimize" title="Minimize">
          −
        </button>
        <button class="btn-control btn-maximize" @click="handleMaximize" title="Maximize">
          {{ window.maximized ? '❐' : '□' }}
        </button>
        <button class="btn-control btn-close" @click="handleClose" title="Close">
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
  border-radius: 8px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: box-shadow 150ms;
}

.floating-window:hover {
  box-shadow: 0 15px 40px rgba(0, 0, 0, 0.3);
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
  padding: 0.25rem 0.5rem;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  cursor: move;
  user-select: none;
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
  font-size: 0.625rem;
  line-height: 1;
  flex-shrink: 0;
}

.linking-dot.clickable {
  cursor: pointer;
  padding: 0.125rem 0.25rem;
  border-radius: 3px;
  transition: background 150ms;
}

.linking-dot.clickable:hover {
  background: var(--bg-hover);
}

/* Color Dropdown */
.color-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  min-width: 120px;
  background: var(--bg-surface, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  padding: 0.25rem;
  z-index: 10000;
}

.color-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.5rem;
  border-radius: 4px;
  border: none;
  background: transparent;
  color: var(--text-primary);
  font-size: 0.75rem;
  cursor: pointer;
  transition: background 0.1s ease;
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

.option-icon {
  font-size: 0.875rem;
  width: 16px;
  text-align: center;
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
  font-size: 0.75rem;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
  background: var(--bg-card);
  color: var(--text-primary);
  font-size: 0.875rem;
  line-height: 1;
  border-radius: 3px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 150ms;
}

.btn-control:hover {
  background: var(--bg-hover);
  transform: scale(1.05);
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
  background: linear-gradient(135deg, transparent 50%, var(--border-color) 50%);
  opacity: 0.5;
  transition: opacity 150ms;
}

.resize-handle:hover {
  opacity: 1;
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
