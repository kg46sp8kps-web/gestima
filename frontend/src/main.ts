import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { registerDirectives } from './directives/selectOnFocus'

import './assets/css/design-system.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
registerDirectives(app)

app.mount('#app')
