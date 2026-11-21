# Connecting the job boards

jobxhunter searches through connectors. **Every one is optional.** With none, it still searches the
web; each connector you add makes the search wider and the adverts more complete.

Set them up in this order. Each guide takes a few minutes and all the keys are free.

| # | Connector | What it adds | Needs | Guide |
|---|---|---|---|---|
| 1 | **Indeed** | the biggest board for the UK and Canada, with full adverts | a click, no key | [`indeed.md`](indeed.md) |
| 2 | **Adzuna** | UK and Canada search plus salary data | free app id and key | [`adzuna.md`](adzuna.md) |
| 3 | **Firecrawl** | reads the full advert behind any link, including company career sites | free key | [`firecrawl.md`](firecrawl.md) |
| 4 | **Reed** | UK only, full adverts | free key | [`reed.md`](reed.md) |

You can do them yourself from the guides, or tell Claude "set up Adzuna" and it will walk you
through one step at a time.

## How keys are stored

Your keys are never written into your workspace, the plugin or any file that could be shared.

- **The normal way:** run `/plugin configure jobxhunter@soheil-jobxhunter` and paste the key into
  the matching field. Restart Claude Code. A key is only read when a connector starts.
- **If a connector still says the key is missing after a restart** (this happens on some setups):
  put the keys in a small file in your home folder instead. Create `~/.jobxhunter/.env` (on Windows,
  a folder named `.jobxhunter` inside your user folder) with the lines the guide gives you. That
  file survives plugin updates.

## Checking what works

`STATUS.md` in this folder is rewritten, with the date, every time you run `/jobxhunter:setup`. It
tests each connector with a real call, because a connector can be listed and still be rejecting its
key.

The test calls, for reference. They use a fixed city so they work before you have a profile: London
and `GB`, or Toronto and `CA` once `master-cvs/TARGETS.md` says the market is `ca`.

| Connector | Test call | Working means |
|---|---|---|
| Indeed | `search_jobs` with `search` `analyst`, `location` `London`, `country_code` `GB` | rows come back |
| Adzuna | `adzuna_search_jobs` with `params={"what": "analyst", "country": "gb", "results_per_page": 1}` | one row comes back |
| Reed | `reed_search_jobs` with `params={"keywords": "analyst", "location_name": "London", "results_to_take": 1}` | one row comes back |
| Firecrawl | `firecrawl_scrape` on `https://example.com` | page text comes back |
| Web search | one search for `analyst jobs London` | results come back |

Each connector ends up in one of four states: **working**, **failing** (with the error it gave),
**not tested** (the call was blocked before it ran, usually a permission prompt that was declined),
or **not set up** (the tool is not there).

## Optional extras

- **`humanizer` skill:** a final wording pass on every CV and letter. jobxhunter uses it when it is
  installed and works without it.
- **`docx` skill:** lets Claude build Word files directly and clone your own Word template. Without
  it, the bundled renderer makes the Word file.
- **`uv`:** the Reed and Adzuna connectors and the Word renderer run through it.
  Install from <https://docs.astral.sh/uv/>.
- **Node.js:** the Firecrawl connector runs through `npx`.
