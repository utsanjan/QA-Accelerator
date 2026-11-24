import streamlit as st

from app.components.connection_status import load_live_status, render_recheck_control
from app.components.theme import page_header
from app.components.toast_loader import toast_loader


def render() -> None:
    page_header("Settings & Health", "Check service connectivity and environment configuration.")

    st.subheader("Connection Status")
    live = load_live_status()
    for key, item in live["data"].items():
        icon = {"ready": "✅", "error": "❌", "unknown": "❔"}.get(item["status"], "⚠️")
        st.markdown(f"**{item['label']}** — {icon} {item.get('badge') or item['status'].title()}")
        st.caption(item["detail"])
    render_recheck_control(live, key="settings_recheck_connections")

    st.divider()
    st.subheader("Connection Tests")

    if st.button("Test Azure OpenAI", help="Send a tiny test prompt to the model. Uses a few tokens."):
        try:
            from langchain_core.messages import HumanMessage

            from src.config import get_azure_llm

            response = get_azure_llm().invoke([HumanMessage(content="Reply with OK only.")])
            st.success(f"Azure OpenAI responded: {str(response.content)[:120]}")
        except Exception as exc:
            st.error(str(exc))

    if st.button("Test Azure DevOps", help="Check the organization, project and PAT. Nothing is imported."):
        try:
            from src.integrations.azure_devops_client import AzureDevOpsClient

            result = AzureDevOpsClient().test_connection()
            st.success(f"Connected to {result['organization']}/{result['project']}")
        except Exception as exc:
            st.error(str(exc))

    if st.button(
        "Test Databricks Connection",
        help="Validate the token and read the warehouse state. The warehouse is not started.",
    ):
        from src.health import check_databricks

        with toast_loader("Databricks test — contacting Databricks...", done="Databricks test — finished."):
            result = check_databricks()
        if result["status"] == "ready":
            st.success(f"Databricks reachable: {result['detail']}")
        elif result["status"] == "missing":
            st.warning("Databricks credentials are not configured.")
        else:
            st.error(f"{result['badge']}: {result['detail']}")

    st.divider()
    st.subheader("Environment Notes")
    st.markdown(
        """
        - Credentials are loaded from `.env` in the project root.
        - Secrets are never displayed in the UI.
        - Update `.env` and refresh this page after changing credentials.
        """
    )
