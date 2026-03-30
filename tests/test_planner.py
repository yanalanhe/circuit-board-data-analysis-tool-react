# tests/test_planner.py
"""Unit tests for pipeline/nodes/planner.py — generate_plan() node."""
import ast
from unittest.mock import MagicMock, patch

import pipeline.nodes.planner  # ensure module is in sys.modules before patching


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_test_state(query: str, csv_metadata: str = "", csv_temp_paths: dict = None) -> dict:
    if csv_temp_paths is None:
        csv_temp_paths = {}
    return {
        "user_query": query,
        "csv_temp_paths": csv_temp_paths,
        "csv_metadata": csv_metadata,
        "intent": "report",
        "plan": [],
        "generated_code": "",
        "validation_errors": [],
        "execution_output": "",
        "execution_success": False,
        "retry_count": 0,
        "replan_triggered": False,
        "error_messages": [],
        "report_charts": [],
        "report_text": "",
        "large_data_detected": False,
        "large_data_message": "",
        "recovery_applied": "",
    }


def _make_mock_response(content: str) -> MagicMock:
    mock_response = MagicMock()
    mock_response.content = content
    return mock_response


# ---------------------------------------------------------------------------
# Task 4.1 — returns {"plan": [...]} with a list of strings
# ---------------------------------------------------------------------------

def test_generate_plan_returns_plan_list():
    raw = "1. Load voltage data\n2. Calculate statistics\n3. Plot chart"
    with patch("pipeline.nodes.planner.ChatOpenAI") as mock_cls:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_mock_response(raw)
        mock_cls.return_value = mock_llm
        from pipeline.nodes.planner import generate_plan
        result = generate_plan(_make_test_state("create a chart of voltage vs time"))
    assert "plan" in result
    assert isinstance(result["plan"], list)
    assert len(result["plan"]) == 3


# ---------------------------------------------------------------------------
# Task 4.2 — plan steps are plain English strings (no code blocks)
# ---------------------------------------------------------------------------

def test_plan_steps_are_plain_strings():
    raw = "1. Load the CSV file\n2. Compute mean and standard deviation\n3. Generate a bar chart"
    with patch("pipeline.nodes.planner.ChatOpenAI") as mock_cls:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_mock_response(raw)
        mock_cls.return_value = mock_llm
        from pipeline.nodes.planner import generate_plan
        result = generate_plan(_make_test_state("analyze my data"))
    for step in result["plan"]:
        assert isinstance(step, str)
        assert "```" not in step  # no code blocks
        assert not step.startswith("`")


# ---------------------------------------------------------------------------
# Task 4.3 — returns ONLY "plan" key (LangGraph convention)
# ---------------------------------------------------------------------------

def test_generate_plan_returns_only_plan_key():
    raw = "1. Load data\n2. Analyze"
    with patch("pipeline.nodes.planner.ChatOpenAI") as mock_cls:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_mock_response(raw)
        mock_cls.return_value = mock_llm
        from pipeline.nodes.planner import generate_plan
        result = generate_plan(_make_test_state("show me the data"))
    assert set(result.keys()) == {"plan"}, (
        f"generate_plan must return only {{'plan'}}, got: {set(result.keys())}"
    )


# ---------------------------------------------------------------------------
# Task 4.4 — error handling: LLM raises → returns fallback plan
# ---------------------------------------------------------------------------

def test_generate_plan_error_handling():
    """On LLM exception, plan returns empty list and error is routed to error_messages."""
    with patch("pipeline.nodes.planner.ChatOpenAI") as mock_cls:
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("API error")
        mock_cls.return_value = mock_llm
        from pipeline.nodes.planner import generate_plan
        result = generate_plan(_make_test_state("create a chart"))
    assert "plan" in result
    assert isinstance(result["plan"], list)
    assert result["plan"] == [], (
        "On error, plan must be empty — error goes to error_messages, not inline plan text"
    )
    assert "error_messages" in result, (
        "Planner node must propagate exceptions to error_messages (AC2, FR29)"
    )
    assert len(result["error_messages"]) > 0
    # Error must be translated — not raw repr; verify actual translated content
    assert "Exception" not in result["error_messages"][0]
    assert "unexpected error occurred" in result["error_messages"][0].lower()


# ---------------------------------------------------------------------------
# Task 4.5 — no streamlit import in pipeline/nodes/planner.py
# ---------------------------------------------------------------------------

