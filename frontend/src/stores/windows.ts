/**
 * Windows Store - Floating windows management
 * Manages draggable, resizable windows with save/load views
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export type WindowModule =
  | 'part-main'
  | 'part-pricing'
  | 'part-operations'
  | 'part-material'
  | 'batch-sets'

export type LinkingGroup = 'red' | 'blue' | 'green' | 'yellow' | null

export interface WindowState {
  id: string
  module: WindowModule
  title: string
  x: number // px from left
  y: number // px from top
  width: number // px
  height: number // px
  zIndex: number
  minimized: boolean
  maximized: boolean
  linkingGroup: LinkingGroup // Color-based context linking
}

export interface SavedView {
  id: string
  name: string
  windows: WindowState[]
  favorite: boolean
  createdAt: string
  updatedAt: string
}

const STORAGE_KEY = 'gestima_windows'
let nextZIndex = 100

export const useWindowsStore = defineStore('windows', () => {
  // State
  const windows = ref<WindowState[]>([])
  const savedViews = ref<SavedView[]>([])
  const currentViewId = ref<string | null>(null)
  const defaultLayoutId = ref<string | null>(null)

  // Getters
  const openWindows = computed(() => windows.value.filter(w => !w.minimized))
  const minimizedWindows = computed(() => windows.value.filter(w => w.minimized))
  const favoriteViews = computed(() => savedViews.value.filter(v => v.favorite))

  // Actions
  function openWindow(module: WindowModule, title: string) {
    // Allow multiple windows of the same type (for comparison workflows)
    // Find free space (no overlapping)
    const defaultWidth = 800
    const defaultHeight = 600
    const position = findFreePosition(defaultWidth, defaultHeight)

    // If no free space found, auto-arrange existing windows first
    if (position.x === -1) {
      arrangeWindows('grid')
      // Try again after arranging
      const newPosition = findFreePosition(defaultWidth, defaultHeight)

      const newWindow: WindowState = {
        id: `${module}-${Date.now()}`,
        module,
        title,
        x: newPosition.x === -1 ? 50 : newPosition.x,
        y: newPosition.y === -1 ? 150 : newPosition.y,
        width: defaultWidth,
        height: defaultHeight,
        zIndex: nextZIndex++,
        minimized: false,
        maximized: false,
        linkingGroup: null
      }

      windows.value.push(newWindow)

      // Arrange all windows including the new one
      arrangeWindows('grid')
      return
    }

    const newWindow: WindowState = {
      id: `${module}-${Date.now()}`,
      module,
      title,
      x: position.x,
      y: position.y,
      width: defaultWidth,
      height: defaultHeight,
      zIndex: nextZIndex++,
      minimized: false,
      maximized: false,
      linkingGroup: null // Default: unlinked
    }

    windows.value.push(newWindow)
  }

  function setWindowLinkingGroup(id: string, group: LinkingGroup) {
    const win = windows.value.find(w => w.id === id)
    if (win) {
      win.linkingGroup = group
    }
  }

  // Find free position (no overlapping with existing windows)
  function findFreePosition(width: number, height: number) {
    const toolbarHeight = 100
    const stepX = 50
    const stepY = 50
    const maxX = window.innerWidth - width
    const maxY = window.innerHeight - height

    // Try positions in a grid pattern
    for (let y = toolbarHeight; y < maxY; y += stepY) {
      for (let x = 0; x < maxX; x += stepX) {
        // Check if this position overlaps any existing window
        const overlaps = windows.value.some(win => {
          if (win.minimized) return false

          return !(
            x + width < win.x || // New window is left of existing
            x > win.x + win.width || // New window is right of existing
            y + height < win.y || // New window is above existing
            y > win.y + win.height // New window is below existing
          )
        })

        if (!overlaps) {
          return { x, y }
        }
      }
    }

    // No free space found - return -1 to signal need for auto-arrange
    return { x: -1, y: -1 }
  }

  function closeWindow(id: string) {
    windows.value = windows.value.filter(w => w.id !== id)
  }

  function minimizeWindow(id: string) {
    const win = windows.value.find(w => w.id === id)
    if (win) win.minimized = true
  }

  function restoreWindow(id: string) {
    const win = windows.value.find(w => w.id === id)
    if (win) {
      win.minimized = false
      win.zIndex = nextZIndex++
    }
  }

  function maximizeWindow(id: string) {
    const win = windows.value.find(w => w.id === id)
    if (win) {
      win.maximized = !win.maximized
      win.zIndex = nextZIndex++
    }
  }

  function bringToFront(id: string) {
    const win = windows.value.find(w => w.id === id)
    if (win) win.zIndex = nextZIndex++
  }

  function updateWindowPosition(id: string, x: number, y: number) {
    const win = windows.value.find(w => w.id === id)
    if (win && !win.maximized) {
      win.x = x
      win.y = y
    }
  }

  function updateWindowSize(id: string, width: number, height: number) {
    const win = windows.value.find(w => w.id === id)
    if (win && !win.maximized) {
      win.width = width
      win.height = height
    }
  }

  function arrangeWindows(mode: 'grid' | 'horizontal' | 'vertical' = 'grid') {
    const openWins = openWindows.value
    if (openWins.length === 0) return

    const toolbarHeight = 100
    const containerWidth = window.innerWidth
    const containerHeight = window.innerHeight - toolbarHeight

    if (mode === 'grid') {
      // Grid layout (2x2, 2x3, etc.)
      const cols = Math.ceil(Math.sqrt(openWins.length))
      const rows = Math.ceil(openWins.length / cols)
      const winWidth = Math.floor(containerWidth / cols)
      const winHeight = Math.floor(containerHeight / rows)

      openWins.forEach((win, idx) => {
        const col = idx % cols
        const row = Math.floor(idx / cols)

        win.x = col * winWidth
        win.y = toolbarHeight + row * winHeight
        win.width = (col === cols - 1) ? containerWidth - col * winWidth : winWidth
        win.height = (row === rows - 1) ? containerHeight - row * winHeight : winHeight
        win.maximized = false
      })
    } else if (mode === 'horizontal') {
      // Horizontal split (side by side)
      const winWidth = Math.floor(containerWidth / openWins.length)

      openWins.forEach((win, idx) => {
        win.x = idx * winWidth
        win.y = toolbarHeight
        win.width = (idx === openWins.length - 1) ? containerWidth - idx * winWidth : winWidth
        win.height = containerHeight
        win.maximized = false
      })
    } else if (mode === 'vertical') {
      // Vertical split (stacked)
      const winHeight = Math.floor(containerHeight / openWins.length)

      openWins.forEach((win, idx) => {
        win.x = 0
        win.y = toolbarHeight + idx * winHeight
        win.width = containerWidth
        win.height = (idx === openWins.length - 1) ? containerHeight - idx * winHeight : winHeight
        win.maximized = false
      })
    }
  }

  function saveCurrentView(name: string) {
    const view: SavedView = {
      id: `view-${Date.now()}`,
      name,
      windows: JSON.parse(JSON.stringify(windows.value)),
      favorite: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }

    savedViews.value.push(view)
    currentViewId.value = view.id
  }

  function loadView(viewId: string) {
    const view = savedViews.value.find(v => v.id === viewId)
    if (!view) return

    // Close all windows
    windows.value = []

    // Restore windows from view
    windows.value = JSON.parse(JSON.stringify(view.windows))
    currentViewId.value = viewId

    // Reset zIndex
    nextZIndex = 100
    windows.value.forEach((win, idx) => {
      win.zIndex = 100 + idx
    })
    nextZIndex = 100 + windows.value.length
  }

  function deleteView(viewId: string) {
    savedViews.value = savedViews.value.filter(v => v.id !== viewId)
    if (currentViewId.value === viewId) {
      currentViewId.value = null
    }
  }

  function toggleFavoriteView(viewId: string) {
    const view = savedViews.value.find(v => v.id === viewId)
    if (view) {
      view.favorite = !view.favorite
      view.updatedAt = new Date().toISOString()
    }
  }

  function setDefaultLayout(viewId: string | null) {
    defaultLayoutId.value = viewId
    saveToStorage()
  }

  function closeAllWindows() {
    windows.value = []
  }

  // Persistence
  function loadFromStorage() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const data = JSON.parse(stored)
        savedViews.value = data.savedViews || []
        defaultLayoutId.value = data.defaultLayoutId || null
        // Don't restore windows on load - start clean
        // WindowsView will auto-load default layout on mount if set
      }
    } catch (error) {
      console.error('Failed to load windows from storage:', error)
    }
  }

  function saveToStorage() {
    try {
      const data = {
        savedViews: savedViews.value,
        defaultLayoutId: defaultLayoutId.value
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
    } catch (error) {
      console.warn('Failed to save windows (Safari private mode?):', error)
    }
  }

  // Auto-save on changes
  const unwatchSavedViews = ref<(() => void) | null>(null)
  if (typeof window !== 'undefined') {
    loadFromStorage()

    import('vue').then(({ watch }) => {
      unwatchSavedViews.value = watch(savedViews, saveToStorage, { deep: true })
    })
  }

  return {
    // State
    windows,
    savedViews,
    currentViewId,
    defaultLayoutId,

    // Getters
    openWindows,
    minimizedWindows,
    favoriteViews,

    // Actions
    openWindow,
    closeWindow,
    minimizeWindow,
    restoreWindow,
    maximizeWindow,
    bringToFront,
    updateWindowPosition,
    updateWindowSize,
    setWindowLinkingGroup,
    arrangeWindows,
    saveCurrentView,
    loadView,
    deleteView,
    toggleFavoriteView,
    setDefaultLayout,
    closeAllWindows
  }
})
