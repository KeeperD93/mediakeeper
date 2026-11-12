"""Sample datasets for webhook tests."""

SAMPLE_DATA = {
    "movie": {
        "titre":   "[Sample Movie](https://www.themoviedb.org/movie/900001)",
        "annee":   "2020",
        "synopsis":"Une équipe de voleurs prépare un dernier casse dans une ville imaginaire...",
        "genres":  "Science-fiction, Action, Aventure",
        "note":    "8.4",
        "duree":   "126",
        "tmdb":    "[Fiche TMDB](https://www.themoviedb.org/movie/900001)",
        "imgur":   "https://image.tmdb.org/t/p/w600_and_h900_face/aej3LRUga5rhgkmRP6XMFw3ejbl.jpg",
    },
    "series": {
        "titre":      "[Sample Show](https://www.themoviedb.org/tv/900002)",
        "annee":      "2018",
        "synopsis":   "Un professeur de lycée découvre un secret enfoui sous sa petite ville...",
        "genres":     "Drame, Crime, Thriller",
        "note":       "9.5",
        "nb_saisons": "5",
        "tmdb":       "[Fiche TMDB](https://www.themoviedb.org/tv/900002)",
        "imgur":      "https://image.tmdb.org/t/p/w600_and_h900_face/4YLQj5XRrMJ7gp8eb0h6umd0iNx.jpg",
    },
    "season": {
        "titre_serie": "[Sample Show](https://www.themoviedb.org/tv/900002)",
        "num_saison":  "1",
        "saison":      "Saison 1",
        "nb_episodes": "7",
        "annee":       "2018",
        "synopsis":    "La première saison de Sample Show, diffusée du 8 janvier au 26 février 2018.",
        "tmdb":        "[Fiche TMDB](https://www.themoviedb.org/tv/900002/season/1)",
        "imgur":       "https://image.tmdb.org/t/p/w600_and_h900_face/4YLQj5XRrMJ7gp8eb0h6umd0iNx.jpg",
    },
    "episode": {
        "titre_serie":   "[Sample Show](https://www.themoviedb.org/tv/900002)",
        "titre_episode": "Sample Episode",
        "saison":        "Saison 5",
        "episode":       "Épisode 14",
        "code":          "S05E14",
        "annee":         "2022",
        "synopsis":      "Alice prend la fuite. Bob est pris en otage. Carol convainc Dave de tout raconter.",
        "tmdb":          "[Fiche TMDB](https://www.themoviedb.org/tv/900002/season/5/episode/14)",
        "imgur":         "https://image.tmdb.org/t/p/w600_and_h900_face/4YLQj5XRrMJ7gp8eb0h6umd0iNx.jpg",
    },
    "grouped": {
        "titre_serie":   "[Sample Show](https://www.themoviedb.org/tv/900002)",
        "series_title":  "[Sample Show](https://www.themoviedb.org/tv/900002)",
        "saison":        "Saison 1",
        "season":        "Season 1",
        "nb_episodes":   "7",
        "episodes":      "7",
        "annee":         "2018",
        "tmdb":          "[Fiche TMDB](https://www.themoviedb.org/tv/900002/season/1)",
        "imgur":         "https://image.tmdb.org/t/p/w600_and_h900_face/4YLQj5XRrMJ7gp8eb0h6umd0iNx.jpg",
    },
}

SAMPLE_SYSTEM = {
    "server_offline":    {"nom_serveur": "Emby",    "heure": "03:42"},
    "duplicate_found":   {"titre_media": "Sample Movie (2020)", "bibliotheque": "Films", "fichier_1": "/films/Sample.Movie.mkv", "fichier_2": "/films/Sample.Movie.2020.mkv", "taille_1": "12.4 GB", "taille_2": "8.2 GB"},
    "request_new":       {"utilisateur": "alice",             "titre_demande": "Sample Movie 2", "type_media": "Film", "annee": "2024", "date": "28 mars 2026"},
    "request_approved":  {"utilisateur": "alice",             "titre_demande": "Sample Movie 2", "approuve_par": "admin"},
    "request_available": {"utilisateur": "alice",             "titre_demande": "Sample Movie 2", "tmdb": "[Fiche TMDB](https://www.themoviedb.org/movie/900003)"},
    "request_partial":   {"utilisateur": "alice",             "titre_demande": "Sample Show", "dispo": "3", "total": "5"},
    "request_rejected":  {"utilisateur": "alice",             "titre_demande": "Film Introuvable", "raison": "Titre non trouvé sur TMDB"},
    "issue_new":         {"utilisateur": "bob",               "titre_media": "Sample Movie", "type_probleme": "Sous-titres manquants", "description": "Pas de sous-titres français disponibles"},
    "issue_comment":     {"utilisateur": "admin",             "titre_media": "Sample Movie", "commentaire": "Je regarde ça dès que possible."},
    "issue_resolved":    {"titre_media": "Sample Movie",      "resolu_par": "admin"},
    "emby_alert":        {"type_alerte": "Transcoding",       "message": "Limite de transcodings simultanés atteinte", "severite": "Warning", "heure": "20:15"},
}

