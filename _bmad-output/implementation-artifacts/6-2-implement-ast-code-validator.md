# Story 6.2: Implement AST-Based Code Validator

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want the system to validate generated code before execution to catch syntax errors and unsafe operations,
So that only safe, valid code reaches the subprocess.

## Acceptance Criteria

1. **Given** generated Python code
   **When** `validate_code()` runs in `pipeline/nodes/validator.py`
   **Then** it returns a tuple: `(is_valid: bool, errors: list[str])`

2. **Given** code with a syntax error
   **When** `validate_code()` runs
   **Then** it catches the SyntaxError via AST parsing and returns `(False, ["Syntax error: ..."])`

3. **Given** code with an import outside the allowlist
   **When** `validate_code()` runs with AST analysis
   **Then** it detects the import and returns `(False, [error_message])` — only these imports are permitted: `pandas`, `numpy`, `matplotlib`, `matplotlib.pyplot`, `math`, `statistics`, `datetime`, `collections`, `itertools`, `io`, `base64`

4. **Given** code with blocked patterns
   **When** `validate_code()` checks for dangerous operations
   **Then** it detects and rejects: `eval()`, `exec()`, `__import__()`, `open()` with write modes, `os.*`, `sys.*`, `subprocess.*`, `socket.*`, `urllib.*`, `requests.*`

5. **Given** valid, safe code
   **When** `validate_code()` runs
   **Then** it returns `(True, [])`

6. **Given** a validation failure
   **When** the validator returns `(False, errors)`
   **Then** the error message is translated to plain English and the pipeline routes back to `generate_code` to retry (with retry count incremented)

## Tasks / Subtasks

- [x] Set up code validation node module (`pipeline/nodes/validator.py`)
  - [x] Define node function signature: `validate_code(state: PipelineState) -> dict`
  - [x] Implement AST parsing for syntax validation
  - [x] Create import allowlist and validation logic
- [x] Implement dangerous pattern detection
  - [x] Block eval(), exec(), __import__()
  - [x] Block open() with write modes (w, a, x)
  - [x] Block os.*, sys.*, subprocess.*, socket.*, urllib.*, requests.*
  - [x] Build AST visitor for pattern detection
- [x] Implement validation error messages
  - [x] Generate clear error messages for each failure type
  - [x] Include context (line numbers, problematic code)
- [x] Integrate validator node into LangGraph pipeline
  - [x] Add node to graph: `graph.add_node("validate_code", validate_code)`
  - [x] Connect conditional edge from generate_code
- [x] Test code validation with various code samples
  - [x] Test valid code (returns True)
  - [x] Test syntax errors
  - [x] Test import violations
  - [x] Test dangerous patterns
  - [x] Test edge cases

## Dev Notes

### Architecture Patterns & Constraints

