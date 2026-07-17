#!/usr/bin/env python3
"""Application tracker — deterministic owner of tracker.xlsx + tracker.csv.

The skill must route ALL tracker state changes through this script so they are
deterministic, not model-improvised. Applied rows are filled green and locked
(sheet protection) so an applied record cannot be silently lost or altered.

Unique key for a row = folder_path (the per-job folder). Add is idempotent on it.

Usage:
  python tracker.py init   --root <applications_dir>
  python tracker.py add    --root <applications_dir> --data '<json>'
  python tracker.py update --root <applications_dir> --key <folder_path> --data '<json>'
  python tracker.py show   --root <applications_dir>

`--data` is a JSON object whose keys are any of COLUMNS. `add` fills logged_date
automatically if absent and defaults status to "Drafted". `update` sets fields on
the matching row; setting status to "Applied" stamps date_applied (if absent),
turns the row green, and locks it. Other status values stamp their matching date
column and recolour the row.
"""
import argparse
import csv
import datetime
import json
import os
import sys

try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import PatternFill, Font, Protection, Alignment
    from openpyxl.utils import get_column_letter
except ImportError:
    sys.exit("openpyxl is required: pip install openpyxl")

COLUMNS = [
    "logged_date", "category", "company", "role", "location", "link", "source",
    "ats_platform", "pay", "level_used", "status", "date_applied",
    "date_interviewed", "date_rejected", "date_offer", "follow_up",
    "cv_path", "cover_letter_path", "folder_path", "notes",
]

# status -> the date column it stamps (if any)
STATUS_DATE = {
    "Applied": "date_applied",
    "Interview": "date_interviewed",
    "Interviewed": "date_interviewed",
    "Rejected": "date_rejected",
    "Offer": "date_offer",
}

STATUS_FILL = {
    "Applied":     "C6EFCE",  # green  — locked, final
    "Interview":   "BDD7EE",  # blue
    "Interviewed": "BDD7EE",
    "Offer":       "FFD966",  # gold
    "Rejected":    "F4CCCC",  # red
    "Skipped":     "D9D9D9",  # grey
    "Not applied": "D9D9D9",
    "Cold-emailed":"E4DFEC",  # light purple — speculative outreach sent
    "Replied":     "DDEBF7",  # pale blue — got a response to outreach
    "Drafted":     None,      # no fill
}

HEADER_FILL = PatternFill("solid", fgColor="305496")
HEADER_FONT = Font(bold=True, color="FFFFFF")


def xlsx_path(root):
    return os.path.join(root, "tracker.xlsx")


def csv_path(root):
    return os.path.join(root, "tracker.csv")


def _today():
    # ISO date; caller may override via --data for reproducibility.
    return datetime.date.today().isoformat()


def _normkey(path):
    """Normalise a folder_path for comparison: unify separators, drop trailing
    slash, case-fold (Windows paths arrive with mixed / and \\)."""
    if path is None:
        return ""
    p = str(path).strip().replace("\\", "/").rstrip("/")
    return os.path.normcase(p)


def _new_workbook():
    wb = Workbook()
    ws = wb.active
    ws.title = "applications"
    ws.append(COLUMNS)
    for col_idx, name in enumerate(COLUMNS, start=1):
        c = ws.cell(row=1, column=col_idx)
        c.fill = HEADER_FILL
        c.font = HEADER_FONT
        c.alignment = Alignment(vertical="center")
        # sensible-ish widths
        width = {"notes": 40, "role": 26, "company": 22, "folder_path": 40,
                 "cv_path": 30, "cover_letter_path": 30, "link": 30}.get(name, 15)
        ws.column_dimensions[get_column_letter(col_idx)].width = width
    ws.freeze_panes = "A2"
    return wb, ws


def _load(root):
    p = xlsx_path(root)
    if not os.path.exists(p):
        sys.exit(f"No tracker at {p}. Run: tracker.py init --root {root}")
    wb = load_workbook(p)
    ws = wb["applications"] if "applications" in wb.sheetnames else wb.active
    return wb, ws


def _rows_as_dicts(ws):
    rows = []
    for r in range(2, ws.max_row + 1):
        if all(ws.cell(row=r, column=c).value in (None, "") for c in range(1, len(COLUMNS) + 1)):
            continue
        d = {COLUMNS[c - 1]: (ws.cell(row=r, column=c).value or "") for c in range(1, len(COLUMNS) + 1)}
        d["_row"] = r
        rows.append(d)
    return rows


