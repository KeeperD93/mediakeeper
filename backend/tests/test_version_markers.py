"""Release version markers must move together: the portal Credits page shows
the frontend package version while the admin surfaces read ``APP_VERSION``."""
import json
from pathlib import Path

from api.changelog import APP_VERSION

_PACKAGE_JSON = Path(__file__).resolve().parents[2] / "frontend" / "package.json"


def test_frontend_package_version_matches_app_version():
    package = json.loads(_PACKAGE_JSON.read_text(encoding="utf-8"))
    assert package["version"] == APP_VERSION
