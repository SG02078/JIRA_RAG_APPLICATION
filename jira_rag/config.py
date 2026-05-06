from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    jira_base_url: str
    jira_email: str
    jira_api_token: str
    jira_project_key: str
    jira_board_id: str | None = None
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    max_issues: int = 100

    @classmethod
    def from_env(cls) -> "Settings":
        required = {
            "JIRA_BASE_URL": os.getenv("JIRA_BASE_URL", "").strip().rstrip("/"),
            "JIRA_EMAIL": os.getenv("JIRA_EMAIL", "").strip(),
            "JIRA_API_TOKEN": os.getenv("JIRA_API_TOKEN", "").strip(),
            "JIRA_PROJECT_KEY": os.getenv("JIRA_PROJECT_KEY", "").strip(),
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        board_id = os.getenv("JIRA_BOARD_ID", "").strip() or None
        return cls(
            jira_base_url=required["JIRA_BASE_URL"],
            jira_email=required["JIRA_EMAIL"],
            jira_api_token=required["JIRA_API_TOKEN"],
            jira_project_key=required["JIRA_PROJECT_KEY"],
            jira_board_id=board_id,
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip() or None,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini",
            max_issues=int(os.getenv("JIRA_MAX_ISSUES", "100")),
        )
