// GESTIMA Design System v4.0 (tokens + components — MUST be first!)
import './assets/css/design-system.css'

// Tailwind utilities (no base reset - design-system.css handles that)
import './assets/css/tailwind.css'

// Base layout (body, main-content, autofill)
import './assets/css/base.css'

// Layout (split panels)
import './assets/css/layout.css'

// Shared module styles (split-pane, grid-layout, widgets, ribbon)
import './assets/css/modules/_shared.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import selectOnFocus from './directives/selectOnFocus'

const app = createApp(App)

app.use(createPinia())
app.use(router)

// Global directives
app.directive('select-on-focus', selectOnFocus)

app.mount('#app')
