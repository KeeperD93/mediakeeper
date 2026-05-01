/**
 * Cinema-party event lifecycle, visibility, and invitation response enums.
 * Mirrored from the `events` / `event_invitations` tables on the backend.
 */
export const EVENT_STATUS = Object.freeze({
  SCHEDULED: 'scheduled',
  ENDED: 'ended',
  CANCELLED: 'cancelled',
} as const)

export type EventStatus = (typeof EVENT_STATUS)[keyof typeof EVENT_STATUS]

export const EVENT_KIND = Object.freeze({
  PUBLIC: 'public',
  PRIVATE: 'private',
} as const)

export type EventKind = (typeof EVENT_KIND)[keyof typeof EVENT_KIND]

export const INVITATION_STATUS = Object.freeze({
  PENDING: 'pending',
  ACCEPTED: 'accepted',
  DECLINED: 'declined',
} as const)

export type InvitationStatus = (typeof INVITATION_STATUS)[keyof typeof INVITATION_STATUS]
