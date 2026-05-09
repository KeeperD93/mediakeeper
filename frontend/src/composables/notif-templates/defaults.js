export const DEFAULT_TPLS = {
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

export function defaultTpl(tplMeta, locale, key) {
  if (tplMeta?.defaults && tplMeta.defaults[key]) return tplMeta.defaults[key]
  const lang = locale || 'fr'
  const tpls = DEFAULT_TPLS[lang] || DEFAULT_TPLS.fr
  return tpls[key] || ''
}

export function defaultColor(tplMeta, key) {
  if (tplMeta?.colors && tplMeta.colors[key]) {
    return '#' + tplMeta.colors[key].toString(16).padStart(6, '0')
  }
  return '#22c55e'
}
