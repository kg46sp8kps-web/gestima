/**
 * GESTIMA Link Manager (ADR-023)
 *
 * Central communication hub for workspace modules.
 * Modules subscribe to colored "links" and receive context updates
 * when other modules on the same link emit changes.
 *
 * Usage:
 *   LinkManager.subscribe('red', myModule);
 *   LinkManager.emit('red', { source: 'parts-123', type: 'select', data: { partId: 456 } });
 *
 * @version 1.0.0
 * @see docs/ADR/023-workspace-module-architecture.md
 */

const LinkManager = {
    /**
     * Available link colors
     */
    COLORS: ['red', 'green', 'blue', 'yellow', 'purple'],

    /**
     * Link contexts (state per color)
     * @private
     */
    _links: {
        red: {},
        green: {},
        blue: {},
        yellow: {},
        purple: {}
    },

    /**
     * Subscribers per link color
     * @private
     */
    _subscribers: new Map(),

    /**
     * localStorage key
     * @private
     */
    _storageKey: 'gestima_link_state',

    /**
     * Emit a change to all subscribers on a link
     *
     * @param {string} color - Link color
     * @param {Object} payload - Event payload
     * @param {string} payload.source - Source module ID
     * @param {string} payload.type - Event type
     * @param {Object} payload.data - Data to merge into context
     */
    emit(color, payload) {
        if (!this.COLORS.includes(color)) {
            console.warn(`[LinkManager] Invalid link color: ${color}`);
            return;
        }

        const { source, type, data } = payload;

        // Update link context
        this._links[color] = {
            ...this._links[color],
            ...data,
            _lastEvent: type,
            _lastSource: source,
            _timestamp: Date.now()
        };

        // Notify subscribers (except source)
        const subs = this._subscribers.get(color) || [];
        subs.forEach(module => {
            if (module.moduleId !== source) {
                try {
                    module.onLinkChange(this._links[color]);
                } catch (e) {
                    console.error(`[LinkManager] Error in onLinkChange for ${module.moduleId}:`, e);
                }
            }
        });

        this._persistState();

        console.debug(`[LinkManager] Emit on ${color}:`, { source, type, data, subscribers: subs.length });
    },

    /**
     * Subscribe a module to a link
     *
     * @param {string} color - Link color
     * @param {Object} module - Module with onLinkChange method
     */
    subscribe(color, module) {
        if (!this.COLORS.includes(color)) {
            console.warn(`[LinkManager] Invalid link color: ${color}`);
            return;
        }

        if (!module || typeof module.onLinkChange !== 'function') {
            console.warn('[LinkManager] Module must have onLinkChange method');
            return;
        }

        if (!this._subscribers.has(color)) {
            this._subscribers.set(color, []);
        }

        const subs = this._subscribers.get(color);

        // Avoid duplicates
        if (!subs.find(m => m.moduleId === module.moduleId)) {
            subs.push(module);
            console.debug(`[LinkManager] Subscribed ${module.moduleId} to ${color} link`);
        }

        // Send current context immediately
        if (Object.keys(this._links[color]).length > 0) {
            try {
                module.onLinkChange(this._links[color]);
            } catch (e) {
                console.error(`[LinkManager] Error in initial onLinkChange for ${module.moduleId}:`, e);
            }
        }
    },

    /**
     * Unsubscribe a module from a link
     *
     * @param {string} color - Link color
     * @param {Object} module - Module to unsubscribe
     */
    unsubscribe(color, module) {
        const subs = this._subscribers.get(color);
        if (!subs) return;

        const index = subs.findIndex(m => m.moduleId === module.moduleId);
        if (index > -1) {
            subs.splice(index, 1);
            console.debug(`[LinkManager] Unsubscribed ${module.moduleId} from ${color} link`);
        }
    },

    /**
     * Get current context for a link
     * @param {string} color
     * @returns {Object}
     */
    getContext(color) {
        return this._links[color] || {};
    },

    /**
     * Set context directly (without notifying)
     * @param {string} color
     * @param {Object} context
     */
    setContext(color, context) {
        if (this.COLORS.includes(color)) {
            this._links[color] = { ...context };
            this._persistState();
        }
    },

    /**
     * Clear a link's context
     * @param {string} color
     * @param {boolean} [notify=true]
     */
    clearContext(color, notify = true) {
        if (!this.COLORS.includes(color)) return;

        this._links[color] = {};
        this._persistState();

        if (notify) {
            const subs = this._subscribers.get(color) || [];
            subs.forEach(module => {
                try {
                    module.onLinkChange({});
                } catch (e) {
                    console.error(`[LinkManager] Error clearing context for ${module.moduleId}:`, e);
                }
            });
        }
    },

    /**
     * Get subscribers for a link (debugging)
     * @param {string} color
     * @returns {Array<string>}
     */
    getSubscribers(color) {
        const subs = this._subscribers.get(color) || [];
        return subs.map(m => m.moduleId);
    },

    /**
     * Persist to localStorage
     * @private
     */
    _persistState() {
        try {
            const state = {};
            this.COLORS.forEach(color => {
                const ctx = { ...this._links[color] };
                delete ctx._lastEvent;
                delete ctx._lastSource;
                delete ctx._timestamp;

                if (Object.keys(ctx).length > 0) {
                    state[color] = ctx;
                }
            });

            if (Object.keys(state).length > 0) {
                localStorage.setItem(this._storageKey, JSON.stringify(state));
            } else {
                localStorage.removeItem(this._storageKey);
            }
        } catch (e) {
            console.debug('[LinkManager] Could not persist state:', e.message);
        }
    },

    /**
     * Restore from localStorage
     */
    restoreState() {
        try {
            const saved = localStorage.getItem(this._storageKey);
            if (saved) {
                const state = JSON.parse(saved);
                this.COLORS.forEach(color => {
                    if (state[color]) {
                        this._links[color] = { ...this._links[color], ...state[color] };
                    }
                });
                console.debug('[LinkManager] Restored state:', state);
            }
        } catch (e) {
            console.warn('[LinkManager] Failed to restore state:', e.message);
        }
    },

    /**
     * Reset all state
     */
    reset() {
        this._links = {
            red: {},
            green: {},
            blue: {},
            yellow: {},
            purple: {}
        };
        this._subscribers.clear();
        try {
            localStorage.removeItem(this._storageKey);
        } catch (e) {
            // Ignore
        }
    },

    /**
     * Get emoji for link color
     * @param {string} color
     * @returns {string}
     */
    getColorEmoji(color) {
        const emojis = {
            red: '🔴',
            green: '🟢',
            blue: '🔵',
            yellow: '🟡',
            purple: '🟣'
        };
        return emojis[color] || '⚪';
    },

    /**
     * Get CSS color value
     * @param {string} color
     * @returns {string}
     */
    getColorCSS(color) {
        const colors = {
            red: '#ef4444',
            green: '#22c55e',
            blue: '#3b82f6',
            yellow: '#eab308',
            purple: '#a855f7'
        };
        return colors[color] || '#9ca3af';
    }
};

// Export to window
window.LinkManager = LinkManager;

// Auto-restore on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    LinkManager.restoreState();
});
