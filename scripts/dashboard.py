#!/usr/bin/env python3
"""Application dashboard: turn a tracker into one self-contained HTML page.

Reads the tracker CSV mirror (dependency-free: stdlib only, no openpyxl needed)
and writes a single HTML file with inline CSS. It opens offline, embeds no
external assets, and phones home to nothing. Your real tracker lives in your
private, gitignored workspace, so nothing here ever leaves your machine.

Usage:
  python dashboard.py --root <workspace_applications_dir>       # reads tracker.csv there
  python dashboard.py --csv path/to/tracker.csv --out board.html
  python dashboard.py --root <dir> --sample                     # stamps a SAMPLE DATA badge

Views: headline tiles, the apply->interview->offer funnel with conversion,
status breakdown, roles by category, and the recruiter-score spread. Bars are
labelled with their category, so meaning never rests on colour alone.
"""
import argparse
import csv
import datetime
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from _lib import enable_utf8_io  # noqa: E402
    enable_utf8_io()
except Exception:  # dashboard must run even if _lib isn't importable
    pass

# Pipeline reach: a row "reached" a stage if its status is at/past it, or the
# stage's date column is stamped. Offer implies interview implies applied.
_APPLIED = {"Applied", "Interview", "Interviewed", "Offer", "Rejected"}
_INTERVIEW = {"Interview", "Interviewed", "Offer"}
_OFFER = {"Offer"}

# Status display order (pipeline order) + an accessible colour per state.
STATUS_ORDER = ["Drafted", "Cold-emailed", "Replied", "Applied", "Interview",
                "Interviewed", "Offer", "Rejected", "Skipped", "Not applied"]
# Warm, devil-red-family status palette (works on both the light nude and the
# near-black grounds; every bar is also labelled, so identity is never colour-alone).
STATUS_COLOR = {
    "Drafted": "#b0968e", "Cold-emailed": "#c77b52", "Replied": "#cc9a5a",
    "Applied": "#8a1f14", "Interview": "#c0392b", "Interviewed": "#c0392b",
    "Offer": "#c8912a", "Rejected": "#8a736e", "Skipped": "#a8948e",
    "Not applied": "#a8948e",
}
# Theme-adaptive brand red: resolves to --brand (devil red on light, brightened on dark).
BRAND = "var(--brand)"


def _read_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [ {(k or "").strip(): (v or "").strip() for k, v in row.items()}
                 for row in csv.DictReader(f) ]


def _score(row):
    """Recruiter/fit score as a float in 0..5. Accepts a bare "4.5" or "3.5/5" in
    the fit_score column, or a "recruiter x/5" mention in notes."""
    fs = (row.get("fit_score") or "").strip()
    m = re.match(r"([0-5](?:\.\d+)?)", fs)          # bare number or leading "4.5/5"
    if m:
        return float(m.group(1))
    m = re.search(r"([0-5](?:\.\d)?)\s*/\s*5", row.get("notes", "") or "")
    if m:
        return float(m.group(1))
    return None


def _reached(row, statuses, date_col):
    return row.get("status") in statuses or bool(row.get(date_col, "").strip())


def compute(rows):
    total = len(rows)
    applied = sum(_reached(r, _APPLIED, "date_applied") for r in rows)
    interview = sum(_reached(r, _INTERVIEW, "date_interviewed") for r in rows)
    offer = sum(_reached(r, _OFFER, "date_offer") for r in rows)
    rejected = sum(_reached(r, {"Rejected"}, "date_rejected") for r in rows)

    status_counts = {}
    for r in rows:
        s = r.get("status") or "Drafted"
        status_counts[s] = status_counts.get(s, 0) + 1

    cats = {}
    for r in rows:
        c = r.get("category") or "uncategorised"
        cats[c] = cats.get(c, 0) + 1

    scores = sorted((s for s in (_score(r) for r in rows) if s is not None), reverse=True)

    return {
        "total": total, "applied": applied, "interview": interview,
        "offer": offer, "rejected": rejected,
        "active": sum(r.get("status") in {"Applied", "Interview", "Interviewed"} for r in rows),
        "response_rate": (interview / applied) if applied else 0.0,
        "status_counts": status_counts, "cats": cats, "scores": scores,
    }


