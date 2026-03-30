---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - '_bmad-output/planning-artifacts/product-brief-data-analysis-copilot-2026-03-05.md'
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/prd-validation-report.md'
  - '_bmad-output/planning-artifacts/ux-design-specification.md'
workflowType: 'architecture'
lastStep: 8
status: 'complete'
completedAt: '2026-03-08'
lastEdited: '2026-03-26'
editHistory:
  - date: '2026-03-26'
    changes: 'Replaced Streamlit UI with Next.js frontend + Python API backend architecture across all relevant sections. Restructured frontend as React SPA, backend as FastAPI REST server. Updated state management, project structure, boundaries, patterns, and deployment instructions.'
project_name: 'data-analysis-copilot'
user_name: 'Yan'
date: '2026-03-08'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
36 FRs across 9 categories:
- Data Input & Management (FR1–4): Multi-CSV upload, editable data table, session-scoped retention
- Natural Language Interface (FR5–9): Chat input, intent classification, plan generation, plan review, user-triggered execution
- Code Generation & Validation (FR10–13): Python code gen from plan, syntax/security/logic validation pre-execution
- Execution Engine (FR14–18): Isolated subprocess execution, failure detection, up to 3 retries + adaptive replanning, autonomous self-correction
- Report Output (FR19–22): Chart rendering, written trend analysis, stakeholder-readable labels, in-app display only
- Code Transparency (FR23–25): Code viewer, editable code, manual re-execution trigger
- Large Data Handling (FR26–29): Size detection, human-readable degradation message, at least one recovery path, no silent failures
- API Layer (FR30–33): REST endpoints for CSV upload, pipeline execution, plan/report retrieval; structured JSON responses; session-scoped state
- Observability (FR34–36): LangSmith tracing (env-var toggle), human-readable error output for developers

**Non-Functional Requirements:**
17 NFRs across 4 categories:
- Performance: Frontend loads <3s; backend ready <5s; plan displayed <30s (incl. API round-trip); full pipeline <15min; UI non-blocking during execution; size detection immediate; non-pipeline API endpoints <500ms
- Reliability: Standard workflow repeatable across runs; self-correction resolves most failures; no silent failures
- Security: Subprocess cannot access host filesystem beyond session dir; no outbound network calls from subprocess; code validated before execution; CSV data not persisted to disk; API keys from env vars only
- Integration: LLM unavailability → clear user error; LangSmith non-blocking; Python deps pinned via requirements.txt; frontend deps pinned via package.json; frontend handles backend unavailability gracefully

**Scale & Complexity:**
Brownfield stabilization + one new capability (large data handling). No multi-tenancy, no cloud deployment, no authentication. Locally hosted, single-user, session-scoped.

- Primary domain: Local web app + AI agent pipeline
- Complexity level: Medium
- Estimated architectural components: ~12 (Next.js Frontend, REST API Layer, Session State Schema, Intent Classifier, Plan Generator, LangGraph Pipeline, Code Validator, Execution Sandbox, Large Data Handler, Report Renderer, LangSmith Observer, API Client)

### Technical Constraints & Dependencies

**Existing stack (from codebase):**
- Next.js / React (frontend UI framework)
- FastAPI (Python REST API backend)
- LangGraph (state machine for agent pipeline)
- OpenAI API / GPT-4o (LLM for plan gen, code gen, self-correction)
- LangSmith (optional tracing, wrapped OpenAI client)
- pandas, matplotlib (data processing and chart rendering)
- Python subprocess (sandboxed code execution)
- dotenv (env var loading)

**Constraints:**
- No persistent storage (in-memory session state on backend, React state on frontend)
- No cloud deployment (localhost only)
- No dynamic library installation (pre-installed libs only in subprocess)
- No mobile breakpoints (desktop-first, 1280px min width)
- LangSmith must be optional and non-blocking
- Frontend communicates with backend exclusively via REST API

### Cross-Cutting Concerns Identified

1. **Async execution + frontend responsiveness** — the most critical architectural concern. Pipeline execution is long-running; the frontend must remain interactive during execution (NFR4). Backend runs pipeline asynchronously; frontend polls or receives status updates via API.
2. **Session state schema** — session data spans frontend (UI state, chat history) and backend (pipeline state, uploaded CSVs). The contract between them must be explicitly defined via API response schemas.
3. **Error translation layer** — every exception from LLM failures, code execution, and API timeouts must be caught and translated to plain English before reaching the user via API response (NFR8, FR29).
4. **Frontend state management** — React state manages UI-layer data (chat history, active tab, display preferences). Switching between Plan / Code / Template views must not re-trigger API calls. Data is cached in React state.
5. **Subprocess security boundary** — the sandbox is the primary security perimeter. Code validation (FR11–13) and subprocess restrictions (NFR9–10) must be consistent and enforced pre-execution.
6. **LangSmith non-blocking integration** — tracing must be wrapped in try/except; failure to reach LangSmith must not propagate to the user experience.
7. **Frontend-backend API contract** — REST API endpoints, request/response shapes, and error formats must be defined upfront so frontend and backend can be developed and tested independently.

## Starter Template Evaluation

### Primary Technology Domain

**Brownfield Python AI pipeline + new Next.js frontend** — the existing Python pipeline implementation is preserved; the UI is migrated from Streamlit to a Next.js (React) frontend communicating with a Python API backend via REST.

### Technology Baseline

**Frontend (Next.js):**
- Next.js (React) — SPA frontend, client-side rendering
- TypeScript — type-safe frontend code
- Code editor component (Monaco-based or CodeMirror) — code viewer/editor panel
- Fetch API — REST communication with Python backend

**Backend (Python API):**
- Python 3.12 runtime
- FastAPI — REST API framework with automatic OpenAPI docs
- uvicorn — ASGI server for FastAPI

