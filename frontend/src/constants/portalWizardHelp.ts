/**
 * Data of the first-login wizard's help step: the three animated demos (real portal
 * screens, reduced) and the four help articles offered under them.
 */
import { Calendar, Crown, Send, Trophy } from 'lucide-vue-next'
import { TICKET_STATUS } from '@/constants/tickets'

export const DEMO = Object.freeze({ REQUEST: 'request', TICKET: 'ticket', LIST: 'list' } as const)
export type Demo = (typeof DEMO)[keyof typeof DEMO]
export const DEMO_ORDER: readonly Demo[] = Object.freeze([DEMO.REQUEST, DEMO.TICKET, DEMO.LIST])

// Views per demo and how long each one stays on screen (loops of 15 s and 9 s).
export const DEMO_TIMING = Object.freeze({
  [DEMO.REQUEST]: { views: 6, ms: 2500 },
  [DEMO.TICKET]: { views: 3, ms: 3000 },
  [DEMO.LIST]: { views: 3, ms: 3000 },
})

// State of the search field drawn in the reduced top bar.
export const DEMO_SEARCH = Object.freeze({
  IDLE: 'idle',
  TYPING: 'typing',
  FILLED: 'filled',
} as const)
export type DemoSearch = (typeof DEMO_SEARCH)[keyof typeof DEMO_SEARCH]

// Tab lit in the reduced top bar.
export const DEMO_TAB = Object.freeze({
  HOME: 'home',
  PROFILE: 'profile',
  PROBLEMS: 'problems',
  NONE: '',
} as const)
export type DemoTab = (typeof DEMO_TAB)[keyof typeof DEMO_TAB]

// Button pressed by the cursor on the reduced title page.
export const DEMO_PRESS = Object.freeze({ REQUEST: 'request', LIST: 'list', NONE: '' } as const)
export type DemoPress = (typeof DEMO_PRESS)[keyof typeof DEMO_PRESS]

// Figures of the test data shown in the screens (not words, so not translated).
export const DEMO_DATA = Object.freeze({
  year: 2024,
  sequelYear: 2026,
  rating: 78,
  certification: 12,
  trendingRank: 1,
  heroSlides: 5,
  quotaUsed: 4,
  quotaMax: 10,
})

// Ticket cards of the reduced « Problèmes » page, newest first.
export const DEMO_OLD_TICKET = Object.freeze({
  id: 12,
  type: 'subtitles',
  status: TICKET_STATUS.RESOLVED,
  tint: 'teal',
  titleKey: 'portal.wizardHelp.screens.lighthouse',
})
export const DEMO_NEW_TICKET = Object.freeze({
  id: 13,
  type: 'audio',
  status: TICKET_STATUS.OPEN,
  tint: 'blue',
  titleKey: 'portal.wizardHelp.screens.movie',
})

// Same choices, same order as the real « Créer une liste » window.
export const DEMO_LIST_PRIVACY = Object.freeze(['private', 'public_readonly', 'collaborative'])
export const DEMO_LIST_CONTENT = Object.freeze(['mixed', 'movies', 'series', 'documentaries'])

// Help articles by their seeded slug (backend services/portal/help_content_*.py).
export const HELP_GUIDES = Object.freeze([
  { key: 'quotas', slug: 'les-quotas-de-demandes', icon: Send },
  { key: 'xp', slug: 'comment-gagner-de-l-xp', icon: Trophy },
  { key: 'leaderboard', slug: 'le-classement-mensuel', icon: Crown },
  { key: 'calendar', slug: 'le-calendrier-et-les-evenements', icon: Calendar },
])
