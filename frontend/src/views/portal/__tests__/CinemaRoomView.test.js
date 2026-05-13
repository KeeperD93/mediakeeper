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

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: '42' } }),
  useRouter: () => ({ push: vi.fn() }),
}))

const mockEnterRoom = vi.fn()
const mockGetOne = vi.fn()
vi.mock('@/composables/portal/useRooms', () => ({
  useRooms: () => ({
    enterRoom: mockEnterRoom,
    getOne: mockGetOne,
  }),
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
vi.mock('lucide-vue-next', () => ({
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
    carouselState.queue.value = []
    carouselState.currentIndex.value = 0
    carouselState.currentTrailer.value = null
    carouselState.hasTrailer.value = false
    carouselState.transitioning.value = false
    carouselState.start.mockClear()
    carouselState.applyMute.mockClear()
    carouselState.destroy.mockClear()
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
    const wrapper = await mountView()
    await flushPromises()

    // Walk past the academy countdown synchronously.
    wrapper.vm.academyActive = false
    wrapper.vm.academyDone = true
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
    const wrapper = await mountView()
    await flushPromises()

    wrapper.vm.academyActive = false
    wrapper.vm.academyDone = true
    await flushPromises()

    const poster = wrapper.find('img.pt-cr-screen-poster')
    expect(poster.exists()).toBe(true)
    expect(poster.attributes('src')).toBe('/api/emby/image/emby-1?type=Primary')
    expect(wrapper.find('.pt-cr-screen-ready-text').exists()).toBe(false)
  })

  it('falls back to the title when academyDone but no poster is set', async () => {
    mockEnterRoom.mockResolvedValue({
      event: setEvent({ scheduledOffsetMs: -1000, posterUrl: '' }),
    })
    const wrapper = await mountView()
    await flushPromises()

    wrapper.vm.academyActive = false
    wrapper.vm.academyDone = true
    await flushPromises()

    expect(wrapper.find('img.pt-cr-screen-poster').exists()).toBe(false)
    expect(wrapper.find('.pt-cr-screen-ready-text').text()).toBe('Pinned Movie')
  })
})
