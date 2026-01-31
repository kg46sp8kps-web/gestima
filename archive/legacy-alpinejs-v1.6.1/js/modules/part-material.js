/**
 * GESTIMA Part Material Module (ADR-023)
 *
 * Combined module for material selection, stock dimensions, and cost display.
 * Listens for partId from link, loads and allows editing of material data.
 *
 * API Endpoints Used:
 *   GET  /api/parts/{part_number}/full    - Load part with material
 *   PUT  /api/parts/{part_number}         - Update part
 *   GET  /api/parts/{part_number}/stock-cost - Calculate stock cost
 *   GET  /api/materials/categories        - List material categories
 *
 * Link Events:
 *   - Listens: partId, partNumber
 *   - Emits: materialChanged { partId, stockCost }
 *
 * @version 1.0.0
 * @see docs/ADR/023-workspace-module-architecture.md
 */

function _partMaterialWorkspaceModule(config = {}) {
    return {
        // ═══════════════════════════════════════════════════════════════
        // ModuleInterface Implementation
        // ═══════════════════════════════════════════════════════════════

        ...ModuleInterface.create({
            moduleType: 'part-material',
            moduleId: config.moduleId,
            linkColor: config.linkColor
        }),

        // ═══════════════════════════════════════════════════════════════
        // Module State
        // ═══════════════════════════════════════════════════════════════

        // Part reference
        partId: config.partId || null,
        partNumber: config.partNumber || null,

        // Part data (editable)
        partData: {
            stock_shape: '',
            price_category_id: null,
            stock_diameter: 0,
            stock_length: 0,
            stock_width: 0,
            stock_height: 0,
            stock_wall_thickness: 0,
            version: 0
        },

        // Material catalog
        categories: [],
        selectedMaterial: null,

        // Stock cost (computed by backend)
        stockCost: {
            cost: 0,
            weight_kg: 0,
            volume_mm3: 0,
            price_per_kg: 0
        },

        // UI State
        loading: false,
        saving: false,
        error: null,

        // Debounce
        _saveTimeout: null,

        // Material Parser
        quickMaterialInput: '',
        parseResult: null,
        parsingMaterial: false,
        _parseTimeout: null,

        // ═══════════════════════════════════════════════════════════════
        // Lifecycle
        // ═══════════════════════════════════════════════════════════════

        async init() {
            console.debug(`[part-material] Initializing module ${this.moduleId}`);

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

            // Load material categories
            await this.loadCategories();

            // Load part data if partNumber is set
            if (this.partNumber) {
                await this.loadPartData();
            }
        },

        destroy() {
            console.debug(`[part-material] Destroying module ${this.moduleId}`);

            if (this.linkColor && window.LinkManager) {
                LinkManager.unsubscribe(this.linkColor, this);
            }

            if (this._saveTimeout) {
                clearTimeout(this._saveTimeout);
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
                await this.loadPartData();
            }
        },

        emitMaterialChanged() {
            if (!this.linkColor || !window.LinkManager) return;

            LinkManager.emit(this.linkColor, {
                source: this.moduleId,
                type: 'materialChanged',
                data: {
                    partId: this.partId,
                    stockCost: this.stockCost
                }
            });
        },

        // ═══════════════════════════════════════════════════════════════
        // Data Loading
        // ═══════════════════════════════════════════════════════════════

        async loadCategories() {
            try {
                const response = await fetch('/api/materials/price-categories');
                if (response.ok) {
                    this.categories = await response.json();
                }
            } catch (err) {
                console.error('[part-material] Failed to load categories:', err);
            }
        },

        async loadPartData() {
            if (!this.partNumber) {
                this.error = 'Není vybrán díl';
                return;
            }

            this.loading = true;
            this.error = null;

            try {
                const response = await fetch(`/api/parts/${this.partNumber}/full`);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();

                // Update part data
                this.partData = {
                    stock_shape: data.stock_shape || '',
                    price_category_id: data.price_category_id || null,
                    stock_diameter: data.stock_diameter || 0,
                    stock_length: data.stock_length || 0,
                    stock_width: data.stock_width || 0,
                    stock_height: data.stock_height || 0,
                    stock_wall_thickness: data.stock_wall_thickness || 0,
                    version: data.version || 0
                };

                // Set selected material
                if (data.price_category_id) {
                    this.selectedMaterial = this.categories.find(
                        c => c.id === data.price_category_id
                    );
                }

                // Load stock cost
                await this.loadStockCost();

                console.debug(`[part-material] Loaded part: ${this.partNumber}`);

            } catch (err) {
                console.error('[part-material] Load error:', err);
                this.error = 'Chyba při načítání dílu';
            } finally {
                this.loading = false;
            }
        },

        async loadStockCost() {
            if (!this.partNumber) return;

            try {
                const response = await fetch(`/api/parts/${this.partNumber}/stock-cost`);
                if (response.ok) {
                    this.stockCost = await response.json();
                }
            } catch (err) {
                console.error('[part-material] Stock cost error:', err);
            }
        },

        // ═══════════════════════════════════════════════════════════════
        // Saving
        // ═══════════════════════════════════════════════════════════════

        debouncedSave() {
            if (this._saveTimeout) {
                clearTimeout(this._saveTimeout);
            }

            this._saveTimeout = setTimeout(() => {
                this.savePartData();
            }, 400);
        },

        async savePartData() {
            if (!this.partNumber || this.saving) return;

            this.saving = true;

            try {
                const payload = {
                    stock_shape: this.partData.stock_shape || null,
                    price_category_id: this.partData.price_category_id || null,
                    stock_diameter: this.partData.stock_diameter || 0,
                    stock_length: this.partData.stock_length || 0,
                    stock_width: this.partData.stock_width || 0,
                    stock_height: this.partData.stock_height || 0,
                    stock_wall_thickness: this.partData.stock_wall_thickness || 0,
                    version: this.partData.version
                };

                const response = await fetch(`/api/parts/${this.partNumber}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    if (response.status === 409) {
                        this._showToast('Data byla změněna jiným uživatelem', 'error');
                        await this.loadPartData();
                        return;
                    }
                    throw new Error(`HTTP ${response.status}`);
                }

                const updated = await response.json();
                this.partData.version = updated.version;

                // Reload stock cost after material change
                await this.loadStockCost();

                // Emit change to linked modules
                this.emitMaterialChanged();

            } catch (err) {
                console.error('[part-material] Save error:', err);
                this._showToast('Chyba při ukládání', 'error');
            } finally {
                this.saving = false;
            }
        },

        // ═══════════════════════════════════════════════════════════════
        // Material Selection
        // ═══════════════════════════════════════════════════════════════

        selectCategory(categoryId) {
            this.partData.price_category_id = categoryId;
            this.selectedMaterial = this.categories.find(c => c.id === categoryId);
            this.debouncedSave();
        },

        get filteredCategories() {
            // Note: Stock shape filtering not yet implemented in DB
            // MaterialPriceCategory doesn't have stock_shapes field
            // For now, return all categories
            return this.categories;
        },

        // ═══════════════════════════════════════════════════════════════
        // Stock Shape Helpers
        // ═══════════════════════════════════════════════════════════════

        get selectedShape() {
            return this.partData.stock_shape;
        },

        get shapeLabel() {
            const labels = {
                'round_bar': 'Tyč kruhová',
                'flat_bar': 'Tyč plochá',
                'square_bar': 'Tyč čtvercová',
                'hexagonal_bar': 'Tyč šestihranná',
                'plate': 'Plech / Deska',
                'tube': 'Trubka',
                'casting': 'Odlitek',
                'forging': 'Výkovek'
            };
            return labels[this.partData.stock_shape] || this.partData.stock_shape || '-';
        },

        get shapeOptions() {
            return [
                { value: 'round_bar', label: 'Tyč kruhová' },
                { value: 'flat_bar', label: 'Tyč plochá' },
                { value: 'square_bar', label: 'Tyč čtvercová' },
                { value: 'hexagonal_bar', label: 'Tyč šestihranná' },
                { value: 'plate', label: 'Plech / Deska' },
                { value: 'tube', label: 'Trubka' },
                { value: 'casting', label: 'Odlitek' },
                { value: 'forging', label: 'Výkovek' }
            ];
        },

        // Which dimension fields to show based on shape
        get showDiameter() {
            return ['round_bar', 'hexagonal_bar', 'tube', 'casting', 'forging'].includes(this.selectedShape);
        },

        get showWidth() {
            return ['flat_bar', 'square_bar', 'plate'].includes(this.selectedShape);
        },

        get showHeight() {
            return ['flat_bar', 'plate'].includes(this.selectedShape);
        },

        get showWallThickness() {
            return this.selectedShape === 'tube';
        },

        // ═══════════════════════════════════════════════════════════════
        // Material Parser
        // ═══════════════════════════════════════════════════════════════

        debouncedParseMaterial() {
            clearTimeout(this._parseTimeout);
            this.parsingMaterial = true;

            this._parseTimeout = setTimeout(async () => {
                await this.parseMaterialDescription();
            }, 400);
        },

        async parseMaterialDescription() {
            if (!this.quickMaterialInput || this.quickMaterialInput.trim().length < 2) {
                this.parseResult = null;
                this.parsingMaterial = false;
                return;
            }

            try {
                const response = await fetch('/api/materials/parse', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ description: this.quickMaterialInput.trim() })
                });

                if (response.ok) {
                    this.parseResult = await response.json();
                } else {
                    this.parseResult = null;
                }
            } catch (err) {
                console.error('[part-material] Parse error:', err);
                this.parseResult = null;
            } finally {
                this.parsingMaterial = false;
            }
        },

        async applyParsedMaterial() {
            if (!this.parseResult || this.parseResult.confidence < 0.4) {
                return;
            }

            // Apply shape
            if (this.parseResult.shape) {
                this.partData.stock_shape = this.parseResult.shape;
            }

            // Apply dimensions
            if (this.parseResult.diameter) {
                this.partData.stock_diameter = this.parseResult.diameter;
            }
            if (this.parseResult.length) {
                this.partData.stock_length = this.parseResult.length;
            }
            if (this.parseResult.width) {
                this.partData.stock_width = this.parseResult.width;
            }
            if (this.parseResult.height) {
                this.partData.stock_height = this.parseResult.height;
            }
            if (this.parseResult.thickness) {
                this.partData.stock_height = this.parseResult.thickness;
            }
            if (this.parseResult.wall_thickness) {
                this.partData.stock_wall_thickness = this.parseResult.wall_thickness;
            }

            // Apply material category if suggested
            if (this.parseResult.suggested_price_category_id) {
                this.partData.price_category_id = this.parseResult.suggested_price_category_id;
                this.selectedMaterial = this.categories.find(
                    c => c.id === this.parseResult.suggested_price_category_id
                );
            }

            // Save changes
            await this.savePartData();

            // Clear parse result and input
            this.quickMaterialInput = '';
            this.parseResult = null;

            this._showToast('Materiál aplikován', 'success');
        },

        clearParseResult() {
            this.quickMaterialInput = '';
            this.parseResult = null;
        },

        formatShape(shape) {
            const labels = {
                'round_bar': 'Kulatina (D)',
                'square_bar': 'Čtyřhran (□)',
                'flat_bar': 'Profil',
                'hexagonal_bar': 'Šestihran (⬡)',
                'plate': 'Plech',
                'tube': 'Trubka (⊙)',
                'casting': 'Odlitek',
                'forging': 'Výkovek'
            };
            return labels[shape] || shape;
        },

        async copyGeometryFromCatalog() {
            if (!this.selectedMaterial) return;

            // TODO: Implement catalog geometry copy
            // This would fetch typical dimensions for selected material
            this._showToast('Funkce zatím není implementována', 'info');
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
    ModuleRegistry.register('part-material', _partMaterialWorkspaceModule, {
        icon: '🔩',
        description: 'Materiál dílu',
        category: 'parts',
        emits: ['materialChanged'],
        consumes: ['partId', 'partNumber']
    });
}

window.partMaterialWorkspaceModule = _partMaterialWorkspaceModule;
