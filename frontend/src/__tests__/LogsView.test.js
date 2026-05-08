import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: key => key }),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {}, path: '/admin/logs' }),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}))

// Mock the formatter so the test doesn't depend on the host's local
// timezone — we just verify which input the template feeds it.
vi.mock('@/utils/logsTime', () => ({
  formatFileDate: vi.fn(iso => `LOCAL[${iso}]`),
  formatLogLine: vi.fn(line => line),
}))

vi.mock('@/composables/useLogs', () => ({
  useLogs: () => ({
    files: ref([
      {
        filename: 'mediakeeper.txt',
        modified: '2026-05-08T12:41:00Z',
        modified_label: '08/05/2026 12:41 UTC-RAW',
        size: 1024,
        size_label: '1 KB',
      },
    ]),
    loadingFiles: ref(false),
    debugEnabled: ref(false),
    currentFile: ref(null),
    rawLines: ref([]),
    search: ref(''),
    autoRefresh: ref(false),
    filters: ref({ INFO: true, DEBUG: true, WARNING: true, ERROR: true, CRITICAL: true }),
    filterModule: ref(''),
    detectedModules: ref([]),
    filteredLines: ref([]),
    displayLines: ref([]),
    statusText: ref(''),
    countText: ref(''),
    lineClass: () => '',
    lineSegments: () => [],
    fetchFiles: vi.fn(),
    loadDebugMode: vi.fn(),
    toggleDebug: vi.fn(),
    viewFile: vi.fn(),
    backToFiles: vi.fn(),
    downloadFile: vi.fn(),
    toggleAutoRefresh: vi.fn(),
  }),
}))

const { default: LogsView } = await import('@/views/LogsView.vue')

describe('LogsView — file date rendering', () => {
  it('feeds f.modified (ISO UTC) to formatFileDate, not modified_label', async () => {
    const w = mount(LogsView)
    await flushPromises()
    const date = w.find('.file-date')
    expect(date.exists()).toBe(true)
    expect(date.text()).toBe('LOCAL[2026-05-08T12:41:00Z]')
    expect(date.text()).not.toContain('UTC-RAW')
  })
})
