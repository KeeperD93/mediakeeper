/**
 * In-app notification type strings. Must match the `type` column emitted
 * by the backend portal notification service (`backend/services/portal/
 * notifications.py` and its callers). Used by the notification bell to
 * pick icons / navigation targets.
 */
export const NOTIF_TYPE = Object.freeze({
  REQUEST_APPROVED: 'request_approved',
  REQUEST_AVAILABLE: 'request_available',
  REQUEST_REJECTED: 'request_rejected',
  PARTIALLY_AVAILABLE: 'partially_available',
  NEW_REQUEST: 'new_request',
  TICKET_CREATED: 'ticket_created',
  TICKET_REPLIED: 'ticket_replied',
  TICKET_RESOLVED: 'ticket_resolved',
  EVENT_ROOM_OPEN: 'event_room_open',
  CHAT_MESSAGE_REPORTED: 'chat_message_reported',
  ADMIN_MESSAGE: 'admin_message',
  LIST_COPIED: 'list_copied',
  LIST_CONTRIBUTOR_ADDED: 'list_contributor_added',
} as const)

export type NotifType = (typeof NOTIF_TYPE)[keyof typeof NOTIF_TYPE]
