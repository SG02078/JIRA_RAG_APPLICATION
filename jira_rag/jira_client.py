from __future__ import annotations

from typing import Any

from requests.auth import HTTPBasicAuth
import requests

from jira_rag.config import Settings


class JiraClientError(RuntimeError):
    pass


class JiraClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(settings.jira_email, settings.jira_api_token)
        self.session.headers.update({"Accept": "application/json"})

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.settings.jira_base_url}{path}"
        try:
            response = self.session.get(url, params=params, timeout=30)
        except requests.RequestException as exc:
            raise JiraClientError(f"Network error while calling Jira: {exc}") from exc
        if response.status_code >= 400:
            raise JiraClientError(f"{response.status_code} {response.reason}: {response.text[:500]}")
        return response.json()

    def search_issues(
        self,
        jql: str,
        fields: list[str] | None = None,
        max_results: int | None = None,
    ) -> list[dict[str, Any]]:
        fields = fields or [
            "summary",
            "status",
            "assignee",
            "priority",
            "issuetype",
            "updated",
            "created",
            "duedate",
            "description",
            "comment",
            "resolution",
        ]
        limit = max_results or self.settings.max_issues
        issues: list[dict[str, Any]] = []
        next_page_token: str | None = None

        while len(issues) < limit:
            params: dict[str, Any] = {
                "jql": jql,
                "fields": ",".join(fields),
                "maxResults": min(100, limit - len(issues)),
            }
            if next_page_token:
                params["nextPageToken"] = next_page_token

            payload = self._get("/rest/api/3/search/jql", params=params)
            issues.extend(payload.get("issues", []))
            next_page_token = payload.get("nextPageToken")
            if not next_page_token:
                break

        return issues

    def get_issue(self, issue_key: str) -> dict[str, Any]:
        params = {
            "fields": "summary,status,assignee,priority,issuetype,updated,created,description,comment,resolution,duedate",
        }
        return self._get(f"/rest/api/3/issue/{issue_key.upper()}", params=params)

    def active_sprints(self) -> list[dict[str, Any]]:
        if not self.settings.jira_board_id:
            return []
        payload = self._get(
            f"/rest/agile/1.0/board/{self.settings.jira_board_id}/sprint",
            params={"state": "active"},
        )
        return payload.get("values", [])

    def board_issues(self) -> list[dict[str, Any]]:
        if self.settings.jira_board_id:
            try:
                active_sprints = self.active_sprints()
            except Exception:
                active_sprints = []
            if active_sprints:
                sprint_ids = ",".join(str(sprint["id"]) for sprint in active_sprints)
                return self.search_issues(f"sprint in ({sprint_ids}) ORDER BY updated DESC")

        return self.search_issues(
            f"project = {self.settings.jira_project_key} ORDER BY updated DESC",
            max_results=self.settings.max_issues,
        )
