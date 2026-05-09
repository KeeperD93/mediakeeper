import { computed } from 'vue'

export function buildTplGroups(t) {
  return computed(() => {
    const groups = [
      {
        id: 'media',
        label: t('notifications.tplGroups.media'),
        icon: '🎬',
        eventKey: 'added',
        color: '#22c55e',
        templates: [
          { key: 'added_movie', label: t('notifications.tplGroups.movie'), testId: 'movie' },
          { key: 'added_series', label: t('notifications.tplGroups.series'), testId: 'series' },
          { key: 'added_season', label: t('notifications.tplGroups.season'), testId: 'season' },
          { key: 'added_episode', label: t('notifications.tplGroups.episode'), testId: 'episode' },
        ],
      },
      {
        id: 'server',
        label: t('notifications.tplGroups.server'),
        icon: '🖥️',
        eventKey: 'offline',
        color: '#f87171',
        templates: [
          {
            key: 'server_offline',
            label: t('notifications.tplGroups.offline'),
            testId: 'server_offline',
          },
        ],
      },
      {
        id: 'duplicates',
        label: t('notifications.tplGroups.duplicates'),
        icon: '🔍',
        eventKey: 'duplicate',
        color: '#fbbf24',
        templates: [
          {
            key: 'duplicate_found',
            label: t('notifications.tplGroups.duplicateFound'),
            testId: 'duplicate_found',
          },
        ],
      },
      {
        id: 'requests',
        label: t('notifications.tplGroups.requests'),
        icon: '📥',
        eventKey: 'new_request',
        color: '#60a5fa',
        templates: [
          {
            key: 'request_new',
            label: t('notifications.tplGroups.requestNew'),
            testId: 'request_new',
          },
          {
            key: 'request_approved',
            label: t('notifications.tplGroups.requestApproved'),
            testId: 'request_approved',
          },
          {
            key: 'request_available',
            label: t('notifications.tplGroups.requestAvailable'),
            testId: 'request_available',
          },
          {
            key: 'request_partial',
            label: t('notifications.tplGroups.requestPartial'),
            testId: 'request_partial',
          },
          {
            key: 'request_rejected',
            label: t('notifications.tplGroups.requestRejected'),
            testId: 'request_rejected',
          },
        ],
      },
      {
        id: 'issues',
        label: t('notifications.tplGroups.issues'),
        icon: '🚨',
        eventKey: 'new_issue',
        color: '#f87171',
        templates: [
          { key: 'issue_new', label: t('notifications.tplGroups.issueNew'), testId: 'issue_new' },
          {
            key: 'issue_comment',
            label: t('notifications.tplGroups.issueComment'),
            testId: 'issue_comment',
          },
          {
            key: 'issue_resolved',
            label: t('notifications.tplGroups.issueResolved'),
            testId: 'issue_resolved',
          },
        ],
      },
      {
        id: 'emby',
        label: t('notifications.tplGroups.embyAlerts'),
        icon: '⚠️',
        eventKey: 'emby_alerts',
        color: '#fbbf24',
        templates: [
          { key: 'emby_alert', label: t('notifications.tplGroups.alert'), testId: 'emby_alert' },
        ],
      },
    ]
    groups.splice(1, 0, {
      id: 'grouped',
      label: t('notifications.tplGroups.grouped'),
      icon: '📦',
      eventKey: 'added',
      color: '#06b6d4',
      templates: [
        {
          key: 'added_grouped',
          label: t('notifications.tplGroups.groupedLabel'),
          testId: 'grouped',
        },
      ],
    })
    return groups
  })
}

export function buildTestTypes(tplGroups) {
  return computed(() =>
    tplGroups.value.flatMap(g => g.templates.map(tp => ({ id: tp.testId, label: tp.label }))),
  )
}
