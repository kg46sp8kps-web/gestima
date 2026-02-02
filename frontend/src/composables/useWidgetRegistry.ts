/**
 * useWidgetRegistry - Global widget registration system
 *
 * Allows widgets to register themselves for discovery and dynamic loading.
 * Currently not used (widgets are loaded via component name in config),
 * but provides foundation for future widget marketplace/plugins.
 *
 * @see docs/ADR/030-universal-responsive-module-template.md
 */

import { ref, readonly } from 'vue'
import type { WidgetDefinition, WidgetType } from '@/types/widget'

// Global widget registry
const registeredWidgets = ref<Map<string, WidgetDefinition>>(new Map())

interface UseWidgetRegistryReturn {
  /**
   * Readonly access to registered widgets
   */
  widgets: Readonly<ReturnType<typeof ref<Map<string, WidgetDefinition>>>>

  /**
   * Register a widget
   */
  registerWidget: (definition: WidgetDefinition) => void

  /**
   * Unregister a widget
   */
  unregisterWidget: (id: string) => void

  /**
   * Get widget by ID
   */
  getWidget: (id: string) => WidgetDefinition | undefined

  /**
   * Get all registered widgets
   */
  getAllWidgets: () => WidgetDefinition[]

  /**
   * Get widgets by type
   */
  getWidgetsByType: (type: WidgetType) => WidgetDefinition[]
}

export function useWidgetRegistry(): UseWidgetRegistryReturn {
  /**
   * Register a widget
   */
  function registerWidget(definition: WidgetDefinition) {
    if (registeredWidgets.value.has(definition.id)) {
      console.warn(`Widget '${definition.id}' already registered`)
      return
    }
    registeredWidgets.value.set(definition.id, definition)
  }

  /**
   * Unregister a widget
   */
  function unregisterWidget(id: string) {
    registeredWidgets.value.delete(id)
  }

  /**
   * Get widget by ID
   */
  function getWidget(id: string): WidgetDefinition | undefined {
    return registeredWidgets.value.get(id)
  }

  /**
   * Get all registered widgets
   */
  function getAllWidgets(): WidgetDefinition[] {
    return Array.from(registeredWidgets.value.values())
  }

  /**
   * Get widgets by type
   */
  function getWidgetsByType(type: WidgetType): WidgetDefinition[] {
    return getAllWidgets().filter(w => w.type === type)
  }

  return {
    widgets: readonly(registeredWidgets),
    registerWidget,
    unregisterWidget,
    getWidget,
    getAllWidgets,
    getWidgetsByType
  }
}
