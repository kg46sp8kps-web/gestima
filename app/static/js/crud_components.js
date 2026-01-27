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


// AUDIT-2026-01-27: Removed unused components:
// - searchComponent() - not used in any template
// - pricingWidget() - not used in any template
// - formValidation() - not used in any template
// - confirmDialog() - not used in any template
// See git history for original implementation if needed.
