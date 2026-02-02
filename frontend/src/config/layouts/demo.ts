/**
 * Demo Module Layout Configuration
 *
 * Showcases CustomizableModule features:
 * - Multiple widget types
 * - Drag & drop
 * - Resize
 * - Compact vs Comfortable layouts
 * - Required vs Optional widgets
 */

import type { ModuleLayoutConfig } from '@/types/widget'

export const demoConfig: ModuleLayoutConfig = {
  moduleKey: 'demo-module',
  cols: 12,
  rowHeight: 60,

  widgets: [
    // Info Card - zobrazuje informace
    {
      id: 'demo-info',
      type: 'info-card',
      title: 'Demo Information',
      component: 'InfoCard',
      minWidth: 2,
      minHeight: 2,
      defaultWidth: 6,
      defaultHeight: 3,
      resizable: true,
      removable: false,
      required: true  // Tento widget nelze odstranit
    },

    // Action Bar - akční tlačítka
    {
      id: 'demo-actions',
      type: 'action-bar',
      title: 'Quick Actions',
      component: 'ActionBar',
      minWidth: 2,
      minHeight: 2,
      defaultWidth: 6,
      defaultHeight: 2,
      resizable: true,
      removable: false,
      required: true
    },

    // Další Info Card - volitelný
    {
      id: 'demo-stats',
      type: 'info-card',
      title: 'Statistics',
      component: 'InfoCard',
      minWidth: 2,
      minHeight: 2,
      defaultWidth: 4,
      defaultHeight: 2,
      resizable: true,
      removable: true,  // Tento widget lze odstranit
      required: false
    },

    // Welcome widget - volitelný
    {
      id: 'demo-welcome',
      type: 'info-card',
      title: 'Welcome',
      component: 'InfoCard',
      minWidth: 2,
      minHeight: 1,
      defaultWidth: 8,
      defaultHeight: 1,
      resizable: true,
      removable: true,
      required: false
    }
  ],

  // Přednastavené layouty
  defaultLayouts: {
    // Compact layout - všechno pod sebou
    compact: [
      { i: 'demo-info', x: 0, y: 0, w: 12, h: 3 },
      { i: 'demo-actions', x: 0, y: 3, w: 12, h: 2 },
      { i: 'demo-stats', x: 0, y: 5, w: 12, h: 2 },
      { i: 'demo-welcome', x: 0, y: 7, w: 12, h: 1 }
    ],

    // Comfortable layout - vedle sebe
    comfortable: [
      { i: 'demo-info', x: 0, y: 0, w: 6, h: 4 },
      { i: 'demo-actions', x: 6, y: 0, w: 6, h: 2 },
      { i: 'demo-stats', x: 6, y: 2, w: 6, h: 2 },
      { i: 'demo-welcome', x: 0, y: 4, w: 12, h: 1 }
    ]
  }
}
