import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import VueI18nPlugin from '@intlify/unplugin-vue-i18n/vite'
import { resolve } from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, import.meta.dirname, '')
  return {
    plugins: [
      vue(),
      VueI18nPlugin({
        runtimeOnly: true,
        compositionOnly: true,
        fullInstall: false,
        jitCompilation: false,
        strictMessage: false,
        include: [resolve(import.meta.dirname, 'src/locales/**')],
      }),
    ],
    resolve: {
      alias: {
        '@': resolve(import.meta.dirname, 'src'),
      },
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: env.API_TARGET || 'http://localhost:8888',
          changeOrigin: true,
          xfwd: true,
          // Chat WebSocket: proxied too (see the Origin rewrite below).
          ws: true,
          cookieDomainRewrite: 'localhost',
          configure: proxy => {
            // Dev-only: rewrite the browser Origin (:5173) to the proxy target so
            // the backend's same-origin CSRF guard sees a same-origin request.
            // `changeOrigin` rewrites Host but NOT Origin — without this, every
            // login / authenticated mutation from :5173 is 403 csrf_origin_mismatch.
            const apiTarget = env.API_TARGET || 'http://localhost:8888'
            proxy.on('proxyReq', proxyReq => {
              proxyReq.setHeader('origin', apiTarget)
            })
            // Same for the chat socket, but only from pages this dev server serves: the
            // Origin check is the socket's only guard, and any other localhost port is
            // same-site. The dev backend leaves FRONTEND_ORIGIN unset or lists API_TARGET.
            proxy.on('proxyReqWs', (proxyReq, req) => {
              if (req.headers.origin === `http://${req.headers.host}`) {
                proxyReq.setHeader('origin', apiTarget)
              }
            })
            proxy.on('proxyRes', proxyRes => {
              const setCookie = proxyRes.headers['set-cookie']
              if (setCookie) {
                proxyRes.headers['set-cookie'] = setCookie.map(cookie =>
                  cookie.replace(/;\s*Secure/gi, '').replace(/;\s*Domain=[^;]*/gi, ''),
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
