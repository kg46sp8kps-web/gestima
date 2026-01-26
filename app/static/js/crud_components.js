/**
 * GESTIMA - Reusable Alpine.js CRUD Components (ADR-015)
 *
 * Factory functions pro běžné CRUD operace.
 * Použití: x-data="entityList('/api/machines')"
 */

/**
 * Entity List Component
 * Pro stránky se seznamem entit (stroje, materiály, etc.)
 *
 * @param {string} apiEndpoint - API endpoint (např. '/api/machines')
 * @returns {object} Alpine.js component
 */
function entityList(apiEndpoint) {
    return {
        loading: false,
        items: [],
        error: null,

        async init() {
            await this.loadItems();
        },

        async loadItems() {
            this.loading = true;
            this.error = null;

            try {
                const response = await fetch(apiEndpoint);
                if (!response.ok) throw new Error('API error');

                this.items = await response.json();
            } catch (error) {
                console.error('Load error:', error);
                this.error = 'Chyba při načítání dat';
                window.showToast && window.showToast(this.error, 'error');
            } finally {
                this.loading = false;
            }
        },

        async deleteItem(id) {
            if (!confirm('Opravdu smazat tento záznam?')) return;

            try {
                const response = await fetch(`${apiEndpoint}/${id}`, {
                    method: 'DELETE'
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Chyba při mazání');
                }

                window.showToast && window.showToast('Záznam smazán', 'success');
                await this.loadItems();
            } catch (error) {
                console.error('Delete error:', error);
                window.showToast && window.showToast(error.message, 'error');
            }
        },

        navigateTo(path) {
            window.location.href = path;
        }
    };
}


/**
 * Entity Edit Component
 * Pro editační formuláře
 *
 * @param {string} apiEndpoint - API endpoint (např. '/api/machines')
 * @param {number|null} entityId - ID entity (null pro create)
 * @returns {object} Alpine.js component
 */
function entityEdit(apiEndpoint, entityId = null) {
    return {
        loading: false,
        saving: false,
        entity: null,
        error: null,

        async init() {
            if (entityId) {
                await this.loadEntity();
            } else {
                // New entity - initialize empty
                this.entity = {};
            }
        },

        async loadEntity() {
            this.loading = true;
            this.error = null;

            try {
                const response = await fetch(`${apiEndpoint}/${entityId}`);
                if (!response.ok) throw new Error('API error');

                this.entity = await response.json();
            } catch (error) {
                console.error('Load error:', error);
                this.error = 'Chyba při načítání dat';
                window.showToast && window.showToast(this.error, 'error');
            } finally {
                this.loading = false;
            }
        },

        async save(formData) {
            this.saving = true;
            this.error = null;

            const method = entityId ? 'PUT' : 'POST';
            const url = entityId ? `${apiEndpoint}/${entityId}` : apiEndpoint;

            try {
                const response = await fetch(url, {
                    method,
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Chyba při ukládání');
                }

                const saved = await response.json();
                window.showToast && window.showToast('Uloženo', 'success');

                // Redirect to list or detail
                return saved;
            } catch (error) {
                console.error('Save error:', error);
                this.error = error.message;
                window.showToast && window.showToast(this.error, 'error');
                throw error;
            } finally {
                this.saving = false;
            }
        },

        cancel() {
            window.history.back();
        }
    };
}


/**
 * Search Component
 * Pro vyhledávání v seznamech
 *
 * @param {string} apiEndpoint - Search API endpoint
 * @returns {object} Alpine.js component
 */
function searchComponent(apiEndpoint) {
    return {
        query: '',
        loading: false,
        results: [],
        total: 0,

        async search() {
            if (this.query.length < 2) {
                this.results = [];
                this.total = 0;
                return;
            }

            this.loading = true;

            try {
                const params = new URLSearchParams({
                    search: this.query,
                    limit: 20
                });

                const response = await fetch(`${apiEndpoint}?${params}`);
                if (!response.ok) throw new Error('API error');

                const data = await response.json();
                this.results = data.items || data.parts || data;
                this.total = data.total || this.results.length;
            } catch (error) {
                console.error('Search error:', error);
                window.showToast && window.showToast('Chyba při hledání', 'error');
            } finally {
                this.loading = false;
            }
        },

        // Debounced search
        searchDebounced() {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => this.search(), 300);
        }
    };
}


/**
 * Pricing Widget Component
 * Pro zobrazení cenové kalkulace na stránce dílu
 *
 * @param {number} partId - ID dílu
 * @returns {object} Alpine.js component
 */
function pricingWidget(partId) {
    return {
        partId,
        loading: false,
        pricing: null,
        quantity: 1,

        async init() {
            await this.loadPricing();
        },

        async loadPricing() {
            this.loading = true;

            try {
                const response = await fetch(
                    `/api/parts/${this.partId}/pricing?quantity=${this.quantity}`
                );
                if (!response.ok) throw new Error('API error');

                this.pricing = await response.json();
            } catch (error) {
                console.error('Pricing error:', error);
                window.showToast && window.showToast('Chyba při výpočtu ceny', 'error');
            } finally {
                this.loading = false;
            }
        },

        async updateQuantity() {
            if (this.quantity < 1) this.quantity = 1;
            await this.loadPricing();
        },

        formatPrice(value) {
            if (!value) return '0 Kč';
            return new Intl.NumberFormat('cs-CZ', {
                style: 'currency',
                currency: 'CZK',
                minimumFractionDigits: 0,
                maximumFractionDigits: 2
            }).format(value);
        },

        formatPercent(value) {
            return `${Math.round(value)}%`;
        }
    };
}


/**
 * Form Validation Helper
 * Pro validaci formulářů
 *
 * @returns {object} Alpine.js component
 */
function formValidation() {
    return {
        errors: {},
        touched: {},

        validate(field, value, rules) {
            this.touched[field] = true;
            const errors = [];

            if (rules.required && !value) {
                errors.push('Toto pole je povinné');
            }

            if (rules.min !== undefined && value < rules.min) {
                errors.push(`Minimální hodnota je ${rules.min}`);
            }

            if (rules.max !== undefined && value > rules.max) {
                errors.push(`Maximální hodnota je ${rules.max}`);
            }

            if (rules.minLength && value.length < rules.minLength) {
                errors.push(`Minimální délka je ${rules.minLength} znaků`);
            }

            if (rules.maxLength && value.length > rules.maxLength) {
                errors.push(`Maximální délka je ${rules.maxLength} znaků`);
            }

            if (rules.pattern && !rules.pattern.test(value)) {
                errors.push(rules.patternMessage || 'Neplatný formát');
            }

            this.errors[field] = errors;
            return errors.length === 0;
        },

        hasError(field) {
            return this.touched[field] && this.errors[field] && this.errors[field].length > 0;
        },

        getError(field) {
            return this.hasError(field) ? this.errors[field][0] : '';
        },

        isValid() {
            return Object.keys(this.errors).every(field =>
                !this.errors[field] || this.errors[field].length === 0
            );
        },

        reset() {
            this.errors = {};
            this.touched = {};
        }
    };
}


/**
 * Confirmation Dialog
 * Pro potvrzovací dialogy
 *
 * @returns {object} Alpine.js component
 */
function confirmDialog() {
    return {
        open: false,
        title: '',
        message: '',
        confirmText: 'Potvrdit',
        cancelText: 'Zrušit',
        onConfirm: null,

        show(options) {
            this.title = options.title || 'Potvrdit akci';
            this.message = options.message || 'Opravdu chcete provést tuto akci?';
            this.confirmText = options.confirmText || 'Potvrdit';
            this.cancelText = options.cancelText || 'Zrušit';
            this.onConfirm = options.onConfirm;
            this.open = true;
        },

        confirm() {
            if (this.onConfirm) {
                this.onConfirm();
            }
            this.close();
        },

        close() {
            this.open = false;
            this.onConfirm = null;
        }
    };
}
