# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "mcp>=1.2.0",
#     "httpx>=0.27.0",
#     "pydantic>=2.0.0",
#     "python-dotenv>=1.0.0",
# ]
# ///
"""Reed.co.uk MCP server.

Exposes the Reed Jobseeker API as MCP tools. Reed is one of the UK's largest job
boards; this server complements salary/market-data sources (Adzuna) and other
listing boards (Indeed, Dice) by adding Reed's own live vacancy index with
full job descriptions available on demand.

Auth: HTTP Basic. The Reed API key is the USERNAME and the password is an EMPTY
string. Set REED_API_KEY in the MCP server env (get one at
https://www.reed.co.uk/developers/jobseeker).
Transport: stdio.
"""

import html
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

BASE_URL = "https://www.reed.co.uk/api/1.0"
TIMEOUT = 30.0
MAX_RESULTS_PER_PAGE = 100  # Reed caps resultsToTake at 100.

mcp = FastMCP(
    "reed_mcp",
    instructions="""Reed.co.uk UK job search.

All salaries are in GBP. Distance is measured in MILES (unlike Adzuna, which uses km).

IMPORTANT: reed_search_jobs returns only a SHORT description of each job. For the
FULL job description — plus normalised yearly salary, salary type, contract type and
the external application URL — call reed_get_job_details with the jobId. Always fetch
the full details before tailoring a CV or cover letter to a role.

Salary can be hidden by the employer. An absent salary is NOT zero — the tools render
it as "Not disclosed"; never treat a missing figure as £0.

Suggested workflow:
- Find roles:  reed_search_jobs (keywords, locationName, distanceFromLocation in miles)
- Read a role: reed_get_job_details (jobId) -> full text before tailoring a CV
""",
)


# --------------------------------------------------------------------------
# Shared infrastructure
# --------------------------------------------------------------------------


class ResponseFormat(str, Enum):
    """Output format for tool responses."""

    MARKDOWN = "markdown"
    JSON = "json"


FORMAT_FIELD = Field(
    default=ResponseFormat.MARKDOWN,
    description="'markdown' for a compact human-readable summary, 'json' for full structured data.",
)


def _api_key() -> str:
    """Read the Reed API key from the environment.

    Raises:
        RuntimeError: If REED_API_KEY is missing.
    """
    key = os.getenv("REED_API_KEY")
    if not key:
        raise RuntimeError(
            "Missing credentials. Set REED_API_KEY in the MCP server env. Get a free key "
            "at https://www.reed.co.uk/developers/jobseeker"
        )
    return key


def _clean(params: dict[str, Any]) -> dict[str, Any]:
    """Drop None values and coerce bools to Reed's 'true'/'false' string convention.

    Reed's boolean query flags (permanent, contract, fullTime, ...) expect the literal
    strings 'true'/'false', unlike Adzuna's 1/absent convention. A flag is only sent
    when the caller set it, so leaving one unset means "no filter".
    """
    out: dict[str, Any] = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, bool):
            out[key] = "true" if value else "false"
            continue
        if isinstance(value, Enum):
            value = value.value
        out[key] = value
    return out


def _handle_api_error(exc: Exception) -> str:
    """Turn an exception into an actionable message for the agent."""
    if isinstance(exc, RuntimeError):
        return f"Error: {exc}"
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        body = exc.response.text[:300]
        if code == 401:
            return (
                "Error: Reed rejected the credentials (401). Check REED_API_KEY is the key "
                "from https://www.reed.co.uk/developers/jobseeker. Reed uses HTTP Basic auth "
                "with the key as the username and an empty password."
            )
        if code == 404:
            return (
                "Error: Not found (404). For reed_get_job_details this usually means the jobId "
                f"does not exist or the ad has expired. Response: {body}"
            )
        if code == 429:
            return (
                "Error: Rate limit exceeded (429). Wait, or widen each query so you need fewer "
                "calls."
            )
        return f"Error: Reed returned HTTP {code}. Response: {body}"
    if isinstance(exc, httpx.TimeoutException):
        return f"Error: Request to Reed timed out after {TIMEOUT}s. Try again."
    if isinstance(exc, httpx.RequestError):
        return f"Error: Could not reach Reed: {exc}"
    return f"Error: Unexpected {type(exc).__name__}: {exc}"


