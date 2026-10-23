// The portal's live chat socket, one per portal session. After a close it checks
// the session over HTTP, then reconnects with a jittered back-off; handshakes
// refused again and again end the attempts. usePortalChat says what each event does.

// Reconnect back-off: 3 s, doubling up to 60 s, back to 3 s once a socket opens.
const RECONNECT_MIN_MS = 3000
const RECONNECT_MAX_MS = 60000
// Sockets refused in a row although the session is fine (chat turned off for this
// account, too many open tabs or devices, a proxy without WebSocket support):
// stop trying after this many.
const MAX_REFUSED_HANDSHAKES = 5

let ws = null
let socketRoomId = null
let handlers = null
let reconnectTimer = null
let reconnectDelay = RECONNECT_MIN_MS
let refusedHandshakes = 0
// Bumped by every close: a session check started before belongs to a closed chat.
let session = 0

/**
 * Open the live socket on ``roomId``. ``on`` supplies:
 * - ``message(msg)``: a chat message broadcast to the room;
 * - ``reopened()``: a reconnected socket is registered, time to catch up;
 * - ``checkSession()``: an HTTP call that resolves falsy once the session is gone
 *   (the API client is then on its way to the login page);
 * - ``accessRemoved()``: that check found chat access removed.
 */
export function openChatSocket(roomId, on) {
  handlers = on
  _connect(roomId, false)
}

/** Close the socket for good: no reconnect until the next openChatSocket. */
export function closeChatSocket() {
  session += 1
  reconnectDelay = RECONNECT_MIN_MS
  refusedHandshakes = 0
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (ws) {
    try {
      ws.close()
    } catch {
      /* ignore */
    }
    ws = null
  }
}

export function sendChatFrame(content) {
  if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ content }))
}

function _connect(roomId, catchUp) {
  if (ws && ws.readyState !== WebSocket.CLOSED) {
    try {
      ws.close()
    } catch {
      /* ignore */
    }
  }
  socketRoomId = roomId
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  const socket = new WebSocket(`${proto}://${location.host}/api/portal/chat/ws/${roomId}`)
  ws = socket
  let opened = false

  socket.onopen = () => {
    opened = true
    reconnectDelay = RECONNECT_MIN_MS
    refusedHandshakes = 0
    // The socket is registered now: a message posted during the reconnect is
    // either in the catch-up or arrives live (ids dedupe the overlap).
    if (catchUp) handlers.reopened()
  }

  socket.onmessage = event => {
    let data
    try {
      data = JSON.parse(event.data)
    } catch {
      return // not a chat frame
    }
    if (data?.type === 'message') handlers.message(data.data)
  }

  socket.onclose = () => {
    // A socket replaced by a newer one, or closed on purpose, must not reconnect.
    if (ws !== socket) return
    ws = null
    if (!opened) refusedHandshakes += 1
    if (refusedHandshakes >= MAX_REFUSED_HANDSHAKES) {
      // Live updates stop here; the panel still loads and posts over HTTP.
      closeChatSocket()
      return
    }
    _scheduleReconnect()
  }
}

// The chat stays on for the whole portal session so the unread counter keeps
// counting in the background. The jitter keeps clients from all coming back
// in the same second after a server restart.
function _scheduleReconnect() {
  if (reconnectTimer) clearTimeout(reconnectTimer)
  const delay = reconnectDelay / 2 + Math.random() * (reconnectDelay / 2)
  reconnectDelay = Math.min(reconnectDelay * 2, RECONNECT_MAX_MS)
  reconnectTimer = setTimeout(_resume, delay)
}

// The server closes the socket when the session ends or chat access is
// removed. Checking the session over HTTP first renews an admin's portal
// session, or sends a member whose session ended back to the login page.
async function _resume() {
  reconnectTimer = null
  const roomId = socketRoomId
  const started = session
  try {
    if (!(await handlers.checkSession()) || started !== session) return
  } catch (e) {
    if (started !== session) return
    // Chat access was removed: reconnecting would only be refused again.
    if (e?.message?.startsWith('permission_denied:')) {
      handlers.accessRemoved()
      return
    }
    console.error('[portalChatSocket.resume]', e)
    _scheduleReconnect()
    return
  }
  _connect(roomId, true)
}
