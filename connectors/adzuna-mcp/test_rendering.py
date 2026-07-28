"""Regression tests for Adzuna rendering + credential redaction.

Pure-Python, no third-party deps (imports render.py, not server.py), so it runs
anywhere:  python test_rendering.py

Guards three fixes:
  1. Salary-histogram bands were sorted as STRINGS, so '100000' sorted before
     '20000' and scrambled the distribution. `_pairs_to_markdown` must sort a
     fully-numeric key set NUMERICALLY, and leave non-numeric keys (ISO months)
     lexical.
  2. A withheld salary (null min AND max) must render 'Not disclosed', never
     the ambiguous '? - ?'.
  3. The app_id/app_key credential redaction must scrub keys out of any error
     text before it reaches the agent transcript.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import _pairs_to_markdown, _numeric, format_salary, redact_credentials  # noqa: E402


def check(label, got, want):
    status = "PASS" if got == want else "FAIL"
    print(f"[{status}] {label}: got {got!r} want {want!r}")
    return got == want


def contains(label, got, needle):
    status = "PASS" if needle in got else "FAIL"
    print(f"[{status}] {label}: {needle!r} in <text>")
    return needle in got


def not_contains(label, got, needle):
    status = "PASS" if needle not in got else "FAIL"
    print(f"[{status}] {label}: {needle!r} NOT in <text>")
    return needle not in got


def _table_keys(md):
    return [line.split("|")[1].strip()
            for line in md.splitlines()
            if line.startswith("| ") and "---" not in line][1:]  # drop header row


def main() -> int:
    ok = True

    # 1. Numeric band ordering — the histogram bug. Insertion order is deliberately
    #    scrambled; a string sort would put 100000 before 20000.
    hist = {"100000": 5, "20000": 10, "10000": 3, "50000": 8}
    md = _pairs_to_markdown(hist, "Salary band (from)", "Vacancies", "Salary distribution")
    ok &= check("histogram numeric order", _table_keys(md), ["10000", "20000", "50000", "100000"])
    ok &= check("_numeric parses commas", _numeric("1,200"), 1200.0)
    ok &= check("_numeric rejects text", _numeric("London"), None)

    # Non-numeric keys (ISO months) stay lexical/chronological, unchanged.
    months = {"2025-03": 3, "2025-01": 1, "2025-02": 2}
    ok &= check("month lexical order", _table_keys(_pairs_to_markdown(months, "Month", "Avg", "History")),
                ["2025-01", "2025-02", "2025-03"])

    # 2. Withheld salary renders 'Not disclosed'; a real range renders normally.
    ok &= check("hidden salary", format_salary(None, None), "Not disclosed")
    ok &= check("real range", format_salary(40000, 50000), "40,000 - 50,000")
    ok &= contains("predicted flagged", format_salary(40000, 50000, predicted=True), "predicted")
    ok &= not_contains("no phantom range", format_salary(None, None), "? - ?")

    # 3. Credential redaction scrubs both key params out of any leaked URL/error text.
    leaked = "GET https://api.adzuna.com/v1/api/jobs/gb/search/1?app_id=abc123&app_key=deadbeef&what=x failed"
    red = redact_credentials(leaked)
    ok &= contains("app_id redacted", red, "app_id=REDACTED")
    ok &= contains("app_key redacted", red, "app_key=REDACTED")
    ok &= not_contains("secret gone", red, "deadbeef")

    print("\nALL PASS" if ok else "\nFAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
