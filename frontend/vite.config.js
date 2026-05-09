import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import VueI18nPlugin from '@intlify/unplugin-vue-i18n/vite'
import { resolve } from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, __dirname, '')
  return {
    plugins: [
      vue(),
      VueI18nPlugin({
        runtimeOnly: true,
        compositionOnly: true,
        fullInstall: false,
        jitCompilation: false,
        strictMessage: false,
        include: [resolve(__dirname, 'src/locales/**')],
      }),
    ],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
      },
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: env.API_TARGET || 'http://localhost:8888',
          changeOrigin: true,
          xfwd: true,
          cookieDomainRewrite: 'localhost',
          configure: (proxy) => {
            proxy.on('proxyRes', (proxyRes) => {
              const setCookie = proxyRes.headers['set-cookie']
              if (setCookie) {
                proxyRes.headers['set-cookie'] = setCookie.map(cookie =>
                  cookie
                    .replace(/;\s*Secure/gi, '')
                    .replace(/;\s*Domain=[^;]*/gi, '')
                )
              }
            })
          },
        },
      },
    },
    build: {
      outDir: 'dist',
      emptyOutDir: true,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) return
            if (id.includes('primevue') || id.includes('@primevue') || id.includes('primeicons')) return 'vendor-ui'
            if (id.includes('lucide-vue-next')) return 'vendor-icons'
            if (id.includes('grid-layout-plus')) return 'vendor-dashboard'
            if (id.includes('vue-i18n')) return 'vendor-i18n'
            if (id.includes('vue-router') || id.includes('/vue/')) return 'vendor-vue'
          },
        },
      },
    },
  }
})