async def _get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    """GET a JSON payload from the Reed API using HTTP Basic auth.

    Args:
        path: Path below the API root, e.g. 'search' or 'jobs/12345'.
        params: Query parameters; None values are dropped, bools become 'true'/'false'.

    Returns:
        The decoded JSON body.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT, auth=(_api_key(), "")) as client:
        response = await client.get(f"{BASE_URL}/{path}", params=_clean(params))
        response.raise_for_status()
        return response.json()


def _as_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def _render(data: Any, fmt: ResponseFormat, markdown_fn) -> str:
    """Return either raw JSON or a markdown view of the payload."""
    if fmt is ResponseFormat.JSON:
        return _as_json(data)
    return markdown_fn(data)


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]*\n\s*")


def _strip_html(text: Any) -> str:
    """Reduce Reed's HTML job-description markup to readable plain text."""
    if not text:
        return ""
    # Turn block boundaries into newlines before stripping the rest of the tags.
    text = re.sub(r"<br\s*/?>", "\n", str(text), flags=re.IGNORECASE)
    text = re.sub(r"</(p|li|div|ul|ol|h[1-6])>", "\n", text, flags=re.IGNORECASE)
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    text = _WS_RE.sub("\n", text)
    return text.strip()


def _salary(minimum: Any, maximum: Any, currency: Any = "GBP", suffix: str = "") -> str:
    """Format a salary range, distinguishing a hidden salary from a real figure.

    A salary the employer withheld comes back as null, NOT zero — those render as
    'Not disclosed', never as a £0 figure.
    """
    symbol = {"GBP": "£", "USD": "$", "EUR": "€"}.get(currency, f"{currency} " if currency else "")

    def one(value: Any) -> Optional[str]:
        if value in (None, ""):
            return None
        try:
            amount = float(value)
        except (TypeError, ValueError):
            return str(value)
        # Preserve pennies for sub-pound-precision figures — an hourly rate of
        # 17.6 must render as £17.60, not £18. Rounding to 0 dp destroyed the one
        # cue that a figure is an hourly/daily rate rather than an annual salary.
        # Whole numbers stay clean: 44000 -> £44,000.
        if amount == int(amount):
            return f"{symbol}{int(amount):,}"
        return f"{symbol}{amount:,.2f}"

    lo, hi = one(minimum), one(maximum)
    if lo is None and hi is None:
        return "Not disclosed"
    if lo and hi:
        body = f"{lo} - {hi}" if lo != hi else lo
    else:
        body = lo or hi
    return f"{body}{suffix}"


# No real UK *annual* salary sits below this floor, so a search-result figure under
# it is a per hour/day/week RATE that Reed's /search payload can't label — only
# /jobs/{jobId} carries `salaryType`. We flag those so a £17.60/hr rate isn't
# misread as a £17.60 annual salary.
NON_ANNUAL_CEILING = 1000


def _period_note(minimum: Any, maximum: Any) -> str:
    """Warn when a /search salary figure is clearly a rate, not an annual salary.

    Reed's /search omits `salaryType`, so the pay period is unknowable from a search
    result alone. Rather than guess the unit, we only assert what is certain: a figure
    below NON_ANNUAL_CEILING cannot be an annual salary, so it must be a rate.
    """
    figures = []
    for value in (minimum, maximum):
        if value in (None, ""):
            continue
        try:
            figures.append(float(value))
        except (TypeError, ValueError):
            continue
    if figures and max(figures) < NON_ANNUAL_CEILING:
        return (
            "  ⚠️ per hour/day/week RATE, not an annual salary — call reed_get_job_details "
            "for the pay period and the normalised yearly figure."
        )
    return ""


# --------------------------------------------------------------------------
# Tool: search jobs
# --------------------------------------------------------------------------


