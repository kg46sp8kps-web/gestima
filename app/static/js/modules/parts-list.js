/**
 * GESTIMA Parts List Module (ADR-023)
 *
 * Displays searchable list of parts. Emits partId when a part is selected.
 * Primary "source" module for workspace linking.
 *
 * API Endpoints Used:
 *   GET /api/parts/search - Search parts with pagination
 *   GET /api/parts/{part_number} - Get part detail
 *
 * Link Events Emitted:
 *   - select: { partId, partNumber, partName } - When part is clicked
 *
 * @version 1.0.0
 * @see docs/ADR/023-workspace-module-architecture.md
 */

function _partsListWorkspaceModule(config = {}) {
    return {
        // ═══════════════════════════════════════════════════════════════
        // ModuleInterface Implementation
        // ═══════════════════════════════════════════════════════════════

        ...ModuleInterface.create({
            moduleType: 'parts-list',
            moduleId: config.moduleId,
            linkColor: config.linkColor
        }),

        // ═══════════════════════════════════════════════════════════════
        // Module State
        // ═══════════════════════════════════════════════════════════════

        // Data
        parts: [],
        totalParts: 0,
        selectedPartId: null,
        selectedPart: null,

        // Search & Pagination
        search: '',
        skip: 0,
        limit: 20,

        // UI State
        loading: false,
        error: null,

        // Debounce
        _searchTimeout: null,

        // ═══════════════════════════════════════════════════════════════
        // Lifecycle
        // ═══════════════════════════════════════════════════════════════

        async init() {
            console.debug(`[parts-list] Initializing module ${this.moduleId}`);

            // Subscribe to link if configured
            if (this.linkColor && window.LinkManager) {
                LinkManager.subscribe(this.linkColor, this);

                // Check existing context
                const ctx = LinkManager.getContext(this.linkColor);
                if (ctx.partId) {
                    this.selectedPartId = ctx.partId;
                }
            }

            // Load initial data
            await this.loadParts();
        },

        destroy() {
            console.debug(`[parts-list] Destroying module ${this.moduleId}`);

            if (this.linkColor && window.LinkManager) {
                LinkManager.unsubscribe(this.linkColor, this);
            }

            if (this._searchTimeout) {
                clearTimeout(this._searchTimeout);
            }
        },

        // ═══════════════════════════════════════════════════════════════
        // Link Communication
        // ═══════════════════════════════════════════════════════════════

        onLinkChange(context) {
            this.linkContext = context;

            // If another module selected a part, highlight it
            if (context.partId && context.partId !== this.selectedPartId) {
                this.selectedPartId = context.partId;
                // Optionally scroll to part or reload if needed
            }
        },

        emitPartSelected(part) {
            if (!this.linkColor || !window.LinkManager) return;

            LinkManager.emit(this.linkColor, {
                source: this.moduleId,
                type: 'select',
                data: {
                    partId: part.id,
                    partNumber: part.part_number,
                    partName: part.name || part.part_number
                }
            });
        },

        // ═══════════════════════════════════════════════════════════════
        // Data Loading
        // ═══════════════════════════════════════════════════════════════

        async loadParts() {
            this.loading = true;
            this.error = null;

            try {
                const params = new URLSearchParams({
                    search: this.search,
                    skip: this.skip.toString(),
                    limit: this.limit.toString()
                });

                const response = await fetch(`/api/parts/search?${params}`);

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();
                this.parts = data.parts || [];
                this.totalParts = data.total || 0;

                console.debug(`[parts-list] Loaded ${this.parts.length} parts (total: ${this.totalParts})`);

            } catch (err) {
                console.error('[parts-list] Load error:', err);
                this.error = 'Chyba při načítání dílů';
                this.parts = [];
                this.totalParts = 0;
            } finally {
                this.loading = false;
            }
        },

        // ═══════════════════════════════════════════════════════════════
        // Search
        // ═══════════════════════════════════════════════════════════════

        debouncedSearch() {
            if (this._searchTimeout) {
                clearTimeout(this._searchTimeout);
            }

            this._searchTimeout = setTimeout(() => {
                this.skip = 0; // Reset pagination on new search
                this.loadParts();
            }, 300);
        },

        clearSearch() {
            this.search = '';
            this.skip = 0;
            this.loadParts();
        },

        // ═══════════════════════════════════════════════════════════════
        // Selection
        // ═══════════════════════════════════════════════════════════════

        selectPart(part) {
            this.selectedPartId = part.id;
            this.selectedPart = part;

            // Emit to linked modules
            this.emitPartSelected(part);

            console.debug(`[parts-list] Selected part: ${part.part_number} (ID: ${part.id})`);
        },

        isSelected(partId) {
            return this.selectedPartId === partId;
        },

        // ═══════════════════════════════════════════════════════════════
        // Pagination
        // ═══════════════════════════════════════════════════════════════

        get hasMore() {
            return this.skip + this.parts.length < this.totalParts;
        },

        get hasPrevious() {
            return this.skip > 0;
        },

        nextPage() {
            if (this.hasMore) {
                this.skip += this.limit;
                this.loadParts();
            }
        },

        prevPage() {
            if (this.hasPrevious) {
                this.skip = Math.max(0, this.skip - this.limit);
                this.loadParts();
            }
        },

        get currentPage() {
            return Math.floor(this.skip / this.limit) + 1;
        },

        get totalPages() {
            return Math.ceil(this.totalParts / this.limit);
        },

        // ═══════════════════════════════════════════════════════════════
        // Navigation
        // ═══════════════════════════════════════════════════════════════

        openPartEdit(part) {
            window.location.href = `/parts/${part.part_number}/edit`;
        },

        // ═══════════════════════════════════════════════════════════════
        // Helpers
        // ═══════════════════════════════════════════════════════════════

        formatDate(dateStr) {
            if (!dateStr) return '-';
            const date = new Date(dateStr);
            return date.toLocaleDateString('cs-CZ', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric'
            });
        },

        _showToast(message, type = 'info') {
            if (window.showToast) {
                window.showToast(message, type);
            }
        }
    };
}

// ═══════════════════════════════════════════════════════════════════════════
// Register in ModuleRegistry
// ═══════════════════════════════════════════════════════════════════════════

if (window.ModuleRegistry) {
    ModuleRegistry.register('parts-list', _partsListWorkspaceModule, {
        icon: '📋',
        description: 'Seznam dílů',
        category: 'parts',
        emits: ['partId', 'partNumber'],
        consumes: []
    });
}

window.partsListWorkspaceModule = _partsListWorkspaceModule;
