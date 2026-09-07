import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import { setupAuthGuard } from './auth/guard'
import { router } from './router'
import './style.css'

const app = createApp(App)
app.use(createPinia())
// Register the guard before the router starts its initial navigation.
setupAuthGuard(router)
app.use(router)
app.mount('#app')