**AI Agent Pipeline:**
- LangGraph 0.3.18 — state machine orchestration for the analysis pipeline
- LangChain 0.3.27 / langchain-core 0.3.83 — LLM tooling and abstractions
- langchain-openai 0.3.35 — OpenAI integration layer
- OpenAI SDK 1.109.1 — direct API client (GPT-4o)
- LangSmith 0.7.0 — optional tracing

**Data Processing & Visualization:**
- pandas 2.2.2 — CSV ingestion, data manipulation
- numpy 1.26.4 — numerical operations
- matplotlib 3.9.0 — chart generation inside subprocess

**Execution & Security:**
- Python `subprocess` (stdlib) — sandboxed code execution
- Python `ast` (stdlib) — syntax validation / static analysis

**Supporting Libraries:**
- pydantic 2.7.4 — data validation / typed state schemas, API request/response models
- python-dotenv 1.0.1 — env var loading

### Architectural Decisions Established by Stack

| Decision Area | Established Choice |
|---|---|
| Language & Runtime | Python 3.12 backend; TypeScript/React frontend |
| Frontend Framework | Next.js (React) — component-based SPA, client-side state management |
| Backend Framework | FastAPI — async REST API server, Pydantic models for request/response validation |
| State Management | React state (frontend UI state); in-memory session dict (backend pipeline state) |
| AI Pipeline Orchestration | LangGraph `StateGraph` — nodes are discrete pipeline stages; edges define retry/replan routing |
| LLM | OpenAI GPT-4o via `langchain-openai`, wrapped with LangSmith for optional tracing |
| Code Execution Sandbox | Python `subprocess` with restriction constraints — primary security boundary |
| Code Editor | Monaco/CodeMirror React component — embedded in Code panel |
| Dependency Management | `requirements.txt` (Python backend); `package.json` (Next.js frontend) — both fully pinned |
| API Communication | REST API with JSON responses; base64-encoded chart images in payloads |

### Dependency Cleanup

1. **langchain-experimental / PythonREPLTool** — currently imported but executes in-process without isolation. The `subprocess` sandbox is the correct production path. PythonREPLTool should be removed from the execution flow.
2. **duckduckgo_search** — imported and wired but out of MVP scope. Should be removed or explicitly gated to avoid unused dependency surface.
3. **Streamlit and related packages** (`streamlit`, `streamlit-ace`, `streamlit-chat`) — removed entirely; replaced by Next.js frontend + FastAPI backend.

**Note:** First implementation story should resolve dependency cleanup before extending functionality.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
1. REST API contract — endpoint definitions, request/response schemas, error format (unblocks independent frontend/backend development)
2. LangGraph `PipelineState` schema — typed data contract across all graph nodes
3. Frontend state management — React state structure for UI-layer data; API client for backend communication

**Important Decisions (Shape Architecture):**
4. Subprocess security — import allowlist + per-session temp dir sandbox
5. Large data handling — dual threshold + uniform stride downsampling
6. Template persistence — `templates.json` (scoped exception to no-persistence constraint)
7. Backend session management — in-memory session store keyed by session ID

**Deferred Decisions (Post-MVP):**
- Report export (PDF/PNG) — explicitly out of scope
- Session persistence across refreshes — out of scope
- Cloud deployment / CI/CD — out of scope

### Data Architecture

**Frontend State (React):**

```typescript
interface AppState {
  sessionId: string;                              // generated on app load, sent with all API calls
  uploadedFiles: { name: string; preview: any[] }[]; // filename + preview rows for data table
  chatHistory: { role: "user" | "bot"; content: string }[];
  activeTab: "plan" | "code" | "template";
  pipelineRunning: boolean;
  planApproved: boolean;
  currentPlan: string[] | null;                   // fetched from API after plan generation
  currentCode: string | null;                     // fetched from API; editable in code panel
  reportCharts: string[];                         // base64 PNG strings from API
  reportText: string | null;                      // trend analysis text from API
  savedTemplates: { name: string; plan: string[]; code: string }[];
  activeTemplate: { name: string; plan: string[]; code: string } | null;
  errorMessage: string | null;                    // user-facing error from API
  largeDataMessage: string | null;                // large data warning from API
}
```

**Backend Session State (in-memory dict per session):**

```python
{
    "session_id": str,
    "uploaded_dfs": dict[str, pd.DataFrame],  # filename → DataFrame
    "csv_temp_path": str | None,              # path to per-session temp CSV file
    "pipeline_state": PipelineState | None,   # written back after graph.invoke()
    "pipeline_running": bool,
}
```

**LangGraph `PipelineState` (TypedDict flowing through all graph nodes):**

```python
class PipelineState(TypedDict):
    user_query: str
    csv_temp_path: str           # nodes load CSV from file as needed; not passed as data
    data_row_count: int
    intent: Literal["report", "qa", "chat"]
    plan: list[str]
    generated_code: str
    validation_errors: list[str]
    execution_output: str
    execution_success: bool
    retry_count: int             # max 3 before adaptive replan (FR16)
    replan_triggered: bool
    error_messages: list[str]    # translated error history (FR29)
    report_charts: list[bytes]   # PNG bytes via BytesIO from subprocess (FR19)
    report_text: str             # written trend analysis (FR20)
    large_data_detected: bool
    large_data_message: str
    recovery_applied: str
```

**Template Persistence:**
- Storage: `templates.json` in backend app root directory
- Format: `[{"name": str, "plan": list[str], "code": str}]`
- Loaded by backend on startup; served to frontend via API
- Written on "Save as Template" user action via API endpoint
- Rationale: deliberate scoped exception to no-persistence constraint — templates are user-created reusable assets

### Authentication & Security

**No authentication** — internal tool, single user, localhost only. Out of scope for MVP.

**Subprocess Security — two-layer model:**

**Layer 1 — AST pre-execution allowlist validation:**
- Permitted imports: `pandas`, `numpy`, `matplotlib`, `matplotlib.pyplot`, `math`, `statistics`, `datetime`, `collections`, `itertools`, `io`, `base64`
- Any import outside this list → validation failure → LangGraph retry with corrected prompt
- Blocked patterns: `eval()`, `exec()`, `__import__()`, `open()` with write modes, `os.*`, `sys.*`, `subprocess.*`, `socket.*`, `urllib.*`, `requests.*`

