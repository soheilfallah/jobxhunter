"""Adzuna MCP server.

Exposes Adzuna's job-search and labour-market-intelligence endpoints as MCP tools.
Complements listing-only sources (Indeed, Dice) by adding salary distributions,
regional vacancy counts and employer leaderboards.

Auth: set ADZUNA_APP_ID and ADZUNA_APP_KEY (free key from developer.adzuna.com/signup).
Transport: stdio.
"""

import json
import os
import re
from enum import Enum
from typing import Any, Optional

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

# Load a local .env if present so `python server.py` (and the mcp-inspector verify
# step) pick up credentials without exporting them by hand. override=False keeps
# any real env vars — e.g. the .mcp.json `env` block — winning over the file.
# Optional dependency: if python-dotenv isn't installed, fall back to env vars only.
try:
    from dotenv import load_dotenv

    load_dotenv(override=False)
except ModuleNotFoundError:
    pass

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

BASE_URL = "https://api.adzuna.com/v1/api"
TIMEOUT = 30.0
MAX_RESULTS_PER_PAGE = 50

# Countries Adzuna serves. Codes are ISO 3166-1 alpha-2, lowercase in the path.
SUPPORTED_COUNTRIES = {
    "gb": "United Kingdom (GBP)",
    "us": "United States (USD)",
    "at": "Austria (EUR)",
    "au": "Australia (AUD)",
    "br": "Brazil (BRL)",
    "ca": "Canada (CAD)",
    "de": "Germany (EUR)",
    "fr": "France (EUR)",
    "in": "India (INR)",
    "nz": "New Zealand (NZD)",
    "pl": "Poland (PLN)",
    "za": "South Africa (ZAR)",
}

COUNTRY_HELP = ", ".join(f"'{k}'" for k in SUPPORTED_COUNTRIES)

mcp = FastMCP(
    "adzuna_mcp",
    instructions=f"""Adzuna job search and labour market data.

Supported countries: {COUNTRY_HELP}. Default is 'gb'.
All salaries are ANNUAL figures in the country's local currency.

IMPORTANT: adzuna_search_jobs returns only a SNIPPET of each job description.
For the full text, fetch the `redirect_url` on the result.

Suggested workflows:
- Find roles:      adzuna_list_categories -> adzuna_search_jobs -> fetch redirect_url
- Salary research: adzuna_salary_histogram + adzuna_salary_history
- Where to target: adzuna_regional_breakdown
- Who is hiring:   adzuna_top_companies
""",
)


# --------------------------------------------------------------------------
# Shared infrastructure
# --------------------------------------------------------------------------


class ResponseFormat(str, Enum):
    """Output format for tool responses."""

    MARKDOWN = "markdown"
    JSON = "json"


class SortBy(str, Enum):
    """Ordering for job search results.

    Adzuna's live API rejects 'default' and 'hybrid' with a 400, so only the
    three values it actually accepts are exposed.
    """

    DATE = "date"
    SALARY = "salary"
    RELEVANCE = "relevance"


class SortDirection(str, Enum):
    """Ascending or descending sort."""

    UP = "up"
    DOWN = "down"


COUNTRY_FIELD = Field(
    default="gb",
    description=f"Lowercase ISO country code. Supported: {COUNTRY_HELP}.",
    pattern=r"^[a-z]{2}$",
)

FORMAT_FIELD = Field(
    default=ResponseFormat.MARKDOWN,
    description="'markdown' for a compact human-readable summary, 'json' for full structured data.",
)


def _credentials() -> dict[str, str]:
    """Read API credentials from the environment.

    Raises:
        RuntimeError: If either credential is missing.
    """
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        raise RuntimeError(
            "Missing credentials. Set ADZUNA_APP_ID and ADZUNA_APP_KEY in the MCP "
            "server env. Get a free pair at https://developer.adzuna.com/signup"
        )
    return {"app_id": app_id, "app_key": app_key}


def _clean(params: dict[str, Any]) -> dict[str, Any]:
    """Drop None values and coerce bools to Adzuna's 1/absent convention."""
    out: dict[str, Any] = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, bool):
            if value:
                out[key] = 1
            continue
        if isinstance(value, Enum):
            value = value.value
        out[key] = value
    return out


