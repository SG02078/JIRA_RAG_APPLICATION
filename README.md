# Agentic Jira RAG Application

Python + Streamlit application that connects to Jira, decides which Jira action is needed for a user question, retrieves relevant issues or board data, and generates an answer or report.

## Features

- Agent-style intent routing for board status, issue summaries, report generation, and JQL-like issue search.
- Jira Cloud support using the current `/rest/api/3/search/jql` endpoint.
- Optional Jira Software board and active sprint retrieval through Agile REST APIs.
- Optional OpenAI answer synthesis when `OPENAI_API_KEY` is configured.
- Streamlit frontend for chat, board dashboards, issue inspection, and report export.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with your Jira site, email, API token, project key, and optional board id.

## Run

```powershell
streamlit run app.py
```

## Example Questions

- What is the current Jira board status?
- Generate a sprint report for the current board.
- Summarize JIRA-123.
- Show blocker bugs in the current project.
- What tickets are overdue or still in progress?

## Notes

- Jira Cloud API tokens can be created from your Atlassian account security settings.
- The app reads Jira data only. It does not create, update, or delete Jira issues.
- If no OpenAI key is configured, the app still works with local heuristics and template-based reporting.
