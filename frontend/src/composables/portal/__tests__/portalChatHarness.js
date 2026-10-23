/**
 * Shared harness for the portal chat tests: a stubbed WebSocket, an API stub
 * routed by URL, and small helpers. Each test file declares its own vi.mock of
 * useApi with ``apiGet`` / ``apiPost`` from here.
 */
import { beforeEach, afterEach, vi } from 'vitest'

export const apiGet = vi.fn()
export const apiPost = vi.fn()

export class FakeSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSED = 3
  static instances = []

  constructor(url) {
    this.url = url
    this.readyState = FakeSocket.CONNECTING
    FakeSocket.instances.push(this)
  }

  // Like a browser, the close event comes later: see drop().
  close() {
    this.readyState = FakeSocket.CLOSED
  }

  open() {
    this.readyState = FakeSocket.OPEN
    this.onopen?.()
  }

  // The server or the network closed the connection (or refused the handshake).
  drop() {
    this.readyState = FakeSocket.CLOSED
    this.onclose?.()
  }

  receive(message) {
    this.onmessage?.({ data: JSON.stringify({ type: 'message', data: message }) })
  }
}

export const LOUNGE = 1
export const PARTY = 2
export const VIEWER = 7
const OTHER = 8
export const UNREAD_URL = '/api/portal/chat/unread'
export const MARK_READ_URL = '/api/portal/chat/mark-read'
export const historyUrl = roomId => `/api/portal/chat/rooms/${roomId}/messages?limit=50`
// How long the open panel waits before reporting what it displayed (usePortalChat).
export const READ_SYNC_MS = 1000

export const message = (id, roomId = LOUNGE, userId = OTHER) => ({
  id,
  room_id: roomId,
  user_id: userId,
  content: `m${id}`,
})
export const onePage = (...items) => ({
  items: items.reverse(),
  has_more: false,
  next_cursor: null,
})

// What the server answers: a test swaps these to script it.
export const replies = { rooms: null, unread: null, history: null }

function routeApi() {
  apiGet.mockImplementation(async url => {
    if (url === '/api/portal/chat/rooms') return replies.rooms()
    if (url === UNREAD_URL) return replies.unread()
    const room = /\/rooms\/(\d+)\/messages/.exec(url)
    if (room) return replies.history(Number(room[1]), url)
    throw new Error(`unexpected GET ${url}`)
  })
}

/** Fresh chat module, fake timers and default answers around every test. */
export function useChatTestEnv() {
  beforeEach(() => {
    vi.resetModules()
    vi.useFakeTimers()
    vi.spyOn(Math, 'random').mockReturnValue(1) // no jitter: the full delay
    vi.stubGlobal('WebSocket', FakeSocket)
    FakeSocket.instances = []
    apiGet.mockReset()
    apiPost.mockReset()
    replies.rooms = () => ({ items: [{ id: LOUNGE }, { id: PARTY }] })
    replies.unread = () => ({ unread: 0 })
    replies.history = roomId => onePage(message(roomId * 100 + 1, roomId))
    routeApi()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })
}

/** A fresh chat composable, not started yet. */
export async function loadChat() {
  const { usePortalChat } = await import('@/composables/portal/usePortalChat')
  return usePortalChat()
}

export async function bootChat() {
  const chat = await loadChat()
  await chat.initGlobalChat({ user_id: VIEWER })
  return chat
}

export function deferred() {
  let resolve
  let reject
  const promise = new Promise((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

export const sockets = () => FakeSocket.instances
export const lastSocket = () => FakeSocket.instances.at(-1)
export const unreadCalls = () => apiGet.mock.calls.filter(([url]) => url === UNREAD_URL).length
export const markReadBodies = () =>
  apiPost.mock.calls.filter(([url]) => url === MARK_READ_URL).map(([, body]) => body)
export const markReadCalls = () => markReadBodies().length
export const ids = chat => chat.messages.value.map(m => m.id)