**Layer 2 — Subprocess launch constraints:**
- Working directory: `tempfile.mkdtemp()` per session — subprocess restricted to this dir only (NFR9)
- Env vars: no inheritance from parent process except whitelisted `PATH`, `PYTHONPATH`
- Timeout: 60 seconds enforced — runaway execution killed
- stdout/stderr: fully captured; never raw-displayed to user — error translation layer applied (NFR8)
- Subprocess cannot write to `templates.json` or any path outside its temp dir (NFR12)

### API & Communication Patterns

**REST API Layer (FastAPI backend):**

| Endpoint | Method | Purpose | Response |
|---|---|---|---|
| `/api/session` | POST | Create new session | `{ session_id }` |
| `/api/upload` | POST | Upload CSV files | `{ filenames, row_counts, large_data_warning? }` |
| `/api/data` | GET | Get uploaded data preview | `{ files: [{ name, columns, rows }] }` |
| `/api/data` | PUT | Update edited data | `{ success }` |
| `/api/chat` | POST | Submit NL query | `{ intent, plan?, response? }` |
| `/api/execute` | POST | Trigger plan execution | `{ status: "started" }` |
| `/api/status` | GET | Poll pipeline status | `{ running, step?, progress? }` |
| `/api/report` | GET | Get execution results | `{ charts: [base64], text, code, errors? }` |
| `/api/code` | PUT | Submit edited code | `{ success }` |
| `/api/rerun` | POST | Re-execute edited code | `{ status: "started" }` |
| `/api/templates` | GET/POST | List/save templates | `{ templates: [...] }` |

**API Response Format (all endpoints):**
```json
{
  "status": "success" | "error",
  "data": { ... },
  "error": { "message": "user-facing message", "code": "ERROR_TYPE" }
}
```

**External API Integrations:**
- OpenAI API via `langchain-openai` — LLM calls for intent classification, plan generation, code generation, self-correction
- LangSmith tracing API — optional, non-blocking, always wrapped in `try/except`

**LangSmith integration pattern (NFR15):**
```python
try:
    # tracing call
except Exception:
    pass  # always silent — failure never surfaces to user
```

**LLM unavailability handling (NFR14):**
`OpenAI APIError` caught at pipeline entry point, translated to plain English message returned via API:
> "Unable to reach the AI service. Please check your API key and internet connection."

### Frontend Architecture

**Async execution model:** Frontend sends execution request to backend API, then polls `/api/status` for progress. The UI remains fully interactive during pipeline execution (NFR4). No page reloads required — React state updates drive re-renders.

**Four-panel layout:**
| Position | Panel | React Component |
|---|---|---|
| Top-left | Chat (fixed input, scrollable history) | Custom chat component with input + message list |
| Top-right | Plan / Code / Template tabs | Tab component with lazy-loaded content panels |
| Bottom-left | CSV uploader + editable data table | File dropzone + data grid component |
| Bottom-right | Report (charts + trend text) | Image renderer (base64 → `<img>`) + markdown/text display |

