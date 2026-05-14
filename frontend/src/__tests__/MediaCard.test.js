import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'

vi.mock('vue-i18n', async importOriginal => {
  const actual = await importOriginal()
  return {
    ...actual,
    useI18n: () => ({ t: key => key, locale: ref('fr') }),
  }
})

import MediaCard from '@/components/portal/MediaCard.vue'

function baseState(overrides = {}) {
  // ``useMediaCardState`` returns refs to its caller; emulate that with
  // ``computed(() => v)`` so MediaCard's ``ref.value`` accesses resolve.
  const raw = {
    availData: null,
    reqStatus: null,
    isRejected: false,
    canResubmit: false,
    retryCount: 0,
    postitTooltip: '',
    isNewOnEmby: false,
    newRibbonTooltip: '',
    statusDot: null,
    showRequestedTag: false,
    requestStatusLabel: '',
    ...overrides,
  }
  const wrapped = {}
  for (const [k, v] of Object.entries(raw)) {
    wrapped[k] = ref(v)
  }
  return wrapped
}

const stateRef = { value: baseState() }
vi.mock('@/composables/portal/useMediaCardState', () => ({
  useMediaCardState: () => stateRef.value,
}))

const stubs = {
  AddToListOverlay: true,
  Film: { template: '<span />' },
  Check: { template: '<span />' },
  Plus: { template: '<span />' },
  RefreshCw: { template: '<span />' },
  ListPlus: { template: '<span />' },
}

function mountCard(item, state = baseState()) {
  stateRef.value = state
  return mount(MediaCard, {
    props: { item },
    global: { stubs },
  })
}

describe('MediaCard — request-status sash', () => {
  it('does NOT render the "available" diagonal ribbon (the green dot is enough)', () => {
    const w = mountCard(
      { tmdb_id: 1, title: 'Inception' },
      baseState({
        statusDot: { variant: 'available', tooltip: 't' },
        reqStatus: { status: 'available' },
      }),
    )
    expect(w.find('.pt-req-status-tag--available').exists()).toBe(false)
    expect(w.find('.pt-status-dot--available').exists()).toBe(true)
  })

  it('still renders the "pending" ribbon (non-redundant information)', () => {
    const w = mountCard(
      { tmdb_id: 2, title: 'Pending' },
      baseState({
        reqStatus: { status: 'pending' },
        requestStatusLabel: 'portal.card.requestStatus.pending',
      }),
    )
    expect(w.find('.pt-req-status-tag--pending').exists()).toBe(true)
  })

  it('still renders the "rejected" ribbon (admin signal)', () => {
    const w = mountCard(
      { tmdb_id: 3, title: 'Bad' },
      baseState({
        reqStatus: { status: 'rejected' },
        requestStatusLabel: 'portal.card.requestStatus.rejected',
      }),
    )
    expect(w.find('.pt-req-status-tag--rejected').exists()).toBe(true)
  })
})
