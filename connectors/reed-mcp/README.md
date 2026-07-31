# reed-mcp

A local stdio MCP server wrapping the [Reed.co.uk Jobseeker API](https://www.reed.co.uk/developers/jobseeker).
Reed is one of the UK's largest job boards. This server sits alongside a salary/market-data
source (Adzuna) and other listing boards (Indeed, Dice): Reed contributes its own live vacancy
index and, unlike a plain search, gives you the **full job description on demand**.

## Tools

| Tool | What it gives you |
|---|---|
| `reed_search_jobs` | Job ads with a short description, employer, location, advertised GBP salary, `jobId` |
| `reed_get_job_details` | The FULL description for one `jobId` + normalised yearly salary, salary type, contract type and the external application URL |

Both tools are read-only and take `response_format` (`markdown` for compact reading, `json` for
programmatic use). All salaries are GBP.

## Two things that bite

- **Distance is in MILES, not km.** `distance_from_location=20` means a 20-mile radius. (Adzuna's
  equivalent is km — don't copy a km number across.) Reed defaults to 10 miles when omitted.
- **Salary can be hidden by the employer, and absent is NOT zero.** A withheld salary comes back
  as `null` and both tools render it as `Not disclosed` — never as £0. Filtering by
  `minimum_salary`/`maximum_salary` also drops ads whose salary was hidden.

## Search → details workflow

`reed_search_jobs` returns only a short snippet per ad. Fetch the full text before tailoring a CV:

```
reed_search_jobs(keywords="audio visual technician", location_name="London",
                 distance_from_location=20, full_time=True)
# -> pick a jobId from the results
reed_get_job_details(job_id=12345678)
# -> full description + yearly salary + contract type + application URL
```

## Auth

Reed uses **HTTP Basic auth**: the API key is the **username** and the **password is empty**.
The server does this for you — you only supply the key.

Get a free key at <https://www.reed.co.uk/developers/jobseeker>. Set it as `REED_API_KEY` in the
MCP server env (or copy `.env.example` to `.env` and fill it in — `server.py` loads it
automatically; a real env var still wins over the file).

## Setup

```bash
cd reed-mcp
python -m venv .venv && .venv/Scripts/python -m pip install mcp httpx python-dotenv
# or: uv venv && uv pip install mcp httpx python-dotenv
```

Wire it into Claude Code — `.mcp.json` in your project, `claude mcp add`, or the user-scope
config:

```json
{
  "mcpServers": {
    "reed": {
      "command": "C:\\path\\to\\reed-mcp\\.venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\reed-mcp\\server.py"],
      "env": {
        "REED_API_KEY": "your_key"
      }
    }
  }
}
```

Use the absolute path to the venv's `python.exe` so the `mcp`/`httpx` dependencies resolve.

Verify before wiring it up:

```bash
npx @modelcontextprotocol/inspector .venv/Scripts/python.exe server.py
```

## Rate limits

Reed's Jobseeker API is rate limited per key. The server surfaces a 429 with a clear message.
Prefer fewer, wider searches over many narrow ones, and only call `reed_get_job_details` for the
ads you actually intend to read.
