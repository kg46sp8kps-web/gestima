/**
 * GESTIMA - Main JavaScript
 */

// Toast notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    
    // Barvy podle typu (50% opacity pro pozadí)
    const bgColor = type === 'success' ? 'rgba(34, 197, 94, 0.5)' : 
                    type === 'error' ? 'rgba(214, 40, 40, 0.5)' : 
                    'rgba(59, 130, 246, 0.5)';
    const borderColor = type === 'success' ? '#22c55e' : 
                        type === 'error' ? '#d62828' : 
                        '#3b82f6';
    
    toast.style.cssText = `
        background: ${bgColor};
        backdrop-filter: blur(8px);
        border: 2px solid ${borderColor};
        border-radius: 6px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        display: flex;
        align-items: center;
        gap: 0.75rem;
        color: white;
        font-size: 0.85rem;
        font-weight: 500;
        transition: opacity 0.3s;
        min-width: 250px;
        max-width: 400px;
    `;
    
    // XSS-safe: použití textContent místo innerHTML
    const messageSpan = document.createElement('span');
    messageSpan.style.flex = '1';
    messageSpan.textContent = message;  // BEZPEČNÉ - escapuje HTML

    const closeBtn = document.createElement('button');
    closeBtn.textContent = '×';
    closeBtn.style.cssText = 'background: none; border: none; color: white; opacity: 0.8; cursor: pointer; font-size: 1.3rem; padding: 0; line-height: 1; font-weight: 300;';
    closeBtn.onclick = () => toast.remove();

    toast.appendChild(messageSpan);
    toast.appendChild(closeBtn);

    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

window.showToast = showToast;

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

window.debounce = debounce;

// ============================================================================
// ALPINE.JS COMPONENTS
// Definované globálně - fungují i při HTMX boost navigaci
// ============================================================================

/**
 * Parts List Component
 * Používá data-is-admin atribut z HTML pro role check
 */
function partsListState() {
    return {
        parts: [],
        search: '',
        loading: true,
        totalParts: 0,
        isAdmin: false,
        availableColumns: [
            { key: 'id', label: 'ID' },
            { key: 'part_number', label: 'Číslo výkresu' },
            { key: 'article_number', label: 'Article' },
            { key: 'name', label: 'Název' },
            { key: 'material', label: 'Materiál' },
            { key: 'length', label: 'Délka' },
            { key: 'updated_at', label: 'Aktualizováno' }
        ],
        visibleColumns: { id: false, part_number: true, article_number: true, name: true, material: true, length: false, updated_at: true },
        init() {
            // Načti isAdmin z data atributu
            this.isAdmin = this.$el.dataset.isAdmin === 'true';
            // Načti uložené sloupce z localStorage (s try/catch pro private mode)
            try {
                const saved = localStorage.getItem('parts_visible_columns');
                if (saved) this.visibleColumns = JSON.parse(saved);
            } catch (e) {
                // localStorage disabled nebo private mode - použij defaults
            }
            // Načti data
            this.loadParts();
        },
        toggleColumn(key) {
            this.visibleColumns[key] = !this.visibleColumns[key];
            try {
                localStorage.setItem('parts_visible_columns', JSON.stringify(this.visibleColumns));
            } catch (e) {
                // localStorage disabled - ignoruj
            }
        },
        resetColumns() {
            this.visibleColumns = { id: false, part_number: true, article_number: true, name: true, material: true, length: false, updated_at: true };
            try {
                localStorage.setItem('parts_visible_columns', JSON.stringify(this.visibleColumns));
            } catch (e) {
                // localStorage disabled - ignoruj
            }
            window.showToast?.('✅ Sloupce resetovány na výchozí', 'success');
        },
        async loadParts() {
            this.loading = true;
            try {
                const params = new URLSearchParams();
                if (this.search) params.set('search', this.search);
                const response = await fetch(`/api/parts/search?${params}`);
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                const data = await response.json();
                this.parts = data.parts || [];
                this.totalParts = data.total || 0;
            } catch (error) {
                window.showToast?.('❌ Chyba při načítání dílů', 'error');
                this.parts = [];
                this.totalParts = 0;
            } finally {
                this.loading = false;
            }
        },
        formatDate(dateStr) {
            return new Date(dateStr).toLocaleDateString('cs-CZ', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
        },
        createPart() { window.location.href = '/parts/new'; },
        editPart(partNumber) { window.location.href = `/parts/${partNumber}/edit`; },
        async duplicatePart(partNumber) {
            if (!confirm('Duplikovat tento díl?')) return;
            try {
                const response = await fetch(`/api/parts/${partNumber}/duplicate`, { method: 'POST' });
                if (response.ok) {
                    window.showToast('✅ Díl duplikován', 'success');
                    await this.loadParts();
                } else {
                    const error = await response.json();
                    window.showToast(`❌ ${error.detail}`, 'error');
                }
            } catch (error) {
                window.showToast('❌ Chyba při duplikaci', 'error');
            }
        },
        async deletePart(partNumber) {
            if (!confirm(`Opravdu smazat díl "${partNumber}"?\n\nTato akce je nevratná!`)) return;
            try {
                const response = await fetch(`/api/parts/${partNumber}`, { method: 'DELETE' });
                if (response.ok) {
                    window.showToast('✅ Díl smazán', 'success');
                    await this.loadParts();
                } else {
                    const error = await response.json();
                    window.showToast(`❌ ${error.detail}`, 'error');
                }
            } catch (error) {
                window.showToast('❌ Chyba při mazání', 'error');
            }
        }
    };
}

// Export pro Alpine
window.partsListState = partsListState;
