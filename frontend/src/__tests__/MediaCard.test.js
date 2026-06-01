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
    postitTooltip: '',
    watchedTooltip: '',
    reqStatusTooltip: '',
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
      'duration',
      'rating',
      'status',
      'count',
      'availability',
      'isNew',
      'blacklisted',
      'showBlacklist',
      'rank',
      'tooltip',
    ],
    emits: ['play', 'request', 'toggle-bookmark', 'toggle-blacklist'],
    template:
      '<div class="stub-poster" ' +
      ':data-status="status" ' +
      ':data-count="count" ' +
      ':data-year="String(year)" ' +
      ':data-duration="duration || \'\'" ' +
      ':data-rank="rank || \'\'" ' +
      ':data-tooltip="tooltip || \'\'" ' +
      ':data-show-blacklist="showBlacklist">' +
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
    expect(w.findComponent({ name: 'PosterCard' }).props('year')).toBe('1999')
  })

  it('falls back to release_date when item.year is missing', () => {
    const w = mountCard({ tmdb_id: 31, title: 'R', release_date: '2024-07-15' })
    expect(w.findComponent({ name: 'PosterCard' }).props('year')).toBe('2024')
  })

  it('falls back to first_air_date for TV items', () => {
    const w = mountCard({ tmdb_id: 32, title: 'TV', first_air_date: '2022-01-01' })
    expect(w.findComponent({ name: 'PosterCard' }).props('year')).toBe('2022')
  })
})

describe('MediaCard — duration derivation', () => {
  it('formats runtime in minutes as h+mm', () => {
    const w = mountCard({ tmdb_id: 40, title: 'D', runtime: 105 })
    expect(w.findComponent({ name: 'PosterCard' }).props('duration')).toBe('1h45')
  })

  it('returns an empty string when runtime is missing or zero', () => {
    const w0 = mountCard({ tmdb_id: 41, title: 'D0', runtime: 0 })
    expect(w0.findComponent({ name: 'PosterCard' }).props('duration')).toBe('')
    const wNull = mountCard({ tmdb_id: 42, title: 'DN' })
    expect(wNull.findComponent({ name: 'PosterCard' }).props('duration')).toBe('')
  })

  it('accepts an alternate `duration` field on the payload', () => {
    const w = mountCard({ tmdb_id: 43, title: 'Alt', duration: 45 })
    expect(w.findComponent({ name: 'PosterCard' }).props('duration')).toBe('45min')
  })
})

describe('MediaCard — rank forwarding', () => {
  it('forwards null rank by default', () => {
    const w = mountCard({ tmdb_id: 50, title: 'NoRank' })
    expect(w.findComponent({ name: 'PosterCard' }).props('rank')).toBeNull()
  })

  it('forwards the rank value to PosterCard', () => {
    const w = mount(MediaCard, {
      props: { item: { tmdb_id: 51, title: 'Top1' }, rank: 1 },
      global: { stubs },
    })
    expect(w.findComponent({ name: 'PosterCard' }).props('rank')).toBe(1)
  })
})

describe('MediaCard — rating forwarding', () => {
  it('forwards item.vote to the PosterCard rating prop', () => {
    const w = mountCard({ tmdb_id: 70, title: 'Rated', vote: 8 })
    expect(w.findComponent({ name: 'PosterCard' }).props('rating')).toBe(8)
  })

  it('forwards 0 when vote is absent', () => {
    const w = mountCard({ tmdb_id: 71, title: 'NoVote' })
    expect(w.findComponent({ name: 'PosterCard' }).props('rating')).toBe(0)
  })
})

describe('MediaCard — tooltip dispatch', () => {
  it('uses watchedTooltip for in_progress / watched states', () => {
    const w = mountCard(
      { tmdb_id: 60, title: 'W', watch_status: 'in_progress', watched_at: '2026-05-10' },
      baseState({ watchedTooltip: 'In progress since X' }),
    )
    expect(w.findComponent({ name: 'PosterCard' }).props('tooltip')).toBe('In progress since X')
  })

  it('uses postitTooltip for pending state', () => {
    const w = mountCard(
      { tmdb_id: 61, title: 'P' },
      baseState({
        reqStatus: { status: 'pending' },
        postitTooltip: 'Requested by Alice on May 1',
      }),
    )
    expect(w.findComponent({ name: 'PosterCard' }).props('tooltip')).toBe(
      'Requested by Alice on May 1',
    )
  })

  it('uses reqStatusTooltip for rejected state', () => {
    const w = mountCard(
      { tmdb_id: 62, title: 'R' },
      baseState({
        reqStatus: { status: 'rejected' },
        isRejected: true,
        reqStatusTooltip: 'Rejected on May 12',
      }),
    )
    expect(w.findComponent({ name: 'PosterCard' }).props('tooltip')).toBe('Rejected on May 12')
  })

  it('returns an empty tooltip when no status drives the ribbon', () => {
    const w = mountCard({ tmdb_id: 63, title: 'Plain' })
    expect(w.findComponent({ name: 'PosterCard' }).props('tooltip')).toBe('')
  })
})
