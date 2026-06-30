"""Tool-registry identifier constants stay in sync with TOOLS_DEFINITION and
keep their key strings stable — the frontend and stored settings key on them."""
from constants.tools import TOOL_EMBY, TOOL_OPENSUBTITLES, TOOL_TMDB
from services.settings._tools_def import TOOLS_DEFINITION


def test_constant_values_are_stable():
    # A rename/typo here would silently break the frontend + persisted settings.
    assert TOOL_EMBY == "emby"
    assert TOOL_TMDB == "tmdb"
    assert TOOL_OPENSUBTITLES == "opensubtitles"


def test_registry_keyed_by_constants():
    assert set(TOOLS_DEFINITION) == {TOOL_EMBY, TOOL_TMDB, TOOL_OPENSUBTITLES}