**LangGraph Pipeline Integration:**
- Node function must accept `PipelineState` (TypedDict) and return `dict`
- Return dict updates pipeline state: `return {"validation_errors": errors, ...}`
- Node is part of conditional execution flow: triggered after code generation, routes back to generate_code on failure or forward to executor on success
- State is immutable between nodes — always return new dict with updates
- [Source: architecture.md#Core-Architectural-Decisions]

**PipelineState Schema for Code Validation:**
```python
class PipelineState(TypedDict):
    user_query: str
    csv_temp_path: str
    data_row_count: int
    intent: Literal["report", "qa", "chat"]
    plan: list[str]
    generated_code: str          # INPUT: Code to validate
    validation_errors: list[str] # OUTPUT: List of validation failures
    execution_output: str
    execution_success: bool
    retry_count: int             # Current retry attempt (0 on first try, max 3)
    replan_triggered: bool
    error_messages: list[str]    # Error history
    report_charts: list[bytes]
    report_text: str
    large_data_detected: bool
    large_data_message: str
    recovery_applied: str
```
[Source: architecture.md#Data-Architecture]

**Code Validation Strategy:**
- Input: `pipeline_state["generated_code"]` (Python code string from code generation node)
- Output: `pipeline_state["validation_errors"]` (list of error strings, empty if valid)
- Validation happens synchronously before execution
- Validator acts as security gatekeeper before subprocess execution
- Two-layer security model: validator + subprocess sandbox (architecture.md#Authentication-Security)
[Source: epics.md#Story-6.2-Implement-AST-Based-Code-Validator]

**Naming Conventions:**
- Node function: `validate_code(state: PipelineState) -> dict:` (verb_noun pattern)
- Variables in node: `snake_case` (e.g., `is_valid`, `error_list`, `ast_tree`)
- File location: `pipeline/nodes/validator.py` (lowercase with underscores)
[Source: architecture.md#Implementation-Patterns]

### Technical Requirements

**AST-Based Validation:**
- Use Python's built-in `ast` module (no external dependencies needed)
- Parse code with `ast.parse()` to catch syntax errors immediately
- Create custom AST.NodeVisitor subclass to traverse and analyze code structure
- Visitor pattern allows systematic checking of all nodes in the AST tree
- This approach is more reliable than regex or string matching
[Source: epics.md#Story-6.2-AC#2]

**Import Allowlist Validation:**
- Permitted imports (ONLY these are allowed):
  - `pandas`, `numpy`, `matplotlib`, `matplotlib.pyplot`
  - `math`, `statistics`, `datetime`, `collections`, `itertools`
  - `io`, `base64`
- Implementation approach:
  1. Walk AST to find all Import and ImportFrom nodes
  2. Extract module names (e.g., from `import pandas as pd`, extract `pandas`)
  3. Check against allowlist; reject if not found
  4. Handle both `import X` and `from X import Y` patterns
- Error message format: `"Unsafe import '{module}' not in allowlist. Only these are permitted: pandas, numpy, matplotlib, ..."`
[Source: epics.md#Story-6.2-AC#3]

**Dangerous Pattern Detection:**
- Block function calls: `eval()`, `exec()`, `__import__()`
  - These allow arbitrary code execution and bypass validation
  - Walk AST for all Call nodes, check func attribute against blocklist
- Block `open()` with write modes: `w`, `a`, `x`, `wb`, `ab`, `xb`
  - Check Call nodes with func.id == "open"
  - If 2nd arg (mode) is present and contains write chars → reject
  - `open()` for reading (default or explicit 'r') is safe
- Block module wildcards: `os.*`, `sys.*`, `subprocess.*`, `socket.*`, `urllib.*`, `requests.*`
  - Any import from these modules is rejected
  - Covers both: `import os` and `from os import ...`
- Error message format: `"Dangerous pattern detected: {pattern}. Not permitted in validated code."`
[Source: epics.md#Story-6.2-AC#4]

**Validation Return Signature:**
- Always return tuple: `(is_valid: bool, errors: list[str])`
- If validation passes: `(True, [])`
- If validation fails: `(False, [list of error messages])`
- Each error message should be clear and actionable
- Include context where possible (e.g., line numbers from AST nodes)
[Source: epics.md#Story-6.2-AC#1,5]

**Error Handling Strategy:**
- Catch `SyntaxError` from `ast.parse()` → convert to readable message with line info
- Catch any other exceptions during validation → log and return generic "validation failed" error
- DO NOT let exceptions propagate (validator should always return tuple, never raise)
- All errors will be translated to user-friendly messages by error translation layer (story 6.4)
- Store errors in state for retry context in code generation (story 6.1 pattern)
[Source: architecture.md#Authentication-Security#LLM-unavailability-handling]

**LangGraph Integration Pattern (from Story 6.1):**
- Node receives updated state with `generated_code` from previous node
- Node validates and returns dict: `{"validation_errors": errors, ...}`
- If errors present, pipeline conditional edge routes back to `generate_code` node
- If no errors, pipeline routes forward to `execute_code` node (next story)
- Conditional routing function determines path based on validation results
[Source: architecture.md#Core-Architectural-Decisions]

### Previous Story Intelligence

**Story 6.1: Code Generation Context & Learnings**
- Code generation uses GPT-4o with temperature 0 for deterministic output
- System prompt includes detailed constraints that LLM should follow
- Generated code includes full imports and logic (not just function definitions)
- Output format for charts: `CHART:<base64_encoded_png>` prefix for stdout parsing
- CSV schema inspection is included in code generation context
- Error context from validation failures is fed back to code generation prompt for retry
- Key pattern: Always return dict with updated state fields (immutable pattern)

**Critical Pattern for This Story:**
- The validator's error messages become input to next code generation attempt
- Code generation node checks `validation_errors` in state and includes them in retry prompt
- This creates feedback loop: generate → validate → regenerate with error context
- Therefore, error messages must be clear enough for LLM to understand and correct
- Avoid cryptic technical messages; favor descriptive, actionable errors

**Files Modified in Story 6.1:**
- `pipeline/nodes/codegen.py` — Code generation implementation
- `pipeline/graph.py` — LangGraph assembly (shows pattern for adding/connecting nodes)
- Tests validate system prompt, retry logic, base64 output format
[Source: 6-1-implement-code-generation-node.md]

### Linked Documents & Source References

- **Epic 6 Overview:** [Source: epics.md#Epic-6-Code-Generation-Validation-Secure-Execution]
- **Story 6.2 Full Requirements:** [Source: epics.md#Story-6.2-Implement-AST-Based-Code-Validator]
- **LangGraph Pipeline Architecture:** [Source: architecture.md#Core-Architectural-Decisions]
- **PipelineState Data Contract:** [Source: architecture.md#Data-Architecture]
- **Security Model (2-layer validation):** [Source: architecture.md#Authentication-Security]
- **Naming & Implementation Patterns:** [Source: architecture.md#Implementation-Patterns]
- **Story 6.1 Implementation Reference:** [Source: 6-1-implement-code-generation-node.md#Dev-Notes]

### Project Structure Notes

**File Organization:**
- Node implementation file: `pipeline/nodes/validator.py` (NEW - create this)
- Graph definition: `pipeline/graph.py` (UPDATE - add node and conditional edge)
- Data models: `pipeline/state.py` (no changes needed - PipelineState already correct)
- Utilities: `utils/error_translation.py` (used for error message translation)
- Tests: `tests/test_validator.py` (NEW - comprehensive test coverage)
- Requirements: `requirements.txt` (no changes - `ast` is built-in)

**Expected Backend Structure** (from previous stories):
```
services/
  api.py          # FastAPI app with endpoints
  pipeline.py     # LangGraph graph initialization
pipeline/
  nodes/
    __init__.py
    classify_intent.py    # Completed in epic 4
    generate_plan.py      # Completed in epic 5
    codegen.py            # Story 6.1: generate code from plan
    validator.py          # THIS STORY: validate generated code
    executor.py           # NEXT STORY: execute valid code
    render_report.py      # Render execution results
  state.py              # PipelineState definition (shared across nodes)
  graph.py              # LangGraph pipeline assembly
utils/
  error_translation.py  # Translate exceptions to user-friendly messages
pipeline_state/         # Temp directory for session state/CSVs
requirements.txt        # All Python dependencies
```
[Source: architecture.md#Implementation-Sequence]

**Graph Integration Pattern (from Story 6.1):**
```python
# In pipeline/graph.py
from pipeline.nodes.validator import validate_code

# Add validator node
graph.add_node("validate_code", validate_code)

# Connect from code generation
graph.add_edge("generate_code", "validate_code")

# Add conditional edge for retry/forward routing
def route_after_validation(state: PipelineState) -> str:
    if state["validation_errors"]:
        return "generate_code"   # retry with error context
    else:
        return "execute_code"    # proceed to execution

graph.add_conditional_edges(
    "validate_code",
    route_after_validation,
    {
        "generate_code": "generate_code",
        "execute_code": "execute_code",
    }
)
```
[Source: architecture.md#Core-Architectural-Decisions]

**Conflicts or Variances:**
- None detected. Story aligns with architecture decisions and Story 6.1 implementation patterns.

## Dev Agent Record

### Agent Model Used

Claude Haiku 4.5 (claude-haiku-4-5-20251001)

### Debug Log References

- Story context created from comprehensive artifact analysis (2026-03-27)
- Epic 6 architecture reviewed for security model and two-layer validation strategy
- Story 6.1 analyzed for LangGraph patterns and state management
- AST validation approach selected as most robust pattern detection mechanism
- Implementation verified: All 57 validator tests pass (100% pass rate)
- Graph integration verified: validate_code_node properly wired in LangGraph pipeline
- Error translation verified: SyntaxError and AllowlistViolationError handling confirmed

### Completion Notes List

**Implementation Status:** ✅ COMPLETE

**Story Created:** 2026-03-27
**Implementation Verified:** 2026-03-27

**All Acceptance Criteria Satisfied:**
1. ✅ AC #1: `validate_code()` returns tuple `(is_valid: bool, errors: list[str])` (validator.py line 59)
2. ✅ AC #2: Syntax errors caught via AST parsing, returns `(False, ["Syntax error: ..."])` (line 69-72)
3. ✅ AC #3: Import allowlist enforced - only pandas, numpy, matplotlib, matplotlib.pyplot, math, statistics, datetime, collections, itertools, io, base64 permitted (line 92-109)
4. ✅ AC #4: Dangerous patterns detected: eval(), exec(), __import__(), open() blocked; os.*, sys.*, subprocess.*, socket.*, urllib.*, requests.* blocked (line 112-134)
5. ✅ AC #5: Valid code returns `(True, [])` (line 136-138)
6. ✅ AC #6: Validation failures routed to error translation layer and pipeline retry loop (validate_code_node line 141-170)

**Tests Verification:**
- ✅ All 57 validator tests pass (100% pass rate)
- ✅ Test coverage includes:
  - Valid code acceptance (3 tests)
  - Syntax error detection (2 tests)
  - Blocked imports (10 tests)
  - Allowed imports (16 tests)
  - Blocked function calls (5 tests)
  - Blocked namespace access (7 tests)
  - Multiple violations (2 tests)
  - LangGraph node wrapper (11 tests)
  - Streamlit boundary guard (1 test)

**Key Implementation Details:**
- **Pure AST Validator:** Uses Python's built-in `ast` module to parse and walk code AST—never executes code
- **Allowlist Pattern:** ALLOWED_IMPORTS frozenset with exact module names (line 23-35)
- **Dangerous Pattern Detection:** BLOCKED_CALLS and BLOCKED_NAMESPACES constants with _get_root_name() helper for attribute chain analysis (line 37-56)
- **Comprehensive Error Collection:** Walks entire AST tree collecting all violations (line 88-138), not just first error
- **Node Wrapper:** `validate_code_node` integrates with LangGraph, returns only changed keys per convention (line 141-170)
- **Error Translation:** SyntaxError → translate_error(SyntaxError), violations → translate_error(AllowlistViolationError) (line 155-161)
- **Graph Integration:** Node wired in pipeline/graph.py with edge from generate_code, conditional routing based on validation_errors (graph.py line 26, 92, 114-115)

**Code Quality:**
- Follows architecture patterns: verb_noun naming, snake_case variables, no Streamlit imports
- LangGraph node signature correct: accepts PipelineState, returns dict with only changed keys
- Error messages are clear and actionable for LLM retry context
- No external dependencies required (ast is built-in Python module)

### File List

**Files Created/Implemented:**
- `pipeline/nodes/validator.py` — AST-based code validation node (171 lines, fully functional)
- `tests/test_validator.py` — Comprehensive validator unit tests (436 lines, 57 tests, all passing)

**Files Modified:**
- `pipeline/graph.py` — Validator node integrated: import statement (line 26), node registration (line 92), edge routing (line 114-115)

**Files Verified (No Changes Required):**
- `pipeline/state.py` — PipelineState TypedDict (already includes validation_errors field)
- `utils/error_translation.py` — Error translation layer (used by validator for SyntaxError and AllowlistViolationError)
- `requirements.txt` — No new dependencies needed (ast is built-in Python module)

**Implementation Completeness:**
- ✅ Node function signature: `validate_code_node(state: PipelineState) -> dict` (line 141)
- ✅ Pure validator function: `validate_code(code: str) -> tuple[bool, list[str]]` (line 59)
- ✅ AST parsing for syntax validation (line 69-72)
- ✅ Import allowlist validation (line 92-109)
- ✅ Dangerous pattern detection (line 112-134)
- ✅ Error message generation (throughout)
- ✅ LangGraph integration (graph.py line 26, 92, 114-115)
- ✅ Comprehensive test coverage (57 tests, 100% passing)

