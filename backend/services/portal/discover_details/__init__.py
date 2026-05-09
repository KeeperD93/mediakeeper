"""Full media details (with credits, videos, recommendations) + TMDB multi-search.

Sub-package modules group code by responsibility while preserving the public
surface that the legacy ``discover_details.py`` module exposed.
"""
import logging as logging
import os as os
import re as re
import unicodedata as unicodedata
from difflib import SequenceMatcher as SequenceMatcher

from sqlalchemy import select as select, tuple_ as tuple_
from sqlalchemy.ext.asyncio import AsyncSession as AsyncSession

from core.http_client import get_external_client as get_external_client
from models.portal.emby_tmdb_index import EmbyTmdbIndex as EmbyTmdbIndex
from services.portal.discover_details_enrich import (
    extract_key_crew as extract_key_crew,
    extract_reviews as extract_reviews,
    extract_studios as extract_studios,
    extract_videos as extract_videos,
    merge_original_language_videos as merge_original_language_videos,
    pick_certification as pick_certification,
    pick_watch_providers as pick_watch_providers,
)
from services.portal.discover_filters import LANGUAGE_TO_REGION as LANGUAGE_TO_REGION
from services.tmdb import TMDB_BASE as TMDB_BASE

from ._constants import LANGUAGE as LANGUAGE, logger as logger
from ._details import (
    get_collection as get_collection,
    get_full_details as get_full_details,
    get_person_filmography as get_person_filmography,
)
from ._query_variants import _search_query_variants as _search_query_variants
from ._scoring import _score_search_result as _score_search_result
from ._search import search_tmdb_multi as search_tmdb_multi
from ._text_helpers import (
    _canonical_search_text as _canonical_search_text,
    _search_languages as _search_languages,
    _tmdb_language as _tmdb_language,
)

__all__ = [
    "LANGUAGE",
    "logger",
    "get_collection",
    "get_full_details",
    "get_person_filmography",
    "search_tmdb_multi",
]
