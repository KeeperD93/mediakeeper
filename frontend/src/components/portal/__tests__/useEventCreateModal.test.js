import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createApp } from 'vue'
import { flushPromises } from '@vue/test-utils'

// Mutable so a test can drive the admin-tunable capacity bounds the
// composable fetches in onMounted. Empty => the composable keeps its
// defaults (min 5, max 20, step 5 -> options [5, 10, 15, 20]).
const { boundsRef } = vi.hoisted(() => ({ boundsRef: { value: {} } }))

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: k => k }) }))

const createMock = vi.fn().mockResolvedValue({ id: 1 })
vi.mock('@/composables/portal/useRooms', () => ({
  useRooms: () => ({ create: createMock, searchUsers: vi.fn() }),
}))

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiGet: vi.fn().mockImplementation(() => Promise.resolve(boundsRef.value)) }),
  // The room's own reason when its scope words it, nothing over a rate limit
  // (its toast says it), else the action that failed.
  resolveScopedError: (scope, code, fallbackKey) => {
    if (code === 'max_participants_out_of_range') return `${scope}.${code}`
    return code === 'rate_limited_notified' ? '' : fallbackKey
  },
}))

import { useEventCreateModal } from '@/components/portal/useEventCreateModal.js'

function withSetup(fn) {
  let result
  const app = createApp({
    setup() {
      result = fn()
      return () => null
    },
  })
  app.mount(document.createElement('div'))
  return [result, app]
}

async function mountModal() {
  const [api, app] = withSetup(() => useEventCreateModal(vi.fn()))
  await flushPromises() // let onMounted apply the fetched capacity bounds
  return [api, app]
}

function fillValid(api) {
  api.title.value = 'Movie night'
  api.selectedMedia.value.push({ tmdb_id: 1, media_type: 'movie', title: 'X' })
  api.date.value = '2999-01-01'
  api.time.value = '20:00'
}

async function submittedCapacity(prepare) {
  const [api, app] = await mountModal()
  prepare(api)
  fillValid(api)
  await api.submit()
  app.unmount()
  return createMock.mock.calls.at(-1)?.[0]?.max_participants
}

describe('useEventCreateModal — capacity', () => {
  beforeEach(() => {
    createMock.mockClear()
    boundsRef.value = {} // default bounds
  })

  it('public events send the capacity the creator picked', async () => {
    const cap = await submittedCapacity(api => {
      api.kind.value = 'public'
      api.maxParticipants.value = 15
    })
    expect(cap).toBe(15)
  })

  it('private events derive the smallest room seating host + invitees', async () => {
    // 6 invitees + the host = 7 seats -> smallest step-5 option >= 7 is 10.
    const cap = await submittedCapacity(api => {
      api.kind.value = 'private'
      for (let i = 1; i <= 6; i++) api.selectedUsers.value.push({ id: i })
    })
    expect(cap).toBe(10)
  })

  it('a small private guest list still fits the minimum room', async () => {
    // 1 invitee + host = 2 -> the smallest option (5).
    const cap = await submittedCapacity(api => {
      api.kind.value = 'private'
      api.selectedUsers.value.push({ id: 1 })
    })
    expect(cap).toBe(5)
  })

  it('private capacity ignores the (hidden) picker value', async () => {
    const cap = await submittedCapacity(api => {
      api.kind.value = 'private'
      api.maxParticipants.value = 20 // hidden in private -> must not leak through
      api.selectedUsers.value.push({ id: 1 })
    })
    expect(cap).toBe(5)
  })

  it('caps the private guest list one seat below the largest room', async () => {
    boundsRef.value = { min: 5, max: 10, step: 5 }
    const [api, app] = await mountModal()
    api.kind.value = 'private'
    for (let i = 1; i <= 12; i++) api.addUser({ id: i })
    expect(api.selectedUsers.value.length).toBe(9) // host + 9 = max 10
    app.unmount()
  })
})

describe('useEventCreateModal — a failed creation', () => {
  beforeEach(() => {
    createMock.mockReset()
    boundsRef.value = {}
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  async function failWith(code) {
    createMock.mockRejectedValueOnce(new Error(code))
    const [api, app] = await mountModal()
    fillValid(api)
    await api.submit()
    app.unmount()
    return api.error.value
  }

  it("shows the room's own reason when the server gives one", async () => {
    expect(await failWith('max_participants_out_of_range')).toBe(
      'portal.mkEvents.errors.max_participants_out_of_range',
    )
  })

  it('names the failed action otherwise, and says nothing over a rate limit', async () => {
    expect(await failWith('http_500')).toBe('common.apiError.saveFailed')
    expect(await failWith('rate_limited_notified')).toBe('')
  })
})
