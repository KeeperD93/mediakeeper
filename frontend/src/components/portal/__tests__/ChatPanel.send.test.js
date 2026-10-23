/**
 * ChatPanel — sending: the message the server returns is added once, even when
 * its live broadcast reached the socket first.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ref } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'

const chat = vi.hoisted(() => ({}))
vi.mock('@/composables/portal/usePortalChat', () => ({ usePortalChat: () => chat }))
vi.mock('@/composables/portal/usePortalAuth', () => ({
  usePortalAuth: () => ({ profile: ref({ user_id: 7 }) }),
}))

import ChatPanel from '@/components/portal/ChatPanel.vue'

const sent = { id: 5, room_id: 1, user_id: 7, content: 'hello', created_at: null }
let wrapper

async function sendHello() {
  wrapper = mount(ChatPanel)
  await flushPromises()
  await wrapper.find('.pt-chat-field').setValue('hello')
  await wrapper.find('.pt-chat-send').trigger('click')
  await flushPromises()
  return wrapper
}

describe('ChatPanel send', () => {
  beforeEach(() => {
    Object.assign(chat, {
      rooms: ref([{ id: 1, name: 'Lounge' }]),
      messages: ref([]),
      currentRoomId: ref(1),
      fetchAllMessages: vi.fn(async () => true),
      sendMessage: vi.fn(async () => ({ message: sent })),
      deleteMessage: vi.fn(),
      reportMessage: vi.fn(),
      setPanelOpen: vi.fn(),
    })
  })

  afterEach(() => wrapper?.unmount())

  it('adds the sent message and clears the draft', async () => {
    await sendHello()
    expect(chat.messages.value.map(m => m.id)).toEqual([5])
    expect(wrapper.find('.pt-chat-field').element.value).toBe('')
  })

  it('does not add it twice when the live broadcast landed first', async () => {
    chat.sendMessage.mockImplementation(async () => {
      chat.messages.value.push({ ...sent })
      return { message: sent }
    })
    await sendHello()
    expect(chat.messages.value.map(m => m.id)).toEqual([5])
  })
})
