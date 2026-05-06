from __future__ import annotations

from datetime import datetime
from typing import Any

from jira_rag.formatting import issue_line, summarize_counts


def markdown_report(title: str, issues: list[dict[str, Any]]) -> str:
    counts = summarize_counts(issues)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"# {title}",
        "",
        f"Generated: {now}",
        f"Issues analyzed: {len(issues)}",
        "",
        "## Status Breakdown",
        *[f"- {name}: {count}" for name, count in counts["status"].most_common()],
        "",
        "## Priority Breakdown",
        *[f"- {name}: {count}" for name, count in counts["priority"].most_common()],
        "",
        "## Assignee Load",
        *[f"- {name}: {count}" for name, count in counts["assignee"].most_common()],
        "",
        "## Recent Issues",
        *[issue_line(issue) for issue in issues[:20]],
    ]
    return "\n".join(lines)
