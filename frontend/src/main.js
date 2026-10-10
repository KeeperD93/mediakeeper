import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import i18n, { initializeLocale } from './i18n'
import { setToastRouter } from './composables/useToast'
import './styles/main.css'
import './assets/mediamanager.css'

async function bootstrap() {
  await initializeLocale()

  const app = createApp(App)

  // Global safety net: any error a component does not handle itself must still
  // be logged, never silently swallowed (network failures used to vanish with
  // no console trace). Per-surface handlers still show the user-facing toast.
  app.config.errorHandler = (err, _instance, info) => {
    console.error(`[app.errorHandler] ${info}`, err)
  }
  window.addEventListener('unhandledrejection', event => {
    console.error('[app.unhandledRejection]', event.reason)
  })

  app.use(router)
  setToastRouter(router)
  app.use(i18n)

  app.mount('#app')
}

void bootstrap()
