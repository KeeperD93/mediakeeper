"""Sentinel : les 3 fixtures autouse de conftest sont la barrière
contre la pollution cross-tests (cf. PR #97 event-loop poisoning).
Si une est supprimée ou downgradée en opt-in, ce test casse
immédiatement avant qu'un autre test cross-file commence à mentir
silencieusement."""
import inspect

from tests import conftest

EXPECTED_FIXTURES = (
    "_reset_rate_limiter",
    "_reset_media_categories_cache",
    "_reset_diagnostic_log_sentinels",
)


def test_critical_autouse_fixtures_still_in_conftest():
    """Each fixture must exist in conftest as a callable."""
    for name in EXPECTED_FIXTURES:
        fn = getattr(conftest, name, None)
        assert fn is not None, f"Autouse fixture {name!r} removed from conftest.py"
        assert callable(fn), f"{name!r} is not callable"


def test_critical_autouse_fixtures_still_decorated_with_autouse():
    """The `@pytest.fixture(autouse=True)` decorator must remain
    immediately above each fixture's def. Catches deletion of the
    decorator AND downgrade to `autouse=False` — both silently
    disable the cleanup the fixtures provide. Source-text check,
    version-proof."""
    src = inspect.getsource(conftest)
    for name in EXPECTED_FIXTURES:
        expected = f"@pytest.fixture(autouse=True)\ndef {name}"
        assert expected in src, (
            f"Fixture {name!r} no longer has "
            f"'@pytest.fixture(autouse=True)' directly above its "
            f"def in conftest.py — autouse cleanup compromised"
        )
