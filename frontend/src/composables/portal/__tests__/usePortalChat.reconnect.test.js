/**
 * Portal chat — reconnect.
 *
 * The server closes the socket when the session ends or chat access is removed,
 * so a reconnect first checks the session over HTTP, backs off (3 s doubling up
 * to 60 s), and catches up once the new socket is open. WebSocket and the API
 * are stubbed; timers are fake.
 */
import { describe, it, expect, vi } from 'vitest'
import {
  apiGet,
  apiPost,
  LOUNGE,
  PARTY,
  VIEWER,
  READ_SYNC_MS,
  historyUrl,
  message,
  onePage,
  replies,
  useChatTestEnv,
  bootChat,
  deferred,
  sockets,
  lastSocket,
  unreadCalls,
  markReadBodies,
  markReadCalls,
  ids,
} from './portalChatHarness'

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiGet, apiPost, apiDelete: vi.fn() }),
}))

describe('usePortalChat — reconnect', () => {
  useChatTestEnv()

  it('checks the session first, then re-syncs once the new socket is open', async () => {
    const chat = await bootChat()
    lastSocket().open()
    replies.unread = () => ({ unread: 5 })

    lastSocket().drop()
    await vi.advanceTimersByTimeAsync(2999)
    expect(sockets()).toHaveLength(1)
    await vi.advanceTimersByTimeAsync(1)
    expect(unreadCalls()).toBe(2) // boot, then the session check
    expect(sockets()).toHaveLength(2)
    expect(chat.unreadCount.value).toBe(0)

    lastSocket().open()
    await vi.advanceTimersByTimeAsync(0)
    expect(unreadCalls()).toBe(3) // the catch-up, once the socket is registered
    expect(chat.unreadCount.value).toBe(5)
  })

  it('backs off from 3 s up to 60 s, then starts over once a socket opens', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    await bootChat()
    lastSocket().open()
    replies.unread = () => {
      throw new TypeError('Failed to fetch')
    }

    lastSocket().drop()
    const waits = []
    for (let attempt = 0; attempt < 7; attempt++) {
      const before = unreadCalls()
      let waited = 0
      while (unreadCalls() === before) {
        await vi.advanceTimersByTimeAsync(1000)
        waited += 1000
      }
      waits.push(waited)
    }
    expect(waits).toEqual([3000, 6000, 12000, 24000, 48000, 60000, 60000])

    replies.unread = () => ({ unread: 0 })
    await vi.advanceTimersByTimeAsync(60_000)
    lastSocket().open()
    const before = unreadCalls()
    lastSocket().drop()
    await vi.advanceTimersByTimeAsync(3000)
    expect(unreadCalls()).toBe(before + 1)
  })

  it('spreads reconnects with jitter (half to full delay)', async () => {
    Math.random.mockReturnValue(0)
    await bootChat()
    lastSocket().drop()
    await vi.advanceTimersByTimeAsync(1499)
    expect(sockets()).toHaveLength(1)
    await vi.advanceTimersByTimeAsync(1)
    expect(sockets()).toHaveLength(2)
  })

  it('starts over after the chat restarts: 3 s back-off, refusals counted afresh', async () => {
    const chat = await bootChat()
    for (let attempt = 0; attempt < 4; attempt++) {
      lastSocket().drop() // handshake refused
      await vi.advanceTimersByTimeAsync(60_000)
    }
    chat.shutdownGlobalChat()
    await chat.initGlobalChat({ user_id: VIEWER })
    const count = sockets().length

    lastSocket().drop()
    await vi.advanceTimersByTimeAsync(3000)
    expect(sockets()).toHaveLength(count + 1)
  })

  it('gives up after five sockets refused in a row, keeping the list and the badge', async () => {
    replies.unread = () => ({ unread: 2 })
    const chat = await bootChat()
    await chat.fetchAllMessages(LOUNGE)
    for (let attempt = 0; attempt < 5; attempt++) {
      lastSocket().drop() // handshake refused: closed without ever opening
      await vi.advanceTimersByTimeAsync(60_000)
    }
    await vi.advanceTimersByTimeAsync(300_000)

    expect(sockets()).toHaveLength(5)
    expect(chat.unreadCount.value).toBe(2)
    expect(ids(chat)).toEqual([101])
  })

  it('counts refusals in a row only: a socket that opens starts the count over', async () => {
    const chat = await bootChat()
    for (let attempt = 0; attempt < 4; attempt++) {
      lastSocket().drop()
      await vi.advanceTimersByTimeAsync(60_000)
    }
    lastSocket().open()
    for (let attempt = 0; attempt < 4; attempt++) {
      lastSocket().drop()
      await vi.advanceTimersByTimeAsync(60_000)
    }

    expect(sockets()).toHaveLength(9)
    expect(chat.currentRoomId.value).toBe(LOUNGE)
  })

  it('stops for good when chat access was removed', async () => {
    const chat = await bootChat()
    lastSocket().open()
    replies.unread = () => {
      throw new Error('permission_denied:can_chat')
    }

    lastSocket().drop()
    await vi.advanceTimersByTimeAsync(120_000)

    expect(unreadCalls()).toBe(2)
    expect(sockets()).toHaveLength(1)
    expect(chat.currentRoomId.value).toBeNull()
  })

  it('does not reconnect once the API client heads to the login page', async () => {
    await bootChat()
    lastSocket().open()
    replies.unread = () => null

    lastSocket().drop()
    await vi.advanceTimersByTimeAsync(120_000)

    expect(unreadCalls()).toBe(2)
    expect(sockets()).toHaveLength(1)
  })

  it('keeps backing off while the server cannot be reached', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    await bootChat()
    lastSocket().open()
    replies.unread = () => {
      throw new TypeError('Failed to fetch')
    }

    lastSocket().drop()
    await vi.advanceTimersByTimeAsync(3000)
    expect(unreadCalls()).toBe(2)
    await vi.advanceTimersByTimeAsync(6000)
    expect(unreadCalls()).toBe(3)

    expect(sockets()).toHaveLength(1)
    expect(consoleError).toHaveBeenCalledWith('[portalChatSocket.resume]', expect.any(TypeError))
  })

  it('reloads the room the open panel shows, then reports it read', async () => {
    const chat = await bootChat()
    lastSocket().open()
    chat.setPanelOpen(true)
    await chat.fetchAllMessages(PARTY)
    await vi.advanceTimersByTimeAsync(READ_SYNC_MS)
    replies.history = roomId =>
      onePage(message(roomId * 100 + 1, roomId), message(roomId * 100 + 2, roomId))

    lastSocket().drop()
    await vi.advanceTimersByTimeAsync(3000)
    lastSocket().open()
    await vi.advanceTimersByTimeAsync(READ_SYNC_MS)

    expect(apiGet).toHaveBeenLastCalledWith(historyUrl(PARTY))
    expect(ids(chat)).toEqual([201, 202])
    expect(markReadBodies()).toEqual([{ up_to: 201 }, { up_to: 202 }])
    expect(chat.unreadCount.value).toBe(0)
  })

  it('never reconnects after the chat is shut down', async () => {
    const chat = await bootChat()
    const socket = lastSocket()
    socket.open()

    chat.shutdownGlobalChat()
    socket.drop() // the browser fires the close event afterwards
    await vi.advanceTimersByTimeAsync(120_000)

    expect(unreadCalls()).toBe(1)
    expect(sockets()).toHaveLength(1)
  })

  it('ignores the late close of a socket replaced by a restarted chat', async () => {
    const chat = await bootChat()
    const first = lastSocket()
    first.open()
    chat.shutdownGlobalChat()
    await chat.initGlobalChat({ user_id: VIEWER })
    expect(sockets()).toHaveLength(2)

    first.drop() // its close event lands after the new socket exists
    await vi.advanceTimersByTimeAsync(120_000)

    expect(sockets()).toHaveLength(2)
  })

  it.each([
    ['answers', pending => pending.resolve({ unread: 4 })],
    ['fails', pending => pending.reject(new TypeError('Failed to fetch'))],
  ])('drops a session check that %s after the chat was shut down', async (_label, settle) => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const chat = await bootChat()
    lastSocket().open()
    const pending = deferred()
    replies.unread = () => pending.promise

    lastSocket().drop()
    await vi.advanceTimersByTimeAsync(3000) // the resume now waits on the check
    chat.shutdownGlobalChat()
    settle(pending)
    await vi.advanceTimersByTimeAsync(120_000)

    expect(unreadCalls()).toBe(2)
    expect(sockets()).toHaveLength(1)
    expect(chat.unreadCount.value).toBe(0)
  })

  it('leaves everything untouched when the chat is shut down during the catch-up', async () => {
    const chat = await bootChat()
    lastSocket().open()
    chat.setPanelOpen(true)
    const history = deferred()
    replies.history = () => history.promise

    lastSocket().drop()
    await vi.advanceTimersByTimeAsync(3000)
    lastSocket().open()
    chat.shutdownGlobalChat()
    history.resolve(onePage(message(101)))
    await vi.advanceTimersByTimeAsync(120_000)

    expect(ids(chat)).toEqual([])
    expect(markReadCalls()).toBe(0)
    expect(sockets()).toHaveLength(2)
  })

  it('drops a catch-up unread count that answers after the chat was shut down', async () => {
    const chat = await bootChat()
    lastSocket().open()
    lastSocket().drop()
    await vi.advanceTimersByTimeAsync(3000)
    const pending = deferred()
    replies.unread = () => pending.promise

    lastSocket().open() // the catch-up now waits on the unread count
    chat.shutdownGlobalChat()
    pending.resolve({ unread: 4 })
    await vi.advanceTimersByTimeAsync(0)

    expect(chat.unreadCount.value).toBe(0)
  })
})
