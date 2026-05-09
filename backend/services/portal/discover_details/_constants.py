"""Module-wide constants, regex and lookup tables for portal discover details."""
import logging
import os
import re

logger = logging.getLogger("mediakeeper.portal.discover")
LANGUAGE = os.getenv("TMDB_LANGUAGE", "fr-FR")

_SEARCH_TOKEN_RE = re.compile(r"^([\"'([{]*)([^\W_]+)([\"')\]},.;:!?]*)$", re.UNICODE)
_REPEATED_LETTER_RE = re.compile(r"([^\W_])\1{2,}", re.IGNORECASE)
_REDUCIBLE_REPEATED_LETTER_RE = re.compile(r"([^\W_])\1+", re.IGNORECASE)
_REPEATED_NORMALIZED_LETTER_RE = re.compile(r"([^\W_])\1{2,}", re.IGNORECASE)
_SEARCH_SEPARATOR_RE = re.compile(r"[\s\-_.:/\\|,;!?()[\]{}\"'`´’‘“”]+", re.UNICODE)

_SEARCH_STOP_WORDS = {
    "a", "an", "and", "at", "au", "aux", "d", "das", "de", "del",
    "dem", "den", "der", "des", "di", "die", "du", "e", "ein", "eine",
    "el", "en", "et", "for", "from", "gli", "il", "in", "la", "las",
    "le", "les", "lo", "los", "of", "on", "ou", "the", "to", "un",
    "una", "und", "une", "with", "y",
    "aos", "as", "com", "con", "da", "das", "do", "dos", "na", "nas",
    "no", "nos", "o", "os", "para", "per", "por", "sur", "um", "uma",
    "uns", "umas",
}
_SEARCH_TRANSLATION = str.maketrans({
    "ß": "ss", "ẞ": "SS",
    "æ": "ae", "Æ": "AE",
    "œ": "oe", "Œ": "OE",
    "ø": "o", "Ø": "O",
    "ð": "d", "Ð": "D",
    "þ": "th", "Þ": "TH",
    "ł": "l", "Ł": "L",
    "ı": "i", "İ": "I",
})
_SEARCH_MAX_VARIANTS = 18
_SEARCH_MAX_UPSTREAM_REQUESTS = 24

_COMPOUND_SPLIT_OVERRIDES = {
    "xmen": "x men",
    "spiderman": "spider man",
    "spiderverse": "spider verse",
    "antman": "ant man",
}
_COMPOUND_SPLIT_WORDS = {
    "and", "de", "des", "du", "el", "la", "le", "les", "of", "the", "us",
    "america", "anneaux", "ant", "apes", "araignee", "bad", "ball",
    "bat", "better", "black", "blade", "bleu", "breaking", "call", "captain",
    "casa", "cite", "civil", "criminal", "criminel", "criminelle", "dark", "dead",
    "death", "doctor", "dragon", "enquete", "fast", "furious", "galaxy",
    "game", "ghost", "grand", "guardians", "harry", "home", "homme", "impossible",
    "investigation", "iron", "jurassic", "knight", "last", "lord", "man",
    "men", "mission", "note", "panther", "papel", "park", "piece",
    "peur", "planet", "potter", "rings", "runner", "saul", "seigneur", "soldier",
    "space", "spider", "star", "strange", "stranger", "things", "thrones",
    "trek", "walking", "war", "wars", "winter", "woman", "world",
}
_COMPOUND_CONNECTOR_WORDS = {
    word for word in _SEARCH_STOP_WORDS if len(word) <= 4
}
