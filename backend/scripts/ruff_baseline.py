"""Fail when ruff reports more issues than the committed baseline allows.

Issues that predate the ruff configuration are counted per file and per rule
in ``ruff-baseline.json`` and tolerated. The check fails as soon as a file's
count for a rule goes up, so fixing an old issue in the same change can hide a
new one of that rule. Counting instead of pinning line numbers keeps the
baseline valid when code moves within a file.

    python backend/scripts/ruff_baseline.py            # whole backend (CI)
    python backend/scripts/ruff_baseline.py FILE...    # those files (commit hook)
    python backend/scripts/ruff_baseline.py --update   # rewrite the baseline

Run ``--update`` after fixing old issues, so they cannot come back, after moving
or splitting a file, whose path is its key here, or after changing a rule or the
ruff version. An increase in its diff that no move explains means new debt.
"""
import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = REPO_ROOT / "ruff-baseline.json"


def run_ruff(paths: list[str]) -> list[dict]:
    result = subprocess.run(  # noqa: S603 -- fixed command, paths come from CI or the commit hook
        [sys.executable, "-m", "ruff", "check", "--no-cache", "--output-format=json", *paths],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
    )
    # Ruff prints a JSON list whenever it ran, even with nothing to report;
    # exit code 1 alone also covers "No module named ruff".
    if result.returncode not in (0, 1) or not result.stdout:
        sys.exit(f"[ruff] could not run: {result.stderr.strip()}")
    return json.loads(result.stdout)


def _key(issue: dict) -> tuple[str, str]:
    path = Path(issue["filename"]).resolve().relative_to(REPO_ROOT).as_posix()
    return path, issue["code"]


def _load_baseline() -> Counter:
    table = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    return Counter({(path, code): n for path, rules in table.items() for code, n in rules.items()})


def update_baseline() -> int:
    counts = Counter(_key(issue) for issue in run_ruff(["backend"]))
    table: defaultdict[str, dict[str, int]] = defaultdict(dict)
    for (path, code), count in sorted(counts.items()):
        table[path][code] = count
    BASELINE_PATH.write_text(json.dumps(table, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"[ruff] baseline rewritten: {counts.total()} issues in {len(table)} files.")
    return 0


def check(paths: list[str]) -> int:
    issues = run_ruff(paths or ["backend"])
    current = Counter(_key(issue) for issue in issues)
    allowed = _load_baseline()
    over_baseline = {key for key, count in current.items() if count > allowed[key]}
    if not over_baseline:
        print("[ruff] OK - no new issue.")
        return 0

    print("[ruff] FAIL - more issues than the baseline allows. Fix the new ones among those listed below.")
    print("  Import order: python -m ruff check --fix --select I FILE. Moved file: run with --update.")
    for issue in issues:
        path, code = _key(issue)
        if (path, code) in over_baseline:
            location = issue["location"]
            print(f"  {path}:{location['row']}:{location['column']}: {code} {issue['message']}")
    for path, code in sorted(over_baseline):
        print(f"  {path} {code}: {current[path, code]} found, {allowed[path, code]} allowed")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare ruff issues with the committed baseline.")
    parser.add_argument("files", nargs="*", help="limit the check to these files")
    parser.add_argument("--update", action="store_true", help="rewrite the baseline for the whole backend")
    args = parser.parse_args(argv)
    if args.update and args.files:
        parser.error("--update always covers the whole backend")
    return update_baseline() if args.update else check(args.files)


if __name__ == "__main__":
    sys.exit(main())
