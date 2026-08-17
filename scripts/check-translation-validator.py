"""Measure translation-validator changes against the real queue.

Answers two questions at once:

1. How many of the rows that died on `failed_translation` would now pass?
   Those are the false positives the validator was producing. The rejected
   output is recovered from `last_error`, where `translation_validation_error`
   stores it after a `| output=` marker (truncated at 500 characters).

2. Does the new validator start rejecting translations that were accepted?
   Those would be false negatives turning into new failures. Published and
   translated rows carry their full text, so this side is exact.

Run it on the server, where the real queue lives:

    python scripts/check-translation-validator.py
    python scripts/check-translation-validator.py --limit 1500 --json report.json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from n1_project.config import Settings  # noqa: E402
from n1_project.validators import translation_issues  # noqa: E402

OUTPUT_MARKER = " | output="


def resolve_db_path(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    return Settings.load(REPO_ROOT / ".env", project_root=REPO_ROOT).db_path


def recovered_output(last_error: str | None) -> tuple[str | None, bool]:
    """Pull the rejected translation back out of the stored error message."""
    if not last_error:
        return None, False
    marker = last_error.find(OUTPUT_MARKER)
    if marker == -1:
        return None, False
    text = last_error[marker + len(OUTPUT_MARKER) :].strip()
    if not text:
        return None, False
    return text.removesuffix("..."), text.endswith("...")


def issue_kind(issue: str) -> str:
    for prefix in (
        "missing numbers",
        "added numbers",
        "missing urls",
        "added urls",
        "missing hashtags",
        "added hashtags",
        "missing emojis",
        "added emojis",
        "added source attributions",
        "line count changed",
        "leading emoji sequence changed",
        "many latin words remain",
        "output has no Cyrillic text",
    ):
        if issue.startswith(prefix):
            return prefix
    if issue.startswith("bad market terminology"):
        return issue.split(":", 1)[0] + ": " + issue.split(":", 2)[1].strip()[:40]
    return issue[:40]


def check_failed_rows(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        """
        SELECT id, source_text, last_error, attempts
        FROM messages
        WHERE status = 'failed_translation'
        ORDER BY id
        """
    ).fetchall()

    now_clean: list[int] = []
    still_flagged: list[dict] = []
    unrecoverable: list[int] = []
    remaining_kinds: Counter = Counter()

    for row in rows:
        output, truncated = recovered_output(row["last_error"])
        if output is None:
            unrecoverable.append(int(row["id"]))
            continue
        issues = translation_issues(str(row["source_text"]), output)
        if issues:
            still_flagged.append(
                {
                    "id": int(row["id"]),
                    "attempts": int(row["attempts"]),
                    "output_truncated": truncated,
                    "issues": issues,
                }
            )
            for issue in issues:
                remaining_kinds[issue_kind(issue)] += 1
        else:
            now_clean.append(int(row["id"]))

    return {
        "total": len(rows),
        "unrecoverable_output": unrecoverable,
        "now_clean_count": len(now_clean),
        "now_clean_ids": now_clean,
        "still_flagged_count": len(still_flagged),
        "still_flagged": still_flagged,
        "remaining_issue_kinds": dict(remaining_kinds.most_common()),
    }


def check_successful_rows(conn: sqlite3.Connection, limit: int) -> dict:
    rows = conn.execute(
        """
        SELECT id, source_text, translated_text
        FROM messages
        WHERE translated_text IS NOT NULL
          AND status NOT IN ('failed_translation', 'received')
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    regressions: list[dict] = []
    regression_kinds: Counter = Counter()
    for row in rows:
        issues = translation_issues(str(row["source_text"]), str(row["translated_text"]))
        if issues:
            regressions.append({"id": int(row["id"]), "issues": issues})
            for issue in issues:
                regression_kinds[issue_kind(issue)] += 1

    return {
        "checked": len(rows),
        "would_now_fail_count": len(regressions),
        "would_now_fail": regressions,
        "issue_kinds": dict(regression_kinds.most_common()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", help="SQLite path; defaults to DB_PATH from .env")
    parser.add_argument("--limit", type=int, default=1500, help="How many accepted rows to re-check")
    parser.add_argument("--json", help="Write the full report to this file")
    args = parser.parse_args()

    db_path = resolve_db_path(args.db)
    if not db_path.exists():
        print(f"database not found: {db_path}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        report = {
            "database": str(db_path),
            "failed_rows": check_failed_rows(conn),
            "accepted_rows": check_successful_rows(conn, args.limit),
        }
    finally:
        conn.close()

    failed = report["failed_rows"]
    accepted = report["accepted_rows"]
    print(f"database: {db_path}")
    print()
    print("dead rows (status=failed_translation)")
    print(f"  total:                      {failed['total']}")
    print(f"  would now pass:             {failed['now_clean_count']}")
    print(f"  still flagged:              {failed['still_flagged_count']}")
    print(f"  output not recoverable:     {len(failed['unrecoverable_output'])}")
    for kind, count in failed["remaining_issue_kinds"].items():
        print(f"    {kind}: {count}")
    print()
    print("accepted rows (published/translated)")
    print(f"  checked:                    {accepted['checked']}")
    print(f"  would now be rejected:      {accepted['would_now_fail_count']}")
    for kind, count in accepted["issue_kinds"].items():
        print(f"    {kind}: {count}")
    if accepted["would_now_fail_count"]:
        print()
        print("  new rejections (first 20):")
        for item in accepted["would_now_fail"][:20]:
            print(f"    row={item['id']}: {'; '.join(item['issues'])}")

    if args.json:
        Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print()
        print(f"full report written to {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
