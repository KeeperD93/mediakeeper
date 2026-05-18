<template>
  <!-- Seats: 4 rows × 25 cols arranged 8 + 9 + 8 with stair gaps.
       Backend seat_index ∈ [0..49] mapped to the 50 best central positions. -->
  <div class="pt-cr-seats-wrap">
    <div class="pt-cr-seats">
      <div v-for="row in 4" :key="`row${row}`" class="pt-cr-row" :style="{ '--rowDepth': row }">
        <div class="pt-cr-block">
          <div
            v-for="col in 8"
            :key="`s-${row}-l-${col}`"
            class="pt-cr-seat"
            :class="seatClass(row - 1, col - 1, 'L')"
            :title="seatTitle(row - 1, col - 1, 'L')"
            :style="{ '--col': col - 1 }"
          >
            <div class="pt-cr-seat-back" />
            <div class="pt-cr-seat-cushion" />
            <div class="pt-cr-seat-base" />
            <div v-if="seatOccupant(row - 1, col - 1, 'L')" class="pt-cr-seat-avatar">
              <img
                v-if="seatOccupant(row - 1, col - 1, 'L').avatar_url"
                :src="seatOccupant(row - 1, col - 1, 'L').avatar_url"
                :alt="seatOccupant(row - 1, col - 1, 'L').username || ''"
                class="pt-cr-seat-avatar-img"
              />
              <span v-else>
                {{
                  seatOccupant(row - 1, col - 1, 'L')
                    .username?.charAt(0)
                    ?.toUpperCase()
                }}
              </span>
            </div>
            <div v-if="seatOccupant(row - 1, col - 1, 'L')" class="pt-cr-seat-label">
              {{ seatOccupant(row - 1, col - 1, 'L').username }}
            </div>
            <div
              v-for="(b, bi) in seatBubbles(row - 1, col - 1, 'L')"
              :key="b.id"
              class="pt-cr-bubble"
              :style="{ '--bi': bi }"
            >
              {{ b.text }}
            </div>
          </div>
        </div>
        <div class="pt-cr-stair" />
        <div class="pt-cr-block pt-cr-block--center">
          <div
            v-for="col in 9"
            :key="`s-${row}-c-${col}`"
            class="pt-cr-seat"
            :class="seatClass(row - 1, col - 1, 'C')"
            :title="seatTitle(row - 1, col - 1, 'C')"
            :style="{ '--col': col + 7 }"
          >
            <div class="pt-cr-seat-back" />
            <div class="pt-cr-seat-cushion" />
            <div class="pt-cr-seat-base" />
            <div v-if="seatOccupant(row - 1, col - 1, 'C')" class="pt-cr-seat-avatar">
              <img
                v-if="seatOccupant(row - 1, col - 1, 'C').avatar_url"
                :src="seatOccupant(row - 1, col - 1, 'C').avatar_url"
                :alt="seatOccupant(row - 1, col - 1, 'C').username || ''"
                class="pt-cr-seat-avatar-img"
              />
              <span v-else>
                {{
                  seatOccupant(row - 1, col - 1, 'C')
                    .username?.charAt(0)
                    ?.toUpperCase()
                }}
              </span>
            </div>
            <div v-if="seatOccupant(row - 1, col - 1, 'C')" class="pt-cr-seat-label">
              {{ seatOccupant(row - 1, col - 1, 'C').username }}
            </div>
            <div
              v-for="(b, bi) in seatBubbles(row - 1, col - 1, 'C')"
              :key="b.id"
              class="pt-cr-bubble"
              :style="{ '--bi': bi }"
            >
              {{ b.text }}
            </div>
          </div>
        </div>
        <div class="pt-cr-stair" />
        <div class="pt-cr-block">
          <div
            v-for="col in 8"
            :key="`s-${row}-r-${col}`"
            class="pt-cr-seat"
            :class="seatClass(row - 1, col - 1, 'R')"
            :title="seatTitle(row - 1, col - 1, 'R')"
            :style="{ '--col': col + 16 }"
          >
            <div class="pt-cr-seat-back" />
            <div class="pt-cr-seat-cushion" />
            <div class="pt-cr-seat-base" />
            <div v-if="seatOccupant(row - 1, col - 1, 'R')" class="pt-cr-seat-avatar">
              <img
                v-if="seatOccupant(row - 1, col - 1, 'R').avatar_url"
                :src="seatOccupant(row - 1, col - 1, 'R').avatar_url"
                :alt="seatOccupant(row - 1, col - 1, 'R').username || ''"
                class="pt-cr-seat-avatar-img"
              />
              <span v-else>
                {{
                  seatOccupant(row - 1, col - 1, 'R')
                    .username?.charAt(0)
                    ?.toUpperCase()
                }}
              </span>
            </div>
            <div v-if="seatOccupant(row - 1, col - 1, 'R')" class="pt-cr-seat-label">
              {{ seatOccupant(row - 1, col - 1, 'R').username }}
            </div>
            <div
              v-for="(b, bi) in seatBubbles(row - 1, col - 1, 'R')"
              :key="b.id"
              class="pt-cr-bubble"
              :style="{ '--bi': bi }"
            >
              {{ b.text }}
            </div>
          </div>
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