**Tab state preservation:** Plan, Code, and Template content stored in React state — tab switches never re-trigger API calls (cross-cutting concern #4).

**Execution progress:** Status polling displays step-level pipeline progress: _Classifying intent → Generating plan → Validating code → Executing → Rendering report_.

**Large data user message pattern (FR27–28):**
Inline message in report panel (no modals — anti-pattern per UX spec):
> "Your dataset has X rows / Y MB, which exceeds the visualization threshold. Automatically downsampling to 10,000 points using uniform stride. You can also filter your data in the table before running."

**Backend unavailability handling (NFR17):**
Frontend displays a clear connection error message when API calls fail — no blank screens or unhandled exceptions.

### Infrastructure & Deployment

- **Backend hosting:** Localhost only — `uvicorn services.api:app --reload`
- **Frontend hosting:** Localhost only — `npm run dev` (Next.js dev server)
- **No CI/CD, no Docker, no cloud** — out of scope for MVP
- **Environment config:** `.env` file via `python-dotenv` (backend)
  - Required: `OPENAI_API_KEY`
  - Optional: `LANGSMITH_API_KEY` (tracing disabled if absent)
- **Dependency management:** `requirements.txt` (Python backend) fully pinned; `package.json` (Next.js frontend) with lockfile

### Decision Impact Analysis

**Implementation Sequence:**
1. Dependency cleanup (remove Streamlit, streamlit-ace, streamlit-chat; add FastAPI, uvicorn)
2. Set up Next.js frontend project with TypeScript
3. Define `PipelineState` TypedDict and LangGraph graph skeleton
4. Implement FastAPI REST endpoints and session management
5. Implement allowlist code validator (AST-based)
6. Implement subprocess sandbox with per-session temp dir
7. Implement large data detector (dual threshold check on upload)
8. Implement uniform stride downsampler + API response with warning
9. Implement frontend components (chat, data table, plan/code tabs, report panel)
10. Implement API client and status polling in frontend
11. Implement template save/load with `templates.json` via API

**Cross-Component Dependencies:**
- API contract (story 4) must be defined before frontend API client (story 10)
- `csv_temp_path` in `PipelineState` is set during session init → session management (story 4) must precede pipeline stories
- Allowlist validator runs before subprocess launch → validator (story 5) is a hard dependency of executor (story 6)
- Large data detection runs on CSV upload, before pipeline starts → story 7 must precede execution stories
- `templates.json` is the only intentional disk write → subprocess sandbox (story 6) must explicitly exclude this path

## Implementation Patterns & Consistency Rules

### Critical Conflict Points: 8 areas where AI agents could make different choices

### Naming Patterns

**Python conventions (applies everywhere):**
- Functions and variables: `snake_case` — e.g. `generate_plan`, `csv_temp_path`, `retry_count`
- Classes: `PascalCase` — e.g. `PipelineState`, `CodeValidator`
- Constants: `UPPER_SNAKE_CASE` — e.g. `MAX_RETRY_COUNT = 3`, `LARGE_DATA_ROW_THRESHOLD = 100_000`
- Private helpers: single leading underscore — e.g. `_translate_error`, `_build_prompt`

**Backend session state key naming — always `snake_case` string literals:**
```python
# CORRECT
sessions[session_id]["pipeline_running"]
sessions[session_id]["uploaded_dfs"]

# WRONG — never camelCase
sessions[session_id]["pipelineRunning"]  # ❌
```

**Frontend React state — `camelCase` (TypeScript convention):**
```typescript
// CORRECT
const [pipelineRunning, setPipelineRunning] = useState(false);
const [chatHistory, setChatHistory] = useState<Message[]>([]);

// WRONG — never snake_case in TypeScript
const [pipeline_running, set_pipeline_running] = useState(false);  // ❌
```

**LangGraph node function naming — verb_noun pattern:**
```python
# CORRECT
def classify_intent(state: PipelineState) -> dict: ...
def generate_plan(state: PipelineState) -> dict: ...
def generate_code(state: PipelineState) -> dict: ...
def validate_code(state: PipelineState) -> dict: ...
def execute_code(state: PipelineState) -> dict: ...
def handle_error(state: PipelineState) -> dict: ...
def render_report(state: PipelineState) -> dict: ...

# WRONG — noun_verb, gerunds, vague names
def code_generator(state): ...   # ❌
def running_code(state): ...     # ❌
def process(state): ...          # ❌
```

**LangGraph edge/node string identifiers — match function names exactly:**
```python
graph.add_node("classify_intent", classify_intent)   # string = function name
graph.add_edge("classify_intent", "generate_plan")
```

### Structure Patterns

**Module organisation (two-tier: Next.js frontend + Python API backend):**
```
frontend/                     # Next.js frontend application
    package.json
    tsconfig.json
    next.config.js
    src/
        app/                  # Next.js app directory
            page.tsx          # Main SPA page
            layout.tsx        # Root layout
        components/
            ChatPanel.tsx     # Chat input + message history
            DataPanel.tsx     # CSV uploader + editable data table
            PlanCodeTabs.tsx  # Plan / Code / Template tabs
            ReportPanel.tsx   # Chart images + trend analysis text
            StatusIndicator.tsx  # Pipeline execution progress
        hooks/
            useApi.ts         # API client hook (fetch wrapper)
            usePolling.ts     # Status polling hook
        types/
            index.ts          # Shared TypeScript interfaces
        lib/
            api.ts            # API client functions

services/                     # Python API backend
    __init__.py
    api.py                    # FastAPI app + REST endpoints
    session.py                # In-memory session store + management

pipeline/                     # AI agent pipeline — NO FastAPI/frontend imports
    __init__.py
    state.py                  # PipelineState TypedDict definition
    graph.py                  # LangGraph graph construction and compilation
    nodes/
        __init__.py
        intent.py             # classify_intent node
        planner.py            # generate_plan node
        codegen.py            # generate_code node
        validator.py          # validate_code node
        executor.py           # execute_code node + subprocess sandbox
        reporter.py           # render_report node
        error_handler.py      # handle_error node

utils/
    __init__.py
    large_data.py             # threshold detection + downsampling
    error_translation.py      # exception → plain English messages
    templates.py              # templates.json read/write

templates.json                # persisted user templates
.env                          # API keys (not committed)
.env.example                  # Template for required env vars
requirements.txt              # pinned Python deps
```

**Backend session initialisation — always in one place (`services/session.py`):**
```python
from typing import Any

sessions: dict[str, dict[str, Any]] = {}

def create_session(session_id: str) -> dict[str, Any]:
    sessions[session_id] = {
        "session_id": session_id,
        "uploaded_dfs": {},
        "csv_temp_path": None,
        "pipeline_state": None,
        "pipeline_running": False,
    }
    return sessions[session_id]

def get_session(session_id: str) -> dict[str, Any] | None:
    return sessions.get(session_id)
```

### Format Patterns

**Chat message format — always this exact shape:**
```python
{"role": "user" | "bot", "content": str}

# WRONG
{"sender": "user", "text": "..."}    # ❌
{"type": "human", "message": "..."}  # ❌
```

**LangGraph node return — always return only changed keys (not full state):**
```python
def generate_plan(state: PipelineState) -> dict:
    return {"plan": [...], "intent": "report"}
    # NOT: return {**state, "plan": [...]}  — LangGraph merges automatically ❌
```

**Validation result — always return tuple `(is_valid: bool, errors: list[str])`:**
```python
def validate_code(code: str) -> tuple[bool, list[str]]:
    errors = []
    # ... AST checks ...
    return len(errors) == 0, errors

# Usage in node:
is_valid, errors = validate_code(state["generated_code"])
if not is_valid:
    return {"validation_errors": errors, "execution_success": False}
```

**Subprocess chart output — base64-encoded PNG via stdout, prefixed `CHART:`:**
```python
# Inside generated code (runs in subprocess):
import base64, io
buf = io.BytesIO()
plt.savefig(buf, format='png', bbox_inches='tight')
print("CHART:" + base64.b64encode(buf.getvalue()).decode())

# In executor.py — parse stdout for CHART: lines:
charts = []
for line in output.split('\n'):
    if line.startswith("CHART:"):
        charts.append(base64.b64decode(line[6:]))
return {"report_charts": charts, "execution_success": True}
```

### Communication Patterns

**Error translation — always through `utils/error_translation.py`, never inline:**
```python
# CORRECT
user_message = translate_error(exception)
return {"error_messages": state["error_messages"] + [user_message]}

# WRONG — never expose raw exceptions to API responses
raise HTTPException(detail=str(exception))    # ❌ raw exception
return {"error_messages": [repr(exception)]}  # ❌
```

**Error taxonomy (`translate_error` maps exceptions to these messages):**

| Exception type | User-facing message |
|---|---|
| `openai.APIError` | "Unable to reach the AI service. Check your API key and connection." |
| `openai.RateLimitError` | "AI service rate limit reached. Please wait a moment and try again." |
| `subprocess.TimeoutExpired` | "Analysis took too long and was stopped. Try a simpler request or subset your data." |
| `SyntaxError` in validation | "Generated code had a syntax error — retrying with a corrected approach." |
| Allowlist violation | "Generated code used a restricted operation — retrying with safer code." |
| All other `Exception` | "An unexpected error occurred. Check the developer console for details." |

**LangSmith tracing — `@traceable` on pipeline entry point only:**
```python
# pipeline/graph.py — trace the full pipeline invocation
@traceable(name="analysis_pipeline")
def run_pipeline(state: PipelineState) -> PipelineState:
    return compiled_graph.invoke(state)

# Individual nodes are NOT decorated — LangGraph traces them automatically
```

### Process Patterns

**Large data check — always on upload, never at execution time:**
```python
# In CSV upload API endpoint (services/api.py)
@app.post("/api/upload")
async def upload_csv(session_id: str, files: list[UploadFile]):
    session = get_session(session_id)
    dfs = {f.filename: pd.read_csv(f.file) for f in files}
    combined_rows = sum(len(df) for df in dfs.values())

    large_data_warning = None
    if combined_rows >= 100_000:
        large_data_warning = f"Dataset has {combined_rows:,} rows..."
        # ... apply downsampling before writing temp file

    session["uploaded_dfs"] = dfs
    return {"filenames": list(dfs.keys()), "large_data_warning": large_data_warning}
```

**Session state mutation — only in API layer or `services/session.py`; never inside `pipeline/`:**
```python
# CORRECT — API layer writes to session state after pipeline completes
session["pipeline_running"] = True
result = run_pipeline(state)
session["pipeline_state"] = result
session["pipeline_running"] = False

# WRONG — pipeline modules must never import or write to session store
from services.session import sessions  # ❌ inside pipeline/nodes/executor.py
sessions[sid]["result"] = ...          # ❌
```

### Enforcement Guidelines

**All AI agents MUST:**
- Use `snake_case` for all Python identifiers (functions, variables, session keys, node string names)
- Use `camelCase` for all TypeScript/React identifiers (variables, functions, props, state)
- Return only changed keys from LangGraph nodes — never spread full state
- Route all exceptions through `utils/error_translation.py` before any API response
- Never import `fastapi` or `services` inside `pipeline/` or `utils/` modules
- Never write to session store from inside `pipeline/` modules
- Use `(bool, list[str])` tuple as the return type of all validation functions
- Prefix subprocess chart output lines with `CHART:` + base64-encoded PNG bytes
- All frontend-backend communication via REST API — no direct pipeline imports in frontend

**Anti-patterns to explicitly avoid:**
```python
sessions[sid]["pipelineRunning"] = True        # ❌ camelCase key in Python
raise HTTPException(detail=str(e))             # ❌ raw exception to user
return {**state, "plan": new_plan}             # ❌ spreading full state from node
from services.session import sessions  # inside pipeline/  # ❌ service layer in pipeline
```
```typescript
const [pipeline_running, set_pipeline_running] = useState(false);  // ❌ snake_case in TypeScript
await fetch('/api/execute', { method: 'POST' });  // ❌ direct fetch without error handling
```

## Project Structure & Boundaries

### Complete Project Directory Structure

```
data-analysis-copilot/
├── requirements.txt              # Fully pinned Python backend dependencies
├── templates.json                # Persisted user templates (created on first save)
├── .env                          # API keys — never committed
├── .env.example                  # Template for required env vars
├── .gitignore
├── README.md
│
├── frontend/                     # Next.js frontend application
│   ├── package.json              # Frontend dependencies (pinned via lockfile)
│   ├── tsconfig.json
│   ├── next.config.js
│   └── src/
│       ├── app/
│       │   ├── page.tsx          # Main SPA page — four-panel layout
│       │   └── layout.tsx        # Root layout with metadata
│       ├── components/
│       │   ├── ChatPanel.tsx     # Chat input + scrollable message history
│       │   ├── DataPanel.tsx     # CSV file uploader + editable data grid
│       │   ├── PlanCodeTabs.tsx  # Plan / Code / Template tab panels
│       │   ├── ReportPanel.tsx   # Chart images (base64) + trend analysis text
│       │   └── StatusIndicator.tsx  # Pipeline execution progress display
│       ├── hooks/
│       │   ├── useApi.ts         # API client hook with error handling
│       │   └── usePolling.ts     # Status polling hook for pipeline execution
│       ├── types/
│       │   └── index.ts          # Shared TypeScript interfaces (AppState, Message, etc.)
│       └── lib/
│           └── api.ts            # API client functions (typed fetch wrappers)
│
├── services/                     # Python API backend
│   ├── __init__.py
│   ├── api.py                    # FastAPI app + REST endpoint definitions (FR30–33)
│   └── session.py                # In-memory session store + create/get helpers
│
├── pipeline/                     # AI agent pipeline — NO FastAPI/services imports
│   ├── __init__.py
│   ├── state.py                  # PipelineState TypedDict definition
│   ├── graph.py                  # LangGraph StateGraph construction + run_pipeline()
│   └── nodes/
│       ├── __init__.py
│       ├── intent.py             # classify_intent node (FR6)
│       ├── planner.py            # generate_plan node (FR7)
│       ├── codegen.py            # generate_code node (FR10)
│       ├── validator.py          # validate_code node (FR11–13)
│       ├── executor.py           # execute_code node + subprocess sandbox (FR14–18)
│       ├── reporter.py           # render_report node (FR19–22)
│       └── error_handler.py      # handle_error node — retry/replan routing (FR15–17)
│
├── utils/
│   ├── __init__.py
│   ├── large_data.py             # detect_large_data(), apply_uniform_stride() (FR26–28)
│   ├── error_translation.py      # translate_error() — exception → plain English (FR29, NFR8)
│   └── templates.py              # load_templates(), save_template() — templates.json I/O
│
├── tests/
│   ├── __init__.py
│   ├── test_validator.py         # Unit tests for allowlist validation logic
│   ├── test_large_data.py        # Unit tests for threshold detection + downsampling
│   ├── test_error_translation.py # Unit tests for error taxonomy mapping
│   ├── test_executor.py          # Subprocess sandbox integration tests
│   └── test_api.py               # API endpoint integration tests
│
├── UI_design/                    # Reference design assets (existing — do not modify)
│   ├── design1.png
│   └── design2.png
│
└── code-for-learning/            # Reference/learning code (existing — do not modify)
    ├── graph_workflow.py
    └── streamlit_app_langchain.py
```

### Architectural Boundaries

**Frontend Boundary (`frontend/`):**
- React/Next.js application — handles all UI rendering and user interaction
- Communicates with backend exclusively via REST API (`lib/api.ts`)
- Manages UI state via React state hooks (chat history, active tab, display preferences)
- Renders charts from base64 strings received via API
- Handles CSV upload via file input → sends to backend API
- Displays connection errors when backend is unavailable (NFR17)

**API Boundary (`services/`):**
- FastAPI REST endpoints — sole interface between frontend and backend
- Owns session lifecycle (create, get, cleanup)
- Invokes `run_pipeline()` asynchronously; updates session state on completion
- Returns structured JSON responses with consistent error format
- Handles CSV upload → calls `detect_large_data()` → writes CSV to temp file

**Pipeline Boundary (`pipeline/`):**
- Zero FastAPI/services imports — pure Python
- All I/O via `PipelineState` TypedDict fields only
- Nodes return `dict` of changed keys only — never `{**state, ...}`
- `graph.py` compiles the graph once at module load; `run_pipeline()` is the sole entry point
- LangSmith `@traceable` applied only on `run_pipeline()` in `graph.py`

**Utils Boundary (`utils/`):**
- Pure utility functions — no LangGraph or FastAPI imports
- All error translation happens here — no other module catches and displays exceptions directly

**Persistence Boundary:**
- `templates.json`: read by `utils/templates.py` on startup; written on Save action via API
- Subprocess temp dir: `tempfile.mkdtemp()` per pipeline run; cleaned up after execution
- Everything else is session-scoped and lost on browser refresh

### Requirements to Structure Mapping

| FR Category | Frontend | Backend | Pipeline |
|---|---|---|---|
| Data Input & Management (FR1–4) | `components/DataPanel.tsx` (upload UI) | `services/api.py` (/upload endpoint), `services/session.py` | `utils/large_data.py` |
| Natural Language Interface (FR5–9) | `components/ChatPanel.tsx` (chat UI) | `services/api.py` (/chat endpoint) | `pipeline/nodes/intent.py`, `planner.py` |
| Code Generation & Validation (FR10–13) | - | - | `pipeline/nodes/codegen.py`, `validator.py` |
| Execution Engine (FR14–18) | `hooks/usePolling.ts` (status polling), `components/StatusIndicator.tsx` | `services/api.py` (/execute, /status endpoints) | `pipeline/nodes/executor.py`, `error_handler.py`, `graph.py` |
| Report Output (FR19–22) | `components/ReportPanel.tsx` (render charts + text) | `services/api.py` (/report endpoint) | `pipeline/nodes/reporter.py` |
| Code Transparency (FR23–25) | `components/PlanCodeTabs.tsx` (Monaco editor + rerun button) | `services/api.py` (/code PUT, /rerun POST) | - |
| Large Data Handling (FR26–29) | Displays warning from API | `services/api.py` (/upload endpoint returns warning) | `utils/large_data.py` |
| API Layer (FR30–33) | `lib/api.ts` (API client functions) | `services/api.py` (REST endpoints), `services/session.py` | - |
| Observability (FR34–36) | Error display from API responses | `services/api.py` (error responses) | `pipeline/graph.py` (`@traceable`), `utils/error_translation.py` |

**Cross-Cutting Concerns → Files:**

| Concern | Frontend | Backend | Pipeline |
|---|---|---|---|
| Session state schema | React state hooks | `services/session.py` (in-memory store) | `pipeline/state.py` (PipelineState TypedDict) |
| Error translation | `lib/api.ts` (handles API errors) | `utils/error_translation.py` | All nodes funnel exceptions here |
| Subprocess security | - | - | `pipeline/nodes/validator.py` (AST allowlist) + `executor.py` (sandbox) |
| Tab state preservation | `components/PlanCodeTabs.tsx` (React state, no re-fetch on tab switch) | - | - |
| LangSmith non-blocking | - | Transparent to frontend | `pipeline/graph.py` (`try/except` wrapper) |
| API contract | `lib/api.ts` enforces response types | `services/api.py` defines endpoints | - |

### Integration Points

**Frontend-to-Backend Data Flow:**
```
User types query → ChatPanel component
  → chatHistory state updated locally (React state)
  → User clicks Execute → POST /api/chat endpoint with { sessionId, query }
  → Backend returns { intent, plan }
  → Plan displayed in PlanCodeTabs component
  → User clicks Execute Plan → POST /api/execute endpoint with { sessionId }
  → Backend returns { status: "started" }
  → Frontend starts polling GET /api/status every 500ms with { sessionId }
  → StatusIndicator component displays step-level progress
  → When complete (status: "complete"), GET /api/report fetches { charts: [base64], text, code }
  → ReportPanel component renders base64 images + trend analysis text
```

**Backend Pipeline Flow:**
```
API /chat or /execute endpoint (services/api.py)
  → retrieves session from in-memory store (services/session.py)
  → invokes run_pipeline(PipelineState)
  → LangGraph routes through nodes:
      classify_intent → generate_plan → generate_code
      → validate_code → [pass] → execute_code (subprocess sandbox)
                      → [fail ≤3] → handle_error → generate_code (retry)
                      → [fail >3] → handle_error → generate_plan (adaptive replan)
      → execute_code [success] → render_report → PipelineState returned
  → session["pipeline_state"] = result
  → API response returns charts + text to frontend via /api/report
```

**External Integrations:**
- **OpenAI API** — called from `pipeline/nodes/` (intent, planner, codegen, error_handler) via `langchain-openai` `ChatOpenAI`
- **LangSmith API** — called transparently via `@traceable` in `pipeline/graph.py`; optional; non-blocking

**Subprocess Data Flow:**
```
execute_code node
  → writes CSV to tempfile.mkdtemp() dir
  → launches Python subprocess with generated code
  → subprocess reads CSV, generates matplotlib charts
  → prints "CHART:<base64_png>" for each chart + trend text to stdout
  → executor.py captures stdout, parses CHART: lines → list[bytes]
  → returns {"report_charts": [...], "report_text": "...", "execution_success": True}
  → temp dir cleaned up after execution
```

### Development Workflow

**Backend Setup:**
```bash
cp .env.example .env              # add OPENAI_API_KEY
pip install -r requirements.txt
uvicorn services.api:app --reload # starts on http://localhost:8000
```

**Frontend Setup:**
```bash
cd frontend
npm install                        # or yarn install
npm run dev                        # starts on http://localhost:3000
```

**Running tests:**
```bash
python -m pytest tests/            # Backend tests
cd frontend && npm test            # Frontend tests (if configured)
```

**`.env.example` (Backend):**
```
OPENAI_API_KEY=                          # required
LANGSMITH_API_KEY=                       # optional — tracing disabled if absent
LANGCHAIN_TRACING_V2=true               # optional
LANGCHAIN_PROJECT=data_analysis_copilot # optional
```

**Access the app:**
```
Frontend: http://localhost:3000
Backend API: http://localhost:8000
API docs: http://localhost:8000/docs
```

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
All technology choices are compatible and work together without conflicts:
- Next.js (React) frontend + FastAPI backend + LangGraph + OpenAI — established production combination
- `PipelineState` TypedDict is natively supported as LangGraph's state schema type
- Pydantic models in FastAPI enable automatic request/response validation and OpenAPI schema generation
- REST API contract provides clear boundary between frontend and backend — can be developed independently
- `subprocess` sandbox + `ast` AST validator are complementary stdlib modules with no conflict
- `templates.json` write path is distinct from subprocess temp dir — no security boundary conflict
- LangSmith `try/except` wrapper ensures tracing failures never propagate to users
- Frontend polling via REST API keeps UI responsive during pipeline execution (NFR4)

**Pattern Consistency:**
- Backend: `snake_case` across session keys, node names, file names, API endpoint parameters
- Frontend: `camelCase` across React state, component props, TypeScript interfaces
- Node return pattern (changed keys only) is consistent with LangGraph's automatic state merge behaviour
- Error translation funnel (`utils/error_translation.py`) is the single path for all exceptions — no inline handling anywhere
- `CHART:` prefix pattern for subprocess chart output is consistent across codegen system prompt and executor stdout parser

**Structure Alignment:**
- Module boundaries (frontend / services / pipeline / utils) map directly to the three-tier architecture: UI / API / Pipeline / Utilities
- Status polling in frontend aligns with the UX specification's non-blocking execution requirement (NFR4)
- Session management in `services/session.py` as the single initialisation point prevents state inconsistency across API calls

### Requirements Coverage Validation ✅

**Functional Requirements (32/32 covered):**

| FR Category | Coverage | Primary Location |
|---|---|---|
| FR1–4: Data Input & Management | ✅ | `streamlit_app.py`, `utils/session.py`, `utils/large_data.py` |
| FR5–9: Natural Language Interface | ✅ | `pipeline/nodes/intent.py`, `planner.py`, `streamlit_app.py` chat panel |
| FR10–13: Code Generation & Validation | ✅ | `pipeline/nodes/codegen.py`, `validator.py` |
| FR14–18: Execution Engine | ✅ | `pipeline/nodes/executor.py`, `error_handler.py`, `pipeline/graph.py` |
| FR19–22: Report Output | ✅ | `pipeline/nodes/reporter.py`, `streamlit_app.py` report panel |
| FR23–25: Code Transparency | ✅ | `streamlit_app.py` Code tab + `streamlit-ace` + re-run button |
| FR26–29: Large Data Handling | ✅ | `utils/large_data.py`, inline message in report panel |
| FR30–32: Observability | ✅ | `pipeline/graph.py` (`@traceable`), `utils/error_translation.py` |

**Non-Functional Requirements (17/17 covered):**

| NFR Group | Coverage | Mechanism |
|---|---|---|
| NFR1–5a: Performance | ✅ | Frontend loads <3s, backend ready <5s (NFR1), status polling updates (NFR4), upload-time detection (NFR5), 60s subprocess timeout (NFR3), <500ms non-pipeline API endpoints (NFR5a) |
| NFR6–8: Reliability | ✅ | LangGraph retry/replan loop (NFR7), error translation layer (NFR8) |
| NFR9–13: Security | ✅ | Temp dir sandbox (NFR9–10), AST allowlist (NFR11), cleanup (NFR12), env vars (NFR13) |
| NFR14–17: Integration | ✅ | APIError handling (NFR14), LangSmith try/except (NFR15), pinned requirements.txt + package.json (NFR16), frontend gracefully handles backend unavailability (NFR17) |

### Implementation Readiness Validation ✅

**Decision Completeness:** All 7 critical and important decisions are documented with rationale and concrete code examples. Zero undecided architectural questions remain.

**Structure Completeness:** All files and directories are explicitly named and mapped to specific FRs. Frontend component structure, backend API endpoints, and pipeline modules are all defined. No placeholder directories.

**Pattern Completeness:** All cross-cutting concerns (7 total) have explicit patterns with correct and incorrect examples provided for both Python and TypeScript.

### Gap Analysis Results

**Critical Gaps: None**

**Important Gaps (3 — resolved here):**

**Gap 1 — REST API Contract Definition:**
The API contract must define exact endpoint signatures, request body schemas, and response schemas using Pydantic models in FastAPI. Example:

```python
# services/api.py
from pydantic import BaseModel

class ChatRequest(BaseModel):
    session_id: str
    query: str

class ChatResponse(BaseModel):
    intent: str
    plan: list[str]

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # implementation
```

All API endpoints must be documented in OpenAPI schema (`/docs` endpoint provided automatically by FastAPI).

**Gap 2 — LangGraph conditional edge routing (retry/replan logic):**
Explicit conditional routing for the self-correction loop must be implemented exactly as follows:

```python
# pipeline/graph.py

def route_after_execution(state: PipelineState) -> str:
    if state["execution_success"]:
        return "render_report"
    elif state["retry_count"] < 3:
        return "generate_code"   # retry with corrected prompt
    else:
        return "generate_plan"   # adaptive replan

graph.add_conditional_edges(
    "execute_code",
    route_after_execution,
    {
        "render_report": "render_report",
        "generate_code": "generate_code",
        "generate_plan": "generate_plan",
    }
)
```

**Gap 3 — FR21: Codegen node chart label requirement:**
`pipeline/nodes/codegen.py` system prompt MUST include the following instruction to GPT-4o:
> "Always include `plt.xlabel()`, `plt.ylabel()`, `plt.title()`, and `plt.tight_layout()` in every matplotlib chart. Labels must be descriptive and readable without engineering context — e.g., 'Voltage (V)' not 'v', 'Time (ms)' not 't'."

This is a prompt-level architectural constraint that must be present in the codegen node's system message.

**Nice-to-Have Gaps:**
- Frontend: State management library (Zustand, Context API) for complex React state — currently using local component state is acceptable for MVP
- Backend: A `tests/conftest.py` with shared fixtures (sample CSVs, mock LLM responses) would accelerate test writing — not blocking for MVP

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed (32 FRs, 16 NFRs, 4 user journeys)
- [x] Scale and complexity assessed (medium — brownfield stabilisation + one new capability)
- [x] Technical constraints identified (no auth, no cloud, session-only, LangSmith optional)
- [x] Cross-cutting concerns mapped and resolved (6 concerns)

**✅ Architectural Decisions**
- [x] Critical decisions documented with rationale and code examples
- [x] Technology stack fully specified with pinned versions
- [x] Security model defined (two-layer: AST allowlist + subprocess temp-dir sandbox)
- [x] Performance considerations addressed (`@st.fragment`, 60s timeout, upload-time size check)

**✅ Implementation Patterns**
- [x] Naming conventions established (snake_case, verb_noun nodes, UPPER_SNAKE constants)
- [x] Structure patterns defined (module boundaries, single session init location)
- [x] Communication patterns specified (error taxonomy, CHART: prefix, chat message format)
- [x] Process patterns documented (large data on upload, session mutation in UI layer only)

**✅ Project Structure**
- [x] Complete directory structure defined with all files explicitly named
- [x] Component boundaries established (UI / Pipeline / Utils three-layer model)
- [x] Integration points mapped (internal data flow, subprocess I/O, external APIs)
- [x] All FR categories mapped to specific files

### Architecture Readiness Assessment

**Overall Status: READY FOR IMPLEMENTATION**

**Confidence Level: High** — all decisions are explicit, concrete, and mutually consistent. Both gaps are resolved within this document.

**Key Strengths:**
- Brownfield approach preserves existing working code; refactoring is additive, not destructive
- `PipelineState` TypedDict as the single data contract eliminates state ambiguity across nodes
- Four-layer boundary (Frontend / API / Pipeline / Utils) prevents circular dependencies between concerns
- Error translation as a centralised funnel ensures no raw exceptions ever reach API responses
- REST API contract enables independent frontend/backend development and testing
- Explicit conditional edge routing for retry/replan prevents agents from guessing the loop logic
- Chart label requirement in codegen system prompt ensures FR21 compliance without extra code
- Frontend polling pattern ensures UI responsiveness during long-running pipeline execution (NFR4)

**Areas for Future Enhancement (post-MVP):**
- Status polling could migrate to WebSockets for real-time progress updates without polling overhead
- `templates.json` could migrate to SQLite without changing the API (`utils/templates.py` is the only consumer)
- Subprocess sandbox could be hardened with OS-level process isolation for higher-security deployments
- Frontend state management could be upgraded to Zustand or Redux for more complex state scenarios

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented — no local interpretations
- Use implementation patterns and concrete examples as the source of truth for code style
- Backend: Respect module boundaries — never import `services` or `fastapi` inside `pipeline/`
- Frontend: Use TypeScript interfaces defined in `src/types/index.ts` for all API communication
- Use the error taxonomy table for all user-facing error messages — no ad-hoc strings
- Implement REST API contract with Pydantic models before frontend development
- Implement `route_after_execution` conditional edges exactly as specified in Gap 2

**First Implementation Priority:**

**Story 1: Project Setup & Dependency Migration**
```bash
# Remove Streamlit dependencies
pip uninstall streamlit streamlit-ace streamlit-chat langchain-experimental duckduckgo_search -y

# Add new backend dependencies
pip install fastapi uvicorn pydantic

# Set up Next.js frontend
npm create next-app@latest frontend -- --typescript --tailwind
cd frontend && npm install

# Update requirements.txt with pinned versions
pip freeze > requirements.txt

# Verify backend API starts
uvicorn services.api:app --reload  # should show http://localhost:8000/docs

# Verify frontend builds
cd frontend && npm run dev  # should show http://localhost:3000
```

**Story 2: REST API Contract Definition**
Define all FastAPI endpoints and Pydantic request/response models in `services/api.py` before implementation

**Story 3: Session Management**
Implement in-memory session store in `services/session.py` with create/get/cleanup functions

**Story 4+: Feature implementation** (follows from Stories 1-3)
