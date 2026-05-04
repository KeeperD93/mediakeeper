<template>
  <!--
    Compact glassmorphism chat panel anchored to the home FAB.

    - Singleton state via usePortalChat (badge, ws, unread)
    - Message format: [HH:MM · DD/MM] pseudo :: content, [report] / [delete (Xs)]
    - Self-delete only valid for 60s after posting (countdown on button)
    - Others can flag a message → backend notifies the admin bell
    - Emoji picker: hardcoded grid, no dep
    - GIF button stub for now
  -->
  <div class="pt-chat" role="dialog" :aria-label="$t('portal.chat')">
    <div class="pt-chat-head">
      <h3>{{ $t('portal.chat') }}</h3>
      <select v-if="rooms.length > 1" v-model="roomSel" class="pt-chat-room" @change="switchRoom">
        <option v-for="r in rooms" :key="r.id" :value="r.id">{{ r.name }}</option>
      </select>
      <button class="pt-chat-x" :aria-label="$t('common.close')" @click="$emit('close')">
        <X :size="16" :stroke-width="2.5" />
      </button>
    </div>

    <div ref="listRef" class="pt-chat-list">
      <div
        v-for="msg in messages"
        :key="msg.id"
        class="pt-chat-row"
        :class="{
          'pt-chat-row--mine': msg.user_id === ownUserId,
          'pt-chat-row--deleted': msg.deleted,
          'pt-chat-row--anon': msg.user_deleted,
        }"
      >
        <div class="pt-chat-meta">
          <span class="pt-chat-date">{{ formatMeta(msg.created_at) }}</span>
          <span class="pt-chat-pseudo">
            {{ msg.user_deleted
              ? $t('portal.chatDeletedUser')
              : (msg.user_name || ('#' + msg.user_id)) }}
          </span>
        </div>
        <div v-if="msg.deleted" class="pt-chat-body pt-chat-body--deleted">
          {{ $t('portal.chatMessageDeleted') }}
        </div>
        <div v-else class="pt-chat-body">{{ msg.content }}</div>
        <div v-if="!msg.deleted" class="pt-chat-actions">
          <button
            v-if="msg.user_id === ownUserId && canSelfDelete(msg)"
            class="pt-chat-act"
            :title="$t('common.delete')"
            @click="doDelete(msg)"
          >
            <Trash2 :size="13" />
            <span>{{ secondsLeft(msg) }}s</span>
          </button>
          <button
            v-if="!msg.user_deleted && msg.user_id !== ownUserId && !reportedIds.has(msg.id)"
            class="pt-chat-act pt-chat-act--warn"
            :class="{ 'pt-chat-act--reporting': reportingId === msg.id }"
            :disabled="reportingId === msg.id"
            :title="$t('portal.chatReport')"
            @click="doReport(msg)"
          >
            <Flag :size="13" />
          </button>
          <span
            v-else-if="!msg.user_deleted && msg.user_id !== ownUserId && reportedIds.has(msg.id)"
            class="pt-chat-act pt-chat-act--reported"
            :class="{ 'pt-chat-act--reported-flash': flashId === msg.id }"
            :title="$t('portal.chatReportedTitle')"
            aria-disabled="true"
          >
            <FlagOff :size="13" />
          </span>
        </div>
      </div>
      <div v-if="!messages.length" class="pt-chat-empty">{{ $t('portal.chatEmpty') }}</div>
    </div>

    <div class="pt-chat-composer">
      <button class="pt-chat-icon" :title="$t('portal.chatEmoji')" @click="toggleEmoji">
        <Smile :size="18" />
      </button>
      <button class="pt-chat-icon pt-chat-icon--disabled" :title="$t('portal.chatGifDisabled')" disabled>
        <span class="pt-chat-gif">GIF</span>
      </button>
      <input
        v-model="draft"
        class="pt-chat-field"
        :placeholder="$t('portal.chatPlaceholder')"
        maxlength="2000"
        @keydown.enter.prevent="send"
      />
      <button class="pt-chat-send" :disabled="!draft.trim()" @click="send">
        <Send :size="16" />
      </button>
    </div>

    <!-- Emoji popover -->
    <div v-if="emojiOpen" class="pt-chat-emoji" @click.stop>
      <button
        v-for="e in EMOJIS"
        :key="e"
        class="pt-chat-emoji-btn"
        @click="insertEmoji(e)"
      >{{ e }}</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { usePortalChat } from '@/composables/portal/usePortalChat'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { Flag, FlagOff, Send, Smile, Trash2, X } from 'lucide-vue-next'

import '@/assets/styles/portal/chat-panel.css'

const emit = defineEmits(['close'])

