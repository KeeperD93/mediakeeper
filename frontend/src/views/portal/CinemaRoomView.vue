<template>
  <div class="pt-cr">
    <div v-if="loading" class="pt-cr-loading">{{ $t('common.loading') }}</div>

    <template v-else-if="event">
      <div class="pt-cr-stage">
        <!-- Ceiling: dome with rows of recessed spots + projector beam -->
        <div class="pt-cr-ceiling">
          <div class="pt-cr-ceiling-row">
            <span v-for="i in 16" :key="`ca${i}`" class="pt-cr-spot" />
          </div>
          <div class="pt-cr-ceiling-row pt-cr-ceiling-row--2">
            <span v-for="i in 14" :key="`cb${i}`" class="pt-cr-spot pt-cr-spot--small" />
          </div>
          <div class="pt-cr-projector" />
        </div>

        <!-- Side walls with sconces + LED aisle strip -->
        <div class="pt-cr-wall pt-cr-wall--left">
          <span class="pt-cr-sconce pt-cr-sconce--1" />
          <span class="pt-cr-sconce pt-cr-sconce--2" />
          <span class="pt-cr-sconce pt-cr-sconce--3" />
          <span class="pt-cr-led" />
        </div>
        <div class="pt-cr-wall pt-cr-wall--right">
          <span class="pt-cr-sconce pt-cr-sconce--1" />
          <span class="pt-cr-sconce pt-cr-sconce--2" />
          <span class="pt-cr-sconce pt-cr-sconce--3" />
          <span class="pt-cr-led" />
        </div>

        <div class="pt-cr-floor" />

        <div class="pt-cr-curtain pt-cr-curtain--left" />
        <div class="pt-cr-curtain pt-cr-curtain--right" />
        <div class="pt-cr-pelmet" />

        <!-- Big screen -->
        <div class="pt-cr-screen-frame">
          <div class="pt-cr-screen">
            <iframe
              v-if="!canLaunch && trailerKey"
              :key="trailerIframeKey"
              :src="trailerSrc"
              class="pt-cr-screen-video"
              frameborder="0"
              allow="autoplay; encrypted-media"
              sandbox="allow-scripts allow-same-origin allow-presentation"
              allowfullscreen
            />

            <div v-else-if="academyActive" class="pt-cr-academy">
              <div class="pt-cr-academy-circle">
                <span :key="academyValue" class="pt-cr-academy-num">{{ academyValue }}</span>
              </div>
            </div>

            <div v-else-if="academyDone" class="pt-cr-screen-ready">
              <span class="pt-cr-screen-ready-text">{{ currentMedia?.title }}</span>
            </div>

            <div v-else class="pt-cr-screen-placeholder">
              <span class="pt-cr-screen-title">{{ event.title }}</span>
            </div>
          </div>
          <div class="pt-cr-screen-halo" />
          <div class="pt-cr-podium" aria-hidden="true" />
        </div>

        <!-- Floating dust in the projector beam -->
        <div class="pt-cr-particles" aria-hidden="true">
          <span v-for="i in 22" :key="`p${i}`" class="pt-cr-particle" />
        </div>

        <CinemaRoomSeats :event="event" />
      </div>

      <!-- Launch CTA: appears ABOVE the screen after the academy countdown -->
      <transition name="pt-cr-cta">
        <div v-if="academyDone" class="pt-cr-launch">
          <a
            :href="currentMediaEmbyUrl"
            target="_blank"
            class="pt-cr-launch-btn"
            @click="onLaunchClick"
          >
            <Play :size="22" :stroke-width="2.5" />
            {{ launchLabel }}
          </a>
          <div v-if="event.tmdb_ids.length > 1" class="pt-cr-launch-marathon">
            {{
              $t('portal.cinema.marathonStep', {
                current: marathonStep + 1,
                total: event.tmdb_ids.length,
              })
            }}
          </div>
        </div>
      </transition>

      <!-- HUD: docked LEFT -->
      <div class="pt-cr-hud">
        <button class="pt-cr-leave" @click="leave">
          <LogOut :size="18" :stroke-width="2.5" />
          {{ $t('portal.cinema.leave') }}
        </button>
        <div class="pt-cr-countdown" :class="{ 'pt-cr-countdown--late': countdownNegative }">
          <span class="pt-cr-countdown-label">
            {{ countdownNegative ? $t('portal.cinema.elapsed') : $t('portal.cinema.startsIn') }}
          </span>
          <span class="pt-cr-countdown-value">{{ countdownDisplay }}</span>
        </div>
        <button
          class="pt-cr-mute"
          :title="muted ? $t('portal.cinema.unmute') : $t('portal.cinema.mute')"
          @click="toggleMute"
        >
          <VolumeX v-if="muted" :size="16" :stroke-width="2.5" />
          <Volume2 v-else :size="16" :stroke-width="2.5" />
          {{ muted ? $t('portal.cinema.unmute') : $t('portal.cinema.mute') }}
        </button>
      </div>

      <EventRoomChat :event-id="event.id" />
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useApi } from '@/composables/useApi'
import { useRooms } from '@/composables/portal/useRooms'
import EventRoomChat from '@/components/portal/EventRoomChat.vue'
import CinemaRoomSeats from '@/components/portal/cinema/CinemaRoomSeats.vue'
import { isTv as isTvMedia } from '@/constants/media'
import { PORTAL_TAB } from '@/constants/portal'
import { LogOut, Play, Volume2, VolumeX } from 'lucide-vue-next'

