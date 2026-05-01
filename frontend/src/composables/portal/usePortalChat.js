import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

// Module-scoped singletons so the FAB badge, the chat panel and any
// other consumer share the same websocket + unread counter.
const rooms = ref([])
const messages = ref([])
const hasMore = ref(false)
const nextCursor = ref(null)
const currentRoomId = ref(null)
const unreadCount = ref(0)
// Consumers (the panel) flip this to true when the panel is visible
// so incoming messages don't bump ``unreadCount`` while the user is
// actually reading.
const panelOpen = ref(false)
let ws = null
let reconnectTimer = null
let intentionalClose = false
let ownUserId = null
let initialised = false

// Reusable beep via Web Audio API — no external asset, no warmup
// latency, respects the user's autoplay policy because it's triggered
// inside the ws.onmessage callback.
let audioCtx = null
function playBeep() {
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)()
    const ctx = audioCtx
    if (ctx.state === 'suspended') ctx.resume().catch(() => {})
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = 'sine'
    osc.frequency.value = 880
    gain.gain.value = 0.0001
    gain.gain.exponentialRampToValueAtTime(0.18, ctx.currentTime + 0.01)
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.18)
    osc.connect(gain).connect(ctx.destination)
    osc.start()
    osc.stop(ctx.currentTime + 0.2)
  } catch { /* audio denied — silently ignore */ }
}

export function usePortalChat() {
  const { apiGet, apiPost, apiDelete } = useApi()

  async function fetchRooms() {
    const res = await apiGet('/api/portal/chat/rooms')
    if (res) rooms.value = res.items || []
  }

  async function fetchMessages(roomId, reset = true) {
    if (reset) {
      messages.value = []
      nextCursor.value = null
    }
    let url = `/api/portal/chat/rooms/${roomId}/messages?limit=50`
    if (nextCursor.value) url += `&cursor=${nextCursor.value}`
    const res = await apiGet(url)
    if (!res) return
    const items = (res.items || []).slice().reverse()
    if (reset) messages.value = items
    else messages.value.unshift(...items)
    nextCursor.value = res.next_cursor
    hasMore.value = res.has_more
  }

  async function fetchAllMessages(roomId) {
    // Drain the cursor pagination so the panel always shows the full
    // history on open. Capped at 20 round trips (~ 1000 messages with
    // limit=50) to keep a misconfigured room from looping forever.
    await fetchMessages(roomId, true)
    let safety = 20
    while (hasMore.value && safety > 0) {
      await fetchMessages(roomId, false)
      safety -= 1
    }
  }

  async function sendMessage(roomId, content) {
    return await apiPost(`/api/portal/chat/rooms/${roomId}/messages`, { content })
  }

  async function deleteMessage(messageId) {
    const res = await apiDelete(`/api/portal/chat/messages/${messageId}`)
    if (res?.success) {
      const idx = messages.value.findIndex((m) => m.id === messageId)
      if (idx >= 0) messages.value[idx].deleted = true
    }
    return res
  }

  async function reportMessage(messageId, reason = null) {
    return await apiPost(`/api/portal/chat/messages/${messageId}/report`, { reason })
  }

  function _connectWs(roomId) {
    intentionalClose = false
    if (ws && ws.readyState !== WebSocket.CLOSED) {
      try { ws.close() } catch { /* ignore */ }
    }
    currentRoomId.value = roomId
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    ws = new WebSocket(`${proto}://${location.host}/api/portal/chat/ws/${roomId}`)

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type !== 'message') return
        const msg = data.data
        // Skip the echo of our own REST POST: the panel already pushed
        // the message into the list when the POST resolved, so honoring
        // the broadcast would duplicate it.
        if (ownUserId != null && msg?.user_id === ownUserId) return
        // Drop accidental duplicates (e.g. reconnect race) — a chat
        // message id is monotonic so a known id means we already have
        // it.
        if (msg?.id != null && messages.value.some((m) => m.id === msg.id)) return
        messages.value.push(msg)
        if (panelOpen.value) {
          playBeep()
        } else {
          unreadCount.value += 1
        }
      } catch { /* ignore parse errors */ }
    }

    ws.onclose = () => {
      ws = null
      if (intentionalClose) return
      // Auto-reconnect: the chat is supposed to be on for the whole
      // portal session so the unread counter keeps incrementing in the
      // background. 3 s back-off keeps us out of a tight loop on a
      // server outage without feeling laggy on a transient hiccup.
      if (reconnectTimer) clearTimeout(reconnectTimer)
      reconnectTimer = setTimeout(() => {
        if (currentRoomId.value != null) _connectWs(currentRoomId.value)
      }, 3000)
    }
  }

  function disconnectWs() {
    intentionalClose = true
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
    if (ws) {
      try { ws.close() } catch { /* ignore */ }
      ws = null
    }
  }

  function sendWsMessage(content) {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ content }))
    }
  }

  async function loadUnread() {
    try {
      const res = await apiGet('/api/portal/chat/unread')
      unreadCount.value = res?.unread || 0
    } catch { /* silent */ }
  }

  async function markRead() {
    if (unreadCount.value === 0) return
    unreadCount.value = 0
    try {
      await apiPost('/api/portal/chat/mark-read', {})
    } catch { /* silent: re-syncs on next loadUnread */ }
  }

  function setPanelOpen(open) {
    panelOpen.value = open
    if (open) markRead()
  }

  /**
   * Boot the persistent global chat for the current portal session.
   * Idempotent: a second call is a no-op until ``shutdownGlobalChat``
   * runs. Safe to call before the user opens the chat — the unread
   * counter and the realtime websocket are wired up in the background
   * so a freshly-logged-in user immediately sees how many messages
   * landed since their last visit.
   */
  async function initGlobalChat(profile) {
    if (initialised) return
    if (!profile || profile.chat_enabled === false) return
    ownUserId = profile.user_id || profile.id || null
    initialised = true
    await fetchRooms()
    if (!rooms.value.length) {
      initialised = false
      return
    }
    const roomId = rooms.value[0].id
    currentRoomId.value = roomId
    await loadUnread()
    _connectWs(roomId)
  }

  function shutdownGlobalChat() {
    disconnectWs()
    initialised = false
    ownUserId = null
    currentRoomId.value = null
    messages.value = []
    unreadCount.value = 0
  }

  return {
    // state
    rooms, messages, hasMore, nextCursor, unreadCount, currentRoomId, panelOpen,
    // api
    fetchRooms, fetchMessages, fetchAllMessages,
    sendMessage, deleteMessage, reportMessage,
    sendWsMessage, loadUnread, markRead,
    setPanelOpen,
    // lifecycle
    initGlobalChat, shutdownGlobalChat,
  }
}