const {
  rooms, messages, currentRoomId,
  fetchAllMessages, sendMessage,
  deleteMessage, reportMessage, setPanelOpen,
} = usePortalChat()
const { profile } = usePortalAuth()

const ownUserId = ref(null)
const roomSel = ref(null)
const draft = ref('')
const listRef = ref(null)
const emojiOpen = ref(false)
// Reported message IDs are tracked client-side so the flag button hides
// the moment the user signals a message — the backend is idempotent on
// duplicates, but the UX needs to lock immediately rather than wait for
// a re-fetch. The Set survives only the current session; a refresh
// re-enables the button until the user retries (the backend then
// returns ``already_reported`` and we add it back).
const reportedIds = ref(new Set())
const reportingId = ref(null)
const flashId = ref(null)

// Hardcoded 60 emoji grid — good enough for a first pass.
const EMOJIS = [
  '😀','😁','😂','🤣','😃','😄','😅','😆','😉','😊',
  '😍','😘','😗','😎','🤩','🤔','😐','😑','🙄','😬',
  '😪','😴','😷','🤒','🤕','🤢','🤮','🥳','🥺','😢',
  '😭','😱','😡','🤬','🤯','😳','🥵','🥶','😈','👻',
  '👍','👎','👏','🙌','🙏','💪','🤝','❤️','💔','💯',
  '🔥','⭐','✨','🎉','🎬','🍿','📺','🎮','🎵','🎤',
]

// Tick ref used to re-compute the 60s countdown without setting up a
// watcher on every message.
const nowTick = ref(Date.now())
let tickTimer = null

function formatMeta(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const mo = String(d.getMonth() + 1).padStart(2, '0')
  return `${hh}:${mm} · ${dd}/${mo}`
}

function canSelfDelete(msg) {
  return secondsLeft(msg) > 0
}
function secondsLeft(msg) {
  if (!msg.created_at) return 0
  const age = (nowTick.value - new Date(msg.created_at).getTime()) / 1000
  return Math.max(0, Math.ceil(60 - age))
}

async function switchRoom() {
  if (!roomSel.value) return
  // Pull the full history (drains the cursor pagination) so the user
  // can scroll all the way back without an extra "load more" gesture.
  // The realtime websocket is owned by the portal layout, so we don't
  // touch it here — new incoming messages are pushed straight into
  // ``messages`` by the global handler.
  await fetchAllMessages(roomSel.value)
  scrollBottom()
}

async function send() {
  const content = draft.value.trim()
  if (!content || !roomSel.value) return
  // REST POST is used (instead of the websocket frame) so the message
  // round-trips through the database and comes back with its real id /
  // timestamp / display name in a single response. We push it locally
  // straight away — the websocket handler skips own-id messages to
  // avoid the duplicate echo.
  const res = await sendMessage(roomSel.value, content)
  if (!res?.message) return // keep the draft so the user can retry
  messages.value.push(res.message)
  draft.value = ''
  scrollBottom()
}

async function doDelete(msg) {
  await deleteMessage(msg.id)
}
async function doReport(msg) {
  if (reportingId.value === msg.id || reportedIds.value.has(msg.id)) return
  reportingId.value = msg.id
  try {
    const res = await reportMessage(msg.id)
    if (res?.success || res?.already_reported) {
      // Atomically replace the Set — Vue refs only react to assignment
      // for non-deeply-tracked containers, so a plain ``add`` would not
      // re-render the v-if on the report button.
      const next = new Set(reportedIds.value)
      next.add(msg.id)
      reportedIds.value = next
      flashId.value = msg.id
      setTimeout(() => {
        if (flashId.value === msg.id) flashId.value = null
      }, 700)
    }
  } finally {
    reportingId.value = null
  }
}

function toggleEmoji() {
  emojiOpen.value = !emojiOpen.value
}
function insertEmoji(e) {
  draft.value += e
  emojiOpen.value = false
}

function scrollBottom() {
  nextTick(() => {
    if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight
  })
}

watch(messages, scrollBottom, { deep: true })

onMounted(async () => {
  ownUserId.value = profile.value?.user_id || profile.value?.id || null
  setPanelOpen(true)
  // Rooms and the realtime websocket are already wired up by the portal
  // layout (initGlobalChat). We just pick the active room and pull the
  // full history into the panel.
  roomSel.value = currentRoomId.value || (rooms.value[0]?.id ?? null)
  if (roomSel.value) await switchRoom()
  // Refresh the countdown every second while the panel is open.
  tickTimer = setInterval(() => { nowTick.value = Date.now() }, 1000)
})

onBeforeUnmount(() => {
  // Keep the websocket alive for background unread tracking — the panel
  // is just a viewport over the singleton ``messages`` ref.
  setPanelOpen(false)
  if (tickTimer) clearInterval(tickTimer)
})
</script>
