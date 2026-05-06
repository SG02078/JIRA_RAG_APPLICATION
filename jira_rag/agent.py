from __future__ import annotations

from typing import Any

from jira_rag.config import Settings
from jira_rag.formatting import issue_line, plain_text_from_adf, summarize_counts
from jira_rag.jira_client import JiraClient
from jira_rag.planner import Planner
from jira_rag.reports import markdown_report
from jira_rag.schemas import Intent


class JiraRagAgent:
    def __init__(self, jira: JiraClient, settings: Settings):
        self.jira = jira
        self.settings = settings
        self.planner = Planner(settings)

    def answer(self, question: str) -> dict[str, Any]:
        plan = self.planner.plan(question)
        if plan.intent == Intent.ISSUE_SUMMARY and plan.issue_key:
            issue = self.jira.get_issue(plan.issue_key)
            answer = self._issue_summary(issue, question)
            return {"intent": plan.intent.value, "answer": answer, "data": {"issue": issue, "plan": plan.model_dump()}}

        if plan.intent == Intent.REPORT:
            issues = self.jira.board_issues()
            report = markdown_report("Jira Board Report", issues)
            answer = self._synthesize(question, report) or self._report_answer(report)
            return {
                "intent": plan.intent.value,
                "answer": answer,
                "data": {"issues": issues, "report": report, "plan": plan.model_dump()},
            }

        if plan.intent == Intent.BOARD_STATUS:
            issues = self.jira.board_issues()
            answer = self._board_status(issues, question)
            return {"intent": plan.intent.value, "answer": answer, "data": {"issues": issues, "plan": plan.model_dump()}}

        jql = plan.jql or f"project = {self.settings.jira_project_key} ORDER BY updated DESC"
        issues = self.jira.search_issues(jql)
        answer = self._search_answer(issues, jql, question)
        return {
            "intent": Intent.ISSUE_SEARCH.value,
            "answer": answer,
            "data": {"issues": issues, "jql": jql, "plan": plan.model_dump()},
        }

    def _board_status(self, issues: list[dict[str, Any]], question: str) -> str:
        counts = summarize_counts(issues)
        context = "\n".join(
            [
                f"Issues: {len(issues)}",
                f"Status: {dict(counts['status'].most_common())}",
                f"Priority: {dict(counts['priority'].most_common())}",
                "Recent issues:",
                *[issue_line(issue) for issue in issues[:10]],
            ]
        )
        generated = self._synthesize(question, context)
        if generated:
            return generated

        status_lines = "\n".join(f"- {name}: {count}" for name, count in counts["status"].most_common())
        recent = "\n".join(issue_line(issue) for issue in issues[:8])
        return f"Current board status based on {len(issues)} issues:\n\n{status_lines}\n\nMost recently updated:\n{recent}"

    def _issue_summary(self, issue: dict[str, Any], question: str) -> str:
        fields = issue.get("fields", {})
        comments = fields.get("comment", {}).get("comments", [])
        latest_comments = "\n".join(
            plain_text_from_adf(comment.get("body")) for comment in comments[-5:] if comment.get("body")
        )
        context = "\n".join(
            [
                f"Key: {issue.get('key')}",
                f"Summary: {fields.get('summary')}",
                f"Status: {(fields.get('status') or {}).get('name')}",
                f"Assignee: {(fields.get('assignee') or {}).get('displayName', 'Unassigned')}",
                f"Priority: {(fields.get('priority') or {}).get('name', 'No priority')}",
                f"Updated: {fields.get('updated')}",
                f"Description: {plain_text_from_adf(fields.get('description'))}",
                f"Recent comments: {latest_comments}",
            ]
        )
        generated = self._synthesize(question, context)
        if generated:
            return generated
        return context

    def _search_answer(self, issues: list[dict[str, Any]], jql: str, question: str) -> str:
        context = "\n".join([f"JQL: {jql}", *[issue_line(issue) for issue in issues[:20]]])
        generated = self._synthesize(question, context)
        if generated:
            return generated
        return f"Found {len(issues)} matching issues with `{jql}`:\n\n" + "\n".join(
            issue_line(issue) for issue in issues[:20]
        )

    def _report_answer(self, report: str) -> str:
        return "Generated a Jira board report. Preview:\n\n" + "\n".join(report.splitlines()[:24])

    def _synthesize(self, question: str, context: str) -> str | None:
        if not self.settings.openai_api_key:
            return None
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.settings.openai_api_key)
            response = client.chat.completions.create(
                model=self.settings.openai_model,
                temperature=0.2,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a Jira reporting assistant. Answer only from the provided Jira context. "
                            "Be concise, include issue keys when useful, and state when context is insufficient."
                        ),
                    },
                    {"role": "user", "content": f"Question:\n{question}\n\nJira context:\n{context}"},
                ],
            )
            return response.choices[0].message.content
        except Exception:
            return None