const props = defineProps({
  event: { type: Object, default: null },
})

const { listMessages } = useRooms()
const { profile } = usePortalAuth()

const myUserId = computed(() => profile.value?.user_id || profile.value?.id || 0)

// 100 seats laid out as 4 rows × 25 cols (blocks 8 + 9 + 8).
// Backend seat_index ∈ [0..49] maps to the 50 best central positions.
const PREMIUM_SEATS = (() => {
  const cells = []
  for (let r = 0; r < 4; r++) {
    for (let c = 0; c < 25; c++) {
      cells.push({ pos: r * 25 + c, dist: Math.abs(r - 1.5) * 2.2 + Math.abs(c - 12) })
    }
  }
  cells.sort((a, b) => a.dist - b.dist)
  return cells.slice(0, 50).map(x => x.pos)
})()

function flatPos(row, colInBlock, block) {
  let col
  if (block === 'L') col = colInBlock
  else if (block === 'C') col = 8 + colInBlock
  else col = 17 + colInBlock
  return row * 25 + col
}

// Terminated events keep their invitations rows for history but must not
// surface seated avatars or live bubbles — the cinema view itself bounces
// the user back home when this is true, this is just defence in depth so
// any future entry point still renders an empty (clean) room.
const terminated = computed(() => Boolean(props.event?.is_terminated))

function seatOccupant(row, colInBlock, block) {
  if (!props.event || terminated.value) return null
  const flat = flatPos(row, colInBlock, block)
  const seatIdx = PREMIUM_SEATS.indexOf(flat)
  if (seatIdx < 0) return null
  const inv = props.event.invitations?.find(
    i => i.status === INVITATION_STATUS.ACCEPTED && i.seat_index === seatIdx,
  )
  if (!inv) return null
  // Presence gate: the seat row stays put (returning viewer reclaims
  // the same seat) but the live avatar is only painted when the
  // back-end's last-seen heartbeat is still within the presence
  // window. ``is_currently_in_room`` is computed server-side
  // (mk_events_utils.is_currently_in_room) and refreshed on every
  // ``getOne`` / ``enter_room`` / marathon-progress merge.
  if (!inv.is_currently_in_room) return null
  return inv
}

function seatClass(row, colInBlock, block) {
  const occ = seatOccupant(row, colInBlock, block)
  if (!occ) return ''
  return occ.user_id === myUserId.value
    ? 'pt-cr-seat--occupied pt-cr-seat--mine'
    : 'pt-cr-seat--occupied'
}

function seatTitle(row, colInBlock, block) {
  return seatOccupant(row, colInBlock, block)?.username || ''
}

// ---------- Chat bubbles above seats ----------
// userId → array of { id, text, ts }. Auto-evicted after BUBBLE_TTL_MS.
const BUBBLE_TTL_MS = 7000
const bubblesByUser = ref({})
let lastSeenMsgId = 0
let bubblePollTimer = null
let bubbleSweepTimer = null

function seatBubbles(row, colInBlock, block) {
  const occ = seatOccupant(row, colInBlock, block)
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
      // Keep only the 3 most recent so the stack doesn't explode.
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