# Adzuna auth travels in the URL query string (app_id/app_key). An exception or an
# upstream error body can echo that credential-bearing URL back — scrub it so keys
# never reach the agent transcript or logs.
_CRED_RE = re.compile(r"(app_id|app_key)=[^&\s]+", re.IGNORECASE)


def _handle_api_error(exc: Exception) -> str:
    """Build the actionable message, then redact any leaked credentials."""
    return _CRED_RE.sub(r"\1=REDACTED", _api_error_message(exc))


def _api_error_message(exc: Exception) -> str:
    """Turn an exception into an actionable message for the agent."""
    if isinstance(exc, RuntimeError):
        return f"Error: {exc}"
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        body = exc.response.text[:300]
        if code == 401:
            return (
                "Error: Adzuna rejected the credentials (401). Check ADZUNA_APP_ID and "
                "ADZUNA_APP_KEY are the pair shown on your app at developer.adzuna.com."
            )
        if code == 404:
            return (
                f"Error: Endpoint or country not found (404). Supported countries: "
                f"{COUNTRY_HELP}. Response: {body}"
            )
        if code == 429:
            return (
                "Error: Rate limit exceeded (429). Adzuna's free tier has a daily call "
                "cap — wait, or widen each query so you need fewer calls."
            )
        return f"Error: Adzuna returned HTTP {code}. Response: {body}"
    if isinstance(exc, httpx.TimeoutException):
        return f"Error: Request to Adzuna timed out after {TIMEOUT}s. Try again."
    if isinstance(exc, httpx.RequestError):
        return f"Error: Could not reach Adzuna: {exc}"
    return f"Error: Unexpected {type(exc).__name__}: {exc}"


async def _get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    """GET a JSON payload from the Adzuna API.

    Args:
        path: Path below the API root, e.g. 'jobs/gb/search/1'.
        params: Query parameters; None values are dropped.

    Returns:
        The decoded JSON body.
    """
    query = {**_credentials(), **_clean(params), "content-type": "application/json"}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(f"{BASE_URL}/{path}", params=query)
        response.raise_for_status()
        return response.json()


def _strip(obj: Any) -> Any:
    """Recursively remove Adzuna's __CLASS__ noise to save agent context."""
    if isinstance(obj, dict):
        return {k: _strip(v) for k, v in obj.items() if k != "__CLASS__"}
    if isinstance(obj, list):
        return [_strip(item) for item in obj]
    return obj


def _as_json(data: Any) -> str:
    return json.dumps(_strip(data), indent=2, ensure_ascii=False)


def _money(value: Any) -> str:
    """Format a salary figure, or '?' when absent."""
    if value in (None, ""):
        return "?"
    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return str(value)


def _pairs_to_markdown(mapping: dict[str, Any], key_header: str, value_header: str, title: str) -> str:
    """Render a flat {key: value} object as a sorted markdown table."""
    if not mapping:
        return f"# {title}\n\nNo data returned for this query."
    rows = sorted(mapping.items(), key=lambda kv: kv[0])
    lines = [f"# {title}", "", f"| {key_header} | {value_header} |", "|---|---|"]
    lines += [f"| {k} | {_money(v)} |" for k, v in rows]
    return "\n".join(lines)


def _render(data: Any, fmt: ResponseFormat, markdown_fn) -> str:
    """Return either raw JSON or a markdown view of the payload."""
    if fmt is ResponseFormat.JSON:
        return _as_json(data)
    return markdown_fn(_strip(data))


# --------------------------------------------------------------------------
# Tool: search jobs
# --------------------------------------------------------------------------