# ---- rendering (plain string building; CSS kept out of f-strings) ----

def _bar(label, count, maxv, color, sub=""):
    pct = (count / maxv * 100) if maxv else 0
    sub = f'<span class="sub">{html.escape(sub)}</span>' if sub else ""
    return (
        '<div class="row" title="{lab}: {n}">'
        '<div class="lab">{lab}</div>'
        '<div class="track"><div class="fill" style="width:{pct:.1f}%;background:{col}"></div></div>'
        '<div class="val">{n}{sub}</div></div>'
    ).format(lab=html.escape(label), n=count, pct=pct, col=color, sub=sub)


def _tile(num, label, accent=False):
    cls = "tile accent" if accent else "tile"
    return f'<div class="{cls}"><div class="big">{num}</div><div class="cap">{html.escape(label)}</div></div>'


def _funnel(d):
    stages = [("Logged", d["total"]), ("Applied", d["applied"]),
              ("Interview", d["interview"]), ("Offer", d["offer"])]
    maxv = d["total"] or 1
    out = ['<div class="bars">']
    prev = None
    for name, n in stages:
        conv = f'{(n/prev*100):.0f}% of prev' if prev else ""
        out.append(_bar(name, n, maxv, BRAND, conv))
        prev = n if n else prev
    out.append("</div>")
    return "".join(out)


def _status(d):
    items = [(s, d["status_counts"][s]) for s in STATUS_ORDER if s in d["status_counts"]]
    for s, n in sorted(d["status_counts"].items()):  # any non-standard statuses
        if s not in STATUS_ORDER:
            items.append((s, n))
    maxv = max((n for _, n in items), default=1)
    return '<div class="bars">' + "".join(
        _bar(s, n, maxv, STATUS_COLOR.get(s, "#8b949e")) for s, n in items) + "</div>"


def _category(d):
    items = sorted(d["cats"].items(), key=lambda kv: kv[1], reverse=True)
    maxv = max((n for _, n in items), default=1)
    return '<div class="bars">' + "".join(
        _bar(c, n, maxv, BRAND) for c, n in items) + "</div>"


def _scores(d):
    scores = d["scores"]
    if not scores:
        return '<p class="empty">No recruiter scores recorded yet.</p>'
    avg = sum(scores) / len(scores)
    # bucket into 0-1,1-2,2-3,3-4,4-5
    buckets = [0, 0, 0, 0, 0]
    for s in scores:
        buckets[min(int(s), 4)] += 1
    labels = ["0–1", "1–2", "2–3", "3–4", "4–5"]
    maxv = max(buckets) or 1
    bars = "".join(_bar(labels[i], buckets[i], maxv, "var(--brand)") for i in range(5))
    return (f'<div class="avg">avg <strong>{avg:.1f}</strong> / 5 '
            f'<span class="sub">({len(scores)} scored)</span></div>'
            f'<div class="bars">{bars}</div>')


