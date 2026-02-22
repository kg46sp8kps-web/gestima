/**
 * Module Registry — static definitions for all tiling workspace modules
 *
 * Each module is lazy-loaded via dynamic import.
 * needsPart: true = module requires a partId to function
 * needsPart: false = module works independently (e.g. parts list)
 */

import type { TileModuleId, TileModuleDefinition } from '@/types/workspace'

export const MODULE_REGISTRY: Record<TileModuleId, TileModuleDefinition> = {
  'operations': {
    id: 'operations',
    label: 'Operace',
    icon: 'Settings',
    component: () => import('./TileOperations.vue'),
    needsPart: true,
  },
  'pricing': {
    id: 'pricing',
    label: 'Kalkulace',
    icon: 'Calculator',
    component: () => import('./TilePricing.vue'),
    needsPart: true,
  },
  'material': {
    id: 'material',
    label: 'Materiál',
    icon: 'Layers',
    component: () => import('./TileMaterial.vue'),
    needsPart: true,
  },
  'drawing': {
    id: 'drawing',
    label: 'Výkres',
    icon: 'FileImage',
    component: () => import('./TileDrawing.vue'),
    needsPart: true,
  },
  'production': {
    id: 'production',
    label: 'Výroba',
    icon: 'Factory',
    component: () => import('./TileProduction.vue'),
    needsPart: true,
  },
  'ai': {
    id: 'ai',
    label: 'AI',
    icon: 'Sparkles',
    component: () => import('./TileAI.vue'),
    needsPart: true,
  },
  'parts-list': {
    id: 'parts-list',
    label: 'Seznam dílů',
    icon: 'List',
    component: () => import('./TilePartsList.vue'),
    needsPart: false,
  },
}

/** All module IDs in display order */
export const MODULE_ORDER: TileModuleId[] = [
  'operations',
  'pricing',
  'material',
  'drawing',
  'production',
  'ai',
  'parts-list',
]

/** Get module definition by ID */
export function getModuleDefinition(id: TileModuleId): TileModuleDefinition {
  return MODULE_REGISTRY[id]
}
