<template>
  <Teleport to="body">
    <transition name="pt-evb">
      <div v-if="visible && currentEvent" class="pt-evb" :style="{ top: `${navOffset}px` }">
        <div class="pt-evb-marquee">
          <div class="pt-evb-content">
            <span class="pt-evb-label">🎬 {{ $t('portal.mkEvents.banner.label') }}</span>
            <span class="pt-evb-sep">·</span>
            <strong class="pt-evb-title">{{ currentEvent.title }}</strong>
            <span class="pt-evb-sep">·</span>
            <span>{{ formatFull(currentEvent.scheduled_at) }}</span>
            <template v-if="participantList">
              <span class="pt-evb-sep">·</span>
              <span>{{ $t('portal.mkEvents.banner.with') }} {{ participantList }}</span>
            </template>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRooms } from '@/composables/portal/useRooms'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { EVENT_STATUS, INVITATION_STATUS } from '@/constants/events'

// Cycles through the user's upcoming events:
//   - Show the current event for ~30 seconds (one full marquee pass)
//   - Hide
//   - Wait 5 minutes
//   - Show the next event in the queue
//
// "Visible to me" = events I created OR accepted, status=scheduled,
// scheduled_at in the future. Public events I haven't accepted are
// excluded so the banner doesn't spam everyone with random events.
const { events, fetchAll } = useRooms()
const { profile } = usePortalAuth()

const visible = ref(false)
const queueIdx = ref(0)
const navOffset = ref(0)
let cycleTimer = null
let refreshTimer = null

// The banner sits flush against the portal nav's bottom edge. The nav
// has a fixed position but a responsive height (tabs collapse, solid
// mode adds a border) — measure it instead of hard-coding. When the
// GDPR deletion banner is also mounted, this banner stacks underneath
// it: take the lowest bottom edge between nav and the deletion banner
// so neither overlaps.
function measureNav() {
  const nav = document.querySelector('.pt-nav')
  const navBottom = nav ? Math.round(nav.getBoundingClientRect().bottom) : 0
  const dpb = document.querySelector('.pt-dpb')
  const dpbBottom = dpb ? Math.round(dpb.getBoundingClientRect().bottom) : 0
  navOffset.value = Math.max(navBottom, dpbBottom)
}

const SHOW_MS = 30000
const HIDE_MS = 5 * 60 * 1000

const myEvents = computed(() => {
  const uid = profile.value?.user_id || profile.value?.id
  if (!uid) return []
  const now = Date.now()
  return events.value
    .filter((e) => e.status === EVENT_STATUS.SCHEDULED)
    .filter((e) => new Date(e.scheduled_at).getTime() > now)
    .filter((e) => e.invitations?.some(
      (i) => i.user_id === uid && (i.status === INVITATION_STATUS.ACCEPTED || e.creator_user_id === uid),
    ))
    .sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at))
})

const currentEvent = computed(() => {
  if (!myEvents.value.length) return null
  return myEvents.value[queueIdx.value % myEvents.value.length]
})

const participantList = computed(() => {
  const ev = currentEvent.value
  if (!ev) return ''
  const accepted = ev.invitations?.filter((i) => i.status === INVITATION_STATUS.ACCEPTED) || []
  const names = accepted.slice(0, 4).map((i) => i.username)
  if (accepted.length > 4) names.push(`+${accepted.length - 4}`)
  return names.join(', ')
})

function showOnce() {
  if (!myEvents.value.length) return
  visible.value = true
  setTimeout(() => {
    visible.value = false
    queueIdx.value = (queueIdx.value + 1) % myEvents.value.length
    cycleTimer = setTimeout(showOnce, HIDE_MS)
  }, SHOW_MS)
}

watch(() => myEvents.value.length, (n) => {
  if (n > 0 && !visible.value && !cycleTimer) showOnce()
})

let navObserver = null
let dpbObserver = null
let bodyObserver = null
onMounted(async () => {
  measureNav()
  window.addEventListener('resize', measureNav)
  window.addEventListener('scroll', measureNav, { passive: true })
  const nav = document.querySelector('.pt-nav')
  if (nav && typeof ResizeObserver !== 'undefined') {
    navObserver = new ResizeObserver(measureNav)
    navObserver.observe(nav)
  }
  // The deletion banner is teleported to <body> and only mounts when
  // the user has a pending deletion — wait for it to appear before
  // observing it. A MutationObserver on <body> picks up the late mount
  // (and unmount) and re-runs measureNav.
  if (typeof MutationObserver !== 'undefined') {
    bodyObserver = new MutationObserver(() => {
      measureNav()
      const dpb = document.querySelector('.pt-dpb')
      if (dpb && !dpbObserver && typeof ResizeObserver !== 'undefined') {
        dpbObserver = new ResizeObserver(measureNav)
        dpbObserver.observe(dpb)
      }
    })
    bodyObserver.observe(document.body, { childList: true, subtree: true })
  }
  await fetchAll()
  if (myEvents.value.length) showOnce()
  // Refresh the upcoming list every 2 minutes so newly created or
  // cancelled events propagate without a full reload.
  refreshTimer = setInterval(fetchAll, 2 * 60 * 1000)
})

onBeforeUnmount(() => {
  if (cycleTimer) clearTimeout(cycleTimer)
  if (refreshTimer) clearInterval(refreshTimer)
  window.removeEventListener('resize', measureNav)
  window.removeEventListener('scroll', measureNav)
  if (navObserver) navObserver.disconnect()
  if (dpbObserver) dpbObserver.disconnect()
  if (bodyObserver) bodyObserver.disconnect()
})

function formatFull(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString(undefined, {
      day: '2-digit', month: 'short',
      hour: '2-digit', minute: '2-digit',
    })
  } catch { return iso }
}
</script>

<style scoped>
.pt-evb {
  position: fixed;
  left: 0;
  right: 0;
  z-index: 99;
  background: transparent;
  color: #fff;
  height: 28px;
  display: flex;
  align-items: center;
  overflow: hidden;
  pointer-events: none;
  border-top: 1px solid var(--portal-border-subtle);
  border-bottom: 1px solid var(--portal-border-subtle);
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.75), 0 0 10px rgba(0, 0, 0, 0.4);
}
.pt-evb-marquee {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  white-space: nowrap;
}
.pt-evb-content {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  left: 100%;
  font-size: var(--portal-text-xs);
  font-weight: var(--portal-font-regular);
  letter-spacing: var(--portal-tracking-wide);
  white-space: nowrap;
  animation: pt-evb-scroll 30s linear forwards;
  display: flex;
  align-items: center;
  gap: 0.55rem;
  color: var(--portal-text-body);
}
.pt-evb-label {
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-eyebrow);
  font-size: var(--portal-text-2xs);
  font-weight: var(--portal-font-bold);
  color: rgba(255, 255, 255, 0.65);
}
.pt-evb-sep {
  color: var(--portal-text-muted);
  font-weight: 400;
}
.pt-evb-title { font-weight: var(--portal-font-bold); color: #fff; }
@keyframes pt-evb-scroll {
  from { transform: translate(0, -50%); }
  to { transform: translate(calc(-100vw - 100%), -50%); }
}

.pt-evb-enter-active, .pt-evb-leave-active {
  transition: transform 0.4s ease, opacity var(--portal-dur-slow) ease;
}
.pt-evb-enter-from, .pt-evb-leave-to {
  transform: translateY(-100%);
  opacity: 0;
}
</style>
