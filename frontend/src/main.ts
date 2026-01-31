// GESTIMA Design System v1.0 (MUST be first!)
import './assets/css/design-system.css'

// Tailwind utilities (no base reset - design-system.css handles that)
import './assets/css/tailwind.css'

// Import GESTIMA CSS globally
// NOTE: variables.css and theme.css are replaced by design-system.css
import './assets/css/base.css'
import './assets/css/layout.css'
import './assets/css/components.css'
import './assets/css/forms.css'

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
