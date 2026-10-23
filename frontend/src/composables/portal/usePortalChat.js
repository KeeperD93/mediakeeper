import { ref } from 'vue'
import { useApi } from '@/composables/useApi'
import { closeChatSocket, openChatSocket, sendChatFrame } from './portalChatSocket'

// Module-scoped singletons so the FAB badge, the chat panel and any
// other consumer share the same websocket + unread counter.
const rooms = ref([])
const messages = ref([])
const currentRoomId = ref(null)
const unreadCount = ref(0)
// Consumers (the panel) flip this to true when the panel is visible
// so incoming messages don't bump ``unreadCount`` while the user is
// actually reading.
const panelOpen = ref(false)
const UNREAD_URL = '/api/portal/chat/unread'
// The open panel reports what it displayed once a burst of messages settles.
const READ_SYNC_DELAY_MS = 1000
let ownUserId = null
let initialised = false
// Bumped by every shutdown: an answer that arrives afterwards is dropped.
let generation = 0
// Room the panel shows or is switching to. Only the newest history load may
// write ``messages``: the panel and a reconnect can load at the same time.
let panelRoomId = null
let historySeq = 0
// Load whose rows the list holds in full: a live message is reported read only
// on top of one, never over rows the list still misses.
let settledSeq = -1
// Newest message the open panel displayed, and the newest the server was told
// about: the read pointer only ever covers what the viewer was shown.
let shownUpTo = 0
let syncedUpTo = 0
let readSyncTimer = null

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
  } catch {
    /* audio denied — silently ignore */
  }
}

