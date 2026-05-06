from __future__ import annotations

import json
import re

from jira_rag.config import Settings
from jira_rag.schemas import AgentPlan, Intent


ISSUE_KEY_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b", re.IGNORECASE)


class Planner:
    def __init__(self, settings: Settings):
        self.settings = settings

    def plan(self, question: str) -> AgentPlan:
        if self.settings.openai_api_key:
            plan = self._openai_plan(question)
            if plan:
                return plan
        return self._local_plan(question)

    def _local_plan(self, question: str) -> AgentPlan:
        normalized = question.lower()
        issue_match = ISSUE_KEY_RE.search(question)

        if issue_match and any(term in normalized for term in ["summarize", "summary", "explain", "detail"]):
            return AgentPlan(
                intent=Intent.ISSUE_SUMMARY,
                issue_key=issue_match.group(0).upper(),
                rationale="Question asks for a summary of a specific Jira issue.",
            )

        if any(term in normalized for term in ["report", "generate", "export"]):
            return AgentPlan(intent=Intent.REPORT, rationale="Question asks for a report.")

        if any(term in normalized for term in ["board", "status", "sprint", "current", "progress"]):
            return AgentPlan(intent=Intent.BOARD_STATUS, rationale="Question asks for current board status.")

        if issue_match:
            return AgentPlan(
                intent=Intent.ISSUE_SUMMARY,
                issue_key=issue_match.group(0).upper(),
                rationale="Question references a specific Jira issue.",
            )

        return AgentPlan(
            intent=Intent.ISSUE_SEARCH,
            jql=self._question_to_jql(normalized),
            rationale="Question requires a Jira issue search.",
        )

    def _question_to_jql(self, normalized_question: str) -> str:
        clauses = [f"project = {self.settings.jira_project_key}"]
        if "bug" in normalized_question:
            clauses.append("issuetype = Bug")
        if "blocker" in normalized_question or "critical" in normalized_question:
            clauses.append("priority in (Blocker, Critical, Highest)")
        if "unassigned" in normalized_question:
            clauses.append("assignee is EMPTY")
        if "done" in normalized_question or "closed" in normalized_question:
            clauses.append('statusCategory = Done')
        if "progress" in normalized_question or "open" in normalized_question:
            clauses.append('statusCategory != Done')
        if "overdue" in normalized_question:
            clauses.append("duedate < now()")
            clauses.append("statusCategory != Done")
        return " AND ".join(clauses) + " ORDER BY updated DESC"

    def _openai_plan(self, question: str) -> AgentPlan | None:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.settings.openai_api_key)
            response = client.chat.completions.create(
                model=self.settings.openai_model,
                temperature=0,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Return only JSON for routing a Jira question. "
                            "intent must be one of: board_status, issue_summary, report, issue_search. "
                            "Use issue_key only if the user names one. "
                            f"Default project key is {self.settings.jira_project_key}. "
                            "For issue_search, provide safe read-only JQL."
                        ),
                    },
                    {"role": "user", "content": question},
                ],
            )
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            return AgentPlan.model_validate(data)
        except Exception:
            return None
