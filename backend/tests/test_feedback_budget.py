"""Report form vs the relayed block: at the form's limit, with the longest author
the server allows, the block fits and the description is never cut with "…".
The form's numbers are read from frontend/src/constants/feedback.ts."""
import re
from pathlib import Path

import pytest

from services.feedback import _CAP_AUTHOR, _MAX_BLOCK, build_report_block

_FRONT_CONSTANTS = Path(__file__).resolve().parents[2] / "frontend/src/constants/feedback.ts"
# The server clips the "Signalé par" author to this length: the longest it can add.
_LONGEST_AUTHOR = "B" * _CAP_AUTHOR
_ADMIN_PAGE = {"zone": "Tableau de bord (admin général)", "module": "Statistiques", "tab": "Users"}
_PORTAL_PAGE = {"zone": "", "module": "", "tab": ""}


def _front(name: str) -> int:
    match = re.search(rf"export const {name} = (\d+)", _FRONT_CONSTANTS.read_text(encoding="utf-8"))
    assert match, f"{name} missing from the form constants"
    return int(match.group(1))


def _form_estimate(fields: dict) -> int:
    """The form's ``used`` total (useFeedbackForm): fixed part, longest author, typed fields."""
    typed = ("title", "description", "reproduction", "resolution", "zone", "module", "tab")
    return (
        _front("FEEDBACK_BLOCK_OVERHEAD") + _front("FEEDBACK_MAX_AUTHOR")
        + sum(len(fields[k]) for k in typed) + len(", ".join(fields["tags"]))
    )


def _fields(page: dict, **over) -> dict:
    fields = {
        "type": "suggestion", "platform": "desktop", "title": "t" * 120, "description": "",
        "reproduction": "r" * 50, "resolution": "9" * 40, "tags": ["urgent", "visual"], **page,
    }
    fields.update(over)
    return fields


def test_form_caps_mirror_the_server():
    assert _front("FEEDBACK_MAX_AUTHOR") == _CAP_AUTHOR
    assert _front("FEEDBACK_MAX_CHARS") == _MAX_BLOCK


def test_form_overhead_is_the_longest_fixed_part():
    # One character per optional field so every label shows; empty location → "-" each.
    fields = _fields(_PORTAL_PAGE, title="", reproduction="r", resolution="9", tags=["g"])
    fixed = len(build_report_block(fields, "X")) - len("r9gX")
    assert _front("FEEDBACK_BLOCK_OVERHEAD") == fixed


@pytest.mark.parametrize("page", [_ADMIN_PAGE, _PORTAL_PAGE], ids=["admin", "portal"])
@pytest.mark.parametrize("kind", ["bug", "suggestion"])
def test_a_report_at_the_form_limit_is_never_cut(page, kind):
    fields = _fields(page, type=kind)
    room = _front("FEEDBACK_MAX_CHARS") - _form_estimate(fields)
    fields["description"] = "d" * room
    assert _form_estimate(fields) == _front("FEEDBACK_MAX_CHARS")

    block = build_report_block(fields, _LONGEST_AUTHOR)
    assert fields["description"] in block
    assert "…" not in block
    assert len(block) <= _MAX_BLOCK