class SearchJobsInput(BaseModel):
    """Input model for the Reed job search endpoint."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    keywords: Optional[str] = Field(
        default=None,
        description="Free-text keywords, e.g. 'audio visual technician'. Reed matches these across "
        "the job title and description.",
    )
    location_name: Optional[str] = Field(
        default=None,
        serialization_alias="locationName",
        description="Town or city to search around, e.g. 'London', 'Manchester'.",
    )
    distance_from_location: Optional[int] = Field(
        default=None,
        serialization_alias="distanceFromLocation",
        description="Search radius in MILES around location_name (NOT km — Reed uses miles, unlike "
        "Adzuna). Reed defaults to 10 miles when omitted.",
        ge=0,
        le=1000,
    )
    employer_id: Optional[int] = Field(
        default=None,
        serialization_alias="employerId",
        description="Filter to a single employer by their numeric Reed employerId (from a search result).",
    )
    employer_profile_id: Optional[int] = Field(
        default=None,
        serialization_alias="employerProfileId",
        description="Filter to a single employer by their numeric employerProfileId (from a search result).",
    )
    permanent: Optional[bool] = Field(
        default=None, description="True to restrict to permanent roles."
    )
    contract: Optional[bool] = Field(
        default=None, description="True to restrict to contract roles."
    )
    temp: Optional[bool] = Field(
        default=None, description="True to restrict to temporary roles."
    )
    part_time: Optional[bool] = Field(
        default=None, serialization_alias="partTime", description="True to restrict to part-time roles."
    )
    full_time: Optional[bool] = Field(
        default=None, serialization_alias="fullTime", description="True to restrict to full-time roles."
    )
    minimum_salary: Optional[int] = Field(
        default=None,
        serialization_alias="minimumSalary",
        description="Minimum ANNUAL salary in GBP. Note: filtering by salary drops ads whose salary "
        "the employer hid, since Reed can't compare a hidden figure.",
        ge=0,
    )
    maximum_salary: Optional[int] = Field(
        default=None,
        serialization_alias="maximumSalary",
        description="Maximum ANNUAL salary in GBP.",
        ge=0,
    )
    posted_by_recruitment_agency: Optional[bool] = Field(
        default=None,
        serialization_alias="postedByRecruitmentAgency",
        description="True to restrict to ads posted by recruitment agencies.",
    )
    posted_by_direct_employer: Optional[bool] = Field(
        default=None,
        serialization_alias="postedByDirectEmployer",
        description="True to restrict to ads posted directly by the hiring employer.",
    )
    graduate: Optional[bool] = Field(
        default=None, description="True to restrict to graduate roles."
    )
    results_to_take: int = Field(
        default=20,
        serialization_alias="resultsToTake",
        description="Number of ads to return (1-100).",
        ge=1,
        le=MAX_RESULTS_PER_PAGE,
    )
    results_to_skip: int = Field(
        default=0,
        serialization_alias="resultsToSkip",
        description="Number of ads to skip for pagination (e.g. 20 to fetch the second page of 20).",
        ge=0,
    )
    response_format: ResponseFormat = FORMAT_FIELD


def _search_markdown(data: dict[str, Any]) -> str:
    results = data.get("results", []) or []
    total = data.get("totalResults", "unknown")
    header = [f"# Reed job results ({len(results)} shown, {total} total)"]
    if not results:
        header.append(
            "\nNo ads matched. Try fewer keywords, a larger distance_from_location (miles), or "
            "drop minimum_salary (which also hides ads with an undisclosed salary)."
        )
        return "\n".join(header)

    blocks = []
    for job in results:
        salary = _salary(job.get("minimumSalary"), job.get("maximumSalary"), job.get("currency", "GBP"))
        salary += _period_note(job.get("minimumSalary"), job.get("maximumSalary"))
        desc = _strip_html(job.get("jobDescription")).replace("\n", " ").strip()
        blocks.append(
            "\n".join(
                [
                    f"## {job.get('jobTitle', 'Untitled')}",
                    f"- **Employer:** {job.get('employerName', '?')}",
                    f"- **Location:** {job.get('locationName', '?')}",
                    f"- **Salary:** {salary}",
                    f"- **Posted:** {job.get('date', '?')}  |  **Expires:** {job.get('expirationDate', '?')}",
                    f"- **jobId (pass to reed_get_job_details):** {job.get('jobId', '?')}",
                    f"- **Reed page:** {job.get('jobUrl') or '?'}",
                    "",
                    f"> {desc}",
                ]
            )
        )
    footer = (
        "\n---\nDescriptions above are SHORT snippets. Call reed_get_job_details with a `jobId` "
        "for the full description, normalised yearly salary, contract type and application URL "
        "before tailoring a CV."
    )
    return "\n".join(header) + "\n\n" + "\n\n".join(blocks) + footer


@mcp.tool(
    name="reed_search_jobs",
    annotations={
        "title": "Search Reed job ads",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def reed_search_jobs(params: SearchJobsInput) -> str:
    """Search the Reed.co.uk job advertisement database with keyword, location, salary and contract filters.

    Returns ads including jobId, employer, location, an advertised salary range (GBP) and a
    SHORT description. Reed only returns a snippet here — call reed_get_job_details with the
    jobId to read the full ad and get normalised yearly salary, contract type and the external
    application URL before tailoring a CV.

    Distance is in MILES (unlike Adzuna's km). Salary can be hidden by the employer; a missing
    salary is rendered as 'Not disclosed', never as £0.

    Args:
        params (SearchJobsInput): Validated search parameters. Key fields:
            - keywords (Optional[str]): free-text keywords across title and description
            - location_name (Optional[str]) + distance_from_location (Optional[int], MILES): where to search
            - employer_id / employer_profile_id (Optional[int]): filter to one employer
            - permanent / contract / temp / part_time / full_time / graduate (Optional[bool]): role-type filters
            - minimum_salary / maximum_salary (Optional[int]): annual GBP salary bounds
            - posted_by_recruitment_agency / posted_by_direct_employer (Optional[bool]): who posted the ad
            - results_to_take (int, 1-100), results_to_skip (int): pagination
            - response_format (ResponseFormat): 'markdown' or 'json'

    Returns:
        str: Markdown summary of matching ads, or JSON with keys `totalResults` (int) and
            `results` (list of job objects each containing jobId, employerId, employerName,
            employerProfileId, jobTitle, locationName, minimumSalary, maximumSalary, currency,
            jobDescription (short), date, expirationDate, jobUrl). A hidden salary comes back
            as null — do not treat it as 0. On failure, an 'Error: ...' string explaining the cause.
    """
    try:
        payload = params.model_dump(exclude={"response_format"}, by_alias=True)
        data = await _get("search", payload)
        return _render(data, params.response_format, _search_markdown)
    except Exception as exc:  # noqa: BLE001 - surfaced as an actionable message
        return _handle_api_error(exc)


# --------------------------------------------------------------------------
# Tool: job details
# --------------------------------------------------------------------------


class JobDetailsInput(BaseModel):
    """Input model for the single-job details endpoint."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    job_id: int = Field(
        serialization_alias="jobId",
        description="The numeric Reed jobId, taken from a reed_search_jobs result.",
    )
    response_format: ResponseFormat = FORMAT_FIELD


