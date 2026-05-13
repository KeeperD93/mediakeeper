import { describe, it, expect } from 'vitest'
import { Bell, Film, Flag, MessageSquare, Target, TicketCheck } from 'lucide-vue-next'
import { iconComponentForNotification } from '@/utils/portal/notificationLabel'

describe('iconComponentForNotification', () => {
  it('returns Bell for an empty or unknown type', () => {
    expect(iconComponentForNotification(null)).toBe(Bell)
    expect(iconComponentForNotification(undefined)).toBe(Bell)
    expect(iconComponentForNotification('')).toBe(Bell)
    expect(iconComponentForNotification('unknown_topic')).toBe(Bell)
  })

  it('maps each prefixed family to its dedicated Lucide glyph', () => {
    expect(iconComponentForNotification('event_invitation')).toBe(Film)
    expect(iconComponentForNotification('event_room_open')).toBe(Film)
    expect(iconComponentForNotification('request_approved')).toBe(Target)
    expect(iconComponentForNotification('ticket_created')).toBe(TicketCheck)
    expect(iconComponentForNotification('chat_dm')).toBe(MessageSquare)
  })

  it('flags reported chat messages with the Flag glyph', () => {
    expect(iconComponentForNotification('chat_message_reported')).toBe(Flag)
  })
})
