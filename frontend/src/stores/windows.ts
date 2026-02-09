/**
 * Windows Store - Floating windows management
 * Manages draggable, resizable windows with save/load views
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getModuleDefaults, saveModuleDefaults } from '@/api/module-defaults'
import type { ModuleDefaults } from '@/types/module-defaults'

export type WindowModule =
  | 'part-main'
  | 'part-pricing'
  | 'part-operations'
  | 'part-technology' // Unified view: Material + Operations + Features
  | 'part-material'
  | 'part-drawing'
  | 'pdf-viewer'
  | 'manual-estimation-list' // Manual Time Estimation (ML Training Data Collection)
  | 'batch-sets'
  | 'partners-list'
  | 'quotes-list'
  | 'quote-from-request'
  | 'manufacturing-items'
  | 'material-items-list'
  | 'master-admin' // Master Admin (Infor, Material Norms, Pracoviště)
  | 'feature-recognition' // Feature Recognition Testing

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

  // Helper: Find first available linking group
  function findAvailableLinkingGroup(): LinkingGroup {
    const groups: LinkingGroup[] = ['red', 'blue', 'green', 'yellow']

    // Find first group not already used
    for (const group of groups) {
      const isUsed = windows.value.some(w => w.linkingGroup === group)
      if (!isUsed) return group
    }

    // All groups used, assign 'red' (user can change later)
    return 'red'
  }

  // Actions
  async function openWindow(module: WindowModule, title: string, linkingGroup?: LinkingGroup) {
    // Load defaults from API (with fallback)
    let defaultWidth = 800
    let defaultHeight = 600

    try {
      const defaults = await getModuleDefaults(module)
      if (defaults) {
        defaultWidth = defaults.default_width
        defaultHeight = defaults.default_height
        // TODO: Apply split positions and column widths from defaults.settings
      }
    } catch (error: unknown) {
      // 404 is expected for new modules without saved defaults - use fallback silently
      const errorObj = error as { response?: { status?: number } }
      if (errorObj?.response?.status !== 404) {
        console.warn(`Failed to load defaults for ${module}, using fallback`, error)
      }
    }

    // Allow multiple windows of the same type (for comparison workflows)
    // Find free space (no overlapping)
    const position = findFreePosition(defaultWidth, defaultHeight)

    // Auto-assign linking group if not specified (for part-main and manufacturing-items, always assign)
    const assignedGroup = linkingGroup !== undefined
      ? linkingGroup
      : (module === 'part-main' || module === 'manufacturing-items' ? findAvailableLinkingGroup() : null)

    // If no free space found, use centered position with offset
    let finalX = position.x
    let finalY = position.y

    if (position.x === -1) {
      // Center of screen with small random offset to avoid exact overlap
      const headerHeight = 56
      const offset = (windows.value.length * 30) % 100
      finalX = Math.max(0, (window.innerWidth - defaultWidth) / 2 + offset)
      finalY = Math.max(headerHeight, (window.innerHeight - defaultHeight) / 2 + offset)
    }

    const newWindow: WindowState = {
      id: `${module}-${Date.now()}`,
      module,
      title,
      x: finalX,
      y: finalY,
      width: defaultWidth,
      height: defaultHeight,
      zIndex: nextZIndex++,
      minimized: false,
      maximized: false,
      linkingGroup: assignedGroup
    }

    windows.value.push(newWindow)
    return newWindow.id
  }

  function setWindowLinkingGroup(id: string, group: LinkingGroup) {
    const win = windows.value.find(w => w.id === id)
    if (win) {
      win.linkingGroup = group
    }
  }

  // Find free position (no overlapping with existing windows)
  function findFreePosition(width: number, height: number) {
    const headerHeight = 56
    const stepX = 50
    const stepY = 50
    const maxX = window.innerWidth - width
    const maxY = window.innerHeight - height

    // Try positions in a grid pattern
    for (let y = headerHeight; y < maxY; y += stepY) {
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

  function updateWindowTitle(id: string, title: string) {
    const win = windows.value.find(w => w.id === id)
    if (win) {
      win.title = title
    }
  }

  function findWindowByModule(module: WindowModule): WindowState | undefined {
    return windows.value.find(w => w.module === module)
  }

  function arrangeWindows(mode: 'grid' | 'horizontal' | 'vertical' = 'grid') {
    const openWins = openWindows.value
    if (openWins.length === 0) return

    const headerHeight = 56
    const footerHeight = 32
    const containerWidth = window.innerWidth
    const containerHeight = window.innerHeight - headerHeight - footerHeight

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
        win.y = headerHeight + row * winHeight
        win.width = (col === cols - 1) ? containerWidth - col * winWidth : winWidth
        win.height = (row === rows - 1) ? containerHeight - row * winHeight : winHeight
        win.maximized = false
      })
    } else if (mode === 'horizontal') {
      // Horizontal split (side by side)
      const winWidth = Math.floor(containerWidth / openWins.length)

      openWins.forEach((win, idx) => {
        win.x = idx * winWidth
        win.y = headerHeight
        win.width = (idx === openWins.length - 1) ? containerWidth - idx * winWidth : winWidth
        win.height = containerHeight
        win.maximized = false
      })
    } else if (mode === 'vertical') {
      // Vertical split (stacked)
      const winHeight = Math.floor(containerHeight / openWins.length)

      openWins.forEach((win, idx) => {
        win.x = 0
        win.y = headerHeight + idx * winHeight
        win.width = containerWidth
        win.height = (idx === openWins.length - 1) ? containerHeight - idx * winHeight : winHeight
        win.maximized = false
      })
    }
  }

  function updateActiveView() {
    if (!currentViewId.value) return false

    const view = savedViews.value.find(v => v.id === currentViewId.value)
    if (!view) return false

    // Update existing view
    view.windows = JSON.parse(JSON.stringify(windows.value))
    view.updatedAt = new Date().toISOString()
    return true
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

  function saveCurrentViewAs(name: string) {
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
    return view.id
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

  // Save current window settings as module defaults
  async function saveWindowAsModuleDefaults(windowId: string) {
    const win = windows.value.find(w => w.id === windowId)
    if (!win) return

    try {
      const data = {
        module_type: win.module,
        default_width: win.width,
        default_height: win.height,
        settings: {
          // TODO: Collect split positions from SplitPane components
          // TODO: Collect column widths from table components
        }
      }

      await saveModuleDefaults(data)
      console.log(`Saved defaults for ${win.module}`)
    } catch (error) {
      console.error('Failed to save module defaults:', error)
    }
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
    updateWindowTitle,
    findWindowByModule,
    setWindowLinkingGroup,
    arrangeWindows,
    updateActiveView,
    saveCurrentView,
    saveCurrentViewAs,
    loadView,
    deleteView,
    toggleFavoriteView,
    setDefaultLayout,
    closeAllWindows,
    saveWindowAsModuleDefaults
  }
})