class SearchJobsInput(BaseModel):
    """Input model for the job search endpoint."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    country: str = COUNTRY_FIELD
    what: Optional[str] = Field(
        default=None,
        description="Keywords; Adzuna ANDs multiple words, so ALL must appear (e.g. 'data scientist' "
        "requires both words). For OR semantics use `what_or`; for an exact phrase use `what_phrase`.",
    )
    what_or: Optional[str] = Field(
        default=None,
        description="Keywords, ANY of which may match — an ad is returned if it contains at least one "
        "(e.g. 'agronomist horticulturist'). Use this to search title variants in a single call.",
    )
    what_and: Optional[str] = Field(
        default=None,
        description="Keywords that must ALL appear. Same effect as space-separating words in `what`; "
        "use it when you want the AND intent to be explicit.",
    )
    what_phrase: Optional[str] = Field(
        default=None,
        description="Exact phrase that must appear (e.g. 'controlled environment agriculture').",
    )
    what_exclude: Optional[str] = Field(
        default=None,
        description="Keywords to exclude; any match drops the ad (e.g. 'security guard').",
    )
    title_only: Optional[str] = Field(
        default=None, description="Keywords that must appear in the job TITLE only."
    )
    where: Optional[str] = Field(
        default=None, description="Free-text location (e.g. 'london', 'wembley', 'remote')."
    )
    distance: Optional[int] = Field(
        default=None, description="Radius in km around `where`. Adzuna defaults to 5.", ge=0, le=500
    )
    location0: Optional[str] = Field(
        default=None,
        description="Top-level area for a precise location filter (e.g. 'UK'). Use adzuna_regional_breakdown to discover valid values.",
    )
    location1: Optional[str] = Field(default=None, description="Second-level area (e.g. 'London').")
    location2: Optional[str] = Field(
        default=None, description="Third-level area (e.g. 'Central London')."
    )
    category: Optional[str] = Field(
        default=None,
        description="Category tag from adzuna_list_categories (e.g. 'it-jobs', 'scientific-qa-jobs').",
    )
    company: Optional[str] = Field(
        default=None, description="Canonical employer name to filter by (e.g. 'NHS')."
    )
    salary_min: Optional[int] = Field(
        default=None, description="Minimum ANNUAL salary in local currency.", ge=0
    )
    salary_max: Optional[int] = Field(
        default=None, description="Maximum ANNUAL salary in local currency.", ge=0
    )
    salary_include_unknown: Optional[bool] = Field(
        default=None,
        description="True to keep ads with no stated salary when filtering by salary.",
    )
    full_time: Optional[bool] = Field(default=None, description="True to restrict to full-time.")
    part_time: Optional[bool] = Field(default=None, description="True to restrict to part-time.")
    permanent: Optional[bool] = Field(default=None, description="True to restrict to permanent.")
    contract: Optional[bool] = Field(default=None, description="True to restrict to contract.")
    max_days_old: Optional[int] = Field(
        default=None, description="Only ads posted within this many days.", ge=1, le=365
    )
    sort_by: Optional[SortBy] = Field(
        default=None, description="Ordering: date, salary or relevance."
    )
    sort_direction: Optional[SortDirection] = Field(
        default=None, description="'up' or 'down'. Pair with sort_by (e.g. sort_by=salary, sort_direction=down)."
    )
    page: int = Field(default=1, description="Result page, 1-indexed.", ge=1)
    results_per_page: int = Field(
        default=20, description="Ads per page (1-50).", ge=1, le=MAX_RESULTS_PER_PAGE
    )
    response_format: ResponseFormat = FORMAT_FIELD


def _search_markdown(data: dict[str, Any]) -> str:
    results = data.get("results", [])
    total = data.get("count", "unknown")
    mean = data.get("mean")
    header = [f"# Adzuna job results ({len(results)} shown, {total} total)"]
    if mean:
        header.append(f"\nMean salary across all matches: {_money(mean)}")
    if not results:
        header.append("\nNo ads matched. Try fewer keywords, a wider `distance`, or drop `salary_min`.")
        return "\n".join(header)

    blocks = []
    for job in results:
        loc = (job.get("location") or {}).get("display_name", "?")
        company = (job.get("company") or {}).get("display_name", "?")
        cat = (job.get("category") or {}).get("label", "?")
        salary = f"{_money(job.get('salary_min'))} - {_money(job.get('salary_max'))}"
        if job.get("salary_is_predicted") in (1, "1"):
            salary += " (predicted, not stated in ad)"
        contract = " / ".join(
            v for v in (job.get("contract_time"), job.get("contract_type")) if v
        )
        desc = (job.get("description") or "").strip().replace("\n", " ")
        blocks.append(
            "\n".join(
                [
                    f"## {job.get('title', 'Untitled')}",
                    f"- **Company:** {company}",
                    f"- **Location:** {loc}",
                    f"- **Salary:** {salary}",
                    f"- **Contract:** {contract or '?'}",
                    f"- **Category:** {cat}",
                    f"- **Posted:** {job.get('created', '?')}",
                    f"- **Adzuna ID:** {job.get('id', '?')}",
                    f"- **Full ad (fetch for complete description):** {job.get('redirect_url', '?')}",
                    "",
                    f"> {desc}",
                ]
            )
        )
    footer = (
        "\n---\nDescriptions above are SNIPPETS only. Fetch each `redirect_url` "
        "for the full job description."
    )
    return "\n".join(header) + "\n\n" + "\n\n".join(blocks) + footer


@mcp.tool(
    name="adzuna_search_jobs",
    annotations={
        "title": "Search Adzuna job ads",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def adzuna_search_jobs(params: SearchJobsInput) -> str:
    """Search Adzuna's job advertisement database with keyword, location, salary and contract filters.

    Returns ads including title, employer, location, salary range (annual, local currency),
    contract type, category, posting date and a `redirect_url`. Adzuna only returns a
    SNIPPET of each description — fetch the `redirect_url` to read the full ad.

    Args:
        params (SearchJobsInput): Validated search parameters. Key fields:
            - country (str): ISO code, default 'gb'
            - what / what_or / what_and / what_phrase / what_exclude / title_only (Optional[str]): keyword filters
            - where (Optional[str]) + distance (Optional[int]): free-text location and radius in km
            - location0/1/2 (Optional[str]): hierarchical location filter
            - category (Optional[str]): tag from adzuna_list_categories
            - salary_min / salary_max (Optional[int]): annual salary bounds
            - full_time / part_time / permanent / contract (Optional[bool]): contract filters
            - max_days_old (Optional[int]), sort_by (Optional[SortBy]), page, results_per_page
            - response_format (ResponseFormat): 'markdown' or 'json'

    Returns:
        str: Markdown summary of matching ads, or JSON with keys `count` (int, total matches),
            `mean` (float, mean salary) and `results` (list of job objects each containing
            id, title, description, created, redirect_url, salary_min, salary_max,
            salary_is_predicted, contract_type, contract_time, latitude, longitude,
            company{display_name}, location{display_name, area[]}, category{label, tag}).
            On failure, an 'Error: ...' string explaining the cause.
    """
    try:
        payload = params.model_dump(exclude={"country", "page", "response_format"})
        data = await _get(f"jobs/{params.country}/search/{params.page}", payload)
        return _render(data, params.response_format, _search_markdown)
    except Exception as exc:  # noqa: BLE001 - surfaced as an actionable message
        return _handle_api_error(exc)


# --------------------------------------------------------------------------
# Tool: categories
# --------------------------------------------------------------------------


class CategoriesInput(BaseModel):
    """Input model for the categories endpoint."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    country: str = COUNTRY_FIELD
    response_format: ResponseFormat = FORMAT_FIELD


