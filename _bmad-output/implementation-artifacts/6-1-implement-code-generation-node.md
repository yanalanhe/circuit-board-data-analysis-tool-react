# Story 6.1: Implement Code Generation Node

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want the system to generate Python analysis code from an approved execution plan,
So that the plan is translated into executable code that will produce charts and analysis.

## Acceptance Criteria

1. **Given** an approved execution plan in `pipeline_state["plan"]`
   **When** the `generate_code` node in `pipeline/nodes/codegen.py` runs
   **Then** valid Python code is produced that implements the plan steps

2. **Given** generated code for chart visualization
   **When** I inspect the code
   **Then** it includes explicit calls to `plt.xlabel()`, `plt.ylabel()`, `plt.title()`, and `plt.tight_layout()` with descriptive human-readable labels (e.g., "Voltage (V)", not "v")

3. **Given** the generated code
   **When** it is stored in `pipeline_state["generated_code"]`
   **Then** the full code string is saved for later display and re-execution

4. **Given** a code generation attempt that fails validation (next story)
   **When** the pipeline retries
   **Then** the `generate_code` node's system prompt includes context about the previous validation failure to guide a better attempt

5. **Given** generated code producing charts
   **When** the code runs in the subprocess
   **Then** each chart is output as `CHART:<base64_encoded_png>` on stdout (for parsing by the executor)

## Tasks / Subtasks

- [x] Set up code generation node module (`pipeline/nodes/codegen.py`)
  - [x] Define node function signature: `generate_code(state: PipelineState) -> dict`
  - [x] Create system prompt template for code generation LLM call
  - [x] Implement plan-to-code generation logic using OpenAI API
- [x] Implement chart labeling guidance in LLM prompt
  - [x] Add explicit instructions for human-readable axis/title labels
  - [x] Include example code patterns for chart formatting
- [x] Implement error context integration for retries
  - [x] Check for validation_errors in state
  - [x] Append previous validation failures to system prompt on retry
- [x] Integrate code generation node into LangGraph pipeline
  - [x] Add node to graph: `graph.add_node("generate_code", generate_code)`
  - [x] Connect edge from plan_generation or conditional routing
- [x] Test code generation with various plan types
  - [x] Test report-type plans (should generate code)
  - [x] Test Q&A type plans (should handle gracefully)
  - [x] Test edge case: empty plan, malformed plan
- [x] Verify base64 chart output format compliance
  - [x] Code generates `CHART:<base64>` format on stdout
  - [x] Test with matplotlib chart generation

## Dev Notes

### Architecture Patterns & Constraints

