# Your job-hunt workspace

Everything about your hunt lives in this folder. It is private: nothing here is uploaded, shared or
committed anywhere.

| Folder or file | What it is |
|---|---|
| `dump/` | Drop your old CVs, certificates, LinkedIn export and notes here. The raw material. |
| `profile.md` | Your one plain profile, written from `dump/` by `/jobxhunter:intake`. Correct it by hand any time. |
| `setup/` | Step-by-step guides for connecting each job board. `STATUS.md` shows what is working. |
| `master-cvs/` | One master CV per role you are going for, plus `TARGETS.md` (the roles and their search titles). |
| `jobs/` | One folder per day you searched, one folder per job inside it. `tracker.md` lists every advert seen. |
| `STATE.md` | Where things stand: last search, counts, the next step. |

## The order

1. `/jobxhunter:setup` made this folder.
2. Put your files in `dump/`, then run `/jobxhunter:intake`.
3. `/jobxhunter:masters` writes a master CV for each role. Read them and edit them: they are yours.
4. `/jobxhunter:search` finds jobs and evaluates each one. It does not write CVs.
5. Read `jobs/<date>/SHORTLIST.md`, then `/jobxhunter:tailor` the ones you want.

## Inside a job folder

```
jobs/<date>/<Company> - <Role>/
  job-description.md    the full advert
  evaluation.md         why it was kept, what it asks, what you can show, the gaps
  notes.md              your own notes
  CV/                   <Your Name> - CV.docx, and the cover letter if you ask for one
```
