# pipeline/nodes/planner.py
"""Execution plan generation node.

NOTE: Never import streamlit in this file.
"""
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from pipeline.state import PipelineState

logger = logging.getLogger(__name__)

_PLAN_SYSTEM_PROMPT = """You are an execution plan generator for a data analysis tool.
Given a user's analysis request and their dataset information, create a clear,
numbered step-by-step execution plan.

Rules:
- Each step must be a plain English sentence — no code, no technical jargon
- Steps should be concrete and actionable (e.g., "Load voltage and current columns",
  NOT "Process the data")
- Include data loading, computation, and visualization steps as appropriate
- Output ONLY the numbered list, one step per line
- Format: "1. Step description" on each line
- Generate exactly 3-7 steps for most analysis requests"""

_PLAN_RETRY_CONTEXT = """
Previous failure context:
{previous_context}

Please generate a DIFFERENT plan that avoids this issue.
Generate exactly 3-7 steps.
"""


def _extract_retry_context(state: PipelineState) -> str:
    """Extract context about previous failure for retry prompting (AC #4)."""
    context_parts = []

    if state.get("replan_triggered"):
        # Include previous plan that failed
        prev_plan = state.get("plan", [])
        if prev_plan:
            context_parts.append("Previous plan that failed:")
            for i, step in enumerate(prev_plan, 1):
                context_parts.append(f"  {i}. {step}")

    # Include error messages from execution failures
    error_messages = state.get("error_messages", [])
    if error_messages:
        context_parts.append("\nExecution errors:")
        for error in error_messages[-3:]:  # last 3 errors only
            context_parts.append(f"  - {error}")

    # Include validation errors if present
    validation_errors = state.get("validation_errors", [])
    if validation_errors:
        context_parts.append("\nValidation issues:")
        for error in validation_errors[-3:]:  # last 3 only
            context_parts.append(f"  - {error}")

    return "\n".join(context_parts) if context_parts else ""


def _validate_plan_length(steps: list[str]) -> list[str]:
    """Validate that plan has 3-7 steps per AC #3. Log warning if not.

    Returns the plan as-is but may log validation info.
    """
    step_count = len(steps)
    if step_count < 3:
        logger.warning(
            f"Generated plan has {step_count} steps; expected 3-7. "
            "Plan may be incomplete. Returning anyway per AC #3."
        )
    elif step_count > 7:
        logger.warning(
            f"Generated plan has {step_count} steps; expected 3-7. "
            "Truncating to first 7 steps per AC #3."
        )
        steps = steps[:7]

    return steps


def _parse_plan_steps(raw_response: str) -> list[str]:
    """Parse numbered steps from LLM response.

    Extracts lines starting with "1.", "2.", etc., stripping numbering.
    Handles multi-digit numbers and various separators.
    """
    steps = []
    for line in raw_response.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Match patterns: "1.", "1)", "1:", "1-" followed by text
        cleaned = re.sub(r"^\d+[.\)\:-]\s*", "", line)
        if cleaned:
            steps.append(cleaned)

    # Fallback: if no steps parsed, treat entire response as single step
    if not steps:
        steps = [raw_response.strip()]

    return steps


def generate_plan(state: PipelineState) -> dict:
    """Generate a step-by-step execution plan from the user query.

    Implements AC #1-5:
    - AC #1: Produces list of numbered steps when intent="report"
    - AC #2: Steps are clear and actionable
    - AC #3: Returns list[str] with 3-7 steps
    - AC #4: Includes previous failure context for retries
    - AC #5: Plan is returned in state for frontend display

    Returns only changed keys per LangGraph convention.
    """
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0)

        # Build the user message (AC #1, #2)
        content = f"User request: {state['user_query']}"
        csv_metadata = state.get("csv_metadata", "")
        if csv_metadata:
            content += f"\n\n{csv_metadata}"

        # Prepare system prompt with retry context if applicable (AC #4)
        system_prompt = _PLAN_SYSTEM_PROMPT
        retry_context = _extract_retry_context(state)
        if retry_context:
            system_prompt += "\n" + _PLAN_RETRY_CONTEXT.format(
                previous_context=retry_context
            )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=content),
        ]

        response = llm.invoke(messages)
        raw = response.content.strip()

        # Parse plan steps
        steps = _parse_plan_steps(raw)

        # Validate length and warn if outside 3-7 range (AC #3)
        steps = _validate_plan_length(steps)

        return {"plan": steps}
    except Exception as e:
        from utils.error_translation import translate_error
        error_msg = translate_error(e)
        return {
            "plan": [],
            "error_messages": list(state.get("error_messages", [])) + [error_msg],
        }