def _categories_markdown(data: dict[str, Any]) -> str:
    results = data.get("results", [])
    lines = ["# Adzuna job categories", "", "| Tag (use as `category`) | Label |", "|---|---|"]
    lines += [f"| `{c.get('tag')}` | {c.get('label')} |" for c in results]
    return "\n".join(lines)


@mcp.tool(
    name="adzuna_list_categories",
    annotations={
        "title": "List Adzuna job categories",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def adzuna_list_categories(params: CategoriesInput) -> str:
    """List the job categories Adzuna applies in a given country.

    Call this before using the `category` filter on other tools — tags are
    country-specific and must match exactly (e.g. 'it-jobs', 'scientific-qa-jobs').

    Args:
        params (CategoriesInput): Validated parameters containing:
            - country (str): ISO code, default 'gb'
            - response_format (ResponseFormat): 'markdown' or 'json'

    Returns:
        str: Markdown table of tag/label pairs, or JSON with key `results`
            (list of objects with `tag` (str) and `label` (str)).
            On failure, an 'Error: ...' string explaining the cause.
    """
    try:
        data = await _get(f"jobs/{params.country}/categories", {})
        return _render(data, params.response_format, _categories_markdown)
    except Exception as exc:  # noqa: BLE001
        return _handle_api_error(exc)


# --------------------------------------------------------------------------
# Tool: salary histogram
# --------------------------------------------------------------------------


class HistogramInput(BaseModel):
    """Input model for the salary histogram endpoint."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    country: str = COUNTRY_FIELD
    what: Optional[str] = Field(
        default=None, description="Keywords describing the role (e.g. 'data scientist')."
    )
    location0: Optional[str] = Field(default=None, description="Top-level area (e.g. 'UK').")
    location1: Optional[str] = Field(default=None, description="Second-level area (e.g. 'London').")
    location2: Optional[str] = Field(default=None, description="Third-level area.")
    category: Optional[str] = Field(
        default=None, description="Category tag from adzuna_list_categories."
    )
    response_format: ResponseFormat = FORMAT_FIELD


@mcp.tool(
    name="adzuna_salary_histogram",
    annotations={
        "title": "Get salary distribution",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def adzuna_salary_histogram(params: HistogramInput) -> str:
    """Get the current distribution of advertised salaries for a role and/or location.

    Each key is the LOWER bound of an annual salary band in local currency; each value is
    the number of live vacancies in that band. Use it to sanity-check a salary expectation
    or to see where a target figure sits in the market.

    Args:
        params (HistogramInput): Validated parameters containing:
            - country (str): ISO code, default 'gb'
            - what (Optional[str]): role keywords
            - location0/1/2 (Optional[str]): hierarchical location filter
            - category (Optional[str]): category tag
            - response_format (ResponseFormat): 'markdown' or 'json'

    Returns:
        str: Markdown table of salary band vs vacancy count, or JSON with key
            `histogram` (dict mapping salary-band lower bound (str) to vacancy count).
            Band order is not guaranteed by the API; this tool sorts it.
            On failure, an 'Error: ...' string explaining the cause.
    """
    try:
        payload = params.model_dump(exclude={"country", "response_format"})
        data = await _get(f"jobs/{params.country}/histogram", payload)
        return _render(
            data,
            params.response_format,
            lambda d: _pairs_to_markdown(
                d.get("histogram", {}), "Salary band (from)", "Vacancies", "Salary distribution"
            ),
        )
    except Exception as exc:  # noqa: BLE001
        return _handle_api_error(exc)


# --------------------------------------------------------------------------
# Tool: salary history
# --------------------------------------------------------------------------


class HistoryInput(BaseModel):
    """Input model for the historical salary endpoint."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    country: str = COUNTRY_FIELD
    what: Optional[str] = Field(default=None, description="Keywords describing the role.")
    location0: Optional[str] = Field(default=None, description="Top-level area (e.g. 'UK').")
    location1: Optional[str] = Field(default=None, description="Second-level area (e.g. 'London').")
    location2: Optional[str] = Field(default=None, description="Third-level area.")
    category: Optional[str] = Field(
        default=None, description="Category tag from adzuna_list_categories."
    )
    months: Optional[int] = Field(
        default=None, description="Number of months of history to return.", ge=1, le=60
    )
    response_format: ResponseFormat = FORMAT_FIELD


@mcp.tool(
    name="adzuna_salary_history",
    annotations={
        "title": "Get historical average salary",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def adzuna_salary_history(params: HistoryInput) -> str:
    """Get the average advertised salary month by month for a role, category and/or location.

    Shows whether pay for a role is trending up or down over time.

    Args:
        params (HistoryInput): Validated parameters containing:
            - country (str): ISO code, default 'gb'
            - what (Optional[str]): role keywords
            - location0/1/2 (Optional[str]): hierarchical location filter
            - category (Optional[str]): category tag
            - months (Optional[int]): months of history to return
            - response_format (ResponseFormat): 'markdown' or 'json'

    Returns:
        str: Markdown table of month vs average salary, or JSON with key `month`
            (dict mapping 'YYYY-MM' (str) to average annual salary (float)).
            Month order is not guaranteed by the API; this tool sorts it.
            On failure, an 'Error: ...' string explaining the cause.
    """
    try:
        payload = params.model_dump(exclude={"country", "response_format"})
        data = await _get(f"jobs/{params.country}/history", payload)
        return _render(
            data,
            params.response_format,
            lambda d: _pairs_to_markdown(
                d.get("month", {}), "Month", "Average salary", "Historical average salary"
            ),
        )
    except Exception as exc:  # noqa: BLE001
        return _handle_api_error(exc)


# --------------------------------------------------------------------------
# Tool: regional breakdown
# --------------------------------------------------------------------------


class GeodataInput(BaseModel):
    """Input model for the regional vacancy endpoint."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    country: str = COUNTRY_FIELD
    location0: Optional[str] = Field(
        default=None, description="Top-level area whose children to list (e.g. 'UK')."
    )
    location1: Optional[str] = Field(
        default=None, description="Second-level area (e.g. 'South East England')."
    )
    location2: Optional[str] = Field(default=None, description="Third-level area.")
    category: Optional[str] = Field(
        default=None, description="Category tag to limit the counts to one job category."
    )
    response_format: ResponseFormat = FORMAT_FIELD


def _geodata_markdown(data: dict[str, Any]) -> str:
    locations = data.get("locations", [])
    if not locations:
        return "# Regional vacancies\n\nNo sub-regions returned. Check the location0/location1 values."
    rows = sorted(locations, key=lambda item: item.get("count", 0), reverse=True)
    lines = [
        "# Regional vacancies",
        "",
        "| Location | Vacancies | Area path (use for location0/1/2) |",
        "|---|---|---|",
    ]
    for item in rows:
        loc = item.get("location") or {}
        area = " > ".join(loc.get("area", []))
        lines.append(f"| {loc.get('display_name', '?')} | {item.get('count', '?')} | {area} |")
    lines.append(
        "\nThe `area` path elements are exactly the values to pass as location0, location1, location2."
    )
    return "\n".join(lines)


@mcp.tool(
    name="adzuna_regional_breakdown",
    annotations={
        "title": "Get vacancy counts by region",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def adzuna_regional_breakdown(params: GeodataInput) -> str:
    """Get the number of live vacancies in the sub-regions of a location.

    Doubles as the discovery tool for location filters: the `area` array on each result
    holds the exact strings to pass as location0/location1/location2 elsewhere.
    Call with no location to see a country's top-level regions.

    Args:
        params (GeodataInput): Validated parameters containing:
            - country (str): ISO code, default 'gb'
            - location0/1/2 (Optional[str]): area whose children to list
            - category (Optional[str]): category tag to limit counts
            - response_format (ResponseFormat): 'markdown' or 'json'

    Returns:
        str: Markdown table of sub-region, vacancy count and area path, or JSON with key
            `locations` (list of objects with `count` (int) and
            `location` {`display_name` (str), `area` (list[str])}).
            On failure, an 'Error: ...' string explaining the cause.
    """
    try:
        payload = params.model_dump(exclude={"country", "response_format"})
        data = await _get(f"jobs/{params.country}/geodata", payload)
        return _render(data, params.response_format, _geodata_markdown)
    except Exception as exc:  # noqa: BLE001
        return _handle_api_error(exc)


# --------------------------------------------------------------------------
# Tool: top companies
# --------------------------------------------------------------------------


class TopCompaniesInput(BaseModel):
    """Input model for the top companies endpoint."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    country: str = COUNTRY_FIELD
    what: Optional[str] = Field(
        default=None, description="Keywords describing the role (e.g. 'research assistant')."
    )
    location0: Optional[str] = Field(default=None, description="Top-level area (e.g. 'UK').")
    location1: Optional[str] = Field(default=None, description="Second-level area (e.g. 'London').")
    location2: Optional[str] = Field(default=None, description="Third-level area.")
    category: Optional[str] = Field(
        default=None, description="Category tag from adzuna_list_categories."
    )
    response_format: ResponseFormat = FORMAT_FIELD


def _companies_markdown(data: dict[str, Any]) -> str:
    board = data.get("leaderboard", [])
    if not board:
        return "# Top employers\n\nNo employers returned for this query."
    lines = ["# Top employers by open vacancies", "", "| Employer | Vacancies | Average salary |", "|---|---|---|"]
    for company in board:
        lines.append(
            f"| {company.get('canonical_name', '?')} | {company.get('count', '?')} "
            f"| {_money(company.get('average_salary'))} |"
        )
    return "\n".join(lines)


@mcp.tool(
    name="adzuna_top_companies",
    annotations={
        "title": "Get top hiring employers",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def adzuna_top_companies(params: TopCompaniesInput) -> str:
    """Get a leaderboard of the employers with the most open vacancies for a search.

    Useful for building a cold-outreach target list: it surfaces who is hiring at volume
    for a role and roughly what they pay, which a plain job search does not.

    Args:
        params (TopCompaniesInput): Validated parameters containing:
            - country (str): ISO code, default 'gb'
            - what (Optional[str]): role keywords
            - location0/1/2 (Optional[str]): hierarchical location filter
            - category (Optional[str]): category tag
            - response_format (ResponseFormat): 'markdown' or 'json'

    Returns:
        str: Markdown table of employer, vacancy count and average salary, or JSON with key
            `leaderboard` (list of objects with `canonical_name` (str), `count` (int) and
            `average_salary` (float)). Feed `canonical_name` back into
            adzuna_search_jobs `company` to list that employer's ads.
            On failure, an 'Error: ...' string explaining the cause.
    """
    try:
        payload = params.model_dump(exclude={"country", "response_format"})
        data = await _get(f"jobs/{params.country}/top_companies", payload)
        return _render(data, params.response_format, _companies_markdown)
    except Exception as exc:  # noqa: BLE001
        return _handle_api_error(exc)


# --------------------------------------------------------------------------
# Tool: jobsworth salary estimate
# --------------------------------------------------------------------------


class JobsworthInput(BaseModel):
    """Input model for the Jobsworth salary-predictor endpoint."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    country: str = COUNTRY_FIELD
    title: str = Field(
        description="The job title to estimate a salary for (e.g. 'Javascript developer')."
    )
    description: str = Field(
        description="Descriptive text about the role — skills, seniority, responsibilities "
        "(e.g. 'Backbone, HTML5, CSS3'). The full job-ad body works well.",
    )
    response_format: ResponseFormat = FORMAT_FIELD


def _jobsworth_markdown(data: dict[str, Any]) -> str:
    salary = data.get("salary")
    if salary in (None, ""):
        return (
            "# Jobsworth salary estimate\n\nAdzuna could not produce an estimate for this "
            "title/description. Try a more standard job title or richer description text."
        )
    return (
        f"# Jobsworth salary estimate\n\nEstimated annual salary: **{_money(salary)}** "
        "(local currency).\n\nThis is Adzuna's model prediction from the title and description "
        "you supplied — not a figure any employer advertised."
    )


@mcp.tool(
    name="adzuna_estimate_salary",
    annotations={
        "title": "Estimate a salary from a job title and description",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def adzuna_estimate_salary(params: JobsworthInput) -> str:
    """Estimate an annual salary for a role from its title and description (Adzuna Jobsworth).

    Unlike the histogram/history tools (which summarise live ads), this predicts a single figure
    for a *specific* role you describe — useful for pricing a CV target or sanity-checking a
    job ad that states no salary. Feed it a job title plus the ad body or a skills summary.

    Args:
        params (JobsworthInput): Validated parameters containing:
            - country (str): ISO code, default 'gb'
            - title (str): the job title to price
            - description (str): role/skills text; the full JD works well
            - response_format (ResponseFormat): 'markdown' or 'json'

    Returns:
        str: Markdown with the estimated annual salary, or JSON with key `salary` (float,
            local currency). The `salary` key is absent when Adzuna cannot produce an estimate.
            On failure, an 'Error: ...' string explaining the cause.
    """
    try:
        payload = params.model_dump(exclude={"country", "response_format"})
        data = await _get(f"jobs/{params.country}/jobsworth", payload)
        return _render(data, params.response_format, _jobsworth_markdown)
    except Exception as exc:  # noqa: BLE001
        return _handle_api_error(exc)


if __name__ == "__main__":
    mcp.run()
