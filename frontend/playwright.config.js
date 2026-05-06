// Playwright config — MediaKeeper frontend E2E baseline.
//
// Runs against the production-like Vite preview build, with all backend
// traffic intercepted by route mocks (see e2e/_fixtures/api-mocks.js).
// No real backend, no NAS, no DB, no secrets.

import { defineConfig, devices } from '@playwright/test'

const PORT = Number(process.env.MK_E2E_PORT || 4173)
const HOST = process.env.MK_E2E_HOST || '127.0.0.1'
const BASE_URL = `http://${HOST}:${PORT}`
const isCI = !!process.env.CI

export default defineConfig({
  testDir: './e2e',
  testMatch: /.*\.spec\.js$/,
  fullyParallel: true,
  forbidOnly: isCI,
  retries: isCI ? 1 : 0,
  workers: isCI ? 1 : undefined,
  timeout: 30_000,
  expect: { timeout: 7_000 },
  reporter: isCI ? [['list'], ['html', { open: 'never' }]] : 'list',
  outputDir: 'test-results',

  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 7_000,
    navigationTimeout: 15_000,
  },

  projects: [
    {
      name: 'chromium-desktop',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 800 },
      },
    },
    {
      name: 'chromium-mobile',
      use: { ...devices['Pixel 5'] },
    },
  ],

  // Build once, then serve dist with Vite preview. No backend needed:
  // every /api/** call is intercepted by the per-test mock layer.
  webServer: {
    command: `npm run build && npx vite preview --host ${HOST} --port ${PORT} --strictPort`,
    url: BASE_URL,
    reuseExistingServer: !isCI,
    stdout: 'ignore',
    stderr: 'pipe',
    timeout: 180_000,
  },
})
