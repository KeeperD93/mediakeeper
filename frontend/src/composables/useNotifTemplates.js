import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'

export function useNotifTemplates() {
  const { t, locale } = useI18n()
  const { apiGet } = useApi()
  const tplMeta = ref({})

  const TPL_GROUPS = computed(() => {
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

  const testTypes = computed(() =>
    TPL_GROUPS.value.flatMap(g => g.templates.map(tp => ({ id: tp.testId, label: tp.label }))),
  )

  const TPL_VARS_FALLBACK = {
    added_movie: [
      ['titre', 'Titre'],
      ['annee', 'Année'],
      ['synopsis', 'Synopsis'],
      ['genres', 'Genres'],
      ['note', 'Note TMDB'],
      ['duree', 'Durée'],
      ['tmdb', 'Lien TMDB'],
      ['imgur', 'Affiche'],
    ],
    added_series: [
      ['titre', 'Titre'],
      ['annee', 'Année'],
      ['synopsis', 'Synopsis'],
      ['genres', 'Genres'],
      ['note', 'Note'],
      ['nb_saisons', 'Nb saisons'],
      ['tmdb', 'Lien TMDB'],
      ['imgur', 'Affiche'],
    ],
    added_season: [
      ['titre_serie', 'Série'],
      ['saison', 'Saison'],
      ['num_saison', 'N° saison'],
      ['nb_episodes', 'Nb épisodes'],
      ['annee', 'Année'],
      ['synopsis', 'Synopsis'],
      ['tmdb', 'Lien TMDB'],
      ['imgur', 'Affiche'],
    ],
    added_episode: [
      ['titre_serie', 'Série'],
      ['titre_episode', 'Épisode'],
      ['saison', 'Saison'],
      ['episode', 'Épisode'],
      ['code', 'Code S01E01'],
      ['annee', 'Année'],
      ['synopsis', 'Synopsis'],
      ['tmdb', 'Lien TMDB'],
      ['imgur', 'Affiche'],
    ],
    added_grouped: [
      ['titre_serie', 'Série'],
      ['saison', 'Saison'],
      ['nb_episodes', 'Nb épisodes'],
      ['annee', 'Année'],
      ['tmdb', 'Lien TMDB'],
      ['imgur', 'Affiche'],
    ],
    server_offline: [
      ['nom_serveur', 'Serveur'],
      ['heure', 'Heure'],
    ],
    duplicate_found: [
      ['titre_media', 'Titre'],
      ['bibliotheque', 'Bibliothèque'],
      ['fichier_1', 'Fichier 1'],
      ['fichier_2', 'Fichier 2'],
      ['taille_1', 'Taille 1'],
      ['taille_2', 'Taille 2'],
    ],
    request_new: [
      ['utilisateur', 'Utilisateur'],
      ['titre_demande', 'Titre'],
      ['type_media', 'Type'],
      ['annee', 'Année'],
      ['date', 'Date'],
    ],
    request_approved: [
      ['utilisateur', 'Utilisateur'],
      ['titre_demande', 'Titre'],
      ['approuve_par', 'Approuvé par'],
    ],
    request_available: [
      ['utilisateur', 'Utilisateur'],
      ['titre_demande', 'Titre'],
      ['tmdb', 'Lien TMDB'],
    ],
    request_partial: [
      ['utilisateur', 'Utilisateur'],
      ['titre_demande', 'Titre'],
      ['dispo', 'Dispo'],
      ['total', 'Total'],
    ],
    request_rejected: [
      ['utilisateur', 'Utilisateur'],
      ['titre_demande', 'Titre'],
      ['raison', 'Raison'],
    ],
    issue_new: [
      ['utilisateur', 'Utilisateur'],
      ['titre_media', 'Titre'],
      ['type_probleme', 'Type'],
      ['description', 'Description'],
    ],
    issue_comment: [
      ['utilisateur', 'Utilisateur'],
      ['titre_media', 'Titre'],
      ['commentaire', 'Commentaire'],
    ],
    issue_resolved: [
      ['titre_media', 'Titre'],
      ['resolu_par', 'Résolu par'],
    ],
    emby_alert: [
      ['type_alerte', 'Type'],
      ['message', 'Message'],
      ['severite', 'Sévérité'],
      ['heure', 'Heure'],
    ],
  }

  function getActiveTplVars(key) {
    if (!key) return []
    if (tplMeta.value.vars && tplMeta.value.vars[key]) return tplMeta.value.vars[key]
    return (TPL_VARS_FALLBACK[key] || []).map(([k, desc]) => ({ key: k, desc }))
  }

  const DEFAULT_TPLS = {
    fr: {
      added_movie:
        '🎬 Un nouvel ajout est disponible !\n\n**<titre> (<annee>)**\n\n<synopsis>\n\nVoir les détails\n<tmdb>\n\n<imgur>',
      added_series:
        '📺 Une nouvelle série est disponible !\n\n**<titre> (<annee>)**\n\n<synopsis>\n\nVoir les détails\n<tmdb>\n\n<imgur>',
      added_season:
        '📦 Une nouvelle saison est disponible !\n\n**<titre_serie> — <saison> (<annee>)**\n\n<synopsis>\n\nVoir les détails\n<tmdb>\n\n<imgur>',
      added_episode:
        '▶️ Un nouvel épisode est disponible !\n\n**<titre_serie> — <code> — <titre_episode>**\n\n<synopsis>\n\nVoir les détails\n<tmdb>\n\n<imgur>',
      added_grouped:
        '▶️ De nouveaux épisodes sont disponibles !\n\n**<titre_serie> — <saison>**\n\n<nb_episodes> nouveaux épisodes ajoutés.\n\nVoir les détails\n<tmdb>\n\n<imgur>',
      server_offline:
        "🔴 Serveur hors ligne\n\n**<nom_serveur>** n'est plus accessible.\nDétecté à **<heure>**.",
      duplicate_found:
        '🔍 Doublon détecté\n\n**<titre_media>**\nBibliothèque : <bibliotheque>\n\n`<fichier_1>` (<taille_1>)\n`<fichier_2>` (<taille_2>)',
      request_new:
        '📥 Nouvelle demande\n\n**<titre_demande>** (<type_media>, <annee>)\nDemandé par **<utilisateur>** le <date>',
      request_approved:
        '✅ Demande approuvée\n\n**<titre_demande>** — demande de <utilisateur> approuvée par <approuve_par>',
      request_available:
        '🎉 Disponible !\n\n**<titre_demande>** est maintenant disponible, <utilisateur> !\n<tmdb>',
      request_partial:
        '⏳ Partiellement disponible\n\n**<titre_demande>**\n<dispo>/<total> épisodes disponibles pour <utilisateur>',
      request_rejected:
        '❌ Demande rejetée\n\n**<titre_demande>** — demande de <utilisateur> rejetée.\nRaison : <raison>',
      issue_new:
        '🚨 Nouveau signalement\n\n**<titre_media>** — <type_probleme>\nSignalé par **<utilisateur>** : <description>',
      issue_comment:
        '💬 Commentaire sur un signalement\n\n**<titre_media>** — commentaire de **<utilisateur>** :\n<commentaire>',
      issue_resolved: '✅ Signalement résolu\n\n**<titre_media>** — résolu par **<resolu_par>**',
      emby_alert: '⚠️ Alerte Emby — <type_alerte>\n\n**<severite>** à <heure>\n<message>',
    },
    en: {
      added_movie:
        '🎬 A new movie is available!\n\n**<title> (<year>)**\n\n<overview>\n\nView details\n<tmdb>\n\n<imgur>',
      added_series:
        '📺 A new series is available!\n\n**<title> (<year>)**\n\n<overview>\n\nView details\n<tmdb>\n\n<imgur>',
      added_season:
        '📦 A new season is available!\n\n**<series_title> — <season> (<year>)**\n\n<overview>\n\nView details\n<tmdb>\n\n<imgur>',
      added_episode:
        '▶️ A new episode is available!\n\n**<series_title> — <code> — <episode_title>**\n\n<overview>\n\nView details\n<tmdb>\n\n<imgur>',
      added_grouped:
        '▶️ New episodes are available!\n\n**<series_title> — <season>**\n\n<episodes> new episodes added.\n\nView details\n<tmdb>\n\n<imgur>',
      server_offline:
        '🔴 Server offline\n\n**<server_name>** is no longer reachable.\nDetected at **<time>**.',
      duplicate_found:
        '🔍 Duplicate found\n\n**<media_title>**\nLibrary: <library>\n\n`<file_1>` (<size_1>)\n`<file_2>` (<size_2>)',
      request_new:
        '📥 New request\n\n**<request_title>** (<media_type>, <year>)\nRequested by **<user>** on <date>',
      request_approved:
        '✅ Request approved\n\n**<request_title>** — request by <user> approved by <approved_by>',
      request_available: '🎉 Available!\n\n**<request_title>** is now available, <user>!\n<tmdb>',
      request_partial:
        '⏳ Partially available\n\n**<request_title>**\n<available>/<total> episodes available for <user>',
      request_rejected:
        '❌ Request rejected\n\n**<request_title>** — request by <user> rejected.\nReason: <reason>',
      issue_new:
        '🚨 New issue\n\n**<media_title>** — <issue_type>\nReported by **<user>**: <description>',
      issue_comment: '💬 Issue comment\n\n**<media_title>** — comment by **<user>**:\n<comment>',
      issue_resolved: '✅ Issue resolved\n\n**<media_title>** — resolved by **<resolved_by>**',
      emby_alert: '⚠️ Emby Alert — <alert_type>\n\n**<severity>** at <time>\n<message>',
    },
  }

  function defaultTpl(key) {
    if (tplMeta.value.defaults && tplMeta.value.defaults[key]) return tplMeta.value.defaults[key]
    const lang = locale.value || 'fr'
    const tpls = DEFAULT_TPLS[lang] || DEFAULT_TPLS.fr
    return tpls[key] || ''
  }

  function defaultColor(key) {
    if (tplMeta.value.colors && tplMeta.value.colors[key]) {
      return '#' + tplMeta.value.colors[key].toString(16).padStart(6, '0')
    }
    return '#22c55e'
  }

  const PREVIEW_SAMPLES = {
    added_movie: {
      titre: 'Inception',
      title: 'Inception',
      annee: '2010',
      year: '2010',
      synopsis: "Un voleur qui s'infiltre dans les rêves des autres...",
      overview: "Un voleur qui s'infiltre dans les rêves des autres...",
      genres: 'Sci-fi, Action',
      note: '8.4',
      rating: '8.4',
      duree: '148',
      runtime: '148',
      tmdb: 'Fiche TMDB',
      tmdb_url: 'https://www.themoviedb.org/movie/27205',
      poster: 'https://image.tmdb.org/t/p/w300/9gk7adHYeDvHkCSEqAvQNLV5Uge.jpg',
      color: '#E8A735',
    },
    added_series: {
      titre: 'Breaking Bad',
      title: 'Breaking Bad',
      annee: '2008',
      year: '2008',
      synopsis: 'Un professeur de chimie devient dealer...',
      overview: 'Un professeur de chimie devient dealer...',
      genres: 'Drame, Crime',
      note: '9.5',
      rating: '9.5',
      nb_saisons: '5',
      seasons: '5',
      tmdb: 'Fiche TMDB',
      tmdb_url: 'https://www.themoviedb.org/tv/1396',
      poster: 'https://image.tmdb.org/t/p/w300/ggFHVNu6YYI5L9pCfOacjizRGt.jpg',
      color: '#5865F2',
    },
    added_season: {
      titre: 'Breaking Bad — Saison 1',
      title: 'Breaking Bad — Saison 1',
      titre_serie: 'Breaking Bad',
      series_title: 'Breaking Bad',
      num_saison: '1',
      season_number: '1',
      saison: 'Saison 1',
      season: 'Saison 1',
      nb_episodes: '7',
      episodes: '7',
      annee: '2008',
      year: '2008',
      synopsis: 'La première saison de Breaking Bad...',
      overview: 'La première saison de Breaking Bad...',
      tmdb: 'Fiche TMDB',
      tmdb_url: 'https://www.themoviedb.org/tv/1396/season/1',
      poster: 'https://image.tmdb.org/t/p/w300/ggFHVNu6YYI5L9pCfOacjizRGt.jpg',
      color: '#5865F2',
    },
    added_episode: {
      titre: 'Breaking Bad — S05E14',
      title: 'Breaking Bad — S05E14',
      titre_serie: 'Breaking Bad',
      series_title: 'Breaking Bad',
      titre_episode: 'Ozymandias',
      episode_title: 'Ozymandias',
      saison: 'Saison 5',
      season: 'Saison 5',
      episode: 'Épisode 14',
      code: 'S05E14',
      annee: '2013',
      year: '2013',
      synopsis: 'Walt prend la fuite...',
      overview: 'Walt prend la fuite...',
      tmdb: 'Fiche TMDB',
      tmdb_url: 'https://www.themoviedb.org/tv/1396/season/5/episode/14',
      poster: 'https://image.tmdb.org/t/p/w300/ggFHVNu6YYI5L9pCfOacjizRGt.jpg',
      color: '#5865F2',
    },
    server_offline: {
      nom_serveur: 'Emby',
      server_name: 'Emby',
      heure: '03:42',
      time: '03:42',
      color: '#f87171',
    },
    duplicate_found: {
      titre_media: 'Inception (2010)',
      media_title: 'Inception (2010)',
      bibliotheque: 'Films',
      library: 'Films',
      fichier_1: '/films/Inception.mkv',
      file_1: '/films/Inception.mkv',
      fichier_2: '/films/Inception.2010.mkv',
      file_2: '/films/Inception.2010.mkv',
      taille_1: '12.4 GB',
      size_1: '12.4 GB',
      taille_2: '8.2 GB',
      size_2: '8.2 GB',
      color: '#fbbf24',
    },
    request_new: {
      utilisateur: 'alice',
      user: 'alice',
      username: 'alice',
      titre_demande: 'Dune Part 2',
      request_title: 'Dune Part 2',
      type_media: 'Film',
      media_type: 'Film',
      annee: '2024',
      year: '2024',
      date: '28 mars 2026',
      tmdb: '',
      color: '#60a5fa',
    },
    request_approved: {
      utilisateur: 'alice',
      user: 'alice',
      username: 'alice',
      titre_demande: 'Dune Part 2',
      request_title: 'Dune Part 2',
      approuve_par: 'admin',
      approved_by: 'admin',
      tmdb: '',
      color: '#22c55e',
    },
    request_available: {
      utilisateur: 'alice',
      user: 'alice',
      username: 'alice',
      titre_demande: 'Dune Part 2',
      request_title: 'Dune Part 2',
      tmdb: 'Fiche TMDB',
      color: '#22c55e',
    },
    request_partial: {
      utilisateur: 'alice',
      user: 'alice',
      username: 'alice',
      titre_demande: 'Breaking Bad',
      request_title: 'Breaking Bad',
      dispo: '3',
      available: '3',
      total: '5',
      color: '#fbbf24',
    },
    request_rejected: {
      utilisateur: 'alice',
      user: 'alice',
      username: 'alice',
      titre_demande: 'Film X',
      request_title: 'Film X',
      raison: 'Titre introuvable',
      reason: 'Titre introuvable',
      color: '#f87171',
    },
    issue_new: {
      utilisateur: 'bob',
      user: 'bob',
      username: 'bob',
      titre_media: 'Inception',
      media_title: 'Inception',
      type_probleme: 'Sous-titres manquants',
      issue_type: 'Sous-titres manquants',
      description: 'Pas de sous-titres FR',
      color: '#f87171',
    },
    issue_comment: {
      utilisateur: 'admin',
      user: 'admin',
      username: 'admin',
      titre_media: 'Inception',
      media_title: 'Inception',
      commentaire: 'Je regarde ça dès que possible.',
      comment: 'Je regarde ça dès que possible.',
      color: '#fbbf24',
    },
    issue_resolved: {
      titre_media: 'Inception',
      media_title: 'Inception',
      resolu_par: 'admin',
      resolved_by: 'admin',
      color: '#22c55e',
    },
    emby_alert: {
      type_alerte: 'Transcoding',
      alert_type: 'Transcoding',
      message: 'Limite atteinte',
      severite: 'Warning',
      severity: 'Warning',
      heure: '20:15',
      time: '20:15',
      color: '#fbbf24',
    },
    added_grouped: {
      titre_serie: 'Breaking Bad',
      series_title: 'Breaking Bad',
      saison: 'Saison 1',
      season: 'Season 1',
      nb_episodes: '7',
      episodes: '7',
      annee: '2008',
      year: '2008',
      tmdb: 'Fiche TMDB',
      tmdb_url: 'https://www.themoviedb.org/tv/1396/season/1',
      poster: 'https://image.tmdb.org/t/p/w300/ggFHVNu6YYI5L9pCfOacjizRGt.jpg',
      color: '#06b6d4',
    },
  }

  function escapeHtml(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;')
  }

  function renderPreview(tpl, key, imageStyle) {
    const sample = PREVIEW_SAMPLES[key] || PREVIEW_SAMPLES.added_movie
    imageStyle = imageStyle || 'image'
    const tmdbToken = '%%MK_SAFE_TMDB_LINK%%'
    const unknownToken = '%%MK_SAFE_UNKNOWN_PLACEHOLDER%%'
    let text = tpl || defaultTpl(key)
    for (const [k, v] of Object.entries(sample)) {
      if (k === 'color' || k === 'poster' || k === 'tmdb_url') continue
      if (k === 'tmdb' && v && sample.tmdb_url) {
        text = text.replace(new RegExp('<tmdb>', 'g'), tmdbToken)
        continue
      }
      text = text.replace(new RegExp('<' + k + '>', 'g'), String(v || ''))
    }
    text = text.replace(/<imgur>/g, '')
    text = text.replace(/<fields>[^<]*<\/fields>/g, '')
    text = text.replace(/<[a-z_]+>/g, unknownToken)
    text = escapeHtml(text)
      .replaceAll(
        tmdbToken,
        `<a href="${sample.tmdb_url}" style="color:#00AFF4;text-decoration:none">${escapeHtml(sample.tmdb)}</a>`,
      )
      .replaceAll(unknownToken, '<em style="opacity:.35;font-style:normal">…</em>')

    const fmt = s =>
      s
        .replace(/\*\*(.*?)\*\*/g, '<strong style="color:#fff">$1</strong>')
        .replace(
          /`([^`]+)`/g,
          '<code style="background:rgba(255,255,255,.1);padding:1px 4px;border-radius:3px;font-size:.7rem">$1</code>',
        )
        .replace(/\n/g, '<br/>')

    const parts = text.trim().split(/\n\n(.*)$/s)
    const contentAbove = parts.length > 1 ? fmt(parts[0]) : ''
    const embedText = parts.length > 1 ? fmt(parts[1]) : fmt(text.trim())

    const poster = sample.poster || ''
    const hasImgur = (tpl || defaultTpl(key)).includes('<imgur>')
    let imgHtml = ''
    if (poster && hasImgur && imageStyle !== 'none') {
      if (imageStyle === 'thumbnail') {
        imgHtml = `<img src="${poster}" style="width:48px;height:68px;object-fit:cover;border-radius:3px;flex-shrink:0;float:right;margin-left:8px"/>`
      } else {
        imgHtml = `<img src="${poster}" style="max-width:140px;border-radius:3px;margin-top:8px;display:block"/>`
      }
    }

    let embed = '<div style="padding:4px 0;overflow:hidden">'
    if (imageStyle === 'thumbnail') embed += imgHtml
    embed += `<div style="font-size:.72rem;color:rgba(255,255,255,.55);line-height:1.5">${embedText}</div>`
    if (imageStyle === 'image') embed += imgHtml
    embed += '</div>'

    return { content: contentAbove || '', embed }
  }

  async function loadMeta() {
    try {
      const d = await apiGet(`/api/notifications/discord/meta?lang=${locale.value}`)
      if (d) tplMeta.value = d
    } catch {
      /* silent: meta fetch, defaults apply */
    }
  }
  watch(locale, () => {
    loadMeta()
  })

  return {
    tplMeta,
    TPL_GROUPS,
    testTypes,
    getActiveTplVars,
    defaultTpl,
    defaultColor,
    renderPreview,
    loadMeta,
  }
}
