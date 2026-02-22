/**
 * Workspace Store — Tiling Layout State Management
 *
 * Replaces windows.ts store for the new tiling-based UI.
 * Manages workspace switching, layout presets, and saved views.
 */

import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import type {
  WorkspaceType,
  LayoutPreset,
  SavedWorkspaceView,
  PartDetailTab,
  PanelState,
  PresetConfig,
  TileModuleId,
} from '@/types/workspace'

const STORAGE_KEY = 'gestima_workspace'

export const useWorkspaceStore = defineStore('workspace', () => {
  // State
  const activeWorkspace = ref<WorkspaceType>('part')
  const layoutPreset = ref<LayoutPreset>('standard')
  const activePartTab = ref<PartDetailTab>('operations')
  const listPanelWidth = ref(320)
  const savedViews = ref<SavedWorkspaceView[]>([])
  const currentViewId = ref<string | null>(null)
  const defaultViewId = ref<string | null>(null)

  // Panel state for tiling system
  const panels = ref<PanelState[]>([])
  const focusedPanelId = ref<string | null>(null)

  // Preset configurations
  const PRESET_CONFIGS: Record<LayoutPreset, PresetConfig> = {
    standard: {
      panelCount: 2,
      gridTemplateColumns: '230px 1fr',
      gridTemplateRows: '1fr',
      panelDefaults: [
        { modules: ['parts-list'], activeModule: 'parts-list', linkingGroup: 'red' },
        { modules: ['operations', 'material', 'pricing', 'drawing', 'production', 'ai'], activeModule: 'operations', linkingGroup: 'red' },
      ],
    },
    comparison: {
      panelCount: 4,
      gridTemplateColumns: '210px 1fr 1fr 210px',
      gridTemplateRows: '1fr',
      panelDefaults: [
        { modules: ['parts-list'], activeModule: 'parts-list', linkingGroup: 'red' },
        { modules: ['operations', 'material', 'pricing', 'drawing', 'production', 'ai'], activeModule: 'operations', linkingGroup: 'red' },
        { modules: ['operations', 'material', 'pricing', 'drawing', 'production', 'ai'], activeModule: 'operations', linkingGroup: 'green' },
        { modules: ['parts-list'], activeModule: 'parts-list', linkingGroup: 'green' },
      ],
    },
    horizontal: {
      panelCount: 3,
      gridTemplateColumns: '210px 1fr',
      gridTemplateRows: '1fr 1fr',
      panelDefaults: [
        { modules: ['parts-list'], activeModule: 'parts-list', linkingGroup: 'red', gridArea: '1 / 1 / 3 / 2' },
        { modules: ['operations', 'material', 'pricing'], activeModule: 'operations', linkingGroup: 'red' },
        { modules: ['drawing', 'production', 'ai'], activeModule: 'drawing', linkingGroup: 'red' },
      ],
    },
    complete: {
      panelCount: 5,
      gridTemplateColumns: '210px 1fr 1fr',
      gridTemplateRows: '1fr 1fr',
      panelDefaults: [
        { modules: ['parts-list'], activeModule: 'parts-list', linkingGroup: 'red', gridArea: '1 / 1 / 3 / 2' },
        { modules: ['operations'], activeModule: 'operations', linkingGroup: 'red' },
        { modules: ['pricing'], activeModule: 'pricing', linkingGroup: 'red' },
        { modules: ['material', 'drawing'], activeModule: 'material', linkingGroup: 'red' },
        { modules: ['production', 'ai'], activeModule: 'production', linkingGroup: 'red' },
      ],
    },
  }

  // Getters
  const favoriteViews = computed(() => savedViews.value.filter(v => v.favorite))
  const isPartWorkspace = computed(() => activeWorkspace.value === 'part')
  const isManufacturingWorkspace = computed(() => activeWorkspace.value === 'manufacturing')
  const isFullScreenWorkspace = computed(() =>
    activeWorkspace.value === 'admin' || activeWorkspace.value === 'timevision'
  )

  // Actions
  function switchWorkspace(workspace: WorkspaceType) {
    activeWorkspace.value = workspace

    // Default tab for manufacturing workspace
    if (workspace === 'manufacturing') {
      activePartTab.value = 'production'
    } else if (workspace === 'part') {
      // Keep current tab or default to operations
      if (!activePartTab.value) {
        activePartTab.value = 'operations'
      }
    }
  }

  function setLayoutPreset(preset: LayoutPreset) {
    layoutPreset.value = preset
    initializePanelsForPreset(preset)
  }

  function setActivePartTab(tab: PartDetailTab) {
    activePartTab.value = tab
  }

  function setListPanelWidth(width: number) {
    listPanelWidth.value = Math.max(200, Math.min(600, width))
  }

  // Saved Views
  function saveCurrentView(name: string) {
    const view: SavedWorkspaceView = {
      id: `view-${Date.now()}`,
      name,
      workspace: activeWorkspace.value,
      layoutPreset: layoutPreset.value,
      listPanelWidth: listPanelWidth.value,
      favorite: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }
    savedViews.value.push(view)
    currentViewId.value = view.id
    return view.id
  }

  function updateActiveView(): boolean {
    if (!currentViewId.value) return false
    const view = savedViews.value.find(v => v.id === currentViewId.value)
    if (!view) return false

    view.workspace = activeWorkspace.value
    view.layoutPreset = layoutPreset.value
    view.listPanelWidth = listPanelWidth.value
    view.updatedAt = new Date().toISOString()
    return true
  }

  function loadView(viewId: string) {
    const view = savedViews.value.find(v => v.id === viewId)
    if (!view) return

    activeWorkspace.value = view.workspace
    layoutPreset.value = view.layoutPreset
    listPanelWidth.value = view.listPanelWidth
    currentViewId.value = viewId
  }

  function deleteView(viewId: string) {
    savedViews.value = savedViews.value.filter(v => v.id !== viewId)
    if (currentViewId.value === viewId) {
      currentViewId.value = null
    }
    if (defaultViewId.value === viewId) {
      defaultViewId.value = null
    }
  }

  function toggleFavoriteView(viewId: string) {
    const view = savedViews.value.find(v => v.id === viewId)
    if (view) {
      view.favorite = !view.favorite
      view.updatedAt = new Date().toISOString()
    }
  }

  function setDefaultView(viewId: string | null) {
    defaultViewId.value = viewId
    saveToStorage()
  }

  // ── Panel management ──

  function getPresetConfig(preset?: LayoutPreset): PresetConfig {
    return PRESET_CONFIGS[preset ?? layoutPreset.value]
  }

  function initializePanelsForPreset(preset?: LayoutPreset) {
    const config = getPresetConfig(preset)
    panels.value = config.panelDefaults.map((def, index) => ({
      id: `panel-${index}`,
      modules: [...def.modules],
      activeModule: def.activeModule,
      partId: null,
      partNumber: null,
      articleNumber: null,
      linkingGroup: def.linkingGroup,
    }))
    focusedPanelId.value = panels.value[0]?.id ?? null
  }

  function updatePanelPartId(
    panelId: string,
    partId: number,
    partNumber: string,
    articleNumber: string | null,
  ) {
    const panel = panels.value.find(p => p.id === panelId)
    if (!panel) return

    // Propagate to all panels with same linkingGroup
    const group = panel.linkingGroup
    for (const p of panels.value) {
      if (p.linkingGroup === group) {
        p.partId = partId
        p.partNumber = partNumber
        p.articleNumber = articleNumber
      }
    }
  }

  function setPanelActiveModule(panelId: string, moduleId: TileModuleId) {
    const panel = panels.value.find(p => p.id === panelId)
    if (panel && panel.modules.includes(moduleId)) {
      panel.activeModule = moduleId
    }
  }

  function addModuleToPanel(panelId: string, moduleId: TileModuleId) {
    const panel = panels.value.find(p => p.id === panelId)
    if (panel && !panel.modules.includes(moduleId)) {
      panel.modules.push(moduleId)
      panel.activeModule = moduleId
    }
  }

  function removeModuleFromPanel(panelId: string, moduleId: TileModuleId) {
    const panel = panels.value.find(p => p.id === panelId)
    if (!panel || panel.modules.length <= 1) return

    const index = panel.modules.indexOf(moduleId)
    if (index === -1) return

    panel.modules.splice(index, 1)
    if (panel.activeModule === moduleId && panel.modules.length > 0) {
      panel.activeModule = panel.modules[0]!
    }
  }

  function moveModuleBetweenPanels(
    fromPanelId: string,
    toPanelId: string,
    moduleId: TileModuleId,
  ) {
    const fromPanel = panels.value.find(p => p.id === fromPanelId)
    const toPanel = panels.value.find(p => p.id === toPanelId)
    if (!fromPanel || !toPanel) return
    if (fromPanel.modules.length <= 1) return // Can't remove last tab

    // Remove from source
    const index = fromPanel.modules.indexOf(moduleId)
    if (index === -1) return
    fromPanel.modules.splice(index, 1)
    if (fromPanel.activeModule === moduleId && fromPanel.modules.length > 0) {
      fromPanel.activeModule = fromPanel.modules[0]!
    }

    // Add to target
    if (!toPanel.modules.includes(moduleId)) {
      toPanel.modules.push(moduleId)
    }
    toPanel.activeModule = moduleId
  }

  function setFocusedPanel(panelId: string) {
    focusedPanelId.value = panelId
  }

  // Persistence
  function loadFromStorage() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const data = JSON.parse(stored)
        savedViews.value = data.savedViews || []
        defaultViewId.value = data.defaultViewId || null
        if (data.lastWorkspace) {
          activeWorkspace.value = data.lastWorkspace
        }
        if (data.lastLayoutPreset) {
          layoutPreset.value = data.lastLayoutPreset
        }
        if (data.listPanelWidth) {
          listPanelWidth.value = data.listPanelWidth
        }
      }

      // Migrate from old windows store format
      const oldStored = localStorage.getItem('gestima_windows')
      if (oldStored && !stored) {
        const oldData = JSON.parse(oldStored)
        if (oldData.savedViews) {
          // Convert old window-based views to workspace views
          savedViews.value = oldData.savedViews.map((v: { id: string; name: string; favorite: boolean; createdAt: string; updatedAt: string }) => ({
            id: v.id,
            name: v.name,
            workspace: 'part' as WorkspaceType,
            layoutPreset: 'standard' as LayoutPreset,
            listPanelWidth: 320,
            favorite: v.favorite,
            createdAt: v.createdAt,
            updatedAt: v.updatedAt
          }))
          defaultViewId.value = oldData.defaultLayoutId || null
          saveToStorage()
        }
      }
    } catch (error) {
      console.error('Failed to load workspace from storage:', error)
    }
  }

  function saveToStorage() {
    try {
      const data = {
        savedViews: savedViews.value,
        defaultViewId: defaultViewId.value,
        lastWorkspace: activeWorkspace.value,
        lastLayoutPreset: layoutPreset.value,
        listPanelWidth: listPanelWidth.value
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
    } catch (error) {
      console.warn('Failed to save workspace (Safari private mode?):', error)
    }
  }

  // Auto-save on changes
  if (typeof window !== 'undefined') {
    loadFromStorage()

    watch([savedViews, activeWorkspace, layoutPreset, listPanelWidth], saveToStorage, { deep: true })
  }

  return {
    // State
    activeWorkspace,
    layoutPreset,
    activePartTab,
    listPanelWidth,
    savedViews,
    currentViewId,
    defaultViewId,
    panels,
    focusedPanelId,

    // Getters
    favoriteViews,
    isPartWorkspace,
    isManufacturingWorkspace,
    isFullScreenWorkspace,

    // Actions
    switchWorkspace,
    setLayoutPreset,
    setActivePartTab,
    setListPanelWidth,
    saveCurrentView,
    updateActiveView,
    loadView,
    deleteView,
    toggleFavoriteView,
    setDefaultView,

    // Panel management
    getPresetConfig,
    initializePanelsForPreset,
    updatePanelPartId,
    setPanelActiveModule,
    addModuleToPanel,
    removeModuleFromPanel,
    moveModuleBetweenPanels,
    setFocusedPanel,
  }
})