def _details_markdown(data: dict[str, Any]) -> str:
    if not data:
        return "# Reed job details\n\nNo job returned for that jobId — it may have expired."

    salary_type = data.get("salaryType")
    suffix = f" {salary_type}" if salary_type else ""
    advertised = _salary(
        data.get("minimumSalary"), data.get("maximumSalary"), data.get("currency", "GBP"), suffix
    )
    yearly = _salary(
        data.get("yearlyMinimumSalary"),
        data.get("yearlyMaximumSalary"),
        data.get("currency", "GBP"),
        " per annum",
    )
    contract = " / ".join(
        v for v in (data.get("jobType"), data.get("contractType")) if v
    )
    description = _strip_html(data.get("jobDescription"))

    lines = [
        f"# {data.get('jobTitle', 'Untitled')}",
        "",
        f"- **Employer:** {data.get('employerName', '?')}",
        f"- **Location:** {data.get('locationName', '?')}",
        f"- **Advertised salary:** {advertised}",
        f"- **Normalised yearly salary:** {yearly}",
        f"- **Contract:** {contract or '?'}",
        f"- **Expires:** {data.get('expirationDate', '?')}",
        f"- **jobId:** {data.get('jobId', '?')}",
        f"- **Apply (external URL):** {data.get('externalUrl') or '(apply via the Reed page below)'}",
        f"- **Reed page:** {data.get('jobUrl') or '?'}",
        "",
        "## Full description",
        "",
        description or "(No description text returned.)",
    ]
    return "\n".join(lines)


@mcp.tool(
    name="reed_get_job_details",
    annotations={
        "title": "Get a Reed job's full details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def reed_get_job_details(params: JobDetailsInput) -> str:
    """Get the FULL details of a single Reed job by its jobId.

    reed_search_jobs returns only a short snippet per ad; this returns the complete job
    description plus data the search omits: the normalised yearly salary range, the salary type
    (per hour/day/week/month/annum), contract type, job type, expiry date and the external
    application URL. Call this before tailoring a CV or cover letter to a specific role.

    Salary can be hidden by the employer; a withheld figure is shown as 'Not disclosed', never £0.

    Args:
        params (JobDetailsInput): Validated parameters containing:
            - job_id (int): the numeric Reed jobId from a search result
            - response_format (ResponseFormat): 'markdown' or 'json'

    Returns:
        str: Markdown with the full description and salary/contract metadata, or JSON with keys
            including jobId, employerId, employerName, jobTitle, locationName, minimumSalary,
            maximumSalary, yearlyMinimumSalary, yearlyMaximumSalary, currency, salaryType,
            contractType, jobType, expirationDate, externalUrl, jobUrl and jobDescription (full).
            A hidden salary comes back as null — do not treat it as 0. On failure, an
            'Error: ...' string explaining the cause.
    """
    try:
        data = await _get(f"jobs/{params.job_id}", {})
        return _render(data, params.response_format, _details_markdown)
    except Exception as exc:  # noqa: BLE001
        return _handle_api_error(exc)


if __name__ == "__main__":
    mcp.run()