def _apply_row_style(ws, r, status):
    fill_hex = STATUS_FILL.get(status, None)
    locked = status in ("Applied",)
    for c in range(1, len(COLUMNS) + 1):
        cell = ws.cell(row=r, column=c)
        if fill_hex:
            cell.fill = PatternFill("solid", fgColor=fill_hex)
        else:
            cell.fill = PatternFill(fill_type=None)
        # every data cell unlocked by default; only applied rows locked.
        cell.protection = Protection(locked=locked)


def _reprotect(ws):
    # Unlock header + everything, then rows re-locked individually in _apply_row_style.
    # Enable sheet protection so locked cells are actually enforced.
    ws.protection.sheet = True
    ws.protection.enable()
    # allow the user to still select/sort; they just can't edit locked (applied) cells
    ws.protection.selectLockedCells = False
    ws.protection.selectUnlockedCells = False
    ws.protection.sort = False
    ws.protection.autoFilter = False


def _write_csv(ws, root):
    with open(csv_path(root), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for d in _rows_as_dicts(ws):
            w.writerow([d[c] for c in COLUMNS])


def _save(wb, ws, root):
    _reprotect(ws)
    wb.save(xlsx_path(root))
    _write_csv(ws, root)


def cmd_init(root):
    os.makedirs(root, exist_ok=True)
    if os.path.exists(xlsx_path(root)):
        print(f"Tracker already exists at {xlsx_path(root)} — leaving intact.")
        return
    wb, ws = _new_workbook()
    # header cells locked by default (fine); data rows added later control their own lock
    _save(wb, ws, root)
    print(f"Initialised tracker: {xlsx_path(root)} (+ csv mirror)")


def cmd_add(root, data):
    wb, ws = _load(root)
    data = dict(data)
    data.setdefault("logged_date", _today())
    data.setdefault("status", "Drafted")
    key = _normkey(data.get("folder_path", ""))
    if key:
        for d in _rows_as_dicts(ws):
            if _normkey(d["folder_path"]) == key:
                print(f"Row already exists for folder_path={data.get('folder_path')} (row {d['_row']}); use update.")
                return
    row = [data.get(col, "") for col in COLUMNS]
    ws.append(row)
    r = ws.max_row
    _apply_row_style(ws, r, data.get("status", "Drafted"))
    _save(wb, ws, root)
    print(f"Added row {r}: {data.get('company','?')} / {data.get('role','?')} [{data.get('status')}]")


def cmd_update(root, key, data):
    wb, ws = _load(root)
    target = None
    nk = _normkey(key)
    for d in _rows_as_dicts(ws):
        if _normkey(d["folder_path"]) == nk:
            target = d
            break
    if not target:
        sys.exit(f"No row with folder_path={key}")
    r = target["_row"]
    # guard: applied rows are final. Refuse silent overwrite unless --force via data.
    if str(target.get("status")) == "Applied" and data.get("status") not in (None, "Applied"):
        if not data.get("_force"):
            sys.exit(f"Row {r} is Applied (locked/final). Pass \"_force\": true in --data to override.")
    data = {k: v for k, v in data.items() if k != "_force"}
    for k, v in data.items():
        if k in COLUMNS:
            ws.cell(row=r, column=COLUMNS.index(k) + 1, value=v)
    new_status = data.get("status", target.get("status"))
    # auto-stamp the matching date column if a status implies one and it's empty
    date_col = STATUS_DATE.get(str(new_status))
    if date_col and not ws.cell(row=r, column=COLUMNS.index(date_col) + 1).value:
        ws.cell(row=r, column=COLUMNS.index(date_col) + 1, value=data.get(date_col, _today()))
    _apply_row_style(ws, r, str(new_status))
    _save(wb, ws, root)
    print(f"Updated row {r} -> status={new_status}")


def cmd_show(root):
    _, ws = _load(root)
    rows = _rows_as_dicts(ws)
    print(f"{len(rows)} row(s) in {xlsx_path(root)}")
    for d in rows:
        print(f"  [{d['status']:<11}] {d['category']:<20} {d['company']:<22} {d['role']}")


def main():
    ap = argparse.ArgumentParser(description="Application tracker (xlsx + csv).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("init", "add", "update", "show"):
        p = sub.add_parser(name)
        p.add_argument("--root", required=True, help="applications directory")
        if name in ("add", "update"):
            p.add_argument("--data", required=True, help="JSON object of column values")
        if name == "update":
            p.add_argument("--key", required=True, help="folder_path of the row to update")
    args = ap.parse_args()
    data = json.loads(args.data) if getattr(args, "data", None) else {}
    if args.cmd == "init":
        cmd_init(args.root)
    elif args.cmd == "add":
        cmd_add(args.root, data)
    elif args.cmd == "update":
        cmd_update(args.root, args.key, data)
    elif args.cmd == "show":
        cmd_show(args.root)


if __name__ == "__main__":
    main()
