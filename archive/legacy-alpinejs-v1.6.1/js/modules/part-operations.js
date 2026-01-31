/**
 * GESTIMA Part Operations Module (ADR-023)
 *
 * Manages operations for a part. Full CRUD with debounced updates.
 * Listens for partId from link.
 *
 * API Endpoints Used:
 *   GET    /api/operations/part/{part_id}        - List operations
 *   POST   /api/operations/                      - Create operation
 *   PUT    /api/operations/{id}                  - Update operation
 *   DELETE /api/operations/{id}                  - Delete operation
 *   POST   /api/operations/{id}/change-mode      - Toggle coop mode
 *   GET    /api/work-centers/                    - List work centers
 *
 * Link Events:
 *   - Listens: partId
 *   - Emits: operationsChanged { partId, totalSetupTime, totalOperationTime }
 *
 * @version 1.0.0
 * @see docs/ADR/023-workspace-module-architecture.md
 */

function _partOperationsWorkspaceModule(config = {}) {
    return {
        // ═══════════════════════════════════════════════════════════════
        // ModuleInterface Implementation
        // ═══════════════════════════════════════════════════════════════

        ...ModuleInterface.create({
            moduleType: 'part-operations',
            moduleId: config.moduleId,
            linkColor: config.linkColor
        }),

        // ═══════════════════════════════════════════════════════════════
        // Module State
        // ═══════════════════════════════════════════════════════════════

        // Part reference
        partId: config.partId || null,

        // Operations data
        operations: [],
        workCenters: [],

        // UI State
        loading: false,
        saving: false,
        error: null,
        expandedOps: {},

        // Debounce tracking
        _updateTimeout: null,
        _updateSequence: 0,

        // ═══════════════════════════════════════════════════════════════
        // Lifecycle
        // ═══════════════════════════════════════════════════════════════

        async init() {
            console.debug(`[part-operations] Initializing module ${this.moduleId}`);

            // Subscribe to link
            if (this.linkColor && window.LinkManager) {
                LinkManager.subscribe(this.linkColor, this);

                // Check existing context
                const ctx = LinkManager.getContext(this.linkColor);
                if (ctx.partId) {
                    this.partId = ctx.partId;
                }
            }

            // Load work centers for dropdown
            await this.loadWorkCenters();

            // Load operations if partId is set
            if (this.partId) {
                await this.loadOperations();
            }
        },

        destroy() {
            console.debug(`[part-operations] Destroying module ${this.moduleId}`);

            if (this.linkColor && window.LinkManager) {
                LinkManager.unsubscribe(this.linkColor, this);
            }

            if (this._updateTimeout) {
                clearTimeout(this._updateTimeout);
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
                await this.loadOperations();
            }
        },

        emitOperationsChanged() {
            if (!this.linkColor || !window.LinkManager) return;

            LinkManager.emit(this.linkColor, {
                source: this.moduleId,
                type: 'operationsChanged',
                data: {
                    partId: this.partId,
                    totalSetupTime: this.totalSetupTime,
                    totalOperationTime: this.totalOperationTime,
                    operationCount: this.operations.length
                }
            });
        },

        // ═══════════════════════════════════════════════════════════════
        // Data Loading
        // ═══════════════════════════════════════════════════════════════

        async loadWorkCenters() {
            try {
                const response = await fetch('/api/work-centers/');
                if (response.ok) {
                    this.workCenters = await response.json();
                }
            } catch (err) {
                console.error('[part-operations] Failed to load work centers:', err);
            }
        },

        async loadOperations() {
            if (!this.partId) {
                this.operations = [];
                return;
            }

            this.loading = true;
            this.error = null;

            try {
                const response = await fetch(`/api/operations/part/${this.partId}`);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                this.operations = await response.json();

                // Sort by sequence
                this.operations.sort((a, b) => a.seq - b.seq);

                console.debug(`[part-operations] Loaded ${this.operations.length} operations`);

                // Emit change
                this.emitOperationsChanged();

            } catch (err) {
                console.error('[part-operations] Load error:', err);
                this.error = 'Chyba při načítání operací';
                this.operations = [];
            } finally {
                this.loading = false;
            }
        },

        // ═══════════════════════════════════════════════════════════════
        // CRUD Operations
        // ═══════════════════════════════════════════════════════════════

        async addOperation() {
            if (!this.partId) return;

            try {
                const nextSeq = this.operations.length > 0
                    ? Math.max(...this.operations.map(o => o.seq)) + 10
                    : 10;

                const payload = {
                    part_id: this.partId,
                    seq: nextSeq,
                    name: `OP${nextSeq}`,
                    type: 'generic',
                    icon: '🔧',
                    setup_time_min: 0,
                    operation_time_min: 0,
                    is_cooperation: false,
                    coop_price_per_piece: 0
                };

                const response = await fetch('/api/operations/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const newOp = await response.json();
                this.operations.push(newOp);
                this.operations.sort((a, b) => a.seq - b.seq);

                // Expand new operation
                this.expandedOps[newOp.id] = true;

                // Emit change
                this.emitOperationsChanged();

                this._showToast('Operace přidána', 'success');

            } catch (err) {
                console.error('[part-operations] Add error:', err);
                this._showToast('Chyba při přidávání operace', 'error');
            }
        },

        async deleteOperation(op) {
            if (!confirm(`Smazat operaci ${op.name}?`)) return;

            try {
                const response = await fetch(`/api/operations/${op.id}`, {
                    method: 'DELETE'
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                // Remove from local array
                this.operations = this.operations.filter(o => o.id !== op.id);

                // Emit change
                this.emitOperationsChanged();

                this._showToast('Operace smazána', 'success');

            } catch (err) {
                console.error('[part-operations] Delete error:', err);
                this._showToast('Chyba při mazání operace', 'error');
            }
        },

        // ═══════════════════════════════════════════════════════════════
        // Debounced Update (L-017 pattern)
        // ═══════════════════════════════════════════════════════════════

        debouncedUpdate(op) {
            if (this._updateTimeout) {
                clearTimeout(this._updateTimeout);
            }

            this._updateSequence++;
            const currentSequence = this._updateSequence;

            // Snapshot to avoid Alpine Proxy issues (L-017)
            const snapshot = JSON.parse(JSON.stringify(op));

            this._updateTimeout = setTimeout(() => {
                this.updateOperation(snapshot, currentSequence);
            }, 300);
        },

        async updateOperation(op, requestSequence) {
            if (this.saving) return;

            // Race protection: ignore stale requests
            if (requestSequence < this._updateSequence) {
                console.debug('[part-operations] Ignoring stale update request');
                return;
            }

            this.saving = true;

            try {
                const payload = {
                    seq: op.seq,
                    name: op.name,
                    type: op.type || 'generic',
                    icon: op.icon || '🔧',
                    work_center_id: op.work_center_id || null,
                    setup_time_min: parseFloat(op.setup_time_min) || 0,
                    operation_time_min: parseFloat(op.operation_time_min) || 0,
                    is_cooperation: op.is_cooperation || false,
                    coop_price_per_piece: parseFloat(op.coop_price_per_piece) || 0,
                    notes: op.notes || '',
                    version: op.version
                };

                const response = await fetch(`/api/operations/${op.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    if (response.status === 409) {
                        this._showToast('Konflikt verze - obnovuji data', 'warning');
                        await this.loadOperations();
                        return;
                    }
                    throw new Error(`HTTP ${response.status}`);
                }

                const updated = await response.json();

                // Update local operation with new version
                const idx = this.operations.findIndex(o => o.id === op.id);
                if (idx !== -1) {
                    this.operations[idx] = { ...this.operations[idx], ...updated };
                }

                // Emit change
                this.emitOperationsChanged();

            } catch (err) {
                console.error('[part-operations] Update error:', err);
                this._showToast('Chyba při ukládání', 'error');
            } finally {
                this.saving = false;
            }
        },

        // ═══════════════════════════════════════════════════════════════
        // Toggle Cooperation Mode
        // ═══════════════════════════════════════════════════════════════

        async toggleCoopMode(op) {
            try {
                const response = await fetch(`/api/operations/${op.id}/change-mode`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ version: op.version })
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const updated = await response.json();

                // Update local operation
                const idx = this.operations.findIndex(o => o.id === op.id);
                if (idx !== -1) {
                    this.operations[idx] = updated;
                }

                // Emit change
                this.emitOperationsChanged();

            } catch (err) {
                console.error('[part-operations] Toggle coop error:', err);
                this._showToast('Chyba při změně režimu', 'error');
            }
        },

        async changeMode(op, mode) {
            try {
                const response = await fetch(`/api/operations/${op.id}/change-mode`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        cutting_mode: mode,
                        version: op.version
                    })
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const updated = await response.json();

                // Update local operation
                const idx = this.operations.findIndex(o => o.id === op.id);
                if (idx !== -1) {
                    this.operations[idx] = updated;
                }

                this._showToast(`Režim nastaven na ${mode.toUpperCase()}`, 'success');

                // Emit change
                this.emitOperationsChanged();

            } catch (err) {
                console.error('[part-operations] Change mode error:', err);
                this._showToast('Chyba při změně režimu', 'error');
            }
        },

        // ═══════════════════════════════════════════════════════════════
        // UI Helpers
        // ═══════════════════════════════════════════════════════════════

        toggleExpand(opId) {
            this.expandedOps[opId] = !this.expandedOps[opId];
        },

        isExpanded(opId) {
            return !!this.expandedOps[opId];
        },

        getWorkCenterName(workCenterId) {
            if (!workCenterId) return '-';
            const wc = this.workCenters.find(w => w.id === workCenterId);
            return wc ? wc.name : '-';
        },

        // ═══════════════════════════════════════════════════════════════
        // Computed
        // ═══════════════════════════════════════════════════════════════

        get totalSetupTime() {
            return this.operations.reduce((sum, op) => sum + (parseFloat(op.setup_time_min) || 0), 0);
        },

        get totalOperationTime() {
            return this.operations.reduce((sum, op) => sum + (parseFloat(op.operation_time_min) || 0), 0);
        },

        get internalOperations() {
            return this.operations.filter(op => !op.is_cooperation);
        },

        get coopOperations() {
            return this.operations.filter(op => op.is_cooperation);
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
    ModuleRegistry.register('part-operations', _partOperationsWorkspaceModule, {
        icon: '🔧',
        description: 'Operace dílu',
        category: 'parts',
        emits: ['operationsChanged'],
        consumes: ['partId']
    });
}

window.partOperationsWorkspaceModule = _partOperationsWorkspaceModule;
