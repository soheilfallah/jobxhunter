# Tools and connectors

Every external tool jobxhunter can use, what it is for, and what to do when it is missing. **Look at
the tools this surface really has** and route from that. Nothing here is required: each one has a
fallback, down to plain web search.

No API key ships with the plugin and none belongs in the repo, the workspace or a commit. The
step-by-step setup guides for users live in the workspace's `setup/` folder (templates in
`assets/workspace/setup/`).

## Tool names

Names are written bare here (`reed_search_jobs`). The prefix depends on the surface:

- **Claude Code, plugin install:** `mcp__plugin_jobxhunter_<server>__<tool>`, for example
  `mcp__plugin_jobxhunter_reed__reed_search_jobs`.
- **Claude Code, claude.ai connectors:** `mcp__claude_ai_Indeed__search_jobs`.
- **Claude Desktop / Cowork:** `<server>:<tool>`, for example `Indeed:search_jobs`.

Server names: `Indeed`, `Dice`, `reed`, `adzuna`, `firecrawl`. If a name does not resolve, list the
available tools and match on the server and tool pair. Never assume a connector exists.

## Job connectors

| Connector | Tools | Good for | Notes |
|---|---|---|---|
| **Indeed** | `search_jobs`, `get_job_details`, `get_company_data` | the broad workhorse, UK and Canada | Flat arguments named `search`, `location` and `country_code` (`GB` or `CA`). One page per query, no page or date argument. Its job ids and links change from call to call, so an id from an earlier search may not open in `get_job_details`. |
| **Reed** | `reed_search_jobs`, `reed_get_job_details` | UK agency, admin, data, security | distance in **miles**. A hidden salary is "Not disclosed", never £0. |
| **Adzuna** | `adzuna_search_jobs`, plus `adzuna_salary_histogram`, `adzuna_salary_history`, `adzuna_regional_breakdown`, `adzuna_top_companies` | wide aggregator and salary context, UK and Canada | `country` `gb` or `ca`. Distance in km. Salaries are annual. Returns a snippet only. |
| **Dice** | `search_jobs` | US-leaning software, data and AI | weak UK coverage. Flat arguments. |

**Reed and Adzuna wrap every argument in one `params` object, in `snake_case`:**

```
reed_search_jobs(params={"keywords": "data analyst", "location_name": "Leeds",
                         "distance_from_location": 20, "results_to_take": 100})
adzuna_search_jobs(params={"what": "data analyst", "where": "Leeds",
                           "country": "gb", "results_per_page": 50})
```

Flat arguments fail with `Field required [params]`; camelCase fails with `Extra inputs are not
permitted`. Retrying the same shape never helps. Indeed and Dice are the opposite: flat arguments,
no wrapper:

```
search_jobs(search="data analyst", location="Leeds", country_code="GB")
```

The Indeed argument is `search`, not `query`. When a call is rejected for its arguments, read the
tool's own schema before trying again.

## Getting the full advert

Never judge or tailor from a snippet.

1. Indeed `get_job_details`, Reed `reed_get_job_details` (also gives yearly salary and the apply link).
   If the detail tool errors, move straight down this list; do not give up on the advert.
2. Adzuna: fetch the result's `redirect_url`.
3. **Firecrawl** `firecrawl_scrape` for anything else: applicant-tracking pages, PDFs, employer
   sites. It renders JavaScript.
4. A plain fetch (`WebFetch`), or an installed scrape skill, for simple pages.
5. A signed-in browser, last, for login-walled pages.

If none of them returns the full text, the advert is `unread`.

## Testing a connector

A connector that is listed can still be rejecting its key. Test with one small real call:

| Connector | Call | Working means |
|---|---|---|
| Indeed | `search_jobs(search="analyst", location="London", country_code="GB")` | rows come back |
| Adzuna | `adzuna_search_jobs(params={"what": "analyst", "country": "gb", "results_per_page": 1})` | one row |
| Reed | `reed_search_jobs(params={"keywords": "analyst", "location_name": "London", "results_to_take": 1})` | one row |
| Firecrawl | `firecrawl_scrape` on `https://example.com` | page text |
| Web search | one search for `analyst jobs London` | results |

An auth error (401, "credentials rejected", "missing credentials") means **failing**. Report it by
name with the error text. A call blocked before it ran (a declined permission prompt) is **not
tested**, which is a third state and not a pass. Never continue as if the source had been searched.

Where two servers offer the same tool (a user's own Firecrawl beside the plugin's), either will do
for the work; prefer the plugin's own when testing. A skill counts under any prefix: `docx` and
`anthropic-skills:docx` are the same skill.

## Where keys live

1. The plugin's own options: `/plugin configure jobxhunter@soheil-jobxhunter`, or
   `claude plugin install jobxhunter@soheil-jobxhunter --config adzuna_app_id=... --config adzuna_app_key=...`.
   A key is read when a connector starts, so restart after setting one.
2. `~/.jobxhunter/.env`, read by the Reed and Adzuna connectors when the plugin options arrive
   empty. It sits outside the plugin, so it survives plugin updates.

When a user pastes a key in chat, register it with the `--config` form above and tell them to
restart. Do not echo the key back, and never write it into a file in the workspace or the plugin.

## Other tools

- **Outreach (`/jobxhunter:discover`):** Clay or RocketReach for finding a named contact (RocketReach
  lookups are paid; one confirmed target at a time), Gmail `create_draft` for the email.
- **Wording:** `references/writing-voice.md` is built in. The `humanizer` skill is used on top of it
  when installed.
- **Word files:** the bundled `scripts/render_docx.py` (run with `uv`), or the `docx` skill when the
  surface has it.
- **PDF:** only for a direct send to a person. The `.docx` is what goes to an ATS.

## By surface

- **Claude Code:** the bundled Reed, Adzuna and Firecrawl servers once their keys are set, plus any
  claude.ai connector on the account.
- **Cowork / Claude Desktop:** the bundled servers are local processes and do not run in its
  sandbox. Search with Indeed and Dice plus web search; render with the `docx` skill.
