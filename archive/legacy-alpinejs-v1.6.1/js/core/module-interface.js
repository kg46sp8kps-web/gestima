/**
 * GESTIMA Module Interface (ADR-023)
 *
 * Base interface for workspace modules. All modules MUST implement these
 * properties and methods to be workspace-compatible.
 *
 * Usage:
 *   function myModule(config) {
 *       return {
 *           ...ModuleInterface.create(config),
 *           // module-specific state and methods
 *       };
 *   }
 *
 * @version 1.0.0
 * @see docs/ADR/023-workspace-module-architecture.md
 */

const ModuleInterface = {
    /**
     * Create base module properties with defaults
     *
     * @param {Object} config - Configuration object
     * @param {string} config.moduleType - Required module type
     * @param {string} [config.moduleId] - Optional instance ID
     * @param {string|null} [config.linkColor] - Optional link color
     * @returns {Object} Base module properties
     */
    create(config) {
        if (!config.moduleType) {
            throw new Error('ModuleInterface: moduleType is required');
        }

        return {
            // Identity
            moduleType: config.moduleType,
            moduleId: config.moduleId || `${config.moduleType}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            linkColor: config.linkColor || null,
            linkContext: {},

            /**
             * Initialize the module
             * Called after Alpine.js mounts the component
             */
            init() {
                if (this.linkColor && window.LinkManager) {
                    window.LinkManager.subscribe(this.linkColor, this);
                }
            },

            /**
             * React to link context changes
             * @param {Object} context - New context from the link
             */
            onLinkChange(context) {
                this.linkContext = context;
            },

            /**
             * Clean up the module
             */
            destroy() {
                if (this.linkColor && window.LinkManager) {
                    window.LinkManager.unsubscribe(this.linkColor, this);
                }
            },

            /**
             * Emit data to connected modules on the same link
             * @param {string} eventType - Type of event
             * @param {Object} data - Data to emit
             */
            emitToLink(eventType, data) {
                if (this.linkColor && window.LinkManager) {
                    window.LinkManager.emit(this.linkColor, {
                        source: this.moduleId,
                        type: eventType,
                        data: data
                    });
                }
            }
        };
    },

    /**
     * Validate that an object implements the module interface
     *
     * @param {Object} module - Module instance to validate
     * @returns {boolean} True if valid
     * @throws {Error} If missing required properties/methods
     */
    validate(module) {
        const required = ['moduleType', 'moduleId', 'init', 'onLinkChange', 'destroy', 'emitToLink'];
        const missing = required.filter(prop => !(prop in module));

        if (missing.length > 0) {
            throw new Error(`ModuleInterface: Missing required members: ${missing.join(', ')}`);
        }

        if (typeof module.moduleType !== 'string' || module.moduleType === '') {
            throw new Error('ModuleInterface: moduleType must be a non-empty string');
        }

        return true;
    }
};

// Export to window for global access
window.ModuleInterface = ModuleInterface;
