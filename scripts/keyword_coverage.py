#!/usr/bin/env python3
"""Deterministic keyword-coverage diagnostic for a tailored CV.

This is the mechanical half of a job the agent already does semantically: during
JD analysis the agent enumerates the must-have (and nice-to-have) terms; this
script then checks, exactly and reproducibly, which of those terms actually appear
in the rendered `CV.txt`. It is a **parse/search diagnostic** — "an ATS keyword
filter would surface these N of M terms" — NOT a Jobscan-style match score, and
NOT an auto-reject gate. Real screening is done by humans against real requirements;
this only tells you whether the words you meant to include actually made it onto the
page (and flags acronyms you forgot to pair with an expansion).

The agent decides WHAT matters; this script decides — deterministically — whether it
is PRESENT. That division keeps the judgement human and the check reproducible.

Usage:
  python keyword_coverage.py --cv CV.txt --must "python, nlp, pandas, sql" [--nice "docker, aws"]
  python keyword_coverage.py --cv CV.txt --must-file must.txt [--json] [--min 0.7]

Terms are comma-  or newline-separated. Multi-word terms ("machine learning") and
symbol terms ("c++", ".net") are handled. Matching is case-insensitive, whole-term.
Exit code is 0 unless --min is given and must-have coverage falls below it (for use
as an eval-harness gate).
"""
import argparse
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass


def _parse_terms(raw):
    """Split a comma/newline-separated term string into a clean, de-duped list."""
    if not raw:
        return []
    parts = re.split(r"[,\n]", raw)
    out, seen = [], set()
    for p in parts:
        t = p.strip()
        key = t.lower()
        if t and key not in seen:
            seen.add(key)
            out.append(t)
    return out


def _term_regex(term):
    """Build a case-insensitive whole-term matcher. Word-boundaries for alnum terms;
    a looser escaped match for symbol terms (c++, .net, c#) where \\b doesn't apply."""
    t = term.strip()
    # collapse internal whitespace to \s+ so "machine  learning" still matches
    escaped = r"\s+".join(re.escape(w) for w in t.split())
    if re.match(r"^[\w\s]+$", t):  # purely alphanumeric/space -> safe word boundaries
        return re.compile(rf"(?<!\w){escaped}(?!\w)", re.IGNORECASE)
    return re.compile(escaped, re.IGNORECASE)


def _looks_like_acronym(term):
    return bool(re.fullmatch(r"[A-Za-z]{2,6}", term)) and term.isupper()


def _acronym_unpaired(term, text):
    """True if an acronym appears but never next to a parenthetical expansion, i.e.
    neither 'TERM (expansion)' nor 'expansion (TERM)' is present."""
    esc = re.escape(term)
    paired = re.search(rf"{esc}\s*\([^)]+\)", text, re.IGNORECASE) or \
        re.search(rf"\([^)]*{esc}[^)]*\)", text, re.IGNORECASE)
    return not paired


def _read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def _coverage(terms, text):
    hits, misses = [], []
    for t in terms:
        n = len(_term_regex(t).findall(text))
        (hits if n else misses).append((t, n))
    return hits, misses


def main():
    ap = argparse.ArgumentParser(description="Deterministic CV keyword-coverage diagnostic.")
    ap.add_argument("--cv", required=True, help="path to the rendered CV.txt")
    ap.add_argument("--must", default="", help="must-have terms (comma/newline separated)")
    ap.add_argument("--must-file", help="file of must-have terms (comma/newline separated)")
    ap.add_argument("--nice", default="", help="nice-to-have terms")
    ap.add_argument("--nice-file", help="file of nice-to-have terms")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of the text report")
    ap.add_argument("--min", type=float, help="fail (exit 1) if must-have coverage < this fraction (0-1)")
    args = ap.parse_args()

    if not os.path.exists(args.cv):
        sys.exit(f"CV not found: {args.cv}")
    text = _read(args.cv)

    must = _parse_terms(args.must) + (_parse_terms(_read(args.must_file)) if args.must_file else [])
    nice = _parse_terms(args.nice) + (_parse_terms(_read(args.nice_file)) if args.nice_file else [])
    # de-dupe must vs itself again (file + inline)
    must = list(dict.fromkeys(must))
    nice = [t for t in dict.fromkeys(nice) if t.lower() not in {m.lower() for m in must}]

    if not must and not nice:
        sys.exit("No terms given. Pass --must (and optionally --nice) or their --*-file forms.")

    m_hits, m_miss = _coverage(must, text)
    n_hits, n_miss = _coverage(nice, text)
    m_total = len(must)
    m_frac = (len(m_hits) / m_total) if m_total else 1.0
    unpaired = [t for t, _ in m_hits + n_hits if _looks_like_acronym(t) and _acronym_unpaired(t, text)]

    if args.json:
        print(json.dumps({
            "cv": args.cv,
            "must": {"matched": [t for t, _ in m_hits], "missing": [t for t, _ in m_miss],
                     "coverage": round(m_frac, 3), "n_matched": len(m_hits), "n_total": m_total},
            "nice": {"matched": [t for t, _ in n_hits], "missing": [t for t, _ in n_miss]},
            "acronyms_unpaired": unpaired,
        }, indent=2, ensure_ascii=False))
    else:
        print("Keyword coverage — parse diagnostic (NOT an ATS auto-reject score)")
        print(f"CV: {args.cv}\n")
        pct = f"{m_frac * 100:.0f}%"
        print(f"Must-haves present: {len(m_hits)}/{m_total} ({pct})")
        if m_hits:
            print("  matched: " + ", ".join(t for t, _ in m_hits))
        if m_miss:
            print("  MISSING: " + ", ".join(t for t, _ in m_miss)
                  + "   <- add these (only if the profile truly supports them)")
        if nice:
            print(f"\nNice-to-haves present: {len(n_hits)}/{len(nice)}")
            if n_hits:
                print("  matched: " + ", ".join(t for t, _ in n_hits))
            if n_miss:
                print("  missing: " + ", ".join(t for t, _ in n_miss))
        if unpaired:
            print("\nAcronyms present but not paired with an expansion (ATS + human tip — "
                  "write e.g. \"NLP (natural language processing)\" once):")
            print("  " + ", ".join(unpaired))
        print("\nReminder: this measures whether the words are on the page, not whether you "
              "are a fit. Never add a term the profile can't back — a surfaced gap beats a lie.")

    if args.min is not None and m_frac < args.min:
        sys.exit(1)


if __name__ == "__main__":
    main()
