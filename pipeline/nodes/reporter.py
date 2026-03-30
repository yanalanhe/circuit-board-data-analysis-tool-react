# pipeline/nodes/reporter.py
"""Report rendering node.

NOTE: Never import streamlit in this file.
"""
from pipeline.state import PipelineState


_DOWNSAMPLE_NOTE = "Downsampled to 10,000 points using uniform stride"


def render_report(state: PipelineState) -> dict:
    """Finalise the pipeline state for report rendering in the UI.

    Charts (report_charts) and text (report_text) are already populated in
    state by execute_code (Story 3.4). This node is the named terminal node
    that signals pipeline completion — actual rendering via st.image() and
    st.markdown() happens in streamlit_app.py within the @st.fragment panel.

    If recovery_applied is set (i.e. data was downsampled before execution),
    appends a human-readable note to report_text so the user knows the charts
    reflect a reduced dataset (AC #4 — Story 8.1).

    Returns:
        Dict with updated report_text when downsampling was applied; empty dict
        otherwise. LangGraph merges returned keys into the pipeline state.
    """
    if state.get("recovery_applied"):
        existing_text = state.get("report_text", "")
        separator = "\n\n" if existing_text else ""
        return {"report_text": existing_text + separator + _DOWNSAMPLE_NOTE}
    return {}
