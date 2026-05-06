from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from jira_rag.agent import JiraRagAgent
from jira_rag.config import Settings
from jira_rag.jira_client import JiraClient, JiraClientError


load_dotenv()


st.set_page_config(page_title="Jira Agentic RAG", page_icon="J", layout="wide")


@st.cache_resource(show_spinner=False)
def build_agent() -> JiraRagAgent:
    settings = Settings.from_env()
    return JiraRagAgent(JiraClient(settings), settings)


def issue_dataframe(issues: list[dict]) -> pd.DataFrame:
    rows = []
    for issue in issues:
        fields = issue.get("fields", {})
        assignee = fields.get("assignee") or {}
        status = fields.get("status") or {}
        priority = fields.get("priority") or {}
        issue_type = fields.get("issuetype") or {}
        rows.append(
            {
                "Key": issue.get("key"),
                "Summary": fields.get("summary"),
                "Status": status.get("name"),
                "Type": issue_type.get("name"),
                "Priority": priority.get("name"),
                "Assignee": assignee.get("displayName") or "Unassigned",
                "Updated": fields.get("updated"),
            }
        )
    return pd.DataFrame(rows)


def render_sidebar() -> None:
    st.sidebar.title("Jira Connection")
    st.sidebar.caption(os.getenv("JIRA_BASE_URL", "JIRA_BASE_URL not set"))
    st.sidebar.text_input("Project", value=os.getenv("JIRA_PROJECT_KEY", ""), disabled=True)
    st.sidebar.text_input("Board ID", value=os.getenv("JIRA_BOARD_ID", ""), disabled=True)
    st.sidebar.divider()
    st.sidebar.caption("Configure values in `.env`, then restart Streamlit.")


def render_board_snapshot(agent: JiraRagAgent) -> None:
    with st.spinner("Loading Jira board snapshot..."):
        try:
            result = agent.answer("current jira board status")
        except Exception as exc:
            st.subheader("Board Snapshot")
            st.error(f"Unable to load board snapshot: {exc}")
            st.info("The Ask tab can still summarize individual issues like `KAN-1`.")
            return
    data = result.get("data", {})
    issues = data.get("issues", [])
    df = issue_dataframe(issues)

    st.subheader("Board Snapshot")
    if df.empty:
        st.info("No issues returned for the configured project or board.")
        return

    total = len(df)
    done = int(df["Status"].str.contains("done|closed|resolved", case=False, na=False).sum())
    in_progress = int(df["Status"].str.contains("progress", case=False, na=False).sum())
    unassigned = int((df["Assignee"] == "Unassigned").sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Issues", total)
    c2.metric("Done", done)
    c3.metric("In Progress", in_progress)
    c4.metric("Unassigned", unassigned)

    chart_col, table_col = st.columns([0.4, 0.6])
    with chart_col:
        status_counts = df["Status"].fillna("Unknown").value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        fig = px.bar(status_counts, x="Count", y="Status", orientation="h", color="Status")
        fig.update_layout(showlegend=False, height=320, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)
    with table_col:
        st.dataframe(df, use_container_width=True, hide_index=True)


def render_chat(agent: JiraRagAgent) -> None:
    st.subheader("Ask Jira")
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Ask about board status, a Jira issue, or request a report.",
            }
        ]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input("What do you want to know about Jira?")
    if not question:
        return

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Planning Jira action and retrieving context..."):
            try:
                result = agent.answer(question)
            except JiraClientError as exc:
                answer = f"Jira request failed: {exc}"
                result = {"answer": answer, "intent": "error", "data": {}}
            except Exception as exc:  # Streamlit should show a friendly failure.
                answer = f"Unable to answer that request: {exc}"
                result = {"answer": answer, "intent": "error", "data": {}}

        st.caption(f"Action: {result.get('intent', 'unknown')}")
        st.markdown(result["answer"])
        st.session_state.messages.append({"role": "assistant", "content": result["answer"]})

        report = result.get("data", {}).get("report")
        if report:
            st.download_button(
                "Download Markdown Report",
                data=report,
                file_name="jira_report.md",
                mime="text/markdown",
            )


def main() -> None:
    st.title("Agentic Jira RAG")
    st.caption("Plan Jira action, retrieve board or issue context, then synthesize an answer.")
    render_sidebar()

    try:
        agent = build_agent()
    except Exception as exc:
        st.error(f"Configuration error: {exc}")
        st.stop()

    tab_chat, tab_board = st.tabs(["Ask", "Board"])
    with tab_chat:
        render_chat(agent)
    with tab_board:
        render_board_snapshot(agent)


if __name__ == "__main__":
    main()
