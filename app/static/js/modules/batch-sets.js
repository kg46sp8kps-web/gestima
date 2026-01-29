/**
 * GESTIMA Batch Sets Module (ADR-022 + ADR-023)
 *
 * Module for managing BatchSets - groups of price calculation batches.
 * Implements ModuleInterface for workspace compatibility.
 *
 * API Endpoints (pricing_router.py):
 *   GET    /api/pricing/batch-sets                     - List all sets
 *   GET    /api/pricing/part/{id}/batch-sets           - List sets for part
 *   GET    /api/pricing/batch-sets/{id}                - Get set with batches
 *   POST   /api/pricing/batch-sets                     - Create new set
 *   PUT    /api/pricing/batch-sets/{id}                - Update name
 *   DELETE /api/pricing/batch-sets/{id}                - Soft delete
 *   POST   /api/pricing/batch-sets/{id}/freeze         - Freeze set
 *   POST   /api/pricing/batch-sets/{id}/recalculate    - Recalculate prices
 *   POST   /api/pricing/batch-sets/{id}/clone          - Clone set
 *   POST   /api/pricing/batch-sets/{id}/batches        - Add batch
 *   DELETE /api/pricing/batch-sets/{id}/batches/{bid}  - Remove batch
 *
 * Usage (standalone via ModuleRegistry):
 *   <div x-data="ModuleRegistry.create('batch-sets', { partId: 123 })">...</div>
 *
 * Usage (linked in workspace):
 *   <div x-data="ModuleRegistry.create('batch-sets', { linkColor: 'red' })">...</div>
 *
 * Usage (direct):
 *   <div x-data="batchSetsWorkspaceModule({ partId: 123 })">...</div>
 *
 * @version 1.0.0
 * @see docs/ADR/022-batch-set-model.md
 * @see docs/ADR/023-workspace-module-architecture.md
 */