export function usePortalChat() {
  const { apiGet, apiPost, apiDelete } = useApi()

  async function fetchRooms() {
    const res = await apiGet('/api/portal/chat/rooms')
    if (res) rooms.value = res.items || []
  }

  /**
   * Load the full history of ``roomId`` into ``messages``, capped at 20 round
   * trips (~1000 messages) so a misconfigured room cannot loop. Returns false
   * when a newer load or a shutdown took over, or the session ended meanwhile.
   */
  async function fetchAllMessages(roomId) {
    const wasSettled = settledSeq === historySeq
    const seq = ++historySeq
    const previousRoom = panelRoomId
    panelRoomId = roomId
    // Rows listed now were stored before the pages are read: one the pages lack
    // was deleted on the server.
    const listed = new Set(messages.value.map(m => m.id))
    const pages = []
    let cursor = null
    try {
      for (let page = 0; page < 20; page++) {
        const query = cursor ? `&cursor=${cursor}` : ''
        const res = await apiGet(`/api/portal/chat/rooms/${roomId}/messages?limit=50${query}`)
        if (seq !== historySeq || !res) return false
        pages.unshift(...(res.items || []).slice().reverse())
        if (!res.has_more) break
        cursor = res.next_cursor
      }
    } catch (e) {
      // A room the viewer cannot read leaves the panel on the room it showed.
      if (seq === historySeq) {
        panelRoomId = previousRoom
        if (wasSettled) settledSeq = seq
      }
      throw e
    }
    // Keep what the socket delivered for this room while the pages loaded, and
    // the deletions made meanwhile.
    const newest = pages.at(-1)?.id ?? 0
    const deleted = new Set(messages.value.filter(m => m.deleted).map(m => m.id))
    const live = messages.value.filter(
      m => m.room_id === roomId && m.id > newest && !listed.has(m.id),
    )
    messages.value = [...pages.map(m => (deleted.has(m.id) ? { ...m, deleted: true } : m)), ...live]
    settledSeq = seq
    if (panelOpen.value) _noteShown(messages.value.at(-1)?.id ?? 0)
    return true
  }

  async function sendMessage(roomId, content) {
    return await apiPost(`/api/portal/chat/rooms/${roomId}/messages`, { content })
  }

  async function deleteMessage(messageId) {
    const res = await apiDelete(`/api/portal/chat/messages/${messageId}`)
    if (res?.success) {
      const idx = messages.value.findIndex(m => m.id === messageId)
      if (idx >= 0) messages.value[idx].deleted = true
    }
    return res
  }

  async function reportMessage(messageId, reason = null) {
    return await apiPost(`/api/portal/chat/messages/${messageId}/report`, { reason })
  }

  function sendWsMessage(content) {
    sendChatFrame(content)
  }

  async function loadUnread() {
    const gen = generation
    try {
      const res = await apiGet(UNREAD_URL)
      if (gen === generation) unreadCount.value = res?.unread || 0
    } catch {
      /* silent */
    }
  }

  // Clears the badge: the open panel moves the server pointer as it displays messages.
  function markRead() {
    unreadCount.value = 0
  }

  function _noteShown(id) {
    if (id <= shownUpTo) return
    shownUpTo = id
    clearTimeout(readSyncTimer)
    readSyncTimer = setTimeout(_syncReadPointer, READ_SYNC_DELAY_MS)
  }

  // Move the server read pointer up to the newest message the panel displayed.
  async function _syncReadPointer() {
    clearTimeout(readSyncTimer)
    readSyncTimer = null
    const gen = generation
    const upTo = shownUpTo
    if (upTo <= syncedUpTo) return
    try {
      await apiPost('/api/portal/chat/mark-read', { up_to: upTo })
      if (gen === generation) syncedUpTo = Math.max(syncedUpTo, upTo)
    } catch {
      /* silent: the next sync sends it again */
    }
  }

  function setPanelOpen(open) {
    panelOpen.value = open
    if (open) markRead()
    else _syncReadPointer()
  }

  function _onMessage(msg) {
    // Already listed: the panel's own POST result, a reload, a reconnect race.
    if (messages.value.some(m => m.id === msg.id)) return
    // The list takes it when the panel shows this room, or no room yet (the
    // panel opens on the socket's room); never another room's history.
    const shown = panelRoomId === null || msg.room_id === panelRoomId
    if (shown) messages.value.push(msg)
    // The viewer's own messages, from this tab or another, never ring or count.
    const own = ownUserId != null && msg.user_id === ownUserId
    if (shown && panelOpen.value) {
      if (!own) playBeep()
      // While a load is due, the list still misses rows: the load reports them all.
      if (settledSeq === historySeq) _noteShown(msg.id)
    } else if (!own) {
      unreadCount.value += 1
    }
  }

  // Re-sync after a reconnect: the open panel reloads the room it shows, which
  // it then reports as read; otherwise only the unread count is refreshed.
  async function _catchUp() {
    const gen = generation
    // The list misses what was posted while the socket was down.
    settledSeq = -1
    try {
      if (panelOpen.value) {
        const loaded = await fetchAllMessages(panelRoomId ?? currentRoomId.value)
        if (loaded && panelOpen.value) return
      }
      if (gen !== generation) return
      // A read report that failed while offline goes out before the server counts.
      if (shownUpTo > syncedUpTo) await _syncReadPointer()
      const res = await apiGet(UNREAD_URL)
      // An open panel owns the badge, and a shutdown drops the answer.
      if (res && gen === generation && !panelOpen.value) unreadCount.value = res.unread || 0
    } catch (e) {
      console.error('[usePortalChat.catchUp]', e)
    }
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
    // A shutdown while the rooms or the count load ends this start.
    const gen = generation
    await fetchRooms()
    if (gen !== generation) return
    if (!rooms.value.length) {
      initialised = false
      return
    }
    const roomId = rooms.value[0].id
    currentRoomId.value = roomId
    await loadUnread()
    if (gen !== generation) return
    openChatSocket(roomId, {
      message: _onMessage,
      reopened: _catchUp,
      checkSession: () => apiGet(UNREAD_URL),
      accessRemoved: shutdownGlobalChat,
    })
  }

  function shutdownGlobalChat() {
    closeChatSocket()
    initialised = false
    ownUserId = null
    currentRoomId.value = null
    generation += 1
    // Drops a history load still in flight.
    historySeq += 1
    panelRoomId = null
    // What the panel displayed in its last second goes unreported: posting while
    // the session ends would race the logout.
    clearTimeout(readSyncTimer)
    readSyncTimer = null
    shownUpTo = 0
    syncedUpTo = 0
    messages.value = []
    unreadCount.value = 0
  }

  return {
    // state
    rooms,
    messages,
    unreadCount,
    currentRoomId,
    panelOpen,
    // api
    fetchRooms,
    fetchAllMessages,
    sendMessage,
    deleteMessage,
    reportMessage,
    sendWsMessage,
    loadUnread,
    markRead,
    setPanelOpen,
    // lifecycle
    initGlobalChat,
    shutdownGlobalChat,
  }
}