CSS = """
:root{--bg:#fff5f2;--card:#ffffff;--ink:#240f0d;--ink2:#6b4a45;--muted:#9c7169;
--line:#f0dcd5;--track:#f7e4dd;--brand:#590000}
@media (prefers-color-scheme:dark){:root{--bg:#1a0000;--card:#2a0808;--ink:#f1efef;
--ink2:#c9b2af;--muted:#9a7d7a;--line:#3a1512;--track:#331717;--brand:#e2564e}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
padding:32px 24px 48px}
.wrap{max-width:1040px;margin:0 auto}
header{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:4px}
h1{font-size:22px;margin:0;letter-spacing:-.01em}
h1 .dot{color:var(--brand)}
.badge{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
color:#8a6d00;background:#ffe08a;border-radius:999px;padding:3px 9px}
.sub-h{color:var(--ink2);font-size:13px;margin:2px 0 22px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:20px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.tile.accent{border-color:var(--brand);box-shadow:0 0 0 1px var(--brand) inset}
.tile .big{font-size:30px;font-weight:700;letter-spacing:-.02em}
.tile .cap{color:var(--ink2);font-size:12.5px;margin-top:2px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(400px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px 20px}
.card h2{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink2);
margin:0 0 14px;font-weight:600}
.bars{display:flex;flex-direction:column;gap:9px}
.row{display:grid;grid-template-columns:120px 1fr auto;align-items:center;gap:10px}
.lab{color:var(--ink2);font-size:13px;text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.track{background:var(--track);border-radius:5px;height:12px;overflow:hidden}
.fill{height:100%;border-radius:5px;min-width:2px}
.val{font-variant-numeric:tabular-nums;font-weight:600;font-size:13px;min-width:34px;text-align:right}
.val .sub{display:block;font-weight:400;color:var(--muted);font-size:11px}
.avg{margin-bottom:12px;color:var(--ink2)}.avg strong{color:var(--ink);font-size:18px}
.avg .sub,.empty{color:var(--muted)}
footer{color:var(--muted);font-size:12px;margin-top:26px;border-top:1px solid var(--line);padding-top:14px}
"""


def render(d, title, generated, sample):
    badge = '<span class="badge">sample data</span>' if sample else ""
    parts = [
        '<div class="wrap">',
        f'<header><h1>{html.escape(title)} <span class="dot">·</span> hunt dashboard</h1>{badge}</header>',
        f'<p class="sub-h">{d["total"]} roles tracked · generated {generated} · runs locally, data never leaves your machine</p>',
        '<div class="tiles">',
        _tile(d["total"], "roles tracked"),
        _tile(d["applied"], "applied"),
        _tile(d["interview"], "interviews"),
        _tile(d["offer"], "offers", accent=bool(d["offer"])),
        _tile(f'{d["response_rate"]*100:.0f}%', "applied → interview"),
        "</div>",
        '<div class="grid">',
        '<div class="card"><h2>Pipeline funnel</h2>' + _funnel(d) + "</div>",
        '<div class="card"><h2>By status</h2>' + _status(d) + "</div>",
        '<div class="card"><h2>By category</h2>' + _category(d) + "</div>",
        '<div class="card"><h2>Recruiter scores</h2>' + _scores(d) + "</div>",
        "</div>",
        '<footer>Generated by jobxhunter · <code>scripts/dashboard.py</code>. '
        'Self-contained HTML. No tracking, no external requests.</footer>',
        "</div>",
    ]
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>{html.escape(title)} hunt dashboard</title><style>{CSS}</style></head>"
            f"<body>{''.join(parts)}</body></html>")


def main():
    ap = argparse.ArgumentParser(description="Render a tracker CSV into a self-contained HTML dashboard.")
    ap.add_argument("--root", help="workspace applications dir holding tracker.csv")
    ap.add_argument("--csv", help="explicit path to a tracker csv (overrides --root)")
    ap.add_argument("--out", help="output HTML path (default: <root>/dashboard.html or ./dashboard.html)")
    ap.add_argument("--title", default="jobxhunter", help="name shown in the header")
    ap.add_argument("--sample", action="store_true", help="stamp a SAMPLE DATA badge")
    args = ap.parse_args()

    csv_path = args.csv or (os.path.join(args.root, "tracker.csv") if args.root else None)
    if not csv_path:
        sys.exit("Give --csv <file> or --root <applications dir> (needs tracker.csv).")
    if not os.path.exists(csv_path):
        sys.exit(f"No tracker csv at {csv_path}. Run the tracker first, or pass --csv.")

    rows = _read_rows(csv_path)
    d = compute(rows)
    out = args.out or (os.path.join(args.root, "dashboard.html") if args.root else "dashboard.html")
    html_doc = render(d, args.title, datetime.date.today().isoformat(), args.sample)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html_doc)
    print(f"Dashboard written: {out}  ({d['total']} roles · {d['applied']} applied · "
          f"{d['interview']} interviews · {d['offer']} offers)")


if __name__ == "__main__":
    main()
