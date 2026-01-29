/**
 * GESTIMA Workspace Controller (ADR-023)
 *
 * Manages multi-panel workspace layout with drag & resize support.
 * Creates module instances via ModuleRegistry and manages their lifecycle.
 *
 * Usage:
 *   <div x-data="workspaceController()" x-init="init()">
 *       <template x-for="panel in panels" :key="panel.id">
 *           <div class="workspace-panel" ...>
 *               <!-- Panel content -->
 *           </div>
 *       </template>
 *   </div>
 *
 * @version 1.0.0
 * @see docs/ADR/023-workspace-module-architecture.md
 */

function workspaceController() {
    return {
        // ═══════════════════════════════════════════════════════════════
        // State
        // ═══════════════════════════════════════════════════════════════

        panels: [],
        activeWorkspace: 'default',
        activePanelId: null,

        // Drag state
        dragging: null,
        dragOffset: { x: 0, y: 0 },

        // Resize state
        resizing: null,
        resizeStart: { x: 0, y: 0, width: 0, height: 0 },

        // UI state
        showAddModal: false,
        selectedModuleType: null,
        selectedLinkColor: null,

        // Layout storage key
        _storageKey: 'gestima_workspace_layout',

        // ═══════════════════════════════════════════════════════════════
        // Lifecycle
        // ═══════════════════════════════════════════════════════════════

        init() {
            console.debug('[Workspace] Initializing workspace controller');

            // Restore LinkManager state
            if (window.LinkManager) {
                LinkManager.restoreState();
            }

            // Load saved layout
            this.loadLayout();

            // If no panels, add a default one
            if (this.panels.length === 0) {
                // Don't add default panel - let user add what they need
            }

            // Setup global event listeners for drag/resize
            this._setupEventListeners();
        },

        _setupEventListeners() {
            // Mouse move handler for drag/resize
            document.addEventListener('mousemove', (e) => {
                if (this.dragging) {
                    this._handleDrag(e);
                }
                if (this.resizing) {
                    this._handleResize(e);
                }
            });

            // Mouse up handler to stop drag/resize
            document.addEventListener('mouseup', () => {
                if (this.dragging) {
                    this.dragging = null;
                    this.saveLayout();
                }
                if (this.resizing) {
                    this.resizing = null;
                    this.saveLayout();
                }
            });

            // Keyboard shortcuts
            document.addEventListener('keydown', (e) => {
                // Escape to close modal
                if (e.key === 'Escape' && this.showAddModal) {
                    this.closeAddModal();
                }
                // Delete to remove active panel
                if (e.key === 'Delete' && this.activePanelId && !this.showAddModal) {
                    if (confirm('Odstranit tento panel?')) {
                        this.removePanel(this.activePanelId);
                    }
                }
            });
        },

        // ═══════════════════════════════════════════════════════════════
        // Panel Management
        // ═══════════════════════════════════════════════════════════════

        /**
         * Add new panel with module
         */
        addPanel(moduleType, linkColor = null, position = {}) {
            if (!window.ModuleRegistry || !ModuleRegistry.has(moduleType)) {
                console.error(`[Workspace] Unknown module type: ${moduleType}`);
                this._showToast(`Neznámý typ modulu: ${moduleType}`, 'error');
                return null;
            }

            const moduleId = `${moduleType}-${Date.now()}`;

            // Calculate position (stack panels or use provided)
            const defaultPosition = this._getDefaultPosition();

            const panel = {
                id: moduleId,
                moduleType: moduleType,
                linkColor: linkColor,
                position: {
                    x: position.x ?? defaultPosition.x,
                    y: position.y ?? defaultPosition.y,
                    width: position.width ?? 450,
                    height: position.height ?? 400
                },
                minimized: false,
                zIndex: this._getNextZIndex()
            };

            this.panels.push(panel);
            this.activePanelId = panel.id;
            this.saveLayout();

            console.debug(`[Workspace] Added panel: ${moduleType} (${moduleId})`);
            return panel;
        },

        /**
         * Remove panel
         */
        removePanel(panelId) {
            const index = this.panels.findIndex(p => p.id === panelId);
            if (index > -1) {
                const panel = this.panels[index];

                // Module cleanup is handled by Alpine x-if removal
                this.panels.splice(index, 1);

                if (this.activePanelId === panelId) {
                    this.activePanelId = this.panels.length > 0 ? this.panels[0].id : null;
                }

                this.saveLayout();
                console.debug(`[Workspace] Removed panel: ${panelId}`);
            }
        },

        /**
         * Update panel position/size
         */
        updatePanel(panelId, updates) {
            const panel = this.panels.find(p => p.id === panelId);
            if (panel) {
                if (updates.position) {
                    Object.assign(panel.position, updates.position);
                }
                if (updates.linkColor !== undefined) {
                    panel.linkColor = updates.linkColor;
                }
                if (updates.minimized !== undefined) {
                    panel.minimized = updates.minimized;
                }
                // Don't save on every update during drag - save on mouseup
            }
        },

        /**
         * Bring panel to front
         */
        bringToFront(panelId) {
            const panel = this.panels.find(p => p.id === panelId);
            if (panel) {
                panel.zIndex = this._getNextZIndex();
                this.activePanelId = panelId;
            }
        },

        /**
         * Toggle panel minimize
         */
        toggleMinimize(panelId) {
            const panel = this.panels.find(p => p.id === panelId);
            if (panel) {
                panel.minimized = !panel.minimized;
                this.saveLayout();
            }
        },

        /**
         * Change panel's link color
         */
        changePanelLink(panelId, newColor) {
            const panel = this.panels.find(p => p.id === panelId);
            if (panel) {
                panel.linkColor = newColor;
                this.saveLayout();
                // Note: Module will need to re-subscribe when linkColor changes
                // This is handled by the module's $watch on linkColor
            }
        },

        // ═══════════════════════════════════════════════════════════════
        // Drag & Drop
        // ═══════════════════════════════════════════════════════════════

        startDrag(panel, event) {
            // Only drag from header
            if (!event.target.closest('.panel-header')) return;
            if (event.target.closest('.panel-controls')) return;

            this.dragging = panel;
            this.dragOffset = {
                x: event.clientX - panel.position.x,
                y: event.clientY - panel.position.y
            };
            this.bringToFront(panel.id);

            event.preventDefault();
        },

        _handleDrag(event) {
            if (!this.dragging) return;

            // Get container dimensions
            const container = document.querySelector('.workspace-container');
            const containerWidth = container ? container.clientWidth : window.innerWidth;

            // Calculate new position
            let newX = event.clientX - this.dragOffset.x;
            let newY = event.clientY - this.dragOffset.y;

            // Constraints:
            // - Left: x >= 0 (wall)
            // - Right: x <= containerWidth - 50px (keep 50px visible)
            // - Top: y >= 0 (wall)
            // - Bottom: UNLIMITED (container will expand)

            newX = Math.max(0, Math.min(containerWidth - 50, newX));
            newY = Math.max(0, newY);

            this.dragging.position.x = newX;
            this.dragging.position.y = newY;

            // Dynamically expand container if needed
            this._updateContainerHeight();
        },

        // ═══════════════════════════════════════════════════════════════
        // Resize
        // ═══════════════════════════════════════════════════════════════

        startResize(panel, event) {
            this.resizing = panel;
            this.resizeStart = {
                x: event.clientX,
                y: event.clientY,
                width: panel.position.width,
                height: panel.position.height
            };
            this.bringToFront(panel.id);

            event.preventDefault();
            event.stopPropagation();
        },

        _handleResize(event) {
            if (!this.resizing) return;

            const deltaX = event.clientX - this.resizeStart.x;
            const deltaY = event.clientY - this.resizeStart.y;

            // Minimum size
            const minWidth = 300;
            const minHeight = 200;

            this.resizing.position.width = Math.max(minWidth, this.resizeStart.width + deltaX);
            this.resizing.position.height = Math.max(minHeight, this.resizeStart.height + deltaY);

            // Dynamically expand container if needed
            this._updateContainerHeight();
        },

        /**
         * Dynamically update container height to fit all panels
         * Allows unlimited vertical scrolling
         */
        _updateContainerHeight() {
            if (this.panels.length === 0) return;

            // Find the lowest panel (y + height)
            let maxBottom = 0;
            this.panels.forEach(panel => {
                if (!panel.minimized) {
                    const bottom = panel.position.y + panel.position.height;
                    if (bottom > maxBottom) {
                        maxBottom = bottom;
                    }
                }
            });

            // Add 100px padding at bottom
            const requiredHeight = maxBottom + 100;

            // Update container min-height (CSS will be set to use min-height)
            const container = document.querySelector('.workspace-container');
            if (container) {
                const minHeight = Math.max(window.innerHeight - 120, requiredHeight);
                container.style.minHeight = `${minHeight}px`;
            }
        },

        // ═══════════════════════════════════════════════════════════════
        // Layout Persistence
        // ═══════════════════════════════════════════════════════════════

        saveLayout() {
            try {
                const layout = {
                    workspace: this.activeWorkspace,
                    panels: this.panels.map(p => ({
                        id: p.id,
                        moduleType: p.moduleType,
                        linkColor: p.linkColor,
                        position: { ...p.position },
                        minimized: p.minimized,
                        zIndex: p.zIndex
                    })),
                    timestamp: Date.now()
                };
                localStorage.setItem(this._storageKey, JSON.stringify(layout));
                console.debug('[Workspace] Layout saved');
            } catch (e) {
                console.warn('[Workspace] Could not save layout:', e.message);
            }
        },

        loadLayout() {
            try {
                const saved = localStorage.getItem(this._storageKey);
                if (saved) {
                    const layout = JSON.parse(saved);
                    this.activeWorkspace = layout.workspace || 'default';
                    this.panels = layout.panels || [];
                    console.debug('[Workspace] Layout loaded:', this.panels.length, 'panels');

                    // Update container height after loading panels
                    setTimeout(() => this._updateContainerHeight(), 100);
                }
            } catch (e) {
                console.warn('[Workspace] Could not load layout:', e.message);
                this.panels = [];
            }
        },

        resetLayout() {
            if (!confirm('Opravdu resetovat workspace? Všechny panely budou odstraněny.')) {
                return;
            }
            this.panels = [];
            this.activePanelId = null;
            localStorage.removeItem(this._storageKey);
            console.debug('[Workspace] Layout reset');
        },

        // ═══════════════════════════════════════════════════════════════
        // Add Module Modal
        // ═══════════════════════════════════════════════════════════════

        openAddModal() {
            this.showAddModal = true;
            this.selectedModuleType = null;
            this.selectedLinkColor = null;
        },

        closeAddModal() {
            this.showAddModal = false;
            this.selectedModuleType = null;
            this.selectedLinkColor = null;
        },

        confirmAddPanel() {
            if (!this.selectedModuleType) {
                this._showToast('Vyberte typ modulu', 'warning');
                return;
            }

            this.addPanel(this.selectedModuleType, this.selectedLinkColor);
            this.closeAddModal();
        },

        // ═══════════════════════════════════════════════════════════════
        // Helpers
        // ═══════════════════════════════════════════════════════════════

        _getDefaultPosition() {
            // Stack panels with offset
            const offset = this.panels.length * 30;
            return {
                x: 50 + offset,
                y: 50 + offset
            };
        },

        _getNextZIndex() {
            const maxZ = this.panels.reduce((max, p) => Math.max(max, p.zIndex || 0), 0);
            return maxZ + 1;
        },

        /**
         * Get available module types from registry
         */
        getAvailableModules() {
            if (window.ModuleRegistry) {
                return ModuleRegistry.listAvailable();
            }
            return [];
        },

        /**
         * Get link colors
         */
        getLinkColors() {
            if (window.LinkManager) {
                return LinkManager.COLORS;
            }
            return ['red', 'green', 'blue', 'yellow', 'purple'];
        },

        /**
         * Get color emoji
         */
        getColorEmoji(color) {
            if (window.LinkManager) {
                return LinkManager.getColorEmoji(color);
            }
            const emojis = { red: '🔴', green: '🟢', blue: '🔵', yellow: '🟡', purple: '🟣' };
            return emojis[color] || '⚪';
        },

        /**
         * Get color CSS
         */
        getColorCSS(color) {
            if (window.LinkManager) {
                return LinkManager.getColorCSS(color);
            }
            const colors = { red: '#ef4444', green: '#22c55e', blue: '#3b82f6', yellow: '#eab308', purple: '#a855f7' };
            return colors[color] || '#9ca3af';
        },

        /**
         * Get module icon
         */
        getModuleIcon(type) {
            if (window.ModuleRegistry) {
                const meta = ModuleRegistry.getMeta(type);
                return meta?.icon || '📁';
            }
            return '📁';
        },

        /**
         * Get module description
         */
        getModuleDescription(type) {
            if (window.ModuleRegistry) {
                const meta = ModuleRegistry.getMeta(type);
                return meta?.description || type;
            }
            return type;
        },

        /**
         * Show toast notification
         */
        _showToast(message, type = 'info') {
            if (window.showToast) {
                window.showToast(message, type);
            } else {
                console.log(`[${type}] ${message}`);
            }
        }
    };
}

// Export to window
window.workspaceController = workspaceController;
