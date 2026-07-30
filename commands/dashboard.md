---
description: Build a shareable HTML dashboard of your hunt — funnel, status, categories, recruiter scores — from the tracker.
argument-hint: "[optional: workspace or applications dir]"
---

Use the **jobxhunter** skill's **DASHBOARD** routine.

Resolve the workspace (explicit path → `JOBXHUNTER_DIR` → discovery; see `SKILL.md`). Run the
deterministic renderer against the tracker's CSV mirror and open the result:

```
python "$root/scripts/dashboard.py" --root "<applications_dir>" --out "<workspace>/dashboard.html"
```

`<applications_dir>` is the folder that holds `tracker.csv`. It writes **one self-contained HTML
file** — headline tiles, the apply→interview→offer funnel with conversion, status and category
breakdowns, and the recruiter-score spread — that opens offline and makes **no network requests**.
Bars are labelled, so meaning never rests on colour alone.

Your real data stays in the gitignored workspace; nothing is sent anywhere. Point a browser at the
file, or share the HTML itself. This routine is **read-only** over the tracker — it never edits an
application row.

Follow `SKILL.md` ("Command: DASHBOARD").
