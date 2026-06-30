"""Deterministic random-looking pseudonym generator for imported users.

Privacy boundary: an imported Emby account must never expose its raw
login on user-facing surfaces (leaderboard, chat, lists). Instead of the
bland ``Utilisateur 1234`` placeholder, every silent account gets a
stable, friendly ``Renard-Bleu-42`` / ``Blue-Fox-42`` pseudo derived from
its ``user_id`` — so the same account always renders identically across
surfaces, localized to the viewer.

French nouns/adjectives are kept masculine on purpose so the
``Noun Adjective`` pairing never breaks gender agreement. English flips to
the natural ``Adjective Noun`` order. The two lists are index-aligned
(same concept) so a user is "the blue fox" in either language.
"""
from __future__ import annotations

import hashlib

_PSEUDO_SALT = "mediakeeper-portal-pseudo-words-v1"

# (fr, en) — French masculine to avoid adjective gender agreement.
_NOUNS: tuple[tuple[str, str], ...] = (
    ("Renard", "Fox"), ("Faucon", "Falcon"), ("Hibou", "Owl"), ("Lynx", "Lynx"),
    ("Cerf", "Stag"), ("Loup", "Wolf"), ("Ours", "Bear"), ("Aigle", "Eagle"),
    ("Corbeau", "Raven"), ("Héron", "Heron"), ("Castor", "Beaver"), ("Blaireau", "Badger"),
    ("Sanglier", "Boar"), ("Lièvre", "Hare"), ("Écureuil", "Squirrel"), ("Hérisson", "Hedgehog"),
    ("Putois", "Polecat"), ("Bouquetin", "Ibex"), ("Chamois", "Chamois"), ("Phoque", "Seal"),
    ("Dauphin", "Dolphin"), ("Requin", "Shark"), ("Manchot", "Penguin"), ("Pélican", "Pelican"),
    ("Cygne", "Swan"), ("Ibis", "Ibis"), ("Flamant", "Flamingo"), ("Colibri", "Hummingbird"),
    ("Martinet", "Swift"), ("Pinson", "Finch"), ("Merle", "Blackbird"), ("Pivert", "Woodpecker"),
    ("Milan", "Kite"), ("Balbuzard", "Osprey"), ("Goéland", "Gull"), ("Macareux", "Puffin"),
    ("Renne", "Reindeer"), ("Bison", "Bison"), ("Élan", "Moose"), ("Tigre", "Tiger"),
    ("Lion", "Lion"), ("Léopard", "Leopard"), ("Guépard", "Cheetah"), ("Jaguar", "Jaguar"),
    ("Puma", "Puma"), ("Cobra", "Cobra"), ("Faisan", "Pheasant"), ("Geai", "Jay"),
)

_ADJECTIVES: tuple[tuple[str, str], ...] = (
    ("Bleu", "Blue"), ("Vert", "Green"), ("Gris", "Grey"), ("Noir", "Black"),
    ("Blanc", "White"), ("Doré", "Golden"), ("Argenté", "Silver"), ("Rapide", "Quick"),
    ("Vif", "Lively"), ("Malin", "Clever"), ("Sauvage", "Wild"), ("Hardi", "Bold"),
    ("Fier", "Proud"), ("Agile", "Agile"), ("Vaillant", "Valiant"), ("Furtif", "Stealthy"),
    ("Royal", "Royal"), ("Céleste", "Celestial"), ("Polaire", "Polar"), ("Nocturne", "Nocturnal"),
    ("Brave", "Brave"), ("Discret", "Discreet"), ("Mystique", "Mystic"), ("Farouche", "Untamed"),
)

# Number suffix range — kept 1..99 so the pseudo stays short and readable.
_NUMBER_SPAN = 99


def _indices(user_id: int) -> tuple[int, int, int]:
    """Three independent, stable indices (noun, adjective, number) for a user."""
    digest = hashlib.sha256(f"{_PSEUDO_SALT}:{user_id}".encode("utf-8")).digest()
    noun = int.from_bytes(digest[0:4], "big") % len(_NOUNS)
    adj = int.from_bytes(digest[4:8], "big") % len(_ADJECTIVES)
    number = int.from_bytes(digest[8:12], "big") % _NUMBER_SPAN + 1
    return noun, adj, number


def generate_pseudo(user_id: int, lang: str = "fr") -> str:
    """Return a stable ``Renard-Bleu-42`` (FR) / ``Blue-Fox-42`` (EN) pseudo."""
    noun_idx, adj_idx, number = _indices(user_id)
    en = (lang or "").lower().startswith("en")
    noun = _NOUNS[noun_idx][1 if en else 0]
    adj = _ADJECTIVES[adj_idx][1 if en else 0]
    pair = f"{adj}-{noun}" if en else f"{noun}-{adj}"
    return f"{pair}-{number}"
