"""Static definition of available tools (Emby, TMDB, OpenSubtitles, ...).

- source_media: only one active at a time (Emby, Plex, Jellyfin)
- tool         : independent complementary tools
"""
from constants.tools import TOOL_EMBY, TOOL_OPENSUBTITLES, TOOL_TMDB

TOOLS_DEFINITION = {
    TOOL_EMBY: {
        "label":    "Emby",
        "type":     "source_media",
        "icon":     "emby.svg",
        "fields": [
            {"key": "url",        "label": "Internal URL (HTTP)",     "placeholder": "http://192.168.1.x:8096"},
            {"key": "public_url", "label": "Public URL (HTTPS)",      "placeholder": "https://emby.mydomain.com (optional)", "help": "Used mainly by the Requests module to generate the 'Play' links that open Emby in the user's browser. Leave empty if you don't expose Emby over HTTPS."},
            {"key": "api_key",    "label": "API key",                 "placeholder": "Dashboard -> Advanced -> Security"},
        ],
    },
    TOOL_TMDB: {
        "label":    "TMDB",
        "type":     "api",
        "icon":     "tmdb.svg",
        "fields": [
            {"key": "api_key", "label": "API key (Bearer Token)", "placeholder": "https://www.themoviedb.org/settings/api"},
        ],
    },
    TOOL_OPENSUBTITLES: {
        "label":    "OpenSubtitles",
        "type":     "api",
        "icon":     "",
        "fields": [
            {"key": "api_key",  "label": "API key",           "placeholder": "opensubtitles.com -> API Consumers"},
            {"key": "username", "label": "Username",          "placeholder": "Optional — raises the quota"},
            {"key": "password", "label": "Password",          "placeholder": "Optional", "type": "password"},
        ],
    },
}
