import { computed, markRaw } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  BarChart3,
  Bell,
  Captions,
  ClipboardCheck,
  Copy,
  Film,
  Home,
  ShieldCheck,
  Users,
} from 'lucide-vue-next'

const ICONS = {
  dashboard: markRaw(Home),
  stats: markRaw(BarChart3),
  watchlist: markRaw(ClipboardCheck),
  media: markRaw(Film),
  duplicates: markRaw(Copy),
  health: markRaw(ShieldCheck),
  subtitles: markRaw(Captions),
  notifications: markRaw(Bell),
  portal: markRaw(Users),
}

/** The modules the setup wizard presents: welcome cards and tour. */
export function useOnboardingModules() {
  const { t } = useI18n()

  const features = computed(() => [
    {
      id: 'dash',
      bg: 'rgba(99,102,241,.12)',
      name: t('sidebar.dashboard'),
      desc: t('onboarding.modDashboard'),
      icon: ICONS.dashboard,
    },
    {
      id: 'stats',
      bg: 'rgba(16,185,129,.1)',
      name: t('sidebar.statistics'),
      desc: t('onboarding.modStats'),
      icon: ICONS.stats,
    },
    {
      id: 'wl',
      bg: 'rgba(139,92,246,.12)',
      name: t('sidebar.watchlist'),
      desc: t('onboarding.modWatchlist'),
      icon: ICONS.watchlist,
    },
    {
      id: 'media',
      bg: 'rgba(6,182,212,.1)',
      name: t('sidebar.mediaManager'),
      desc: t('onboarding.modMedia'),
      icon: ICONS.media,
    },
    {
      id: 'doub',
      bg: 'rgba(245,158,11,.1)',
      name: t('sidebar.duplicates'),
      desc: t('onboarding.modDoublons'),
      icon: ICONS.duplicates,
    },
    {
      id: 'health',
      bg: 'rgba(234,179,8,.1)',
      name: t('sidebar.healthCheck'),
      desc: t('onboarding.modHealth'),
      icon: ICONS.health,
    },
    {
      id: 'subs',
      bg: 'rgba(168,85,247,.1)',
      name: t('sidebar.subtitles'),
      desc: t('onboarding.modSubtitles'),
      icon: ICONS.subtitles,
    },
    {
      id: 'notif',
      bg: 'rgba(244,63,94,.1)',
      name: t('sidebar.notifications'),
      desc: t('onboarding.modNotifs'),
      icon: ICONS.notifications,
    },
    {
      id: 'portal',
      bg: 'rgba(59,130,246,.12)',
      name: t('sidebar.requests'),
      desc: t('onboarding.modPortal'),
      icon: ICONS.portal,
    },
  ])

  const modules = computed(() => [
    {
      id: 'dashboard',
      name: t('sidebar.dashboard'),
      bg: 'rgba(99,102,241,.12)',
      desc: t('onboarding.modDashboard'),
      icon: ICONS.dashboard,
      features: [
        t('onboarding.featSessions'),
        t('onboarding.featStats'),
        t('onboarding.featAlerts'),
        t('onboarding.featWidgets'),
      ],
    },
    {
      id: 'stats',
      name: t('sidebar.statistics'),
      bg: 'rgba(16,185,129,.1)',
      desc: t('onboarding.modStats'),
      icon: ICONS.stats,
      features: [
        t('onboarding.featHistory'),
        t('onboarding.featTopUsers'),
        t('onboarding.featLibraries'),
        t('onboarding.featHeatmap'),
      ],
    },
    {
      id: 'watchlist',
      name: t('sidebar.watchlist'),
      bg: 'rgba(139,92,246,.12)',
      desc: t('onboarding.modWatchlist'),
      icon: ICONS.watchlist,
      features: [
        t('onboarding.featMissing'),
        t('onboarding.featCalendar'),
        t('onboarding.featTimeline'),
        t('onboarding.featTracking'),
      ],
    },
    {
      id: 'media',
      name: t('sidebar.mediaManager'),
      bg: 'rgba(6,182,212,.1)',
      desc: t('onboarding.modMedia'),
      icon: ICONS.media,
      features: [
        t('onboarding.featTmdbRename'),
        t('onboarding.featBatchRename'),
        t('onboarding.featMove'),
        t('onboarding.featFolders'),
      ],
    },
    {
      id: 'duplicates',
      name: t('sidebar.duplicates'),
      bg: 'rgba(245,158,11,.1)',
      desc: t('onboarding.modDoublons'),
      icon: ICONS.duplicates,
      features: [
        t('onboarding.featDetect'),
        t('onboarding.featCompare'),
        t('onboarding.featAutoClean'),
        t('onboarding.featIgnore'),
      ],
    },
    {
      id: 'health',
      name: t('sidebar.healthCheck'),
      bg: 'rgba(234,179,8,.1)',
      desc: t('onboarding.modHealth'),
      icon: ICONS.health,
      features: [
        t('onboarding.featHealthCodecs'),
        t('onboarding.featHealthResolution'),
        t('onboarding.featHealthSubtitles'),
        t('onboarding.featHealthRules'),
      ],
    },
    {
      id: 'subtitles',
      name: t('sidebar.subtitles'),
      bg: 'rgba(168,85,247,.1)',
      desc: t('onboarding.modSubtitles'),
      icon: ICONS.subtitles,
      features: [
        t('onboarding.featSubSearch'),
        t('onboarding.featSubProfiles'),
        t('onboarding.featSubAuto'),
        t('onboarding.featSubAudit'),
      ],
    },
    {
      id: 'notifs',
      name: t('sidebar.notifications'),
      bg: 'rgba(244,63,94,.1)',
      desc: t('onboarding.modNotifs'),
      icon: ICONS.notifications,
      features: [
        t('onboarding.featDiscord'),
        t('onboarding.featDnd'),
        t('onboarding.featTemplates'),
        t('onboarding.featFilters'),
      ],
    },
    {
      id: 'portal',
      name: t('sidebar.requests'),
      bg: 'rgba(59,130,246,.12)',
      desc: t('onboarding.modPortal'),
      icon: ICONS.portal,
      features: [
        t('onboarding.featPortalRequests'),
        t('onboarding.featPortalTickets'),
        t('onboarding.featPortalProfile'),
        t('onboarding.featPortalAchievements'),
      ],
    },
  ])

  return { features, modules }
}
