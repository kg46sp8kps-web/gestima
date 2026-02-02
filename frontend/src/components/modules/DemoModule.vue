<script setup lang="ts">
/**
 * DemoModule.vue - Demonstrates CustomizableModule template
 *
 * Shows all features:
 * - Drag & drop widgets
 * - Resize widgets
 * - Edit mode toggle
 * - Save/load layouts (localStorage)
 * - Add/remove optional widgets
 * - Reset to default
 * - Export/import layouts
 * - Responsive breakpoints
 */

import { ref, computed } from 'vue'
import CustomizableModule from '@/components/layout/CustomizableModule.vue'
import { demoConfig } from '@/config/layouts/demo'

// Demo data
const currentUser = ref({
  name: 'Demo User',
  role: 'Administrator',
  lastLogin: new Date().toISOString()
})

const stats = ref({
  totalModules: 7,
  migratedModules: 0,
  codeReduction: '47%',
  status: 'Ready for migration'
})

// Widget context - data předávaná jednotlivým widgetům
const widgetContext = computed(() => ({
  // Demo Info widget - zobrazí user informace
  'demo-info': {
    fields: [
      { label: 'User', value: currentUser.value.name, format: 'text' },
      { label: 'Role', value: currentUser.value.role, format: 'text' },
      { label: 'Last Login', value: currentUser.value.lastLogin, format: 'date' },
      { label: 'Module', value: 'CustomizableModule Demo', format: 'text' }
    ]
  },

  // Demo Actions widget - akční tlačítka
  'demo-actions': {
    actions: [
      {
        id: 'refresh',
        label: 'Refresh',
        icon: 'RefreshCw',
        color: '#2563eb'
      },
      {
        id: 'settings',
        label: 'Settings',
        icon: 'Settings',
        color: '#059669'
      },
      {
        id: 'help',
        label: 'Help',
        icon: 'HelpCircle',
        color: '#7c3aed'
      },
      {
        id: 'export',
        label: 'Export',
        icon: 'Download',
        color: '#ea580c'
      }
    ]
  },

  // Demo Stats widget - statistiky
  'demo-stats': {
    fields: [
      { label: 'Total Modules', value: stats.value.totalModules, format: 'number' },
      { label: 'Migrated', value: stats.value.migratedModules, format: 'number' },
      { label: 'Code Reduction', value: stats.value.codeReduction, format: 'text' },
      { label: 'Status', value: stats.value.status, format: 'text' }
    ]
  },

  // Demo Welcome widget - uvítací zpráva
  'demo-welcome': {
    fields: [
      {
        label: '👋 Welcome to CustomizableModule Demo',
        value: 'Click "Edit Layout" to customize this view!',
        format: 'text'
      }
    ]
  }
}))

// Widget action handler
function handleWidgetAction(widgetId: string, action: string, payload?: any) {
  console.log('Widget action:', { widgetId, action, payload })

  // Handle specific actions
  if (action === 'action:refresh') {
    console.log('Refreshing data...')
    stats.value.totalModules++
  }

  if (action === 'action:settings') {
    console.log('Opening settings...')
  }

  if (action === 'action:help') {
    console.log('Opening help...')
  }

  if (action === 'action:export') {
    console.log('Exporting data...')
  }
}
</script>

<template>
  <div class="demo-module">
    <!-- Info banner -->
    <div class="demo-banner">
      <h2>🎨 CustomizableModule Template Demo</h2>
      <p>
        Tento modul demonstruje všechny funkce universal template systému.
        Klikni na "Edit Layout" tlačítko v toolbaru pro customizaci!
      </p>
      <ul class="demo-features">
        <li>✅ Drag & drop widgety</li>
        <li>✅ Resize widgety (tahej za pravý dolní roh)</li>
        <li>✅ Přidej/odstraň volitelné widgety</li>
        <li>✅ Uložit/načíst vlastní layout (localStorage)</li>
        <li>✅ Export/import layoutu (JSON)</li>
        <li>✅ Reset na výchozí layout</li>
        <li>✅ Responsive breakpoints (změní okno!)</li>
      </ul>
    </div>

    <!-- CustomizableModule Template -->
    <CustomizableModule
      :config="demoConfig"
      :widget-context="widgetContext"
      @widget-action="handleWidgetAction"
    />
  </div>
</template>

<style scoped>
.demo-module {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--bg-base);
}

.demo-banner {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: var(--space-6);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
}

.demo-banner h2 {
  margin: 0 0 var(--space-3) 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
}

.demo-banner p {
  margin: 0 0 var(--space-4) 0;
  font-size: var(--text-base);
  opacity: 0.95;
}

.demo-features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.demo-features li {
  font-size: var(--text-sm);
  opacity: 0.9;
}

/* Responsive: Full width on narrow screens */
@media (max-width: 768px) {
  .demo-module {
    padding: var(--space-2);
    gap: var(--space-2);
  }

  .demo-banner {
    padding: var(--space-4);
  }

  .demo-features {
    grid-template-columns: 1fr;
  }
}
</style>
