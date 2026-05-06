import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    environmentOptions: {
      jsdom: { url: 'http://localhost/' },
    },
    globals: true,
    setupFiles: ['./src/__tests__/setup.js'],
    include: ['src/**/*.{test,spec}.{js,mjs}'],
    exclude: ['**/node_modules/**', '**/dist/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      include: ['src/**/*.{js,vue}'],
      exclude: [
        'src/**/*.{test,spec}.{js,mjs}',
        'src/**/__tests__/**',
        'src/main.js',
        'src/router/**',
        'src/locales/**',
      ],
      // Progressive floor. Baseline 2026-05-06: statements 3.51% / branches
      // 2.49% / functions 2.41% / lines 3.66%. Threshold 2 prevents obvious
      // regressions and should be raised as smoke tests grow.
      thresholds: {
        statements: 2,
        branches: 2,
        functions: 2,
        lines: 2,
      },
    },
  },
})
