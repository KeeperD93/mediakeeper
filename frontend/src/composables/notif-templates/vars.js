export const TPL_VARS_FALLBACK = {
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

export function getActiveTplVars(tplMeta, key) {
  if (!key) return []
  if (tplMeta?.vars && tplMeta.vars[key]) return tplMeta.vars[key]
  return (TPL_VARS_FALLBACK[key] || []).map(([k, desc]) => ({ key: k, desc }))
}
