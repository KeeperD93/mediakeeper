/**
 * Lucide icon map for the Help Center — articles + categories.
 * Kept separate from the achievement ICON_MAP so that adding a help
 * icon never bloats the trophy bundle (and vice versa).
 *
 * The admin UI offers a select restricted to these keys: anything
 * outside the whitelist falls back to BookOpen.
 */
import {
  Send, Tags, Gauge,
  Sparkles, Trophy, Medal, Wand2, AtSign, ImagePlus, Eye, Settings,
  LifeBuoy, Bell, Shuffle, CalendarDays,
  BookOpen, MessageSquare, Inbox, User, ListChecks, AlertTriangle, MoreHorizontal,
  HelpCircle,
} from 'lucide-vue-next'

export const HELP_ICON_MAP = {
  Send, Tags, Gauge,
  Sparkles, Trophy, Medal, Wand2, AtSign, ImagePlus, Eye, Settings,
  LifeBuoy, Bell, Shuffle, CalendarDays,
  BookOpen, MessageSquare,
  HelpCircle,
}

export const HELP_CATEGORY_ICON = {
  general: Inbox,
  requests: Send,
  profile: User,
  lists: ListChecks,
  issues: AlertTriangle,
  misc: MoreHorizontal,
}

export function helpIconFor(name) {
  return HELP_ICON_MAP[name] || BookOpen
}

export const HELP_ICON_NAMES = Object.keys(HELP_ICON_MAP)
