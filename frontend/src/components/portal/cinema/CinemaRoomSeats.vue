<template>
  <!-- Cinema seats: a full opaque grid that fills the room. ``cols`` and
       ``rows`` are computed from the viewport so the grid adapts to the
       screen without ever truncating seats on the sides. The centred
       block of 5 × ceil(max_participants / 5) seats is occupable (carries
       an avatar); every other seat is a decorative-but-opaque filler. -->
  <div ref="wrapEl" class="pt-cr-seats-wrap">
    <div class="pt-cr-seats">
      <div v-for="r in rows" :key="`row-${r}`" class="pt-cr-row" :style="{ '--rowDepth': r }">
        <div
          v-for="c in cols"
          :key="`seat-${r}-${c}`"
          class="pt-cr-seat"
          :class="seatClass(seatIndexAt(r - 1, c - 1))"
          :title="seatTitle(seatIndexAt(r - 1, c - 1))"
        >
          <div class="pt-cr-seat-back" />
          <div class="pt-cr-seat-cushion" />
          <div class="pt-cr-seat-base" />
          <template v-if="seatOccupant(seatIndexAt(r - 1, c - 1))">
            <div class="pt-cr-seat-avatar">
              <MkAvatar
                :src="seatOccupant(seatIndexAt(r - 1, c - 1)).avatar_url || null"
                :name="seatOccupant(seatIndexAt(r - 1, c - 1)).username || '?'"
                :size="48"
                :tier="seatOccupant(seatIndexAt(r - 1, c - 1)).tier || 'bronze'"
                class="pt-cr-seat-avatar-mk"
              />
            </div>
            <div class="pt-cr-seat-label">
              {{ seatOccupant(seatIndexAt(r - 1, c - 1)).username }}
            </div>
            <div
              v-for="(b, bi) in seatBubbles(seatIndexAt(r - 1, c - 1))"
              :key="b.id"
              class="pt-cr-bubble"
              :style="{ '--bi': bi }"
            >
              {{ b.text }}
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRooms } from '@/composables/portal/useRooms'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { INVITATION_STATUS } from '@/constants/events'
import MkAvatar from '@/components/common/MkAvatar.vue'

// Occupable block is 5 seats wide (matches the admin capacity step) and
// ceil(max_participants / 5) rows tall, centred in the larger filler grid.
const OCCUPABLE_PER_ROW = 5

const props = defineProps({
  event: { type: Object, default: null },
})

const { listMessages } = useRooms()
const { profile } = usePortalAuth()

const myUserId = computed(() => profile.value?.user_id || profile.value?.id || 0)

// Terminated events keep their invitations for history but must not
// surface seated avatars or live bubbles — the cinema view bounces the
// user home when this is true, this is just defence in depth.
const terminated = computed(() => Boolean(props.event?.is_terminated))

const capacity = computed(() => {
  const raw = Number(props.event?.max_participants)
  if (Number.isFinite(raw) && raw > 0) return raw
  // Defensive default — should never hit in practice because the
  // backend serializer always populates max_participants.
  return OCCUPABLE_PER_ROW
})

const occRows = computed(() => Math.max(1, Math.ceil(capacity.value / OCCUPABLE_PER_ROW)))

// ---------- Responsive filler grid ----------
// Derive the grid from the *measured* seat + container so it tracks the CSS
// clamp and browser zoom exactly. Computing the seat size from ``vw`` used
// to drift out of sync on zoom — wrong column count and seats spilling onto
// the podium. Columns fill the row width (forced odd so the 5 occupable
// seats stay centred); rows fill the band under the 48vh screen.
const wrapEl = ref(null)
const cols = ref(OCCUPABLE_PER_ROW)
const rows = ref(1)

