/**
 * CinemaRoomView — render-time guards.
 *
 * 1. Info button is rendered when a trailer is playing (canLaunch=false +
 *    currentTrailer set).
 * 2. The launch CTA is a <button>, not an <a> — regression guard on the
 *    retarget that keeps users on the cinema page after clicking.
 * 3. After the academy countdown ends and the current media has a
 *    poster_url, the poster <img> is rendered inside the screen.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref, computed } from 'vue'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: (k, named) => (named ? `${k}:${JSON.stringify(named)}` : k) }),
}))

const mockRouterPush = vi.fn()
const mockRouterReplace = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: '42' } }),
  useRouter: () => ({ push: mockRouterPush, replace: mockRouterReplace }),
}))

const mockEnterRoom = vi.fn()
const mockGetOne = vi.fn()
vi.mock('@/composables/portal/useRooms', () => ({
  useRooms: () => ({
    enterRoom: mockEnterRoom,
    getOne: mockGetOne,
  }),
}))

const marathonProgressState = {
  progress: ref({ is_marathon: false, current_step: 0, ready: false, participants: [] }),
  loading: ref(false),
  error: ref(null),
  enabled: ref(false),
  ready: ref(false),
  start: vi.fn(),
  stop: vi.fn(),
}
vi.mock('@/composables/portal/useMarathonProgress', () => ({
  useMarathonProgress: () => marathonProgressState,
}))

const flowState = {
  now: ref(Date.now()),
  remainingMs: ref(60_000),
  countdownNegative: ref(false),
  canLaunch: ref(false),
  canStartAcademy: ref(false),
  countdownDisplay: ref('01:00'),
  academyActive: ref(false),
  academyValue: ref(10),
  academyDone: ref(false),
  startTicker: vi.fn(),
  startAcademy: vi.fn(),
  resetAcademy: vi.fn(),
}
vi.mock('@/composables/portal/useCinemaRoomFlow', () => ({
  useCinemaRoomFlow: () => flowState,
}))

const mockShowToast = vi.fn()
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ showToast: mockShowToast }),
}))

vi.mock('@/composables/apiClient', () => ({
  fetchApiResponse: vi.fn(),
}))

const carouselState = {
  queue: ref([]),
  currentIndex: ref(0),
  currentTrailer: ref(null),
  hasTrailer: ref(false),
  videoPlaying: ref(false),
  transitioning: ref(false),
  fadeStyle: computed(() => ({ transitionDuration: '600ms' })),
  muted: ref(true),
  start: vi.fn().mockResolvedValue(undefined),
  advanceNext: vi.fn(),
  applyMute: vi.fn(),
  destroy: vi.fn(),
}

vi.mock('@/composables/portal/useCinemaTrailerCarousel', () => ({
  useCinemaTrailerCarousel: () => carouselState,
}))

vi.mock('@/components/portal/EventRoomChat.vue', () => ({
  default: { template: '<div class="event-room-chat-stub" />' },
}))
vi.mock('@/components/portal/cinema/CinemaRoomSeats.vue', () => ({
  default: { template: '<div class="cinema-seats-stub" />' },
}))
vi.mock('@/components/portal/cinema/CinemaRoomStage.vue', () => ({
  default: { template: '<div class="cinema-stage-stub" />' },
}))
vi.mock('@/components/portal/cinema/MarathonProgressPanel.vue', () => ({
  default: { template: '<div class="marathon-panel-stub" />' },
}))
vi.mock('lucide-vue-next', () => ({
  Check: { template: '<svg class="lucide-check" />' },
  Film: { template: '<svg class="lucide-film" />' },
  Info: { template: '<svg class="lucide-info" />' },
  LogOut: { template: '<svg class="lucide-logout" />' },
  Play: { template: '<svg class="lucide-play" />' },
  Volume2: { template: '<svg class="lucide-vol2" />' },
  VolumeX: { template: '<svg class="lucide-volx" />' },
}))

vi.mock('@/assets/styles/portal/cinema-room-stage.css', () => ({}))
vi.mock('@/assets/styles/portal/cinema-room-screen.css', () => ({}))
vi.mock('@/assets/styles/portal/cinema-room-seats.css', () => ({}))
vi.mock('@/assets/styles/portal/cinema-room-hud.css', () => ({}))

function setEvent({ scheduledOffsetMs = 60_000, posterUrl = '' } = {}) {
  return {
    id: 42,
    title: 'Test Event',
    scheduled_at: new Date(Date.now() + scheduledOffsetMs).toISOString(),
    tmdb_ids: [
      {
        tmdb_id: 1234,
        media_type: 'movie',
        title: 'Pinned Movie',
        poster_url: posterUrl,
        emby_url: 'https://emby.example/web/index.html#!/item?id=emby-1',
      },
    ],
  }
}

async function mountView() {
  const View = (await import('@/views/portal/CinemaRoomView.vue')).default
  return mount(View)
}

describe('CinemaRoomView.vue', () => {
  beforeEach(() => {
    mockEnterRoom.mockReset()
    mockGetOne.mockReset()
    mockRouterPush.mockReset()
    mockRouterReplace.mockReset()
    mockShowToast.mockReset()
    carouselState.queue.value = []
    carouselState.currentIndex.value = 0
    carouselState.currentTrailer.value = null
    carouselState.hasTrailer.value = false
    carouselState.transitioning.value = false
    carouselState.start.mockClear()
    carouselState.applyMute.mockClear()
    carouselState.destroy.mockClear()
    flowState.canLaunch.value = false
    flowState.canStartAcademy.value = false
    flowState.academyActive.value = false
    flowState.academyDone.value = false
    flowState.countdownNegative.value = false
    marathonProgressState.progress.value = {
      is_marathon: false,
      current_step: 0,
      ready: false,
      participants: [],
    }
    marathonProgressState.ready.value = false
    marathonProgressState.start.mockClear()
    marathonProgressState.stop.mockClear()
  })

  it('renders the Info button while a trailer is playing', async () => {
    mockEnterRoom.mockResolvedValue({ event: setEvent({ scheduledOffsetMs: 60_000 }) })
    carouselState.queue.value = [
      {
        key: 'aaaaaaaaaaa',
        title: 'Trailer A',
        source: 'youtube',
        emby_item_id: 'emby-abc',
        tmdb_id: 1234,
        media_type: 'movie',
        emby_url: 'https://emby.example/web/index.html#!/item?id=emby-abc',
      },
    ]
    carouselState.currentTrailer.value = carouselState.queue.value[0]
    carouselState.hasTrailer.value = true

    const wrapper = await mountView()
    await flushPromises()

    expect(wrapper.find('.pt-cr-info').exists()).toBe(true)
    expect(wrapper.find('.pt-cr-info').attributes('aria-label')).toContain('Trailer A')
  })

  it('renders the launch CTA as a <button>, not an <a> (retarget guard)', async () => {
    mockEnterRoom.mockResolvedValue({ event: setEvent({ scheduledOffsetMs: -1000 }) })
    flowState.canLaunch.value = true
    const wrapper = await mountView()
    await flushPromises()

    // Walk past the academy countdown synchronously.
    flowState.academyActive.value = false
    flowState.academyDone.value = true
    await flushPromises()

    const cta = wrapper.find('.pt-cr-launch-btn')
    expect(cta.exists()).toBe(true)
    expect(cta.element.tagName).toBe('BUTTON')
    expect(wrapper.find('a.pt-cr-launch-btn').exists()).toBe(false)
  })

  it('renders the poster when academyDone + currentMedia.poster_url is set', async () => {
    mockEnterRoom.mockResolvedValue({
      event: setEvent({ scheduledOffsetMs: -1000, posterUrl: '/api/emby/image/emby-1?type=Primary' }),
    })
    flowState.canLaunch.value = true
    const wrapper = await mountView()
    await flushPromises()

    flowState.academyActive.value = false
    flowState.academyDone.value = true
    await flushPromises()

    const poster = wrapper.find('img.pt-cr-screen-poster')
    expect(poster.exists()).toBe(true)
    expect(poster.attributes('src')).toBe('/api/emby/image/emby-1?type=Primary')
    expect(wrapper.find('.pt-cr-screen-ready-text').exists()).toBe(false)
  })

  it('disables the launch button when the marathon is not ready', async () => {
    const marathon = setEvent({ scheduledOffsetMs: -1000 })
    marathon.tmdb_ids = [
      { tmdb_id: 1, media_type: 'movie', title: 'A' },
      { tmdb_id: 2, media_type: 'movie', title: 'B' },
    ]
    mockEnterRoom.mockResolvedValue({ event: marathon })
    flowState.canLaunch.value = true
    marathonProgressState.progress.value = {
      is_marathon: true, current_step: 0, total_steps: 2, ready: false,
      participants: [], ineligible_count: 0,
    }
    marathonProgressState.ready.value = false

    const wrapper = await mountView()
    await flushPromises()
    flowState.academyDone.value = true
    await flushPromises()

    const cta = wrapper.find('.pt-cr-launch-btn')
    expect(cta.attributes('disabled')).toBeDefined()
  })

  it('enables the launch button when the marathon is ready', async () => {
    const marathon = setEvent({ scheduledOffsetMs: -1000 })
    marathon.tmdb_ids = [
      { tmdb_id: 1, media_type: 'movie', title: 'A' },
      { tmdb_id: 2, media_type: 'movie', title: 'B' },
    ]
    mockEnterRoom.mockResolvedValue({ event: marathon })
    flowState.canLaunch.value = true
    marathonProgressState.progress.value = {
      is_marathon: true, current_step: 0, total_steps: 2, ready: true,
      participants: [], ineligible_count: 0,
    }
    marathonProgressState.ready.value = true

    const wrapper = await mountView()
    await flushPromises()
    flowState.academyDone.value = true
    await flushPromises()

    const cta = wrapper.find('.pt-cr-launch-btn')
    expect(cta.attributes('disabled')).toBeUndefined()
  })

  it('bounces home when enter_room rejects with not_member (no read-only fallback)', async () => {
    // Anyone with the room URL but no accepted invitation must NOT be
    // allowed to wander into the cinema, even read-only — the backend
    // already refuses (``not_member``) and the front-end used to fall
    // back to ``getOne`` which leaked the room layout to non-invitees.
    mockEnterRoom.mockResolvedValue({ error: 'not_member' })

    await mountView()
    await flushPromises()

    expect(mockGetOne).not.toHaveBeenCalled()
    expect(mockShowToast).toHaveBeenCalledWith(
      'portal.cinema.errors.not_member',
      expect.anything(),
    )
    expect(mockRouterReplace).toHaveBeenCalledWith(
      expect.objectContaining({ name: expect.any(String) }),
    )
  })

  it('bounces home with a toast when the getOne fallback returns a terminated event', async () => {
    // ``enter_room`` declines for a non-cutoff reason (forbidden, network
    // glitch, room full, ...) so the view falls back to ``getOne``. The
    // fallback resolves with ``is_terminated: true`` — the defence-in-depth
    // guard must redirect to the portal home and surface the same toast as
    // the explicit ``event_ended`` branch instead of rendering zombie seats.
    mockEnterRoom.mockResolvedValue({ error: 'forbidden' })
    const stale = setEvent({ scheduledOffsetMs: -25 * 60 * 60 * 1000 })
    stale.is_terminated = true
    stale.status = 'scheduled'
    mockGetOne.mockResolvedValue(stale)

    await mountView()
    await flushPromises()

    expect(mockShowToast).toHaveBeenCalledWith(
      'portal.cinema.errors.event_ended',
      expect.anything(),
    )
    expect(mockRouterReplace).toHaveBeenCalledWith(
      expect.objectContaining({ name: expect.any(String) }),
    )
  })

  it('falls back to the title when academyDone but no poster is set', async () => {
    mockEnterRoom.mockResolvedValue({
      event: setEvent({ scheduledOffsetMs: -1000, posterUrl: '' }),
    })
    flowState.canLaunch.value = true
    const wrapper = await mountView()
    await flushPromises()

    flowState.academyActive.value = false
    flowState.academyDone.value = true
    await flushPromises()

    expect(wrapper.find('img.pt-cr-screen-poster').exists()).toBe(false)
    expect(wrapper.find('.pt-cr-screen-ready-text').text()).toBe('Pinned Movie')
  })
})