def test_no_streamlit_import_in_planner():
    with open("pipeline/nodes/planner.py", "r") as f:
        source = f.read()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "streamlit" not in alias.name, (
                        "pipeline/nodes/planner.py must NOT import streamlit"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert "streamlit" not in node.module, (
                        "pipeline/nodes/planner.py must NOT import streamlit"
                    )


# ---------------------------------------------------------------------------
# Task 4.6 — plan parsing: numbered lines stripped correctly
# ---------------------------------------------------------------------------

def test_plan_parsing_strips_numbering():
    raw = "1. Load voltage data\n2. Calculate statistics\n3. Plot voltage vs time"
    with patch("pipeline.nodes.planner.ChatOpenAI") as mock_cls:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_mock_response(raw)
        mock_cls.return_value = mock_llm
        from pipeline.nodes.planner import generate_plan
        result = generate_plan(_make_test_state("create a chart of voltage vs time"))
    assert result["plan"][0] == "Load voltage data"
    assert result["plan"][1] == "Calculate statistics"
    assert result["plan"][2] == "Plot voltage vs time"


def test_plan_parsing_strips_multidigit_numbering():
    raw = "10. Load data\n11. Analyze"
    with patch("pipeline.nodes.planner.ChatOpenAI") as mock_cls:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_mock_response(raw)
        mock_cls.return_value = mock_llm
        from pipeline.nodes.planner import generate_plan
        result = generate_plan(_make_test_state("analyze"))
    assert result["plan"][0] == "Load data"
    assert result["plan"][1] == "Analyze"


# ---------------------------------------------------------------------------
# Task 4.7 — empty/whitespace lines are filtered out
# ---------------------------------------------------------------------------

def test_plan_filters_empty_lines():
    raw = "1. Load data\n\n   \n2. Analyze\n\n3. Plot"
    with patch("pipeline.nodes.planner.ChatOpenAI") as mock_cls:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_mock_response(raw)
        mock_cls.return_value = mock_llm
        from pipeline.nodes.planner import generate_plan
        result = generate_plan(_make_test_state("create chart"))
    assert len(result["plan"]) == 3
    for step in result["plan"]:
        assert step.strip() != ""


# ---------------------------------------------------------------------------
# Additional: LLM called with correct model and messages
# ---------------------------------------------------------------------------

def test_generate_plan_uses_gpt4o():
    raw = "1. Load data"
    with patch("pipeline.nodes.planner.ChatOpenAI") as mock_cls:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_mock_response(raw)
        mock_cls.return_value = mock_llm
        from pipeline.nodes.planner import generate_plan
        generate_plan(_make_test_state("analyze data"))
    mock_cls.assert_called_once()
    call_kwargs = mock_cls.call_args
    assert call_kwargs[1].get("model") == "gpt-4o", (
        f"Expected model='gpt-4o', got: {call_kwargs[1].get('model')}"
    )


def test_generate_plan_includes_query_in_prompt():
    raw = "1. Load data"
    with patch("pipeline.nodes.planner.ChatOpenAI") as mock_cls:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_mock_response(raw)
        mock_cls.return_value = mock_llm
        from pipeline.nodes.planner import generate_plan
        generate_plan(_make_test_state("create a chart of voltage vs time"))
    mock_llm.invoke.assert_called_once()
    messages = mock_llm.invoke.call_args[0][0]
    # Last message (HumanMessage) should contain the user query
    human_msg = messages[-1]
    assert "voltage vs time" in human_msg.content


# ---------------------------------------------------------------------------
# AC #3 — Plan validation: 3-7 steps requirement
# ---------------------------------------------------------------------------

def test_generate_plan_accepts_3_steps():
    """AC #3: Plan with 3 steps is valid."""
    raw = "1. Load\n2. Analyze\n3. Plot"
    with patch("pipeline.nodes.planner.ChatOpenAI") as mock_cls:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_mock_response(raw)
        mock_cls.return_value = mock_llm
        from pipeline.nodes.planner import generate_plan
        result = generate_plan(_make_test_state("analyze data"))
    assert len(result["plan"]) == 3


def test_generate_plan_accepts_7_steps():
    """AC #3: Plan with 7 steps is valid."""
    raw = "\n".join([f"{i}. Step {i}" for i in range(1, 8)])
    with patch("pipeline.nodes.planner.ChatOpenAI") as mock_cls:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_mock_response(raw)
        mock_cls.return_value = mock_llm
        from pipeline.nodes.planner import generate_plan
        result = generate_plan(_make_test_state("analyze data"))
    assert len(result["plan"]) == 7


def test_generate_plan_truncates_too_many_steps():
    """AC #3: Plan with >7 steps is truncated to 7."""
    raw = "\n".join([f"{i}. Step {i}" for i in range(1, 12)])  # 11 steps
    with patch("pipeline.nodes.planner.ChatOpenAI") as mock_cls:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_mock_response(raw)
        mock_cls.return_value = mock_llm
        from pipeline.nodes.planner import generate_plan
        result = generate_plan(_make_test_state("analyze data"))
    assert len(result["plan"]) == 7, "Should truncate to 7 steps max"


def test_generate_plan_handles_too_few_steps():
    """AC #3: Plan with <3 steps is still returned (with warning logged)."""
    raw = "1. Load\n2. Analyze"  # only 2 steps
    with patch("pipeline.nodes.planner.ChatOpenAI") as mock_cls:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_mock_response(raw)
        mock_cls.return_value = mock_llm
        from pipeline.nodes.planner import generate_plan
        result = generate_plan(_make_test_state("analyze data"))
    # Should return the 2 steps despite being below minimum (graceful degradation)
    assert len(result["plan"]) == 2


# ---------------------------------------------------------------------------
# AC #4 — Retry context support
# ---------------------------------------------------------------------------

def test_generate_plan_includes_retry_context_on_replan():
    """AC #4: When replan_triggered=True, previous plan is included in prompt."""
    raw = "1. Load\n2. Analyze\n3. Plot"
    state = _make_test_state("analyze data")
    state["replan_triggered"] = True
    state["plan"] = ["Previous step 1", "Previous step 2"]
    state["error_messages"] = ["Previous execution failed"]

    with patch("pipeline.nodes.planner.ChatOpenAI") as mock_cls:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_mock_response(raw)
        mock_cls.return_value = mock_llm
        from pipeline.nodes.planner import generate_plan
        result = generate_plan(state)

    # Verify system prompt includes retry context
    mock_llm.invoke.assert_called_once()
    messages = mock_llm.invoke.call_args[0][0]
    system_msg = messages[0]
    assert "Previous failure context" in system_msg.content or "previous plan" in system_msg.content.lower(), (
        "System prompt must reference previous failure context when replan_triggered=True (AC #4)"
    )
    assert len(result["plan"]) >= 1


def test_generate_plan_includes_error_messages_in_retry():
    """AC #4: Error messages from previous execution are in retry prompt."""
    raw = "1. Load\n2. Analyze\n3. Plot"
    state = _make_test_state("analyze data")
    state["replan_triggered"] = True
    state["error_messages"] = ["Code validation failed", "Invalid syntax detected"]

    with patch("pipeline.nodes.planner.ChatOpenAI") as mock_cls:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_mock_response(raw)
        mock_cls.return_value = mock_llm
        from pipeline.nodes.planner import generate_plan
        result = generate_plan(state)

    mock_llm.invoke.assert_called_once()
    messages = mock_llm.invoke.call_args[0][0]
    system_msg = messages[0]
    # Should mention execution errors or failure context
    assert "previous" in system_msg.content.lower() or "error" in system_msg.content.lower(), (
        "Retry prompt must include error context (AC #4)"
    )


def test_generate_plan_no_retry_context_when_not_replanning():
    """When replan_triggered=False, no retry context in prompt."""
    raw = "1. Load\n2. Analyze\n3. Plot"
    state = _make_test_state("analyze data")
    state["replan_triggered"] = False
    state["error_messages"] = []

    with patch("pipeline.nodes.planner.ChatOpenAI") as mock_cls:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_mock_response(raw)
        mock_cls.return_value = mock_llm
        from pipeline.nodes.planner import generate_plan
        result = generate_plan(state)

    mock_llm.invoke.assert_called_once()
    messages = mock_llm.invoke.call_args[0][0]
    system_msg = messages[0]
    # Should NOT include retry-specific context
    assert "Previous failure context" not in system_msg.content or system_msg.content.count("previous") == 0


# ---------------------------------------------------------------------------
# Additional parsing tests
# ---------------------------------------------------------------------------

def test_plan_parsing_handles_different_separators():
    """Plan parser should handle 1., 1), 1:, 1- separators."""
    raw = "1. Load\n2) Analyze\n3: Plot\n4- Summarize"
    with patch("pipeline.nodes.planner.ChatOpenAI") as mock_cls:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_mock_response(raw)
        mock_cls.return_value = mock_llm
        from pipeline.nodes.planner import generate_plan
        result = generate_plan(_make_test_state("analyze data"))
    assert len(result["plan"]) == 4
    assert result["plan"][0] == "Load"
    assert result["plan"][1] == "Analyze"
    assert result["plan"][2] == "Plot"
    assert result["plan"][3] == "Summarize"