function computeGrid() {
  const wrap = wrapEl.value
  const seatsEl = wrap?.firstElementChild
  const sample = wrap?.querySelector('.pt-cr-seat')
  if (!wrap || !seatsEl || !sample) return
  const seatsStyle = getComputedStyle(seatsEl)
  const padX = parseFloat(seatsStyle.paddingLeft) + parseFloat(seatsStyle.paddingRight)
  const rowGap = parseFloat(seatsStyle.rowGap) || 0
  const colGap = parseFloat(getComputedStyle(sample.parentElement).columnGap) || 0
  // offsetWidth/Height = untransformed layout box (ignores the perspective).
  const seatW = sample.offsetWidth
  const seatH = sample.offsetHeight
  if (!seatW || !seatH) return

  let c = Math.floor((wrap.clientWidth - padX + colGap) / (seatW + colGap))
  if (c % 2 === 0) c -= 1
  cols.value = Math.max(OCCUPABLE_PER_ROW, c)

  const r = Math.floor((window.innerHeight * 0.4) / (seatH + rowGap))
  rows.value = Math.max(occRows.value, r)
}

// Map a grid cell to its occupable seat_index, or null for a filler seat.
function seatIndexAt(row, col) {
  const rowOffset = Math.floor((rows.value - occRows.value) / 2)
  const colOffset = Math.floor((cols.value - OCCUPABLE_PER_ROW) / 2)
  const oRow = row - rowOffset
  const oCol = col - colOffset
  if (oRow < 0 || oRow >= occRows.value || oCol < 0 || oCol >= OCCUPABLE_PER_ROW) return null
  return oRow * OCCUPABLE_PER_ROW + oCol
}

function seatOccupant(seatIdx) {
  if (seatIdx === null || !props.event || terminated.value) return null
  if (seatIdx < 0 || seatIdx >= capacity.value) return null
  const inv = props.event.invitations?.find(
    i => i.status === INVITATION_STATUS.ACCEPTED && i.seat_index === seatIdx,
  )
  if (!inv) return null
  // Presence gate: only paint the avatar while the heartbeat is fresh.
  if (!inv.is_currently_in_room) return null
  return inv
}

function seatClass(seatIdx) {
  if (seatIdx === null) return 'pt-cr-seat--decorative'
  // All chairs share one look; only the current viewer's seat gets a
  // subtle avatar halo via ``--mine``. Occupancy is shown by the avatar.
  const occ = seatOccupant(seatIdx)
  return occ && occ.user_id === myUserId.value ? 'pt-cr-seat--mine' : ''
}

function seatTitle(seatIdx) {
  return seatOccupant(seatIdx)?.username || ''
}

// ---------- Chat bubbles above seats ----------
// userId → array of { id, text, ts }. Auto-evicted after BUBBLE_TTL_MS.
const BUBBLE_TTL_MS = 7000
const bubblesByUser = ref({})
let lastSeenMsgId = 0
let bubblePollTimer = null
let bubbleSweepTimer = null

function seatBubbles(seatIdx) {
  const occ = seatOccupant(seatIdx)
  if (!occ) return []
  return bubblesByUser.value[occ.user_id] || []
}

async function pollBubbles() {
  if (!props.event || terminated.value) return
  try {
    const res = await listMessages(props.event.id, { since: lastSeenMsgId })
    const msgs = res?.messages || res || []
    if (!Array.isArray(msgs) || !msgs.length) return
    const next = { ...bubblesByUser.value }
    for (const m of msgs) {
      if (m.id <= lastSeenMsgId) continue
      lastSeenMsgId = m.id
      const arr = next[m.user_id] ? [...next[m.user_id]] : []
      arr.push({ id: m.id, text: m.content || m.text || '', ts: Date.now() })
      next[m.user_id] = arr.slice(-3)
    }
    bubblesByUser.value = next
  } catch {
    /* silent */
  }
}

function sweepBubbles() {
  const cutoff = Date.now() - BUBBLE_TTL_MS
  const next = {}
  let changed = false
  for (const [uid, arr] of Object.entries(bubblesByUser.value)) {
    const kept = arr.filter(b => b.ts >= cutoff)
    if (kept.length !== arr.length) changed = true
    if (kept.length) next[uid] = kept
  }
  if (changed) bubblesByUser.value = next
}

onMounted(() => {
  // nextTick so the initial seats are laid out before we measure them.
  nextTick(computeGrid)
  window.addEventListener('resize', computeGrid)
  bubblePollTimer = setInterval(pollBubbles, 3000)
  bubbleSweepTimer = setInterval(sweepBubbles, 1000)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', computeGrid)
  if (bubblePollTimer) clearInterval(bubblePollTimer)
  if (bubbleSweepTimer) clearInterval(bubbleSweepTimer)
})
</script>
