# adzuna-mcp

A local stdio MCP server wrapping the [Adzuna API](https://developer.adzuna.com/). Built to sit
alongside a listings source like Indeed: Indeed finds ads, Adzuna adds the **salary and market
data that listings boards don't expose** — distributions, trends, regional vacancy counts and
employer leaderboards.

## Tools

| Tool | What it gives you |
|---|---|
| `adzuna_search_jobs` | Job ads with salary range, contract type, category, `redirect_url` |
| `adzuna_list_categories` | Valid `category` tags (call before filtering by category) |
| `adzuna_salary_histogram` | Salary distribution for a role/location — is £45k ambitious or low? |
| `adzuna_salary_history` | Month-by-month average salary trend |
| `adzuna_regional_breakdown` | Vacancy counts by sub-region; also how you discover `location0/1/2` values |
| `adzuna_top_companies` | Top 5 employers by vacancy count + their average salary |
| `adzuna_estimate_salary` | Predicted salary for a title + description (Adzuna Jobsworth) — price a role that states no salary |

All tools are read-only and take `country` (default `gb`) and `response_format`
(`markdown` for compact reading, `json` for programmatic use).

## Using it with `/cv-tailor`

The intended loop when tailoring a CV to a target role:

1. **Find live ads.** `adzuna_search_jobs` with `what_phrase` (exact role), `where` + `distance`,
   and `max_days_old` to skip stale posts. Sort fresh-first with `sort_by=date`.
   ```
   adzuna_search_jobs(what_phrase="audio visual technician", where="london",
                      distance=20, max_days_old=30, sort_by="date")
   ```
2. **Read the full JD.** Each result gives only a snippet — fetch its `redirect_url` for the
   complete description, then feed that into `/cv-tailor` as the job spec.
   > **Heads-up:** Adzuna's `…/jobs/details/<id>` page is JavaScript-rendered, so a plain HTTP
   > fetch returns an empty shell. Read it with a JS-capable fetch (Claude-in-Chrome), or follow
   > the `…/jobs/land/ad/<id>` redirect variant, which forwards to the employer's ATS where the
   > full JD is usually server-rendered. This is Adzuna's frontend behaviour, not a server bug.
3. **Price a role with no stated salary.** Many ads omit pay. `adzuna_estimate_salary(title, description)`
   returns Adzuna's predicted figure so you can set expectations before applying.
4. **Sanity-check your target £.** `adzuna_salary_histogram(what=...)` shows where a figure sits
   in the live market; `adzuna_salary_history` shows whether pay is trending up or down.
5. **Build an outreach list.** `adzuna_top_companies(what=...)` surfaces who is hiring at volume
   for the role — feed a `canonical_name` back into `adzuna_search_jobs` `company` to see their ads.

Cowork/`​/cv-tailor` sessions read and write files under `C:\Users\flhso\Claude`
(`coworkUserFilesPath`), so drop JDs and CV drafts there to keep them in view.

## The one real limitation

**Adzuna returns only a snippet of each job description.** Every search result carries a
`redirect_url`. To get a full JD you fetch that URL yourself. This is why the pairing with a
crawler matters: Adzuna is a fast, filterable, salary-aware *index*; the full text lives behind
the redirect.

## Setup

1. Register at <https://developer.adzuna.com/signup> for a free `app_id` / `app_key`.
   (Note: this is a **separate account** from a normal adzuna.co.uk jobseeker login.)
2. Install:

```bash
cd adzuna-mcp
uv venv && uv pip install mcp httpx python-dotenv
# or: python -m venv .venv && .venv/bin/pip install mcp httpx python-dotenv
```

For local runs (and the mcp-inspector verify step below), copy `.env.example` to
`.env` and fill in your `app_id` / `app_key` — `server.py` loads it automatically.
Real env vars still win over `.env`, so the `.mcp.json` `env` block below keeps working.

3. Wire it into Claude Code — `.mcp.json` in your project, or `claude mcp add`:

```json
{
  "mcpServers": {
    "adzuna": {
      "command": "python",
      "args": ["D:\\soh-workspace\\projects\\adzuna-mcp\\server.py"],
      "env": {
        "ADZUNA_APP_ID": "your_app_id",
        "ADZUNA_APP_KEY": "your_app_key"
      }
    }
  }
}
```

Use the absolute path to the venv's python (`.venv\Scripts\python.exe` on Windows) if the
dependencies aren't on your global interpreter.

4. Verify before wiring it up:

```bash
npx @modelcontextprotocol/inspector python server.py
```

## Country support

`gb` `us` `at` `au` `br` `ca` `de` `fr` `in` `nz` `pl` `za` — annual salaries, local currency.
The server accepts any two-letter code and lets Adzuna's 404 tell you if one isn't served, so
the list staying accurate isn't a hard dependency.

## Rate limits

Adzuna's default free/trial limits (per their Terms of Service) are **25 hits/min, 250/day,
1000/week, 2500/month**. The server surfaces a 429 with a clear message. Prefer fewer, wider
queries over many narrow ones; `adzuna_salary_histogram` answers "what does this pay?" in one
call where a paginated search would take several.

Trial-tier data also can't be republished or aggregated into ongoing work beyond the 14-day
evaluation without a licence — fine for personal jobsmith research, worth knowing before you
build anything public on it.

## Notes

- **Keyword semantics matter.** `what` ANDs its words — every word must appear, so
  `what="plant science research assistant agronomist"` matches almost nothing. Use `what_or` to
  match ANY of several terms in one call, `what_phrase` for an exact phrase, or `title_only` to
  restrict to the job title. There is no cross-field OR, so for genuinely different role titles run
  one search per variant (or list them in a single `what_or`).
- `location0/1/2` are exact strings, not free text. Get them from `adzuna_regional_breakdown` —
  the `area` array on each result is literally the values to pass back in.
- `where="United Kingdom"` narrows to almost nothing — use a city + `distance`, or omit `where` and
  rely on `location0/1/2`.
- `where` + `distance` is the free-text alternative and is usually easier.
- `salary_is_predicted: 1` means Adzuna estimated the figure; the ad didn't state it. Don't quote
  predicted numbers as if the employer published them.
- Not implemented: `version`. A small addition if wanted.
