import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref, computed } from 'vue'

vi.mock('vue-i18n', async importOriginal => {
  const actual = await importOriginal()
  return {
    ...actual,
    useI18n: () => ({ t: key => key, locale: ref('fr') }),
  }
})

const profileRef = ref({ role: 'user' })
vi.mock('@/composables/portal/usePortalAuth', () => ({
  usePortalAuth: () => ({ profile: profileRef }),
}))

function baseState(overrides = {}) {
  const raw = {
    availData: null,
    reqStatus: null,
    isRejected: false,
    canResubmit: false,
    retryCount: 0,
    isNewOnEmby: false,
    displayedReqStatus: null,
    ...overrides,
  }
  const wrapped = {}
  for (const [k, v] of Object.entries(raw)) {
    wrapped[k] = computed(() => v)
  }
  return wrapped
}

const stateRef = { value: baseState() }
vi.mock('@/composables/portal/useMediaCardState', () => ({
  useMediaCardState: () => stateRef.value,
}))

import MediaCard from '@/components/portal/MediaCard.vue'

const stubs = {
  AddToListOverlay: {
    name: 'AddToListOverlay',
    props: ['open', 'media'],
    template: '<div class="stub-add-overlay" :data-open="open" />',
  },
  PosterCard: {
    name: 'PosterCard',
    props: [
      'title',
      'image',
      'year',
      'status',
      'count',
      'availability',
      'isNew',
      'blacklisted',
      'showBlacklist',
    ],
    emits: ['play', 'request', 'toggle-bookmark', 'toggle-blacklist'],
    template:
      '<div class="stub-poster" :data-status="status" :data-count="count" :data-year="String(year)" :data-show-blacklist="showBlacklist">' +
      '<button type="button" class="stub-play" @click="$emit(\'play\')">play</button>' +
      '<button type="button" class="stub-request" @click="$emit(\'request\')">request</button>' +
      '<button type="button" class="stub-bookmark" @click="$emit(\'toggle-bookmark\')">bookmark</button>' +
      '<button type="button" class="stub-blacklist" @click="$emit(\'toggle-blacklist\')">blacklist</button>' +
      '</div>',
  },
}

beforeEach(() => {
  profileRef.value = { role: 'user' }
  stateRef.value = baseState()
})

function mountCard(item, state) {
  if (state) stateRef.value = state
  return mount(MediaCard, { props: { item }, global: { stubs } })
}

describe('MediaCard — status mapping', () => {
  it('emits no status when the item is plain', () => {
    const w = mountCard({ tmdb_id: 1, title: 'Plain' })
    expect(w.findComponent({ name: 'PosterCard' }).props('status')).toBeNull()
  })

  it('routes in_progress when the item carries watch_status=in_progress', () => {
    const w = mountCard({ tmdb_id: 2, title: 'In', watch_status: 'in_progress' })
    expect(w.find('.stub-poster').attributes('data-status')).toBe('in_progress')
  })

  it('routes watched when watched_at is set without an in_progress flag', () => {
    const w = mountCard({ tmdb_id: 3, title: 'Done', watched_at: '2026-05-01' })
    expect(w.find('.stub-poster').attributes('data-status')).toBe('watched')
  })

  it('routes rejected and forwards retry count via the count prop', () => {
    const w = mountCard(
      { tmdb_id: 4, title: 'Bad' },
      baseState({ reqStatus: { status: 'rejected' }, isRejected: true, retryCount: 2 }),
    )
    const poster = w.find('.stub-poster')
    expect(poster.attributes('data-status')).toBe('rejected')
    expect(poster.attributes('data-count')).toBe('3')
  })

  it('routes blacklisted when displayedReqStatus is blacklisted', () => {
    const w = mountCard(
      { tmdb_id: 5, title: 'Hidden' },
      baseState({ displayedReqStatus: 'blacklisted' }),
    )
    expect(w.find('.stub-poster').attributes('data-status')).toBe('blacklisted')
  })
})

describe('MediaCard — emits', () => {
  it('emits select when the wrapper itself is clicked', async () => {
    const w = mountCard({ tmdb_id: 10, title: 'A' })
    await w.find('.mk-mediacard').trigger('click')
    expect(w.emitted('select')).toHaveLength(1)
    expect(w.emitted('select')[0][0]).toEqual({ tmdb_id: 10, title: 'A' })
  })

  it('does NOT emit select when a child button bubbles up', async () => {
    const w = mountCard(
      { tmdb_id: 11, title: 'B' },
      baseState({ reqStatus: { status: 'rejected' }, isRejected: true }),
    )
    await w.find('.stub-request').trigger('click')
    expect(w.emitted('select')).toBeUndefined()
  })

  it('emits request when PosterCard signals request and the request is not frozen', async () => {
    const w = mountCard(
      { tmdb_id: 12, title: 'C' },
      baseState({ reqStatus: { status: 'rejected' }, isRejected: true }),
    )
    await w.find('.stub-request').trigger('click')
    expect(w.emitted('request')).toHaveLength(1)
  })

  it('does NOT emit request when the existing request is pending', async () => {
    const w = mountCard(
      { tmdb_id: 13, title: 'D' },
      baseState({ reqStatus: { status: 'pending' }, isRejected: false }),
    )
    await w.find('.stub-request').trigger('click')
    expect(w.emitted('request')).toBeUndefined()
  })

  it('emits addToList and opens the overlay when bookmark is clicked', async () => {
    const w = mountCard({ tmdb_id: 14, title: 'E' })
    expect(w.find('.stub-add-overlay').attributes('data-open')).toBe('false')
    await w.find('.stub-bookmark').trigger('click')
    expect(w.emitted('addToList')).toHaveLength(1)
    expect(w.find('.stub-add-overlay').attributes('data-open')).toBe('true')
  })
})

describe('MediaCard — admin gate for blacklist', () => {
  it('hides the blacklist button for non-admin users', () => {
    profileRef.value = { role: 'user' }
    const w = mountCard({ tmdb_id: 20, title: 'U' })
    expect(w.find('.stub-poster').attributes('data-show-blacklist')).toBe('false')
  })

  it('exposes the blacklist button for admin users', () => {
    profileRef.value = { role: 'admin' }
    const w = mountCard({ tmdb_id: 21, title: 'A' })
    expect(w.find('.stub-poster').attributes('data-show-blacklist')).toBe('true')
  })
})

describe('MediaCard — year derivation', () => {
  it('uses item.year when present', () => {
    const w = mountCard({ tmdb_id: 30, title: 'Y', year: 1999 })
    expect(w.findComponent({ name: 'PosterCard' }).props('year')).toBe(1999)
  })

  it('falls back to release_date when item.year is missing', () => {
    const w = mountCard({ tmdb_id: 31, title: 'R', release_date: '2024-07-15' })
    expect(w.findComponent({ name: 'PosterCard' }).props('year')).toBe(2024)
  })
})
