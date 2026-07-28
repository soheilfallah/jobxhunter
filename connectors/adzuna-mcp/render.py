"""Pure rendering + credential-redaction helpers for the Adzuna MCP server.

No third-party dependencies, so these are unit-testable on plain Python
(see test_rendering.py) without standing up the MCP / httpx / pydantic stack.
server.py imports everything here.
"""
import re
from typing import Any, Optional

# Adzuna auth travels in the URL query string (app_id / app_key). An exception or an
# upstream error body can echo that credential-bearing URL back — scrub it so keys
# never reach the agent transcript or logs.
_CRED_RE = re.compile(r"(app_id|app_key)=[^&\s]+", re.IGNORECASE)


def _money(value: Any) -> str:
    """Format a salary figure, or '?' when absent."""
    if value in (None, ""):
        return "?"
    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return str(value)


def _numeric(value: Any) -> Optional[float]:
    """Parse a key as a number, or None if it isn't one (strips thousands commas)."""
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _pairs_to_markdown(mapping: dict, key_header: str, value_header: str, title: str) -> str:
    """Render a flat {key: value} object as a sorted markdown table.

    When EVERY key is numeric (e.g. the salary-histogram band lower-bounds
    10000, 20000, ... 100000) sort them NUMERICALLY — a plain string sort put
    '100000' before '20000' and scrambled the distribution. Otherwise (company
    names, ISO-date months) fall back to a lexical sort, which is already correct.
    """
    if not mapping:
        return f"# {title}\n\nNo data returned for this query."
    if all(_numeric(k) is not None for k in mapping):
        rows = sorted(mapping.items(), key=lambda kv: _numeric(kv[0]))
    else:
        rows = sorted(mapping.items(), key=lambda kv: str(kv[0]))
    lines = [f"# {title}", "", f"| {key_header} | {value_header} |", "|---|---|"]
    lines += [f"| {k} | {_money(v)} |" for k, v in rows]
    return "\n".join(lines)


def format_salary(salary_min: Any, salary_max: Any, predicted: bool = False) -> str:
    """Render an advertised salary range. A withheld salary (null min AND max) is
    'Not disclosed', never the ambiguous '? - ?' (which reads as a real range)."""
    if salary_min in (None, "") and salary_max in (None, ""):
        return "Not disclosed"
    text = f"{_money(salary_min)} - {_money(salary_max)}"
    if predicted:
        text += " (predicted, not stated in ad)"
    return text


def redact_credentials(text: str) -> str:
    """Scrub app_id / app_key values out of any text before it reaches the agent."""
    return _CRED_RE.sub(r"\1=REDACTED", text)
