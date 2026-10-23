/**
 * Portal chat — read state.
 *
 * The open panel tells the server the newest message it displayed, once a burst
 * settles or when it closes, so the read pointer never covers a message the viewer
 * was not shown. While the panel is closed, the badge follows the server's count.
 * WebSocket and the API are stubbed; timers are fake.
 */
import { describe, it, expect, vi } from 'vitest'
import {
  apiGet,
  apiPost,
  LOUNGE,
  PARTY,
  VIEWER,
  READ_SYNC_MS,
  message,
  onePage,
  replies,
  useChatTestEnv,
  bootChat,
  deferred,
  lastSocket,
  markReadBodies,
  markReadCalls,
} from './portalChatHarness'

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiGet, apiPost, apiDelete: vi.fn() }),
}))

describe('usePortalChat — read state', () => {
  useChatTestEnv()

  it('reports the newest message shown when the panel closes', async () => {
    const chat = await bootChat()
    lastSocket().open()
    chat.setPanelOpen(true)
    await chat.fetchAllMessages(LOUNGE)

    lastSocket().receive(message(102))
    expect(chat.unreadCount.value).toBe(0)
    chat.setPanelOpen(false)
    await vi.advanceTimersByTimeAsync(0)

    expect(markReadBodies()).toEqual([{ up_to: 102 }])
  })

  it('reports a burst of live messages once it settles', async () => {
    const chat = await bootChat()
    lastSocket().open()
    chat.setPanelOpen(true)
    await chat.fetchAllMessages(LOUNGE)

    lastSocket().receive(message(102))
    await vi.advanceTimersByTimeAsync(800)
    lastSocket().receive(message(103)) // the burst goes on: the report waits again
    await vi.advanceTimersByTimeAsync(READ_SYNC_MS - 1)
    expect(markReadCalls()).toBe(0)
    await vi.advanceTimersByTimeAsync(1)

    expect(markReadBodies()).toEqual([{ up_to: 103 }])
  })

  it('re-sends a report that failed offline before the reconnect count', async () => {
    const chat = await bootChat()
    lastSocket().open()
    chat.setPanelOpen(true)
    await chat.fetchAllMessages(LOUNGE)
    lastSocket().receive(message(102))

    lastSocket().drop() // offline: the report sent on close fails
    apiPost.mockRejectedValueOnce(new TypeError('Failed to fetch'))
    chat.setPanelOpen(false)
    await vi.advanceTimersByTimeAsync(3000) // back online: session check, new socket
    lastSocket().open()
    await vi.advanceTimersByTimeAsync(0)

    expect(markReadBodies()).toEqual([{ up_to: 102 }, { up_to: 102 }])
  })

  it('leaves the read pointer alone when the panel showed nothing', async () => {
    const chat = await bootChat()
    chat.setPanelOpen(true)
    chat.setPanelOpen(false)
    await vi.advanceTimersByTimeAsync(5000)
    expect(markReadCalls()).toBe(0)
  })

  it('never reports a message posted while the socket was down', async () => {
    const chat = await bootChat()
    lastSocket().open()
    chat.setPanelOpen(true)
    await chat.fetchAllMessages(LOUNGE)
    lastSocket().receive(message(102))

    lastSocket().drop() // 103 is posted meanwhile and never shown
    chat.setPanelOpen(false)
    await vi.advanceTimersByTimeAsync(0)

    expect(markReadBodies()).toEqual([{ up_to: 102 }])
  })

  it('reports nothing more when the panel closes before the catch-up reload ends', async () => {
    const chat = await bootChat()
    lastSocket().open()
    chat.setPanelOpen(true)
    await chat.fetchAllMessages(LOUNGE)
    await vi.advanceTimersByTimeAsync(READ_SYNC_MS)
    const reload = deferred()
    replies.history = () => reload.promise
    replies.unread = () => ({ unread: 2 })

    lastSocket().drop()
    await vi.advanceTimersByTimeAsync(3000)
    lastSocket().open() // the catch-up reload starts
    chat.setPanelOpen(false)
    reload.resolve(onePage(message(101), message(102), message(103)))
    await vi.advanceTimersByTimeAsync(5000)

    expect(markReadBodies()).toEqual([{ up_to: 101 }])
    expect(chat.unreadCount.value).toBe(2)
  })

  it('holds back a live message while a reload is due, leaving the gap unread', async () => {
    const chat = await bootChat()
    lastSocket().open()
    chat.setPanelOpen(true)
    await chat.fetchAllMessages(LOUNGE)
    await vi.advanceTimersByTimeAsync(READ_SYNC_MS)
    const reload = deferred()
    replies.history = () => reload.promise
    replies.unread = () => ({ unread: 3 })

    lastSocket().drop() // 102 and 103 are posted meanwhile
    await vi.advanceTimersByTimeAsync(3000)
    lastSocket().open() // the catch-up reload starts
    lastSocket().receive(message(104))
    await vi.advanceTimersByTimeAsync(READ_SYNC_MS)
    chat.setPanelOpen(false) // before the reload ends
    reload.resolve(onePage(message(101), message(102), message(103), message(104)))
    await vi.advanceTimersByTimeAsync(0)

    expect(markReadBodies()).toEqual([{ up_to: 101 }])
    expect(chat.unreadCount.value).toBe(3)
  })

  it('holds back live messages when the catch-up reload fails', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const chat = await bootChat()
    lastSocket().open()
    chat.setPanelOpen(true)
    await chat.fetchAllMessages(LOUNGE)
    await vi.advanceTimersByTimeAsync(READ_SYNC_MS)
    replies.history = () => {
      throw new TypeError('Failed to fetch')
    }

    lastSocket().drop() // 102 is posted meanwhile
    await vi.advanceTimersByTimeAsync(3000)
    lastSocket().open() // the catch-up reload fails: the gap stays off screen
    await vi.advanceTimersByTimeAsync(0)
    lastSocket().receive(message(103))
    await vi.advanceTimersByTimeAsync(READ_SYNC_MS)
    chat.setPanelOpen(false)
    await vi.advanceTimersByTimeAsync(0)

    expect(markReadBodies()).toEqual([{ up_to: 101 }])
  })

  it('reports nothing while the panel holds no loaded history', async () => {
    const chat = await bootChat()
    lastSocket().open()
    chat.setPanelOpen(true) // opened before the rooms answered: no history loads
    lastSocket().receive(message(150))
    await vi.advanceTimersByTimeAsync(READ_SYNC_MS)
    chat.setPanelOpen(false)
    await vi.advanceTimersByTimeAsync(0)

    expect(markReadCalls()).toBe(0)
  })

  it('reports what the panel showed during an outage, so it never comes back unread', async () => {
    const chat = await bootChat()
    lastSocket().open()
    lastSocket().drop() // 102 and 103 are posted while the socket is down
    replies.history = roomId =>
      onePage(message(101, roomId), message(102, roomId), message(103, roomId))

    chat.setPanelOpen(true)
    await chat.fetchAllMessages(LOUNGE)
    chat.setPanelOpen(false)
    await vi.advanceTimersByTimeAsync(0)

    expect(markReadBodies()).toEqual([{ up_to: 103 }])
  })

  it('reports again after the chat restarts, as another account may have signed in', async () => {
    const chat = await bootChat()
    chat.setPanelOpen(true)
    await chat.fetchAllMessages(PARTY)
    chat.setPanelOpen(false)
    chat.shutdownGlobalChat()
    await chat.initGlobalChat({ user_id: VIEWER })

    chat.setPanelOpen(true)
    await chat.fetchAllMessages(LOUNGE)
    chat.setPanelOpen(false)
    await vi.advanceTimersByTimeAsync(0)

    expect(markReadBodies()).toEqual([{ up_to: 201 }, { up_to: 101 }])
  })

  it('keeps the badge clear when the panel opens during the catch-up count', async () => {
    const chat = await bootChat()
    lastSocket().open()
    lastSocket().drop()
    await vi.advanceTimersByTimeAsync(3000)
    const count = deferred()
    replies.unread = () => count.promise

    lastSocket().open() // the catch-up asks for the count
    chat.setPanelOpen(true)
    count.resolve({ unread: 2 })
    await vi.advanceTimersByTimeAsync(0)

    expect(chat.unreadCount.value).toBe(0)
  })
})