import '@/assets/styles/portal/cinema-room-stage.css'
import '@/assets/styles/portal/cinema-room-screen.css'
import '@/assets/styles/portal/cinema-room-seats.css'
import '@/assets/styles/portal/cinema-room-hud.css'

const route = useRoute()
const router = useRouter()
const { apiGet } = useApi()
const { enterRoom, getOne } = useRooms()

const event = ref(null)
const loading = ref(true)
const trailerKey = ref(null)
const now = ref(Date.now())
const marathonStep = ref(0)
const muted = ref(true)
const trailerIframeKey = ref(0)

const academyActive = ref(false)
const academyValue = ref(10)
const academyDone = ref(false)

let tickTimer = null
let randomTrailerTimer = null
let academyTimer = null

// ---------- Countdown / launch ----------
const scheduledTime = computed(() =>
  event.value ? new Date(event.value.scheduled_at).getTime() : 0,
)
const remainingMs = computed(() => scheduledTime.value - now.value)
const countdownNegative = computed(() => remainingMs.value < 0)
const canLaunch = computed(() => remainingMs.value <= 0)

const countdownDisplay = computed(() => {
  const ms = Math.abs(remainingMs.value)
  const total = Math.floor(ms / 1000)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  if (h > 0) return `${h}h ${String(m).padStart(2, '0')}m`
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

const currentMedia = computed(() => event.value?.tmdb_ids?.[marathonStep.value] || null)
const currentMediaEmbyUrl = computed(() => currentMedia.value?.emby_url || '#')
const launchLabel = computed(() => {
  if (!currentMedia.value) return ''
  return isTvMedia(currentMedia.value) ? 'Start the series' : 'Start the movie'
})

const trailerSrc = computed(() => {
  if (!trailerKey.value) return ''
  const muteFlag = muted.value ? 1 : 0
  return `https://www.youtube-nocookie.com/embed/${trailerKey.value}?autoplay=1&controls=0&mute=${muteFlag}&loop=1&playlist=${trailerKey.value}&modestbranding=1&playsinline=1`
})

function toggleMute() {
  muted.value = !muted.value
  // Force the iframe to reload so the mute change takes effect.
  trailerIframeKey.value += 1
}

watch(canLaunch, v => {
  if (v && !academyActive.value && !academyDone.value) startAcademy()
})

function startAcademy() {
  academyActive.value = true
  academyValue.value = 10
  academyTimer = setInterval(() => {
    academyValue.value -= 1
    if (academyValue.value <= 0) {
      clearInterval(academyTimer)
      academyTimer = null
      academyActive.value = false
      academyDone.value = true
    }
  }, 1000)
}

async function load() {
  loading.value = true
  try {
    const id = parseInt(route.params.id, 10)
    const enterRes = await enterRoom(id).catch(() => null)
    if (enterRes && !enterRes.error) {
      event.value = enterRes.event
    } else {
      event.value = await getOne(id)
    }
  } finally {
    loading.value = false
  }
  loadRandomTrailer()
  if (canLaunch.value && !academyDone.value && !academyActive.value) startAcademy()
}

async function loadRandomTrailer() {
  try {
    const res = await apiGet('/api/portal/trailers/random?limit=10').catch(() => null)
    if (res?.items?.length) {
      const pick = res.items[Math.floor(Math.random() * res.items.length)]
      trailerKey.value = pick.key || null
    }
  } catch {
    /* silent */
  }
}

function leave() {
  if (window.opener) window.close()
  else router.push({ name: PORTAL_TAB.HOME })
}

function onLaunchClick() {
  if (!event.value) return
  if (marathonStep.value < event.value.tmdb_ids.length - 1) {
    setTimeout(() => {
      marathonStep.value += 1
      academyDone.value = false
      academyActive.value = false
      startAcademy()
    }, 500)
  }
}

onMounted(() => {
  load()
  tickTimer = setInterval(() => {
    now.value = Date.now()
  }, 1000)
  randomTrailerTimer = setInterval(loadRandomTrailer, 3 * 60 * 1000)
})

onBeforeUnmount(() => {
  if (tickTimer) clearInterval(tickTimer)
  if (randomTrailerTimer) clearInterval(randomTrailerTimer)
  if (academyTimer) clearInterval(academyTimer)
})
</script>
