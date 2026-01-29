// GESTIMA Design System v1.0 (MUST be first!)
import './assets/css/design-system.css'

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

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