function _batchSetsWorkspaceModule(config = {}) {
    return {
        // ═══════════════════════════════════════════════════════════════
        // ModuleInterface Implementation
        // ═══════════════════════════════════════════════════════════════

        ...ModuleInterface.create({
            moduleType: 'batch-sets',
            moduleId: config.moduleId,
            linkColor: config.linkColor
        }),

        // ═══════════════════════════════════════════════════════════════
        // Module State
        // ═══════════════════════════════════════════════════════════════

        // Context
        partId: config.partId || null,
        partNumber: config.partNumber || null,

        // Data
        batchSets: [],
        selectedSetId: null,
        batches: [],

        // UI State
        loading: false,
        error: null,
        newBatchQty: null,

        // Filter
        statusFilter: null,  // null = all, 'draft', 'frozen'

        // ═══════════════════════════════════════════════════════════════
        // Computed Properties
        // ═══════════════════════════════════════════════════════════════

        /**
         * Get currently selected batch set
         */
        get selectedSet() {
            if (this.selectedSetId) {
                return this.batchSets.find(s => s.id === this.selectedSetId);
            }
            // Default: draft set or latest frozen
            return this.batchSets.find(s => s.status === 'draft') ||
                   this.batchSets
                       .filter(s => s.status === 'frozen')
                       .sort((a, b) => new Date(b.frozen_at) - new Date(a.frozen_at))[0] ||
                   null;
        },

        /**
         * Check if current set is frozen
         */
        get isSetFrozen() {
            return this.selectedSet?.status === 'frozen';
        },

        /**
         * Check if we have a draft set
         */
        get hasDraftSet() {
            return this.batchSets.some(s => s.status === 'draft');
        },

        /**
         * Filtered batch sets by status
         */
        get filteredBatchSets() {
            if (!this.statusFilter) {
                return this.batchSets;
            }
            return this.batchSets.filter(s => s.status === this.statusFilter);
        },

        /**
         * Total value of all batches in selected set
         */
        get totalValue() {
            return this.batches.reduce((sum, b) => sum + (b.total_cost || 0), 0);
        },

        /**
         * Total quantity across all batches
         */
        get totalQuantity() {
            return this.batches.reduce((sum, b) => sum + (b.quantity || 0), 0);
        },

        // ═══════════════════════════════════════════════════════════════
        // Lifecycle
        // ═══════════════════════════════════════════════════════════════

        /**
         * Initialize module
         */
        async init() {
            console.debug(`[batch-sets] Init module ${this.moduleId}`);

            // Subscribe to link if linked
            if (this.linkColor && window.LinkManager) {
                window.LinkManager.subscribe(this.linkColor, this);
            }

            // Load data
            if (this.partId) {
                await this.loadBatchSets();
            } else {
                // No partId = load all batch sets
                await this.loadAllBatchSets();
            }
        },

        /**
         * React to link context changes
         */
        async onLinkChange(context) {
            console.debug(`[batch-sets] Link change:`, context);
            this.linkContext = context;

            // React to partId changes
            if (context.partId && context.partId !== this.partId) {
                this.partId = context.partId;
                this.partNumber = context.partNumber || null;
                this.selectedSetId = null;
                this.batches = [];
                await this.loadBatchSets();
            }
        },

        /**
         * Clean up module
         */
        destroy() {
            console.debug(`[batch-sets] Destroy module ${this.moduleId}`);
            if (this.linkColor && window.LinkManager) {
                window.LinkManager.unsubscribe(this.linkColor, this);
            }
        },

        // ═══════════════════════════════════════════════════════════════
        // Data Loading
        // ═══════════════════════════════════════════════════════════════

        /**
         * Load all batch sets (no part filter)
         */
        async loadAllBatchSets() {
            this.loading = true;
            this.error = null;

            try {
                let url = '/api/pricing/batch-sets';
                if (this.statusFilter) {
                    url += `?status=${this.statusFilter}`;
                }

                const response = await fetch(url);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                this.batchSets = await response.json();

                // Auto-select first set
                if (this.batchSets.length > 0 && !this.selectedSetId) {
                    this.selectSet(this.batchSets[0].id);
                }

            } catch (e) {
                console.error('[batch-sets] Error loading all batch sets:', e);
                this.error = e.message;
                this._showToast('Chyba při načítání cenových sad', 'error');
            } finally {
                this.loading = false;
            }
        },

        /**
         * Load batch sets for current part
         */
        async loadBatchSets() {
            if (!this.partId) {
                this.batchSets = [];
                this.batches = [];
                return;
            }

            this.loading = true;
            this.error = null;

            try {
                const response = await fetch(`/api/pricing/part/${this.partId}/batch-sets`);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                this.batchSets = await response.json();

                // Auto-select set
                if (this.batchSets.length > 0) {
                    const setToSelect = this.selectedSetId
                        ? this.batchSets.find(s => s.id === this.selectedSetId)?.id
                        : this.selectedSet?.id;

                    if (setToSelect) {
                        await this.selectSet(setToSelect);
                    }
                } else {
                    this.batches = [];
                }

            } catch (e) {
                console.error('[batch-sets] Error loading batch sets:', e);
                this.error = e.message;
                this._showToast('Chyba při načítání cenových sad', 'error');
            } finally {
                this.loading = false;
            }
        },

        /**
         * Load batch set detail with batches
         */
        async loadBatchSetDetail(setId) {
            if (!setId) {
                this.batches = [];
                return;
            }

            try {
                const response = await fetch(`/api/pricing/batch-sets/${setId}`);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                const data = await response.json();
                this.batches = data.batches || [];

                // Update set in list with fresh data
                const index = this.batchSets.findIndex(s => s.id === setId);
                if (index >= 0) {
                    this.batchSets[index] = {
                        ...this.batchSets[index],
                        batch_count: this.batches.length
                    };
                }

            } catch (e) {
                console.error('[batch-sets] Error loading batch set detail:', e);
                this.batches = [];
            }
        },

        // ═══════════════════════════════════════════════════════════════
        // CRUD Actions
        // ═══════════════════════════════════════════════════════════════

        /**
         * Create new batch set for current part
         */
        async createSet() {
            if (!this.partId) {
                this._showToast('Nejdříve vyberte díl', 'warning');
                return;
            }

            try {
                const response = await fetch('/api/pricing/batch-sets', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ part_id: this.partId })
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || `HTTP ${response.status}`);
                }

                const newSet = await response.json();
                this.batchSets.unshift(newSet);
                await this.selectSet(newSet.id);

                this._showToast('Nová cenová sada vytvořena', 'success');

            } catch (e) {
                console.error('[batch-sets] Error creating set:', e);
                this._showToast(`Chyba: ${e.message}`, 'error');
            }
        },

        /**
         * Update batch set name
         */
        async updateSetName(setId, newName) {
            const set = this.batchSets.find(s => s.id === setId);
            if (!set) return;

            try {
                const response = await fetch(`/api/pricing/batch-sets/${setId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: newName, version: set.version })
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || `HTTP ${response.status}`);
                }

                const updated = await response.json();
                const index = this.batchSets.findIndex(s => s.id === setId);
                if (index >= 0) {
                    this.batchSets[index] = { ...this.batchSets[index], ...updated };
                }

                this._showToast('Název sady aktualizován', 'success');

            } catch (e) {
                console.error('[batch-sets] Error updating set:', e);
                this._showToast(`Chyba: ${e.message}`, 'error');
            }
        },

        /**
         * Delete batch set (soft delete, admin only)
         */
        async deleteSet(setId) {
            if (!confirm('Opravdu chcete smazat tuto sadu? Tato akce je nevratná.')) {
                return;
            }

            try {
                const response = await fetch(`/api/pricing/batch-sets/${setId}`, {
                    method: 'DELETE'
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || `HTTP ${response.status}`);
                }

                this.batchSets = this.batchSets.filter(s => s.id !== setId);

                if (this.selectedSetId === setId) {
                    this.selectedSetId = null;
                    this.batches = [];
                }

                this._showToast('Cenová sada smazána', 'success');

            } catch (e) {
                console.error('[batch-sets] Error deleting set:', e);
                this._showToast(`Chyba: ${e.message}`, 'error');
            }
        },

        // ═══════════════════════════════════════════════════════════════
        // BatchSet Operations
        // ═══════════════════════════════════════════════════════════════

        /**
         * Freeze current batch set
         */
        async freezeSet() {
            const set = this.selectedSet;
            if (!set || set.status !== 'draft') {
                this._showToast('Nelze zmrazit - sada není koncept', 'warning');
                return;
            }

            if (this.batches.length === 0) {
                this._showToast('Nelze zmrazit prázdnou sadu', 'warning');
                return;
            }

            if (!confirm(`Zmrazit sadu "${set.name}"? Ceny budou uzamčeny.`)) {
                return;
            }

            try {
                const response = await fetch(`/api/pricing/batch-sets/${set.id}/freeze`, {
                    method: 'POST'
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || `HTTP ${response.status}`);
                }

                const updated = await response.json();

                // Update set in list
                const index = this.batchSets.findIndex(s => s.id === set.id);
                if (index >= 0) {
                    this.batchSets[index] = {
                        ...this.batchSets[index],
                        status: updated.status,
                        frozen_at: updated.frozen_at
                    };
                }

                // Update batches
                this.batches = updated.batches || [];

                this._showToast('Cenová sada zmrazena', 'success');

                // Emit to linked modules
                this.emitToLink('freeze-set', { batchSetId: set.id });

            } catch (e) {
                console.error('[batch-sets] Error freezing set:', e);
                this._showToast(`Chyba: ${e.message}`, 'error');
            }
        },

        /**
         * Recalculate all batches in set
         */
        async recalculatePrices() {
            const set = this.selectedSet;
            if (!set) return;

            if (set.status === 'frozen') {
                this._showToast('Nelze přepočítat zmrazenou sadu', 'warning');
                return;
            }

            try {
                const response = await fetch(`/api/pricing/batch-sets/${set.id}/recalculate`, {
                    method: 'POST'
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || `HTTP ${response.status}`);
                }

                const updated = await response.json();
                this.batches = updated.batches || [];

                this._showToast('Ceny přepočítány', 'success');

            } catch (e) {
                console.error('[batch-sets] Error recalculating:', e);
                this._showToast(`Chyba: ${e.message}`, 'error');
            }
        },

        /**
         * Clone batch set (creates new draft)
         */
        async cloneSet(setId) {
            const set = this.batchSets.find(s => s.id === setId);
            if (!set) return;

            try {
                const response = await fetch(`/api/pricing/batch-sets/${setId}/clone`, {
                    method: 'POST'
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || `HTTP ${response.status}`);
                }

                const newSet = await response.json();
                this.batchSets.unshift({
                    ...newSet,
                    batch_count: set.batch_count
                });
                await this.selectSet(newSet.id);

                this._showToast('Sada naklonována', 'success');

            } catch (e) {
                console.error('[batch-sets] Error cloning set:', e);
                this._showToast(`Chyba: ${e.message}`, 'error');
            }
        },

        // ═══════════════════════════════════════════════════════════════
        // Batch Operations (within set)
        // ═══════════════════════════════════════════════════════════════

        /**
         * Add batch to current set
         */
        async addBatch(quantity) {
            const set = this.selectedSet;
            if (!set || set.status !== 'draft') {
                this._showToast('Nelze přidávat do zmrazené sady', 'warning');
                return;
            }

            const qty = quantity || this.newBatchQty;
            if (!qty || qty <= 0) {
                this._showToast('Zadejte platné množství', 'warning');
                return;
            }

            try {
                const response = await fetch(`/api/pricing/batch-sets/${set.id}/batches?quantity=${qty}`, {
                    method: 'POST'
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || `HTTP ${response.status}`);
                }

                const newBatch = await response.json();
                this.batches.push(newBatch);
                this.batches.sort((a, b) => a.quantity - b.quantity);
                this.newBatchQty = null;

                // Update batch count in set list
                const index = this.batchSets.findIndex(s => s.id === set.id);
                if (index >= 0) {
                    this.batchSets[index].batch_count = this.batches.length;
                }

                this._showToast(`Dávka ${qty} ks přidána`, 'success');

            } catch (e) {
                console.error('[batch-sets] Error adding batch:', e);
                this._showToast(`Chyba: ${e.message}`, 'error');
            }
        },

        /**
         * Remove batch from current set
         */
        async removeBatch(batchId) {
            const set = this.selectedSet;
            if (!set || set.status !== 'draft') {
                this._showToast('Nelze mazat ze zmrazené sady', 'warning');
                return;
            }

            const batch = this.batches.find(b => b.id === batchId);
            if (!batch) return;

            if (!confirm(`Odstranit dávku ${batch.quantity} ks?`)) {
                return;
            }

            try {
                const response = await fetch(`/api/pricing/batch-sets/${set.id}/batches/${batchId}`, {
                    method: 'DELETE'
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || `HTTP ${response.status}`);
                }

                this.batches = this.batches.filter(b => b.id !== batchId);

                // Update batch count
                const index = this.batchSets.findIndex(s => s.id === set.id);
                if (index >= 0) {
                    this.batchSets[index].batch_count = this.batches.length;
                }

                this._showToast('Dávka odstraněna', 'success');

            } catch (e) {
                console.error('[batch-sets] Error removing batch:', e);
                this._showToast(`Chyba: ${e.message}`, 'error');
            }
        },

        // ═══════════════════════════════════════════════════════════════
        // UI Helpers
        // ═══════════════════════════════════════════════════════════════

        /**
         * Select a batch set
         */
        async selectSet(setId) {
            this.selectedSetId = setId;
            await this.loadBatchSetDetail(setId);

            // Emit to linked modules
            this.emitToLink('select-set', { batchSetId: setId });
        },

        /**
         * Set status filter
         */
        setFilter(status) {
            this.statusFilter = status;
            if (!this.partId) {
                this.loadAllBatchSets();
            }
        },

        /**
         * Format date for display
         */
        formatDate(dateStr) {
            if (!dateStr) return '-';
            return new Date(dateStr).toLocaleString('cs-CZ', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        },

        /**
         * Format currency
         */
        formatCurrency(value) {
            if (value == null) return '-';
            return new Intl.NumberFormat('cs-CZ', {
                style: 'currency',
                currency: 'CZK',
                minimumFractionDigits: 0,
                maximumFractionDigits: 0
            }).format(value);
        },

        /**
         * Get status label
         */
        getStatusLabel(status) {
            return status === 'frozen' ? '🔒 Zmrazeno' : '📝 Koncept';
        },

        /**
         * Get status CSS class
         */
        getStatusClass(status) {
            return status === 'frozen' ? 'status-frozen' : 'status-draft';
        },

        /**
         * Show toast notification
         * @private
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

// ═══════════════════════════════════════════════════════════════════════════
// Register in ModuleRegistry
// ═══════════════════════════════════════════════════════════════════════════

if (window.ModuleRegistry) {
    ModuleRegistry.register('batch-sets', _batchSetsWorkspaceModule, {
        icon: '💰',
        description: 'Cenové sady',
        category: 'pricing',
        emits: ['batchSetSelected'],
        consumes: ['partId']
    });
}

// Export to window with different name to avoid collision with inline modules
// Use ModuleRegistry.create('batch-sets', config) for workspace integration
// or window.batchSetsWorkspaceModule(config) for direct usage
window.batchSetsWorkspaceModule = _batchSetsWorkspaceModule;