# English preview variants. Keys stay FR (``_render._add_aliases`` maps them to
# the EN template variables); only the human-readable values are translated.
SAMPLE_DATA_EN = {
    "movie": {
        "titre":   "[Sample Movie](https://www.themoviedb.org/movie/900001)",
        "annee":   "2020",
        "synopsis":"A crew of thieves plans one last heist in an imaginary city...",
        "genres":  "Science Fiction, Action, Adventure",
        "note":    "8.4",
        "duree":   "126",
        "tmdb":    "[TMDB page](https://www.themoviedb.org/movie/900001)",
        "imgur":   "https://image.tmdb.org/t/p/w600_and_h900_face/aej3LRUga5rhgkmRP6XMFw3ejbl.jpg",
    },
    "series": {
        "titre":      "[Sample Show](https://www.themoviedb.org/tv/900002)",
        "annee":      "2018",
        "synopsis":   "A high-school teacher uncovers a secret buried under his small town...",
        "genres":     "Drama, Crime, Thriller",
        "note":       "9.5",
        "nb_saisons": "5",
        "tmdb":       "[TMDB page](https://www.themoviedb.org/tv/900002)",
        "imgur":      "https://image.tmdb.org/t/p/w600_and_h900_face/4YLQj5XRrMJ7gp8eb0h6umd0iNx.jpg",
    },
    "season": {
        "titre_serie": "[Sample Show](https://www.themoviedb.org/tv/900002)",
        "num_saison":  "1",
        "saison":      "Season 1",
        "nb_episodes": "7",
        "annee":       "2018",
        "synopsis":    "The first season of Sample Show, aired from January 8 to February 26, 2018.",
        "tmdb":        "[TMDB page](https://www.themoviedb.org/tv/900002/season/1)",
        "imgur":       "https://image.tmdb.org/t/p/w600_and_h900_face/4YLQj5XRrMJ7gp8eb0h6umd0iNx.jpg",
    },
    "episode": {
        "titre_serie":   "[Sample Show](https://www.themoviedb.org/tv/900002)",
        "titre_episode": "Sample Episode",
        "saison":        "Season 5",
        "episode":       "Episode 14",
        "code":          "S05E14",
        "annee":         "2022",
        "synopsis":      "Alice goes on the run. Bob is held captive. Carol convinces Dave to tell the truth.",
        "tmdb":          "[TMDB page](https://www.themoviedb.org/tv/900002/season/5/episode/14)",
        "imgur":         "https://image.tmdb.org/t/p/w600_and_h900_face/4YLQj5XRrMJ7gp8eb0h6umd0iNx.jpg",
    },
    "grouped": {
        "titre_serie":   "[Sample Show](https://www.themoviedb.org/tv/900002)",
        "series_title":  "[Sample Show](https://www.themoviedb.org/tv/900002)",
        "saison":        "Season 1",
        "season":        "Season 1",
        "nb_episodes":   "7",
        "episodes":      "7",
        "annee":         "2018",
        "tmdb":          "[TMDB page](https://www.themoviedb.org/tv/900002/season/1)",
        "imgur":         "https://image.tmdb.org/t/p/w600_and_h900_face/4YLQj5XRrMJ7gp8eb0h6umd0iNx.jpg",
    },
}

SAMPLE_SYSTEM_EN = {
    "server_offline":    {"nom_serveur": "Emby",    "heure": "03:42"},
    "duplicate_found":   {"titre_media": "Sample Movie (2020)", "bibliotheque": "Movies", "fichier_1": "/movies/Sample.Movie.mkv", "fichier_2": "/movies/Sample.Movie.2020.mkv", "taille_1": "12.4 GB", "taille_2": "8.2 GB"},
    "request_new":       {"utilisateur": "alice",             "titre_demande": "Sample Movie 2", "type_media": "Movie", "annee": "2024", "date": "March 28, 2026"},
    "request_approved":  {"utilisateur": "alice",             "titre_demande": "Sample Movie 2", "approuve_par": "admin"},
    "request_available": {"utilisateur": "alice",             "titre_demande": "Sample Movie 2", "tmdb": "[TMDB page](https://www.themoviedb.org/movie/900003)"},
    "request_partial":   {"utilisateur": "alice",             "titre_demande": "Sample Show", "dispo": "3", "total": "5"},
    "request_rejected":  {"utilisateur": "alice",             "titre_demande": "Unknown Movie", "raison": "Title not found on TMDB"},
    "issue_new":         {"utilisateur": "bob",               "titre_media": "Sample Movie", "type_probleme": "Missing subtitles", "description": "No English subtitles available"},
    "issue_comment":     {"utilisateur": "admin",             "titre_media": "Sample Movie", "commentaire": "I'll look into it as soon as possible."},
    "issue_resolved":    {"titre_media": "Sample Movie",      "resolu_par": "admin"},
    "emby_alert":        {"type_alerte": "Transcoding",       "message": "Simultaneous transcode limit reached", "severite": "Warning", "heure": "20:15"},
}


def sample_data_for(lang: str) -> dict:
    """Sample media payloads in the webhook's language (FR is the default)."""
    return SAMPLE_DATA_EN if lang == "en" else SAMPLE_DATA


def sample_system_for(lang: str) -> dict:
    """Sample system payloads in the webhook's language (FR is the default)."""
    return SAMPLE_SYSTEM_EN if lang == "en" else SAMPLE_SYSTEM
