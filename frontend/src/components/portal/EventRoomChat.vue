<template>
  <aside class="pt-erc" :class="{ 'pt-erc--collapsed': collapsed }">
    <button
      class="pt-erc-toggle"
      :aria-label="$t(collapsed ? 'common.open' : 'common.close')"
      @click="collapsed = !collapsed"
    >
      <ChevronLeft v-if="collapsed" :size="16" :stroke-width="2.5" />
      <ChevronRight v-else :size="16" :stroke-width="2.5" />
    </button>

    <div v-if="!collapsed" class="pt-erc-inner">
      <header class="pt-erc-head">
        <h3>{{ $t('portal.cinema.chatTitle') }}</h3>
      </header>

      <div ref="listRef" class="pt-erc-list">
        <div v-if="loading" class="pt-erc-empty">{{ $t('common.loading') }}</div>
        <div v-else-if="!messages.length" class="pt-erc-empty">
          {{ $t('portal.cinema.chatEmpty') }}
        </div>
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="pt-erc-msg"
          :class="{ 'pt-erc-msg--mine': msg.user_id === myUserId }"
        >
          <div class="pt-erc-msg-head">
            <span class="pt-erc-pseudo">{{ msg.username }}</span>
            <span class="pt-erc-time">{{ formatTime(msg.sent_at) }}</span>
          </div>
          <div class="pt-erc-body">{{ msg.content }}</div>
        </div>
      </div>

      <div class="pt-erc-composer">
        <input
          v-model="draft"
          type="text"
          maxlength="2000"
          :placeholder="$t('portal.cinema.chatPlaceholder')"
          class="pt-erc-input"
          @keydown.enter.prevent="send"
        />
        <button
          class="pt-erc-send"
          :aria-label="$t('portal.tickets.thread.reply.send')"
          :disabled="!draft.trim() || sending"
          @click="send"
        >
          <Send :size="16" :stroke-width="2.5" />
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRooms } from '@/composables/portal/useRooms'
import { usePortalAuth } from '@/composables/portal/usePortalAuth'
import { ChevronLeft, ChevronRight, Send } from 'lucide-vue-next'
import { localizedTime } from '@/utils/datetime'

const props = defineProps({
  eventId: { type: Number, required: true },
})

const { listMessages, postMessage } = useRooms()
const { profile } = usePortalAuth()

const messages = ref([])
const draft = ref('')
const loading = ref(false)
const sending = ref(false)
const collapsed = ref(false)
const listRef = ref(null)
let pollTimer = null

const myUserId = computed(() => profile.value?.user_id || profile.value?.id || 0)

async function refresh() {
  loading.value = !messages.value.length
  try {
    messages.value = await listMessages(props.eventId)
    await nextTick()
    scrollBottom()
  } finally {
    loading.value = false
  }
}

async function send() {
  const txt = draft.value.trim()
  if (!txt || sending.value) return
  sending.value = true
  try {
    const msg = await postMessage(props.eventId, txt)
    if (msg && !msg.error) {
      messages.value.push({
        id: msg.id,
        user_id: myUserId.value,
        username: profile.value?.display_name || 'moi',
        content: msg.content,
        sent_at: msg.sent_at,
      })
      draft.value = ''
      await nextTick()
      scrollBottom()
    }
  } finally {
    sending.value = false
  }
}

function scrollBottom() {
  if (!listRef.value) return
  listRef.value.scrollTop = listRef.value.scrollHeight
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return localizedTime(d, { hour: '2-digit', minute: '2-digit' })
}

onMounted(() => {
  refresh()
  // Poll every 4 s. WebSocket plumbing is left for a future iteration.
  pollTimer = setInterval(refresh, 4000)
})
onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.pt-erc {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: clamp(280px, 28vw, 380px);
  background: rgb(15, 15, 22, 0.92);
  border-left: 1px solid rgb(255, 255, 255, 0.1);
  display: flex;
  flex-direction: column;
  z-index: 11;
  backdrop-filter: var(--portal-blur-md);
  -webkit-backdrop-filter: var(--portal-blur-md);
  transition: transform var(--portal-dur-slow);
}
.pt-erc--collapsed {
  transform: translateX(calc(100% - 30px));
}
.pt-erc-toggle {
  position: absolute;
  left: -30px;
  top: 50%;
  transform: translateY(-50%);
  width: 30px;
  height: 60px;
  border: 1px solid rgb(255, 255, 255, 0.15);
  border-right: none;
  background: rgb(15, 15, 22, 0.92);
  color: var(--portal-text-primary);
  border-radius: 8px 0 0 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.pt-erc-inner {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-height: 0;
}
.pt-erc-head {
  padding: 1rem;
  border-bottom: 1px solid var(--portal-border-default);
}
.pt-erc-head h3 {
  font-size: var(--portal-text-base);
  font-weight: var(--portal-font-extrabold);
  color: var(--portal-text-primary);
}

.pt-erc-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.pt-erc-empty {
  color: var(--portal-text-muted);
  font-size: var(--portal-text-sm);
  text-align: center;
  padding: 1rem;
}
.pt-erc-msg {
  background: var(--portal-surface-2);
  border: 1px solid var(--portal-border-subtle);
  border-radius: var(--radius-btn);
  padding: 0.5rem 0.7rem;
}
.pt-erc-msg--mine {
  background: rgb(67, 56, 202, 0.18);
  border-color: rgb(67, 56, 202, 0.4);
}
.pt-erc-msg-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.2rem;
}
.pt-erc-pseudo {
  font-size: var(--portal-text-xs);
  font-weight: var(--portal-font-bold);
  color: var(--portal-text-body);
}
.pt-erc-time {
  font-size: var(--portal-text-2xs);
  color: var(--portal-text-muted);
}
.pt-erc-body {
  font-size: var(--portal-text-sm);
  color: var(--portal-text-primary);
  /* stylelint-disable-next-line declaration-property-value-keyword-no-deprecated -- non-standard but widely supported; behaviour differs from overflow-wrap: break-word on CJK */
  word-break: break-word;
  white-space: pre-wrap;
}

.pt-erc-composer {
  display: flex;
  gap: 0.4rem;
  padding: 0.6rem;
  border-top: 1px solid var(--portal-border-default);
}
.pt-erc-input {
  flex: 1;
  background: rgb(255, 255, 255, 0.05);
  border: 1px solid var(--portal-border-strong);
  color: #fff !important;
  -webkit-text-fill-color: #fff !important;
  caret-color: var(--portal-text-primary);
  border-radius: var(--radius-sm);
  padding: 0.5rem 0.7rem;
  font-size: var(--portal-text-sm);
  outline: none;
  font-family: inherit;
}
.pt-erc-input:focus {
  border-color: rgb(67, 56, 202, 0.7);
}
.pt-erc-send {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  border: none;
  background: var(--accent-700);
  color: var(--portal-text-primary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.pt-erc-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
