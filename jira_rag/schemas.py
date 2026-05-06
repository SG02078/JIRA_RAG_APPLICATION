from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Intent(str, Enum):
    BOARD_STATUS = "board_status"
    ISSUE_SUMMARY = "issue_summary"
    REPORT = "report"
    ISSUE_SEARCH = "issue_search"


class AgentPlan(BaseModel):
    intent: Intent
    issue_key: str | None = None
    jql: str | None = None
    rationale: str = Field(default="")
