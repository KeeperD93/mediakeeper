"""Sample datasets for webhook tests."""

SAMPLE_DATA = {
    "movie": {
        "titre":   "[Inception](https://www.themoviedb.org/movie/27205)",
        "annee":   "2010",
        "synopsis":"Dom Cobb est un voleur expérimenté dans l'art de l'extraction...",
        "genres":  "Science-fiction, Action, Aventure",
        "note":    "8.4",
        "duree":   "148",
        "tmdb":    "[Fiche TMDB](https://www.themoviedb.org/movie/27205)",
        "imgur":   "https://image.tmdb.org/t/p/w600_and_h900_face/aej3LRUga5rhgkmRP6XMFw3ejbl.jpg",
    },
    "series": {
        "titre":      "[Breaking Bad](https://www.themoviedb.org/tv/1396)",
        "annee":      "2008",
        "synopsis":   "Un professeur de chimie atteint d'un cancer se lance dans la fabrication de méthamphétamine...",
        "genres":     "Drame, Crime, Thriller",
        "note":       "9.5",
        "nb_saisons": "5",
        "tmdb":       "[Fiche TMDB](https://www.themoviedb.org/tv/1396)",
        "imgur":      "https://image.tmdb.org/t/p/w600_and_h900_face/4YLQj5XRrMJ7gp8eb0h6umd0iNx.jpg",
    },
    "season": {
        "titre_serie": "[Breaking Bad](https://www.themoviedb.org/tv/1396)",
        "num_saison":  "1",
        "saison":      "Saison 1",
        "nb_episodes": "7",
        "annee":       "2008",
        "synopsis":    "La première saison de Breaking Bad, diffusée du 20 janvier au 9 mars 2008.",
        "tmdb":        "[Fiche TMDB](https://www.themoviedb.org/tv/1396/season/1)",
        "imgur":       "https://image.tmdb.org/t/p/w600_and_h900_face/4YLQj5XRrMJ7gp8eb0h6umd0iNx.jpg",
    },
    "episode": {
        "titre_serie":   "[Breaking Bad](https://www.themoviedb.org/tv/1396)",
        "titre_episode": "Ozymandias",
        "saison":        "Saison 5",
        "episode":       "Épisode 14",
        "code":          "S05E14",
        "annee":         "2013",
        "synopsis":      "Walt prend la fuite. Jesse est pris en otage. Marie convainc Skyler de tout raconter à Walter Jr.",
        "tmdb":          "[Fiche TMDB](https://www.themoviedb.org/tv/1396/season/5/episode/14)",
        "imgur":         "https://image.tmdb.org/t/p/w600_and_h900_face/4YLQj5XRrMJ7gp8eb0h6umd0iNx.jpg",
    },
    "grouped": {
        "titre_serie":   "[Breaking Bad](https://www.themoviedb.org/tv/1396)",
        "series_title":  "[Breaking Bad](https://www.themoviedb.org/tv/1396)",
        "saison":        "Saison 1",
        "season":        "Season 1",
        "nb_episodes":   "7",
        "episodes":      "7",
        "annee":         "2008",
        "tmdb":          "[Fiche TMDB](https://www.themoviedb.org/tv/1396/season/1)",
        "imgur":         "https://image.tmdb.org/t/p/w600_and_h900_face/4YLQj5XRrMJ7gp8eb0h6umd0iNx.jpg",
    },
}

SAMPLE_SYSTEM = {
    "server_offline":    {"nom_serveur": "Emby",    "heure": "03:42"},
    "duplicate_found":   {"titre_media": "Inception (2010)",  "bibliotheque": "Films", "fichier_1": "/films/Inception.mkv", "fichier_2": "/films/Inception.2010.mkv", "taille_1": "12.4 GB", "taille_2": "8.2 GB"},
    "request_new":       {"utilisateur": "alice",             "titre_demande": "Dune Part 2", "type_media": "Film", "annee": "2024", "date": "28 mars 2026"},
    "request_approved":  {"utilisateur": "alice",             "titre_demande": "Dune Part 2", "approuve_par": "admin"},
    "request_available": {"utilisateur": "alice",             "titre_demande": "Dune Part 2", "tmdb": "[Fiche TMDB](https://www.themoviedb.org/movie/693134)"},
    "request_partial":   {"utilisateur": "alice",             "titre_demande": "Breaking Bad", "dispo": "3", "total": "5"},
    "request_rejected":  {"utilisateur": "alice",             "titre_demande": "Film Introuvable", "raison": "Titre non trouvé sur TMDB"},
    "issue_new":         {"utilisateur": "bob",               "titre_media": "Inception", "type_probleme": "Sous-titres manquants", "description": "Pas de sous-titres français disponibles"},
    "issue_comment":     {"utilisateur": "admin",             "titre_media": "Inception", "commentaire": "Je regarde ça dès que possible."},
    "issue_resolved":    {"titre_media": "Inception",         "resolu_par": "admin"},
    "emby_alert":        {"type_alerte": "Transcoding",       "message": "Limite de transcodings simultanés atteinte", "severite": "Warning", "heure": "20:15"},
}

