import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key, params) => (params ? `${key}:${JSON.stringify(params)}` : key),
  }),
}))

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    apiFetch: vi.fn(),
    apiGet: vi.fn().mockResolvedValue(null),
  }),
}))

const { useLogs } = await import('@/composables/useLogs')

// The composable owns the ``search`` ref, so we mount a tiny harness
// component to expose ``lineSegments`` and the search input together.
const Harness = defineComponent({
  setup(_, { expose }) {
    const api = useLogs()
    expose(api)
    return () => h('div')
  },
})

describe('useLogs.lineSegments', () => {
  it('returns a single non-highlight segment when search is empty', () => {
    const w = mount(Harness)
    const segs = w.vm.lineSegments('plain log line')
    expect(segs).toEqual([{ text: 'plain log line', highlight: false }])
  })

  it('renders match segments around the search term', () => {
    const w = mount(Harness)
    w.vm.search = 'Error'
    const segs = w.vm.lineSegments('an Error here Error again')
    expect(segs).toEqual([
      { text: 'an ', highlight: false },
      { text: 'Error', highlight: true },
      { text: ' here ', highlight: false },
      { text: 'Error', highlight: true },
      { text: ' again', highlight: false },
    ])
  })

  it('matches case-insensitively but preserves original casing', () => {
    const w = mount(Harness)
    w.vm.search = 'ERROR'
    const segs = w.vm.lineSegments('mixed Error and ERROR')
    expect(segs[1]).toEqual({ text: 'Error', highlight: true })
    expect(segs[3]).toEqual({ text: 'ERROR', highlight: true })
  })

  it('treats search term as literal (no regex escapes)', () => {
    const w = mount(Harness)
    w.vm.search = '.*+?'
    expect(w.vm.lineSegments('contains .*+? exact')).toEqual([
      { text: 'contains ', highlight: false },
      { text: '.*+?', highlight: true },
      { text: ' exact', highlight: false },
    ])
  })

  it('returns a single segment when the search term is missing from the line', () => {
    const w = mount(Harness)
    w.vm.search = 'absent'
    expect(w.vm.lineSegments('present only')).toEqual([
      { text: 'present only', highlight: false },
    ])
  })
})

describe('LogsView segment rendering', () => {
  it('renders hostile html-looking content as plain text, never as a tag', () => {
    const RenderHarness = defineComponent({
      setup() {
        const api = useLogs()
        api.search.value = 'alert'
        return () => h(
          'div',
          {},
          api.lineSegments('<script>alert(1)</script>').map((seg) =>
            seg.highlight
              ? h('mark', { class: 'log-highlight' }, seg.text)
              : seg.text,
          ),
        )
      },
    })
    const w = mount(RenderHarness)
    expect(w.html()).not.toContain('<script>')
    expect(w.text()).toContain('<script>alert(1)</script>')
  })
})
