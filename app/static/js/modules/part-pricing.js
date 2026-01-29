/**
 * GESTIMA Part Pricing Module (ADR-023)
 *
 * Displays pricing overview for a part - batches, costs, margins.
 * Listens for partId from link.
 *
 * API Endpoints Used:
 *   GET  /api/parts/{part_number}/full           - Get part data
 *   GET  /api/parts/{part_number}/pricing/series - Get batch pricing
 *   GET  /api/batches/part/{part_id}             - Get batches
 *   POST /api/batches/                           - Create batch
 *   DELETE /api/batches/{id}                     - Delete batch
 *
 * Link Events:
 *   - Listens: partId, partNumber, materialChanged, operationsChanged
 *
 * @version 1.0.0
 * @see docs/ADR/023-workspace-module-architecture.md
 */

function _partPricingWorkspaceModule(config = {}) {
    return {
        // ═══════════════════════════════════════════════════════════════
        // ModuleInterface Implementation
        // ═══════════════════════════════════════════════════════════════

        ...ModuleInterface.create({
            moduleType: 'part-pricing',
            moduleId: config.moduleId,
            linkColor: config.linkColor
        }),

        // ═══════════════════════════════════════════════════════════════
        // Module State
        // ═══════════════════════════════════════════════════════════════

        // Part reference
        partId: config.partId || null,
        partNumber: config.partNumber || null,

        // Pricing data
        batches: [],
        priceBreakdowns: [],
        batchSets: [],

        // Selection
        selectedSetId: null,
        newBatchQty: 1,
        newSetName: '',
        showCreateSetModal: false,

        // UI State
        loading: false,
        error: null,

        // ═══════════════════════════════════════════════════════════════
        // Lifecycle
        // ═══════════════════════════════════════════════════════════════

        async init() {
            console.debug(`[part-pricing] Initializing module ${this.moduleId}`);

            // Subscribe to link
            if (this.linkColor && window.LinkManager) {
                LinkManager.subscribe(this.linkColor, this);

                // Check existing context
                const ctx = LinkManager.getContext(this.linkColor);
                if (ctx.partId) {
                    this.partId = ctx.partId;
                    this.partNumber = ctx.partNumber;
                }
            }

            // Load data if part is set
            if (this.partId) {
                await this.loadData();
            }
        },

        destroy() {
            console.debug(`[part-pricing] Destroying module ${this.moduleId}`);

            if (this.linkColor && window.LinkManager) {
                LinkManager.unsubscribe(this.linkColor, this);
            }
        },

        // ═══════════════════════════════════════════════════════════════
        // Link Communication
        // ═══════════════════════════════════════════════════════════════

        async onLinkChange(context) {
            this.linkContext = context;

            // React to part selection
            if (context.partId && context.partId !== this.partId) {
                this.partId = context.partId;
                this.partNumber = context.partNumber;
                await this.loadData();
            }

            // React to material/operations changes - recalculate and reload
            if (context.type === 'materialChanged' || context.type === 'operationsChanged') {
                if (this.partId) {
                    await this.recalculateBatches();
                    await this.loadData();  // Reload after recalc
                }
            }
        },

        // ═══════════════════════════════════════════════════════════════
        // Data Loading
        // ═══════════════════════════════════════════════════════════════

        async loadData() {
            if (!this.partId) return;

            this.loading = true;
            this.error = null;

            try {
                // Load batches, sets and pricing in parallel
                await Promise.all([
                    this.loadBatches(),
                    this.loadBatchSets(),
                    this.loadPricing()
                ]);

                console.debug(`[part-pricing] Loaded ${this.batches.length} batches, ${this.batchSets.length} sets`);

            } catch (err) {
                console.error('[part-pricing] Load error:', err);
                this.error = 'Chyba při načítání cen';
            } finally {
                this.loading = false;
            }
        },

        async loadBatches() {
            try {
                const response = await fetch(`/api/batches/part/${this.partId}`);
                if (response.ok) {
                    this.batches = await response.json();
                    // Sort by quantity
                    this.batches.sort((a, b) => a.quantity - b.quantity);
                }
            } catch (err) {
                console.error('[part-pricing] Batches load error:', err);
            }
        },

        async loadBatchSets() {
            try {
                const response = await fetch(`/api/pricing/part/${this.partId}/batch-sets`);
                if (response.ok) {
                    this.batchSets = await response.json();
                }
            } catch (err) {
                console.error('[part-pricing] Batch sets load error:', err);
            }
        },

        async loadPricing() {
            if (!this.partNumber) return;

            try {
                const response = await fetch(`/api/parts/${this.partNumber}/pricing/series`);
                if (response.ok) {
                    this.priceBreakdowns = await response.json();
                }
            } catch (err) {
                console.error('[part-pricing] Pricing load error:', err);
            }
        },

        async recalculateBatches() {
            if (!this.partId) return;

            try {
                const response = await fetch(`/api/batches/part/${this.partId}/recalculate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                console.debug('[part-pricing] Batches recalculated');

            } catch (err) {
                console.error('[part-pricing] Recalculate error:', err);
                this._showToast('Chyba při přepočtu cen', 'warning');
            }
        },

        // ═══════════════════════════════════════════════════════════════
        // Batch Management
        // ═══════════════════════════════════════════════════════════════

        async addBatch() {
            if (!this.partId || !this.newBatchQty || this.newBatchQty < 1) return;

            try {
                const payload = {
                    part_id: this.partId,
                    quantity: this.newBatchQty
                };

                const response = await fetch('/api/batches/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const newBatch = await response.json();
                this.batches.push(newBatch);
                this.batches.sort((a, b) => a.quantity - b.quantity);

                this.newBatchQty = 1;
                this._showToast('Dávka přidána', 'success');

                // Reload pricing
                await this.loadPricing();

            } catch (err) {
                console.error('[part-pricing] Add batch error:', err);
                this._showToast('Chyba při přidávání dávky', 'error');
            }
        },

        async deleteBatch(batch) {
            if (batch.is_frozen) {
                this._showToast('Nelze smazat zmrazenou dávku', 'warning');
                return;
            }

            if (!confirm(`Smazat dávku ${batch.quantity} ks?`)) return;

            try {
                const response = await fetch(`/api/batches/${batch.batch_number}`, {
                    method: 'DELETE'
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                this.batches = this.batches.filter(b => b.id !== batch.id);
                this._showToast('Dávka smazána', 'success');

                // Reload pricing
                await this.loadPricing();

            } catch (err) {
                console.error('[part-pricing] Delete batch error:', err);
                this._showToast('Chyba při mazání dávky', 'error');
            }
        },

        // ═══════════════════════════════════════════════════════════════
        // Batch Sets Management
        // ═══════════════════════════════════════════════════════════════

        selectBatchSet(setId) {
            this.selectedSetId = setId;
        },

        async createBatchSet() {
            if (!this.partId || !this.newSetName.trim()) return;

            try {
                const payload = {
                    part_id: this.partId,
                    name: this.newSetName.trim(),
                    status: 'draft'
                };

                const response = await fetch('/api/pricing/batch-sets', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const newSet = await response.json();
                this.batchSets.push(newSet);
                this.selectedSetId = newSet.id;
                this.newSetName = '';
                this.showCreateSetModal = false;

                this._showToast('Sada cen vytvořena', 'success');
                await this.loadData();

            } catch (err) {
                console.error('[part-pricing] Create set error:', err);
                this._showToast('Chyba při vytváření sady', 'error');
            }
        },

        async freezeCurrentSet() {
            if (!this.selectedSetId) {
                this._showToast('Není vybrána žádná sada', 'warning');
                return;
            }

            const set = this.batchSets.find(s => s.id === this.selectedSetId);
            if (!set) return;

            if (set.status === 'frozen') {
                this._showToast('Sada je již zmrazena', 'info');
                return;
            }

            if (!confirm(`Zmrazit sadu "${set.name}"? Zmrazené ceny už nelze měnit.`)) return;

            try {
                const response = await fetch(`/api/pricing/batch-sets/${this.selectedSetId}/freeze`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                this._showToast('Sada zmrazena', 'success');
                await this.loadData();

            } catch (err) {
                console.error('[part-pricing] Freeze set error:', err);
                this._showToast('Chyba při zmrazování sady', 'error');
            }
        },

        async freezeLooseBatches() {
            if (!this.partId) return;

            const looseBatches = this.batches.filter(b => !b.batch_set_id && !b.is_frozen);
            if (looseBatches.length === 0) {
                this._showToast('Žádné volné dávky k zmrazení', 'info');
                return;
            }

            if (!confirm(`Zmrazit ${looseBatches.length} volných dávek do nové sady?`)) return;

            try {
                const response = await fetch(`/api/pricing/parts/${this.partId}/freeze-batches-as-set`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const newSet = await response.json();
                this._showToast(`Vytvořena zmrazená sada "${newSet.name}"`, 'success');
                await this.loadData();

            } catch (err) {
                console.error('[part-pricing] Freeze loose batches error:', err);
                this._showToast('Chyba při zmrazování dávek', 'error');
            }
        },

        // ═══════════════════════════════════════════════════════════════
        // Computed
        // ═══════════════════════════════════════════════════════════════

        get displayedBatches() {
            if (this.selectedSetId === null) {
                // Show loose batches (not in any set)
                return this.batches.filter(b => !b.batch_set_id);
            } else if (this.selectedSetId === 'all') {
                // Show all batches
                return this.batches;
            } else {
                // Show batches from selected set
                return this.batches.filter(b => b.batch_set_id === this.selectedSetId);
            }
        },

        get looseBatches() {
            return this.batches.filter(b => !b.batch_set_id && !b.is_frozen);
        },

        get frozenBatches() {
            return this.batches.filter(b => b.is_frozen);
        },

        get selectedSet() {
            if (!this.selectedSetId || this.selectedSetId === 'all') return null;
            return this.batchSets.find(s => s.id === this.selectedSetId);
        },

        // ═══════════════════════════════════════════════════════════════
        // Formatting
        // ═══════════════════════════════════════════════════════════════

        formatCurrency(value) {
            return Math.round(value || 0).toLocaleString('cs-CZ') + ' Kč';
        },

        getCostBarWidth(batch, costType) {
            const total = (batch.material_cost || 0) +
                         (batch.coop_cost || 0) +
                         (batch.setup_cost || 0) +
                         (batch.machining_cost || 0);
            if (total === 0) return '0%';
            const value = batch[costType] || 0;
            return `${(value / total * 100).toFixed(1)}%`;
        },

        // ═══════════════════════════════════════════════════════════════
        // Helpers
        // ═══════════════════════════════════════════════════════════════

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
    ModuleRegistry.register('part-pricing', _partPricingWorkspaceModule, {
        icon: '💰',
        description: 'Cenový přehled',
        category: 'pricing',
        emits: [],
        consumes: ['partId', 'partNumber', 'materialChanged', 'operationsChanged']
    });
}

window.partPricingWorkspaceModule = _partPricingWorkspaceModule;