# English preview variants. Keys stay FR (``_render._add_aliases`` maps them to
# the EN template variables); only the human-readable values are translated.
SAMPLE_DATA_EN = {
    "movie": {
        "titre":   "[Inception](https://www.themoviedb.org/movie/27205)",
        "annee":   "2010",
        "synopsis":"Dom Cobb is a skilled thief, the absolute best in the dangerous art of extraction...",
        "genres":  "Science Fiction, Action, Adventure",
        "note":    "8.4",
        "duree":   "148",
        "tmdb":    "[TMDB page](https://www.themoviedb.org/movie/27205)",
        "imgur":   "https://image.tmdb.org/t/p/w600_and_h900_face/aej3LRUga5rhgkmRP6XMFw3ejbl.jpg",
    },
    "series": {
        "titre":      "[Breaking Bad](https://www.themoviedb.org/tv/1396)",
        "annee":      "2008",
        "synopsis":   "A high-school chemistry teacher diagnosed with cancer starts making methamphetamine...",
        "genres":     "Drama, Crime, Thriller",
        "note":       "9.5",
        "nb_saisons": "5",
        "tmdb":       "[TMDB page](https://www.themoviedb.org/tv/1396)",
        "imgur":      "https://image.tmdb.org/t/p/w600_and_h900_face/4YLQj5XRrMJ7gp8eb0h6umd0iNx.jpg",
    },
    "season": {
        "titre_serie": "[Breaking Bad](https://www.themoviedb.org/tv/1396)",
        "num_saison":  "1",
        "saison":      "Season 1",
        "nb_episodes": "7",
        "annee":       "2008",
        "synopsis":    "The first season of Breaking Bad, aired from January 20 to March 9, 2008.",
        "tmdb":        "[TMDB page](https://www.themoviedb.org/tv/1396/season/1)",
        "imgur":       "https://image.tmdb.org/t/p/w600_and_h900_face/4YLQj5XRrMJ7gp8eb0h6umd0iNx.jpg",
    },
    "episode": {
        "titre_serie":   "[Breaking Bad](https://www.themoviedb.org/tv/1396)",
        "titre_episode": "Ozymandias",
        "saison":        "Season 5",
        "episode":       "Episode 14",
        "code":          "S05E14",
        "annee":         "2013",
        "synopsis":      "Walt goes on the run. Jesse is held captive. Marie convinces Skyler to tell Walter Jr. the truth.",
        "tmdb":          "[TMDB page](https://www.themoviedb.org/tv/1396/season/5/episode/14)",
        "imgur":         "https://image.tmdb.org/t/p/w600_and_h900_face/4YLQj5XRrMJ7gp8eb0h6umd0iNx.jpg",
    },
    "grouped": {
        "titre_serie":   "[Breaking Bad](https://www.themoviedb.org/tv/1396)",
        "series_title":  "[Breaking Bad](https://www.themoviedb.org/tv/1396)",
        "saison":        "Season 1",
        "season":        "Season 1",
        "nb_episodes":   "7",
        "episodes":      "7",
        "annee":         "2008",
        "tmdb":          "[TMDB page](https://www.themoviedb.org/tv/1396/season/1)",
        "imgur":         "https://image.tmdb.org/t/p/w600_and_h900_face/4YLQj5XRrMJ7gp8eb0h6umd0iNx.jpg",
    },
}

SAMPLE_SYSTEM_EN = {
    "server_offline":    {"nom_serveur": "Emby",    "heure": "03:42"},
    "duplicate_found":   {"titre_media": "Inception (2010)",  "bibliotheque": "Movies", "fichier_1": "/movies/Inception.mkv", "fichier_2": "/movies/Inception.2010.mkv", "taille_1": "12.4 GB", "taille_2": "8.2 GB"},
    "request_new":       {"utilisateur": "alice",             "titre_demande": "Dune Part 2", "type_media": "Movie", "annee": "2024", "date": "March 28, 2026"},
    "request_approved":  {"utilisateur": "alice",             "titre_demande": "Dune Part 2", "approuve_par": "admin"},
    "request_available": {"utilisateur": "alice",             "titre_demande": "Dune Part 2", "tmdb": "[TMDB page](https://www.themoviedb.org/movie/693134)"},
    "request_partial":   {"utilisateur": "alice",             "titre_demande": "Breaking Bad", "dispo": "3", "total": "5"},
    "request_rejected":  {"utilisateur": "alice",             "titre_demande": "Unknown Movie", "raison": "Title not found on TMDB"},
    "issue_new":         {"utilisateur": "bob",               "titre_media": "Inception", "type_probleme": "Missing subtitles", "description": "No English subtitles available"},
    "issue_comment":     {"utilisateur": "admin",             "titre_media": "Inception", "commentaire": "I'll look into it as soon as possible."},
    "issue_resolved":    {"titre_media": "Inception",         "resolu_par": "admin"},
    "emby_alert":        {"type_alerte": "Transcoding",       "message": "Simultaneous transcode limit reached", "severite": "Warning", "heure": "20:15"},
}


def sample_data_for(lang: str) -> dict:
    """Sample media payloads in the webhook's language (FR is the default)."""
    return SAMPLE_DATA_EN if lang == "en" else SAMPLE_DATA


def sample_system_for(lang: str) -> dict:
    """Sample system payloads in the webhook's language (FR is the default)."""
    return SAMPLE_SYSTEM_EN if lang == "en" else SAMPLE_SYSTEM
