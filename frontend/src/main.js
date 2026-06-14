import { createApp } from 'vue'
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'
import 'primeicons/primeicons.css'

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

  app.use(PrimeVue, {
    theme: {
      preset: Aura,
      options: {
        darkModeSelector: ':not(.light)',
        cssLayer: false,
      },
    },
  })

  app.mount('#app')
}

void bootstrap()
