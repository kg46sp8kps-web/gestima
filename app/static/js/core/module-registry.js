/**
 * GESTIMA Module Registry (ADR-023)
 *
 * Central registry for all available workspace module types.
 * Modules register themselves here; workspace uses this to create instances.
 *
 * Usage:
 *   // Register a module type
 *   ModuleRegistry.register('batch-sets', batchSetsModule, {
 *       icon: '💰',
 *       description: 'Cenové sady'
 *   });
 *
 *   // Create an instance
 *   const module = ModuleRegistry.create('batch-sets', { partId: 123 });
 *
 * @version 1.0.0
 * @see docs/ADR/023-workspace-module-architecture.md
 */

const ModuleRegistry = {
    /**
     * Registered module types
     * @private
     */
    _types: {},

    /**
     * Register a module factory function
     *
     * @param {string} type - Module type identifier
     * @param {Function} factory - Factory function that returns module object
     * @param {Object} [meta] - Optional metadata
     * @param {Array<string>} [meta.emits] - Context fields this module emits
     * @param {Array<string>} [meta.consumes] - Context fields this module consumes
     */
    register(type, factory, meta = {}) {
        if (typeof type !== 'string' || type === '') {
            throw new Error('ModuleRegistry: type must be a non-empty string');
        }
        if (typeof factory !== 'function') {
            throw new Error('ModuleRegistry: factory must be a function');
        }

        this._types[type] = {
            factory: factory,
            meta: {
                type: type,
                icon: meta.icon || this.getIcon(type),
                description: meta.description || this.getDescription(type),
                category: meta.category || 'general',
                emits: meta.emits || [],
                consumes: meta.consumes || []
            }
        };

        console.debug(`[ModuleRegistry] Registered: ${type}`);
    },

    /**
     * Create a module instance
     *
     * @param {string} type - Module type
     * @param {Object} [config] - Configuration passed to factory
     * @returns {Object} Module instance
     */
    create(type, config = {}) {
        const registration = this._types[type];
        if (!registration) {
            throw new Error(`ModuleRegistry: Unknown module type '${type}'. Available: ${Object.keys(this._types).join(', ')}`);
        }

        const module = registration.factory(config);

        // Validate interface in development
        if (window.ModuleInterface) {
            try {
                window.ModuleInterface.validate(module);
            } catch (e) {
                console.warn(`[ModuleRegistry] Module '${type}' interface warning:`, e.message);
            }
        }

        return module;
    },

    /**
     * Check if a module type is registered
     * @param {string} type - Module type
     * @returns {boolean}
     */
    has(type) {
        return type in this._types;
    },

    /**
     * Get metadata for a module type
     * @param {string} type - Module type
     * @returns {Object|null}
     */
    getMeta(type) {
        const registration = this._types[type];
        return registration ? registration.meta : null;
    },

    /**
     * List all available module types
     * @param {string} [category] - Optional filter
     * @returns {Array<Object>}
     */
    listAvailable(category = null) {
        let modules = Object.values(this._types).map(t => t.meta);

        if (category) {
            modules = modules.filter(m => m.category === category);
        }

        return modules.sort((a, b) => a.description.localeCompare(b.description, 'cs'));
    },

    /**
     * Get default icon for module type
     * @param {string} type
     * @returns {string}
     */
    getIcon(type) {
        const icons = {
            'parts': '📋',
            'batch-sets': '💰',
            'operations': '🔧',
            'features': '✨',
            'quotes': '📄',
            'customers': '👥',
            'orders': '📦',
            'work-orders': '🏭',
            'materials': '🔩',
            'work-centers': '⚙️'
        };
        return icons[type] || '📁';
    },

    /**
     * Get default description for module type (Czech)
     * @param {string} type
     * @returns {string}
     */
    getDescription(type) {
        const descriptions = {
            'parts': 'Seznam dílů',
            'batch-sets': 'Cenové sady',
            'operations': 'Operace dílu',
            'features': 'Kroky operací',
            'quotes': 'Nabídky pro zákazníky',
            'customers': 'Zákazníci',
            'orders': 'Objednávky',
            'work-orders': 'Výrobní příkazy',
            'materials': 'Katalog materiálů',
            'work-centers': 'Pracovní centra'
        };
        return descriptions[type] || type;
    },

    /**
     * Check if two module types are compatible for linking
     * Compatible = one emits what the other consumes
     *
     * @param {string} type1 - First module type
     * @param {string} type2 - Second module type
     * @returns {{ compatible: boolean, reason: string }}
     */
    checkCompatibility(type1, type2) {
        const meta1 = this.getMeta(type1);
        const meta2 = this.getMeta(type2);

        if (!meta1 || !meta2) {
            return { compatible: false, reason: 'Neznámý typ modulu' };
        }

        // Check if type1 emits something type2 consumes
        const type1EmitsForType2 = meta1.emits.some(e => meta2.consumes.includes(e));
        // Check if type2 emits something type1 consumes
        const type2EmitsForType1 = meta2.emits.some(e => meta1.consumes.includes(e));

        if (type1EmitsForType2 || type2EmitsForType1) {
            return { compatible: true, reason: 'Moduly sdílejí kompatibilní kontext' };
        }

        // If both have no emits/consumes defined, assume compatible (legacy)
        if (meta1.emits.length === 0 && meta1.consumes.length === 0 &&
            meta2.emits.length === 0 && meta2.consumes.length === 0) {
            return { compatible: true, reason: 'Kompatibilita neurčena' };
        }

        return {
            compatible: false,
            reason: `${meta1.description} a ${meta2.description} nesdílejí kontext`
        };
    },

    /**
     * Get compatible module types for a given type
     * @param {string} type - Module type
     * @returns {Array<string>} Compatible types
     */
    getCompatibleTypes(type) {
        const allTypes = Object.keys(this._types);
        return allTypes.filter(t => t !== type && this.checkCompatibility(type, t).compatible);
    },

    /**
     * Unregister a module type (for testing)
     * @param {string} type
     */
    unregister(type) {
        delete this._types[type];
    },

    /**
     * Clear all registrations (for testing)
     */
    clear() {
        this._types = {};
    }
};

// Export to window
window.ModuleRegistry = ModuleRegistry;
