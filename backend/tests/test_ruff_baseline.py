"""The ruff baseline tolerates old issues and stops any increase."""
import json
import subprocess

import pytest

from scripts import ruff_baseline

EXAMPLE = "backend/services/example.py"
OTHER = "backend/core/other.py"


def _issue(path: str, code: str, row: int = 1) -> dict:
    return {
        "filename": str(ruff_baseline.REPO_ROOT / path),
        "code": code,
        "message": f"Test message for {code}",
        "location": {"row": row, "column": 5},
    }


@pytest.fixture
def baseline(tmp_path, monkeypatch):
    path = tmp_path / "ruff-baseline.json"
    monkeypatch.setattr(ruff_baseline, "BASELINE_PATH", path)
    return path


@pytest.fixture
def fake_ruff(monkeypatch):
    """Replace the ruff process: set ``.result`` and read ``.commands``."""

    class FakeRuff:
        def __init__(self):
            self.commands = []
            self.kwargs = {}
            self.result = subprocess.CompletedProcess([], 0, stdout="[]", stderr="")

        def report(self, *issues: dict) -> None:
            self.result = subprocess.CompletedProcess([], 1 if issues else 0, stdout=json.dumps(issues), stderr="")

        def __call__(self, command, **kwargs):
            self.commands.append(command)
            self.kwargs = kwargs
            return self.result

    fake = FakeRuff()
    monkeypatch.setattr(ruff_baseline.subprocess, "run", fake)
    return fake


def _write(path, table: dict) -> None:
    path.write_text(json.dumps(table), encoding="utf-8")


def test_same_counts_as_the_baseline_pass(baseline, fake_ruff):
    _write(baseline, {EXAMPLE: {"B904": 2}})
    fake_ruff.report(_issue(EXAMPLE, "B904", 3), _issue(EXAMPLE, "B904", 9))
    assert ruff_baseline.main([]) == 0


def test_fewer_issues_than_the_baseline_pass(baseline, fake_ruff):
    _write(baseline, {EXAMPLE: {"B904": 2}})
    fake_ruff.report(_issue(EXAMPLE, "B904"))
    assert ruff_baseline.main([]) == 0


def test_a_moved_issue_still_matches(baseline, fake_ruff):
    _write(baseline, {EXAMPLE: {"B904": 1}})
    fake_ruff.report(_issue(EXAMPLE, "B904", 400))
    assert ruff_baseline.main([]) == 0


def test_one_more_issue_fails_and_names_it(baseline, fake_ruff, capsys):
    _write(baseline, {EXAMPLE: {"B904": 1}})
    fake_ruff.report(_issue(EXAMPLE, "B904", 3), _issue(EXAMPLE, "B904", 9))
    assert ruff_baseline.main([]) == 1
    output = capsys.readouterr().out
    assert f"{EXAMPLE}:9:5: B904 Test message for B904" in output
    assert f"{EXAMPLE} B904: 2 found, 1 allowed" in output


def test_a_rule_new_to_the_file_fails(baseline, fake_ruff, capsys):
    _write(baseline, {EXAMPLE: {"B904": 1}})
    fake_ruff.report(_issue(EXAMPLE, "B904"), _issue(EXAMPLE, "F401", 2))
    assert ruff_baseline.main([]) == 1
    output = capsys.readouterr().out
    assert "F401" in output
    assert "B904" not in output


def test_a_file_absent_from_the_baseline_fails(baseline, fake_ruff):
    _write(baseline, {EXAMPLE: {"B904": 1}})
    fake_ruff.report(_issue(OTHER, "B904"))
    assert ruff_baseline.main([]) == 1


def test_ruff_runs_from_the_repo_root_and_returns_json(baseline, fake_ruff):
    _write(baseline, {})
    ruff_baseline.main([])
    assert fake_ruff.commands[0][1:] == ["-m", "ruff", "check", "--no-cache", "--output-format=json", "backend"]
    assert fake_ruff.kwargs["cwd"] == ruff_baseline.REPO_ROOT
    assert fake_ruff.kwargs["encoding"] == "utf-8"


def test_no_argument_checks_the_whole_backend(baseline, fake_ruff):
    _write(baseline, {})
    ruff_baseline.main([])
    assert fake_ruff.commands[0][-1] == "backend"


def test_given_files_are_the_only_ones_checked(baseline, fake_ruff):
    _write(baseline, {OTHER: {"B904": 4}})
    ruff_baseline.main([EXAMPLE])
    assert fake_ruff.commands[0][-1] == EXAMPLE
    assert "backend" not in fake_ruff.commands[0]


def test_a_ruff_failure_is_not_read_as_a_clean_run(baseline, fake_ruff):
    _write(baseline, {})
    fake_ruff.result = subprocess.CompletedProcess([], 2, stdout="[]", stderr="invalid configuration")
    with pytest.raises(SystemExit, match="invalid configuration"):
        ruff_baseline.main([])


def test_a_missing_ruff_is_not_read_as_a_clean_run(baseline, fake_ruff):
    _write(baseline, {})
    fake_ruff.result = subprocess.CompletedProcess([], 1, stdout="", stderr="No module named ruff")
    with pytest.raises(SystemExit, match="No module named ruff"):
        ruff_baseline.main([])


def test_update_writes_sorted_relative_counts(baseline, fake_ruff):
    fake_ruff.report(
        _issue(EXAMPLE, "F401"),
        _issue(OTHER, "B904"),
        _issue(EXAMPLE, "B904"),
        _issue(EXAMPLE, "B904", 8),
    )
    assert ruff_baseline.main(["--update"]) == 0
    raw = baseline.read_bytes()
    assert b"\r\n" not in raw
    assert raw.endswith(b"}\n")
    table = json.loads(raw)
    assert table == {OTHER: {"B904": 1}, EXAMPLE: {"B904": 2, "F401": 1}}
    assert list(table) == [OTHER, EXAMPLE]
    assert list(table[EXAMPLE]) == ["B904", "F401"]


def test_an_updated_baseline_accepts_the_same_issues(baseline, fake_ruff):
    fake_ruff.report(_issue(EXAMPLE, "B904"), _issue(OTHER, "F401"))
    ruff_baseline.main(["--update"])
    assert ruff_baseline.main([]) == 0


def test_update_refuses_a_partial_rewrite(baseline, fake_ruff):
    with pytest.raises(SystemExit):
        ruff_baseline.main(["--update", EXAMPLE])
    assert fake_ruff.commands == []
