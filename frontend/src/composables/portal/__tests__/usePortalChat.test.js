/**
 * Portal chat — live messages and history.
 *
 * A live message lands in the list of the room the panel shows. History loads
 * never overlap: the newest one wins, a room that refuses its history leaves the
 * panel where it was, and a deletion survives a reload. WebSocket and the API are
 * stubbed; timers are fake.
 */
import { describe, it, expect, vi } from 'vitest'
import {
  apiGet,
  apiPost,
  LOUNGE,
  PARTY,
  VIEWER,
  historyUrl,
  message,
  onePage,
  replies,
  useChatTestEnv,
  loadChat,
  bootChat,
  deferred,
  sockets,
  unreadCalls,
  lastSocket,
  ids,
} from './portalChatHarness'

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ apiGet, apiPost, apiDelete: vi.fn() }),
}))

describe('usePortalChat', () => {
  useChatTestEnv()

  describe('start and stop', () => {
    it('opens no socket when the chat shuts down while it starts', async () => {
      const chat = await loadChat()
      const pending = deferred()
      replies.rooms = () => pending.promise
      const starting = chat.initGlobalChat({ user_id: VIEWER })

      chat.shutdownGlobalChat() // the viewer leaves the portal meanwhile
      pending.resolve({ items: [{ id: LOUNGE }] })
      await starting
      await vi.advanceTimersByTimeAsync(60_000)

      expect(sockets()).toHaveLength(0)
      expect(chat.currentRoomId.value).toBeNull()
      expect(unreadCalls()).toBe(0)
      expect(chat.unreadCount.value).toBe(0)
    })

    it('keeps the badge clear and opens no socket when the chat shuts down during the count', async () => {
      const chat = await loadChat()
      const count = deferred()
      replies.unread = () => count.promise
      const starting = chat.initGlobalChat({ user_id: VIEWER })
      await vi.advanceTimersByTimeAsync(0) // the rooms answered; the count is pending

      chat.shutdownGlobalChat()
      count.resolve({ unread: 4 })
      await starting

      expect(chat.unreadCount.value).toBe(0)
      expect(sockets()).toHaveLength(0)
    })

    it('lets a session check from before a restart touch nothing', async () => {
      const chat = await bootChat()
      lastSocket().open()
      const check = deferred()
      replies.unread = () => check.promise
      lastSocket().drop()
      await vi.advanceTimersByTimeAsync(3000) // the resume waits on the check

      chat.shutdownGlobalChat()
      replies.unread = () => ({ unread: 0 })
      await chat.initGlobalChat({ user_id: VIEWER })
      const count = sockets().length
      check.resolve({ unread: 0 })
      await vi.advanceTimersByTimeAsync(60_000)

      expect(sockets()).toHaveLength(count)
    })
  })

  describe('live messages', () => {
    it("shows the viewer's own messages from another tab without counting them", async () => {
      const chat = await bootChat()
      lastSocket().open()

      lastSocket().receive(message(103, LOUNGE, VIEWER))
      lastSocket().receive(message(104))

      expect(ids(chat)).toEqual([103, 104])
      expect(chat.unreadCount.value).toBe(1)
    })

    it("never appends a lounge message to another room's history", async () => {
      const chat = await bootChat()
      lastSocket().open()
      chat.setPanelOpen(true)
      await chat.fetchAllMessages(PARTY)

      lastSocket().receive(message(105, LOUNGE))

      expect(ids(chat)).toEqual([201])
      expect(chat.unreadCount.value).toBe(1)
    })

    it('forgets the room the panel showed once the chat shuts down', async () => {
      const chat = await bootChat()
      await chat.fetchAllMessages(PARTY)
      chat.shutdownGlobalChat()
      await chat.initGlobalChat({ user_id: VIEWER })
      lastSocket().open()

      lastSocket().receive(message(107))

      expect(ids(chat)).toEqual([107])
    })

    it('ignores a message already listed', async () => {
      const chat = await bootChat()
      lastSocket().open()
      lastSocket().receive(message(106))
      lastSocket().receive(message(106))
      expect(ids(chat)).toEqual([106])
      expect(chat.unreadCount.value).toBe(1)
    })
  })

  describe('history', () => {
    it('lets the newest load win: an older one never writes', async () => {
      const chat = await bootChat()
      const slow = deferred()
      replies.history = () => slow.promise
      const first = chat.fetchAllMessages(LOUNGE)
      replies.history = roomId => onePage(message(101, roomId), message(102, roomId))
      expect(await chat.fetchAllMessages(LOUNGE)).toBe(true)

      slow.resolve(onePage(message(99))) // rows the newer load never returned
      expect(await first).toBe(false)
      expect(ids(chat)).toEqual([101, 102])
    })

    it('drains every page in order, then stops', async () => {
      const chat = await bootChat()
      replies.history = (roomId, url) =>
        url.includes('cursor=')
          ? onePage(message(1), message(2))
          : { items: [message(4), message(3)], has_more: true, next_cursor: 3 }

      await chat.fetchAllMessages(LOUNGE)

      expect(apiGet).toHaveBeenCalledWith(`${historyUrl(LOUNGE)}&cursor=3`)
      expect(ids(chat)).toEqual([1, 2, 3, 4])
    })

    it('keeps the live messages that arrived while the pages loaded', async () => {
      const chat = await bootChat()
      lastSocket().open()
      const pending = deferred()
      replies.history = () => pending.promise
      const load = chat.fetchAllMessages(LOUNGE)

      lastSocket().receive(message(150)) // posted after the pages were read
      pending.resolve(onePage(message(130), message(140)))
      await load

      expect(ids(chat)).toEqual([130, 140, 150])
    })

    it("leaves the previous room's live messages out when the panel switches rooms", async () => {
      const chat = await bootChat()
      lastSocket().open()
      await chat.fetchAllMessages(LOUNGE)
      lastSocket().receive(message(150))
      replies.history = roomId => onePage(message(120, roomId))

      await chat.fetchAllMessages(PARTY)

      expect(ids(chat)).toEqual([120])
    })

    it('drops a row deleted on the server when the panel reloads', async () => {
      const chat = await bootChat()
      lastSocket().open()
      await chat.fetchAllMessages(LOUNGE)
      lastSocket().receive(message(150)) // listed live, then deleted by its author

      await chat.fetchAllMessages(LOUNGE) // the server no longer returns it

      expect(ids(chat)).toEqual([101])
    })

    it('stays on the room it showed when another room refuses its history', async () => {
      const chat = await bootChat()
      lastSocket().open()
      await chat.fetchAllMessages(LOUNGE)
      replies.history = () => {
        throw new Error('forbidden')
      }
      await expect(chat.fetchAllMessages(PARTY)).rejects.toThrow('forbidden')

      lastSocket().receive(message(150))

      expect(ids(chat)).toEqual([101, 150])
    })

    it('keeps a deletion made while the history reloads', async () => {
      const chat = await bootChat()
      await chat.fetchAllMessages(LOUNGE)
      const pending = deferred()
      replies.history = () => pending.promise
      const reload = chat.fetchAllMessages(LOUNGE)

      chat.messages.value[0].deleted = true // what a confirmed delete does meanwhile
      pending.resolve(onePage(message(101)))
      await reload

      expect(chat.messages.value.map(m => [m.id, m.deleted])).toEqual([[101, true]])
    })

    it('stops paging once the chat is shut down', async () => {
      const chat = await bootChat()
      const pending = deferred()
      replies.history = () => pending.promise
      const load = chat.fetchAllMessages(LOUNGE)

      chat.shutdownGlobalChat()
      pending.resolve({ items: [message(160)], has_more: true, next_cursor: 160 })

      expect(await load).toBe(false)
      expect(apiGet).not.toHaveBeenCalledWith(`${historyUrl(LOUNGE)}&cursor=160`)
      expect(ids(chat)).toEqual([])
    })
  })
})
