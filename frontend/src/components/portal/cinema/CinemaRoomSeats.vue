<template>
  <!-- Cinema seats: dynamic layout driven by ``event.max_participants``.
       The N seats (5/10/15/20) lay out as ceil(N/5) rows × 5 occupable
       columns centred via flex. Decorative seats on each side give the
       room a "filled" feel — they're rendered through the same DOM but
       carry no avatar and disappear via media queries on narrow screens
       so we never truncate occupable seats. -->
  <div class="pt-cr-seats-wrap">
    <div class="pt-cr-seats">
      <div v-for="row in rows" :key="`row-${row}`" class="pt-cr-row" :style="{ '--rowDepth': row }">
        <!-- Decorative seats — left side. -->
        <div
          v-for="i in DECORATIVE_PER_SIDE"
          :key="`dec-l-${row}-${i}`"
          class="pt-cr-seat pt-cr-seat--decorative"
          :class="`pt-cr-seat--dec-${i}`"
          aria-hidden="true"
        >
          <div class="pt-cr-seat-back" />
          <div class="pt-cr-seat-cushion" />
          <div class="pt-cr-seat-base" />
        </div>

        <!-- Occupable seats — 5 per row, indexed by ``seat_index``. -->
        <div
          v-for="col in OCCUPABLE_PER_ROW"
          :key="`s-${row}-${col}`"
          class="pt-cr-seat"
          :class="seatClass(seatIndexOf(row - 1, col - 1))"
          :title="seatTitle(seatIndexOf(row - 1, col - 1))"
        >
          <div class="pt-cr-seat-back" />
          <div class="pt-cr-seat-cushion" />
          <div class="pt-cr-seat-base" />
          <template v-if="seatOccupant(seatIndexOf(row - 1, col - 1))">
            <div class="pt-cr-seat-avatar">
              <MkAvatar
                :src="seatOccupant(seatIndexOf(row - 1, col - 1)).avatar_url || null"
                :name="seatOccupant(seatIndexOf(row - 1, col - 1)).username || '?'"
                :size="48"
                :tier="seatOccupant(seatIndexOf(row - 1, col - 1)).tier || 'bronze'"
                class="pt-cr-seat-avatar-mk"
              />
            </div>
            <div class="pt-cr-seat-label">
              {{ seatOccupant(seatIndexOf(row - 1, col - 1)).username }}
            </div>
            <div
              v-for="(b, bi) in seatBubbles(seatIndexOf(row - 1, col - 1))"
              :key="b.id"
              class="pt-cr-bubble"
              :style="{ '--bi': bi }"
            >
              {{ b.text }}
            </div>
          </template>
        </div>

        <!-- Decorative seats — right side. -->
        <div
          v-for="i in DECORATIVE_PER_SIDE"
          :key="`dec-r-${row}-${i}`"
          class="pt-cr-seat pt-cr-seat--decorative"
          :class="`pt-cr-seat--dec-${i}`"
          aria-hidden="true"
        >
          <div class="pt-cr-seat-back" />
          <div class="pt-cr-seat-cushion" />
          <div class="pt-cr-seat-base" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRooms } from '@/composables/portal/useRooms'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { INVITATION_STATUS } from '@/constants/events'
import MkAvatar from '@/components/common/MkAvatar.vue'

// Seat layout constants — kept here so the template stays declarative.
// ``OCCUPABLE_PER_ROW`` matches the admin step (5) so every row neatly
// represents one capacity bucket. ``DECORATIVE_PER_SIDE`` is rendered
// in the DOM but the matching CSS class drops the outermost columns
// (``--dec-3``, ``--dec-2``) under tighter breakpoints to avoid
// truncating the occupable centre.
const OCCUPABLE_PER_ROW = 5
const DECORATIVE_PER_SIDE = 3

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

const rows = computed(() => Math.max(1, Math.ceil(capacity.value / OCCUPABLE_PER_ROW)))

function seatIndexOf(row, col) {
  return row * OCCUPABLE_PER_ROW + col
}

function seatOccupant(seatIdx) {
  if (!props.event || terminated.value) return null
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
  if (seatIdx >= capacity.value) return 'pt-cr-seat--out-of-capacity'
  const occ = seatOccupant(seatIdx)
  if (!occ) return ''
  return occ.user_id === myUserId.value
    ? 'pt-cr-seat--occupied pt-cr-seat--mine'
    : 'pt-cr-seat--occupied'
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
  bubblePollTimer = setInterval(pollBubbles, 3000)
  bubbleSweepTimer = setInterval(sweepBubbles, 1000)
})

onBeforeUnmount(() => {
  if (bubblePollTimer) clearInterval(bubblePollTimer)
  if (bubbleSweepTimer) clearInterval(bubbleSweepTimer)
})
</script>
