// Feedback (bug/suggestion) form vocabulary. Kept in sync with the backend
// FeedbackReport schema (backend/api/feedback.py) and the tracker taxonomy.

export const FEEDBACK_TYPES = Object.freeze(['bug', 'suggestion'] as const)
export type FeedbackType = (typeof FEEDBACK_TYPES)[number]

// Platform checkboxes; both ticked resolves to the tracker's "both".
export const FEEDBACK_PLATFORMS = Object.freeze(['desktop', 'mobile'] as const)
export type FeedbackPlatform = (typeof FEEDBACK_PLATFORMS)[number]

// Ordered severity → nature. Labels resolve under feedback.tags.<key>.
export const FEEDBACK_TAGS = Object.freeze([
  'urgent',
  'crash',
  'data_loss',
  'security',
  'visual',
  'performance',
  'accessibility',
  'translation',
  'compatibility',
] as const)
export type FeedbackTag = (typeof FEEDBACK_TAGS)[number]

// Discord caps a webhook message at 2000 chars; the live counter keeps the
// whole block (delimiters + labels + meta + fields) under this, mirroring the
// backend guard in services/feedback.py.
export const FEEDBACK_MAX_CHARS = 2000
