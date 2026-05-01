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
