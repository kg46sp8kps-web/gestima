/**
 * Part Detail Module Layout Configuration
 *
 * Defines widget layout for part detail panel.
 * Two widgets: info edit form + action buttons.
 */

import type { ModuleLayoutConfig } from '@/types/widget'

export const partDetailConfig: ModuleLayoutConfig = {
  moduleKey: 'part-detail',
  cols: 12,
  rowHeight: 60,

  widgets: [
    {
      id: 'part-info-edit',
      type: 'form',
      title: 'Part Information',
      component: 'PartInfoEdit',
      minWidth: 4,
      minHeight: 3,
      defaultWidth: 12,
      defaultHeight: 4,
      resizable: true,
      removable: false,
      required: true
    },
    {
      id: 'part-actions',
      type: 'action-bar',
      title: 'Actions',
      component: 'PartActions',
      minWidth: 4,
      minHeight: 2,
      defaultWidth: 12,
      defaultHeight: 2,
      resizable: true,
      removable: false,
      required: true
    }
  ],

  defaultLayouts: {
    compact: [
      { i: 'part-info-edit', x: 0, y: 0, w: 12, h: 4 },
      { i: 'part-actions', x: 0, y: 4, w: 12, h: 2 }
    ],
    comfortable: [
      { i: 'part-info-edit', x: 0, y: 0, w: 12, h: 4 },
      { i: 'part-actions', x: 0, y: 4, w: 12, h: 2 }
    ]
  }
}
