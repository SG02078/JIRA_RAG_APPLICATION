from __future__ import annotations

from collections import Counter
from typing import Any


def field(issue: dict[str, Any], name: str, default: Any = None) -> Any:
    return issue.get("fields", {}).get(name, default)


def plain_text_from_adf(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(filter(None, (plain_text_from_adf(item) for item in value)))
    if isinstance(value, dict):
        text = value.get("text", "")
        nested = plain_text_from_adf(value.get("content", []))
        return " ".join(part for part in [text, nested] if part).strip()
    return str(value)


def issue_line(issue: dict[str, Any]) -> str:
    fields = issue.get("fields", {})
    status = (fields.get("status") or {}).get("name", "Unknown")
    assignee = (fields.get("assignee") or {}).get("displayName", "Unassigned")
    priority = (fields.get("priority") or {}).get("name", "No priority")
    return f"- {issue.get('key')}: {fields.get('summary')} [{status}, {priority}, {assignee}]"


def summarize_counts(issues: list[dict[str, Any]]) -> dict[str, Counter]:
    return {
        "status": Counter((field(issue, "status") or {}).get("name", "Unknown") for issue in issues),
        "assignee": Counter((field(issue, "assignee") or {}).get("displayName", "Unassigned") for issue in issues),
        "priority": Counter((field(issue, "priority") or {}).get("name", "No priority") for issue in issues),
        "type": Counter((field(issue, "issuetype") or {}).get("name", "Unknown") for issue in issues),
    }