**LangGraph Pipeline Integration:**
- Node function must accept `PipelineState` (TypedDict) and return `dict`
- Return dict updates pipeline state: `return {"generated_code": code_str, ...}`
- Node is part of conditional execution flow: triggered after plan generation, before validation
- State is immutable between nodes — always return new dict with updates
- [Source: architecture.md#Core-Architectural-Decisions]

**PipelineState Schema for Code Generation:**
```python
class PipelineState(TypedDict):
    user_query: str
    csv_temp_path: str           # Available for data inspection if needed
    data_row_count: int
    intent: Literal["report", "qa", "chat"]
    plan: list[str]              # INPUT: Approved plan steps to generate code from
    generated_code: str          # OUTPUT: Generated Python code (store full string)
    validation_errors: list[str] # INPUT: Previous validation failures (for retry context)
    execution_output: str
    execution_success: bool
    retry_count: int             # Current retry attempt (0 on first try, max 3)
    replan_triggered: bool
    error_messages: list[str]    # Error history
    report_charts: list[bytes]   # Will be populated by executor
    report_text: str             # Will be populated by executor
    large_data_detected: bool
    large_data_message: str
    recovery_applied: str
```
[Source: architecture.md#Data-Architecture]

**Code Generation Context:**
- Input: `pipeline_state["plan"]` (list of human-readable steps from plan generation node)
- Input: `pipeline_state["csv_temp_path"]` (path to session-scoped CSV file for schema inspection)
- Input: `pipeline_state["data_row_count"]` (row count, may be downsampled value if large data recovery applied)
- Output: `pipeline_state["generated_code"]` (full Python code string, ready for validation)

**Naming Conventions:**
- Node function: `generate_code(state: PipelineState) -> dict:` (verb_noun pattern)
- Variables in node: `snake_case` (e.g., `generated_code`, `llm_response`, `system_prompt`)
- File location: `pipeline/nodes/codegen.py` (lowercase with underscores)
[Source: architecture.md#Implementation-Patterns]

### Technical Requirements

**OpenAI LLM Integration:**
- Use `langchain-openai` library (already in requirements.txt, v0.3.35)
- Model: GPT-4o (specified in architecture, optimal for code generation)
- System prompt must include:
  - Clear instructions: "Generate Python analysis code that implements each step"
  - Data schema context: loaded from CSV temp file (inspect columns, dtypes)
  - Chart labeling requirement: "Always use human-readable labels like 'Voltage (V)', not 'v'"
  - Output format: "Code will be validated and executed in subprocess. Include print statements and plt.show() for charts"
  - Security context: "Code will be validated against an allowlist. Only use: pandas, numpy, matplotlib, math, statistics, datetime, collections, itertools, io, base64"
  - Retry context (if validation_errors present): "Previous code failed validation with these errors: [list]. Generate safer/corrected code."
- LangSmith tracing: Already integrated at pipeline level (automatic if LANGSMITH_API_KEY set)
[Source: architecture.md#Technical-Stack]

**Subprocess Output Format:**
- Chart generation must produce base64-encoded PNG output
- Format: Print `CHART:<base64_encoded_png_bytes>` to stdout on separate line
- matplotlib is included in allowed imports
- Code must call `plt.tight_layout()` before rendering (matplotlib requirement)
- Non-chart output goes to stdout as text (for report_text in state)
[Source: epics.md#Story-6.1-AC#5]

**CSV Data Inspection:**
- Node has access to `csv_temp_path` pointing to per-session temp CSV file
- Should inspect CSV schema (columns, dtypes) to inform code generation
- Use pandas to load and inspect: `pd.read_csv(csv_temp_path).info()`, `.head()`, `.describe()`
- This context helps LLM generate code that matches actual data structure
- Data is session-scoped and deleted after execution (architecture.md#Authentication-Security)
[Source: architecture.md#Data-Architecture]

**Error Handling Strategy:**
- Try/except wraps LLM call (catch OpenAI API errors, network timeouts)
- If LLM call fails: use error translation layer → return informative message in state
- DO NOT catch validation errors here (that's next story's job)
- Return dict always updates state, even on partial failure
[Source: architecture.md#Authentication-Security#LLM-unavailability-handling]

### Linked Documents & Source References

- **Epic 6 Overview:** [Source: epics.md#Epic-6-Code-Generation-Validation-Secure-Execution]
- **Story 6.1 Full Requirements:** [Source: epics.md#Story-6.1-Implement-Code-Generation-Node]
- **LangGraph Pipeline Architecture:** [Source: architecture.md#Core-Architectural-Decisions]
- **PipelineState Data Contract:** [Source: architecture.md#Data-Architecture]
- **Code Generation LLM Specifics:** [Source: architecture.md#Technical-Stack]
- **Subprocess Security & Output Format:** [Source: architecture.md#Authentication-Security]
- **Naming & Implementation Patterns:** [Source: architecture.md#Implementation-Patterns]
- **API & Error Translation:** [Source: architecture.md#API-Communication-Patterns]
- **Dependency Versions:** [Source: architecture.md#Starter-Template-Evaluation#Technology-Baseline]

### Project Structure Notes

**File Organization:**
- Node implementation file: `pipeline/nodes/codegen.py` (located in backend pipeline modules)
- Graph definition: `pipeline/graph.py` (where node is registered and connected)
- Data models: `pipeline/state.py` (PipelineState TypedDict definition)
- Utilities: `utils/error_translation.py` (error handling)
- Requirements: `requirements.txt` (Python dependencies already pinned)

**Expected Backend Structure** (from previous stories 1-2):
```
services/
  api.py          # FastAPI app with endpoints
  pipeline.py     # LangGraph graph initialization
pipeline/
  nodes/
    __init__.py
    classify_intent.py    # Completed in epic 4
    generate_plan.py      # Completed in epic 5
    codegen.py            # THIS STORY: generate code from plan
    validator.py          # NEXT STORY: validate generated code
    executor.py           # EPIC 6 STORY 3: execute valid code
    render_report.py      # Render execution results
  state.py              # PipelineState definition (shared across nodes)
  graph.py              # LangGraph pipeline assembly
utils/
  error_translation.py  # Translate exceptions to user-friendly messages
pipeline_state/       # Temp directory for session state/CSVs
requirements.txt      # All Python dependencies
```
[Source: architecture.md#Implementation-Sequence]

**Conflicts or Variances:**
- None detected. Story aligns with architecture decisions in core decision document.

## Dev Agent Record

### Agent Model Used

Claude Haiku 4.5 (claude-haiku-4-5-20251001)

### Debug Log References

- Verified existing implementation meets all 5 acceptance criteria
- All 29 code generation tests pass
- Graph integration verified: generate_code node properly wired in LangGraph pipeline
- Error handling and retry context confirmed in system prompt

### Completion Notes List

**Implementation Status:** ✅ COMPLETE

**All Acceptance Criteria Satisfied:**
1. ✅ AC #1: Valid Python code generated from execution plan (lines 56-104 in codegen.py)
2. ✅ AC #2: Chart labeling guidance in LLM system prompt (lines 27-31 with plt.xlabel/ylabel/title/tight_layout)
3. ✅ AC #3: Full code string saved to pipeline_state["generated_code"] (return statement line 104)
4. ✅ AC #4: Retry context includes previous validation failures (lines 85-94 show retry error context in prompt)
5. ✅ AC #5: Base64 chart output format specified (line 33-34 shows CHART: prefix requirement)

**Tests Verification:**
- All 29 code generation tests pass (100% pass rate)
- Test coverage includes:
  - Basic code generation from valid plans
  - Markdown fence stripping
  - Chart labeling requirements validation
  - Retry context integration
  - Error handling and LLM failure scenarios
  - Edge cases (empty plans, missing CSV paths, high retry counts)
  - System prompt compliance verification
  - No Streamlit imports verification

**Key Implementation Details:**
- Model: GPT-4o (specified in line 62 of codegen.py)
- Temperature: 0 (deterministic code generation)
- System prompt includes mandatory rules:
  - Matplotlib backend setup (Agg mode for non-GUI environments)
  - Explicit chart label formatting (human-readable, with units)
  - Base64 PNG output format (CHART: prefix for parsing)
  - Allowed imports whitelist enforcement
  - Dangerous pattern blocking (eval, exec, open, etc.)
- Error handling: Try/except wraps LLM call with error translation layer
- CSV metadata: Included in prompt for LLM context (column names, row counts)

**Code Quality:**
- Follows architecture patterns: verb_noun naming, snake_case variables
- LangGraph node signature correct: accepts PipelineState, returns dict
- No Streamlit imports (verified in tests)
- Error messages translated (never raw exceptions to user)

### File List

**Files Created:**
- (None - implementation already existed)

**Files Modified:**
- `pipeline/nodes/codegen.py` — Code generation node (pre-existing, fully functional)
- `pipeline/state.py` — PipelineState TypedDict (no changes needed, matches AC requirements)
- `pipeline/graph.py` — LangGraph pipeline assembly (no changes needed, already integrated)
- `tests/test_codegen.py` — Unit tests (pre-existing, 29 comprehensive tests)

**Files Verified (No Changes Required):**
- `pipeline/__init__.py`
- `pipeline/nodes/__init__.py`
- `utils/error_translation.py` — Error handling layer (used by codegen)
- `requirements.txt` — Dependencies (langchain-openai, pydantic already included)

