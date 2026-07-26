"""Regression tests for salary rendering in the Reed MCP server.

Run: .venv/Scripts/python.exe test_rendering.py

Guards the fix for the "£17.60/hr rate renders as an ambiguous '£18'" bug: Reed's
/search endpoint returns raw salary figures with no `salaryType`, so an hourly/daily
rate must (a) keep its pennies and (b) be flagged as a non-annual rate.
"""

from server import _period_note, _salary


def check(label, got, want):
    status = "PASS" if got == want else "FAIL"
    print(f"[{status}] {label}: got {got!r} want {want!r}")
    return got == want


def contains(label, got, needle):
    status = "PASS" if needle in got else "FAIL"
    print(f"[{status}] {label}: {needle!r} in {got!r}")
    return needle in got


def main() -> int:
    ok = True

    # Precision: hourly rate keeps pennies (was the bug — rounded 17.6 -> £18).
    ok &= check("hourly precision", _salary(17.6, 17.6), "£17.60")
    # Whole numbers stay clean, no spurious decimals.
    ok &= check("annual whole", _salary(44000, 44000), "£44,000")
    ok &= check("daily range", _salary(150, 175), "£150 - £175")
    # Hidden salary is not zero.
    ok &= check("hidden", _salary(None, None), "Not disclosed")
    ok &= check("currency symbol fallback", _salary(1000.5, 1000.5, "USD"), "$1,000.50")

    # Non-annual rate flag: sub-£1000 figures are certainly rates, not salaries.
    ok &= contains("hourly flagged", _period_note(17.6, 17.6), "RATE")
    ok &= contains("daily flagged", _period_note(150, 175), "RATE")
    # Real annual salaries are NOT flagged.
    ok &= check("annual not flagged", _period_note(44000, 44000), "")
    ok &= check("annual range not flagged", _period_note(32000, 35000), "")
    # Hidden salary produces no flag.
    ok &= check("hidden not flagged", _period_note(None, None), "")

    print("\nALL PASS" if ok else "\nFAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
