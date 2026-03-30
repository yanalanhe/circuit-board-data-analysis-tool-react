---
stepsCompleted: [1, 2, 3]
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/ux-design-specification.md'
workflowType: 'epics-and-stories'
architectureType: 'next.js-react-fastapi'
date: '2026-03-26'
---

# data-analysis-copilot - Epic Breakdown (Next.js/React + FastAPI)

## Overview

This document provides the complete epic and story breakdown for data-analysis-copilot for the **Next.js/React frontend + FastAPI Python backend** architecture. Requirements are organized into epics that deliver user value while respecting architectural boundaries and the REST API contract.

## Requirements Inventory

### Functional Requirements

**Data Input & Management (FR1-4)**
- FR1: Users can upload one or more CSV files in a single session
- FR2: Users can view uploaded CSV data in an editable table within the UI
- FR3: Users can edit data directly in the data table before running analysis
- FR4: The system retains uploaded CSV data and chat history for the duration of a session across the frontend and backend

**Natural Language Interface (FR5-9)**
- FR5: Users can submit analysis requests in natural language via a chat interface
- FR6: The system classifies the intent of each query (report generation, simple Q&A, or general chat)
- FR7: The system generates a step-by-step execution plan from a natural language analysis request
- FR8: Users can review the generated execution plan before triggering execution
- FR9: Users explicitly trigger plan execution — execution is not automatic

**Code Generation & Validation (FR10-13)**
- FR10: The system generates Python analysis code from the execution plan
- FR11: The system validates generated code for syntax errors before execution
- FR12: The system validates generated code for unsafe or potentially destructive operations before execution
- FR13: The system validates generated code for logical correctness before execution

**Execution Engine (FR14-18)**
- FR14: The system executes generated Python code in an isolated subprocess
- FR15: The system detects code execution failures and initiates a retry with a corrected approach
- FR16: The system retries failed code generation up to 3 times before triggering adaptive replanning
- FR17: The system adaptively replans the analysis approach when repeated code generation attempts fail
- FR18: The system completes standard analysis requests without requiring user intervention on failure

**Report Output (FR19-22)**
- FR19: The system renders visual charts in a dedicated report panel from executed analysis code
- FR20: The system renders written trend analysis in the report panel alongside charts
- FR21: Report charts include clear labels, axis titles, and readable annotations sufficient for a non-technical stakeholder to act on
- FR22: Users can view the complete report output within the application UI without exporting

**Code Transparency (FR23-25)**
- FR23: Users can view the Python code generated to produce any report
- FR24: Users can edit the generated Python code directly in the UI
- FR25: Users can manually trigger re-execution of edited code

**Large Data Handling (FR26-29)**
- FR26: The system detects when an uploaded dataset exceeds a size threshold for effective visualization
- FR27: The system displays a clear, human-readable message when dataset size causes degraded or unrenderable visualization
- FR28: The system provides at least one recovery path when a dataset is too large — either automatic downsampling or a prompt to subset/reduce the data
- FR29: The system surfaces a user-readable error message for all execution failures — no silent failures

**API Layer (FR30-33)**
- FR30: The backend exposes REST API endpoints for CSV upload, pipeline execution, plan retrieval, and report retrieval
- FR31: The frontend communicates with the backend exclusively via the REST API — no direct pipeline access from the browser
- FR32: The API returns structured JSON responses including status, data payloads, and error messages
- FR33: The API supports session-scoped state so that multiple API calls within a session share uploaded data and pipeline context

**Observability (FR34-36)**
- FR34: The system logs all LLM calls and agent decisions to LangSmith when tracing is enabled
- FR35: Developers can enable or disable LangSmith tracing via environment variable configuration
- FR36: The system surfaces execution error information in a human-readable format to assist developer debugging

### Non-Functional Requirements

**Performance (NFR1-5a)**
- NFR1: The Next.js frontend loads and reaches an interactive state within 3 seconds on localhost; the Python API backend is ready to accept requests within 5 seconds of starting
- NFR2: A generated execution plan is displayed in the UI within 30 seconds of submitting a natural language query (inclusive of API round-trip)
- NFR3: The full execution pipeline (code generation → validation → execution → report render) completes within 15 minutes for a typical batch dataset
- NFR4: The frontend UI remains responsive during pipeline execution — asynchronous API calls do not block user interaction
- NFR5: Dataset size detection and any resulting user message are surfaced immediately upon or before execution — no unresponsive UI states during size evaluation
- NFR5a: Backend API endpoints respond within 500ms for non-pipeline requests (CSV upload confirmation, session state retrieval, plan retrieval)

**Reliability (NFR6-8)**
- NFR6: The standard workflow (upload CSV → NL query → plan → execute → report) completes without failure on repeated runs with the same input on locally hosted instances
- NFR7: The self-correction loop resolves code generation failures without user intervention for the majority of standard analysis requests
- NFR8: All execution failures surface a user-readable message — no silent failures, no raw stack traces presented to end users

**Security (NFR9-13)**
- NFR9: Generated Python code executes in an isolated subprocess that cannot access the host filesystem beyond the session working directory
- NFR10: Generated Python code cannot make outbound network calls from within the subprocess
- NFR11: The system validates generated code for unsafe operations (file writes, network calls, OS commands) before execution
- NFR12: CSV data uploaded in a session does not persist to disk beyond the session lifecycle
- NFR13: LLM API keys are loaded from environment variables and are never hardcoded or logged in application output

**Integration (NFR14-17)**
- NFR14: When the LLM API is unavailable, the system surfaces a clear user-facing error message via the API response rather than hanging or crashing silently
- NFR15: LangSmith tracing is non-blocking — if LangSmith is unreachable or unconfigured, the backend continues to function normally
- NFR16: The application specifies all required dependencies explicitly — Python backend dependencies via requirements file, Next.js frontend dependencies via package.json — ensuring consistent behavior across different local installations
- NFR17: The frontend gracefully handles backend API unavailability with a clear connection error message rather than blank screens or unhandled exceptions

### Additional Requirements

**Frontend Architecture (Next.js/React):**
- Next.js (React) SPA with TypeScript for type-safe frontend code
- Four-panel layout: Chat (top-left, fixed input + scrollable history), Plan/Code/Template tabs (top-right), CSV uploader + editable data table (bottom-left), Report panel (bottom-right)
- Desktop-first, 1280px minimum width; no mobile breakpoints required for MVP
- React state management for UI-layer data: `sessionId`, `uploadedFiles`, `chatHistory`, `activeTab`, `pipelineRunning`, `planApproved`, `currentPlan`, `currentCode`, `reportCharts`, `reportText`, `savedTemplates`, `errorMessage`, `largeDataMessage`
- Status polling via `setInterval` for async pipeline execution monitoring (replaces Streamlit's @st.fragment)
- API client hook (`useApi`) wrapping fetch for backend communication
- Monaco/CodeMirror React component for code viewer/editor (FR23-25)
- Data grid component (e.g., `tanstack-table`, `react-data-grid`) for CSV upload and editable table (FR1-3)
- No modal dialogs — all error and large-data messages displayed inline within relevant panels

**Backend Architecture (FastAPI):**
- FastAPI REST API server with async request handlers
- Python 3.12 runtime
- Session management: in-memory session store keyed by `session_id` (UUID generated on frontend app load)
- Per-session state: `uploaded_dfs`, `csv_temp_path`, `pipeline_state`, `pipeline_running`
- Pydantic models for request/response validation
- LangGraph 0.3.18 for pipeline orchestration (preserved from existing implementation)
- Error translation layer: all exceptions → plain English API responses via `/api` responses
- LangSmith 0.7.0 for optional tracing (env-var toggle, non-blocking)

**REST API Contract (Critical — unblocks frontend/backend parallel development):**

| Endpoint | Method | Purpose | Request | Response |
|---|---|---|---|---|
| `/api/session` | POST | Create new session | `{}` | `{status, data: {session_id}}` |
| `/api/upload` | POST | Upload CSV files | `{session_id, files: [binary]}` | `{status, data: {filenames, row_counts, large_data_warning?}}` |
| `/api/data` | GET | Get uploaded data preview | `?session_id=...` | `{status, data: {files: [{name, columns, rows}]}}` |
| `/api/data` | PUT | Update edited data | `{session_id, edited_rows}` | `{status, data: {success}}` |
| `/api/chat` | POST | Submit NL query | `{session_id, message}` | `{status, data: {intent, plan?, response?}, error?}` |
| `/api/execute` | POST | Trigger plan execution | `{session_id}` | `{status, data: {status: "started"}}` |
| `/api/status` | GET | Poll pipeline status | `?session_id=...` | `{status, data: {running, step?, progress?}}` |
| `/api/report` | GET | Get execution results | `?session_id=...` | `{status, data: {charts: [base64], text, code, errors?}}` |
| `/api/code` | PUT | Submit edited code | `{session_id, code}` | `{status, data: {success}}` |
| `/api/rerun` | POST | Re-execute edited code | `{session_id}` | `{status, data: {status: "started"}}` |
| `/api/templates` | GET | List templates | `?session_id=...` | `{status, data: {templates: [...]}}` |
| `/api/templates` | POST | Save template | `{session_id, name, plan, code}` | `{status, data: {success}}` |

**API Response Format (all endpoints):**
```json
{
  "status": "success" | "error",
  "data": { ... },
  "error": { "message": "user-facing message", "code": "ERROR_TYPE" }
}
```

**Shared Components & Patterns:**
- Chat message format: `{role: "user" | "bot", content: string}`
- Large data handling: dual threshold detection (100K rows OR 20MB) on CSV upload, uniform stride downsampling to 10K points (FR26-28)
- Template persistence: `templates.json` in backend root; loaded on startup, served via `/api/templates`
- Subprocess security: AST allowlist validation (Layer 1) + per-session temp dir (Layer 2), 60s timeout, no filesystem/network access
- Import allowlist: `pandas`, `numpy`, `matplotlib`, `math`, `statistics`, `datetime`, `collections`, `itertools`, `io`, `base64`
- Blocked operations: `eval()`, `exec()`, `__import__()`, `open()` with write modes, `os.*`, `sys.*`, `subprocess.*`, `socket.*`, `urllib.*`, `requests.*`
- Chart output format: `CHART:<base64_png>` prefix on stdout lines (parsed by executor)
- Error translation: all exceptions caught and translated to plain English before API response

**Dependency Specifications:**
- **Backend:** `requirements.txt` with pinned versions: FastAPI, uvicorn, pydantic, LangGraph, LangChain, langchain-openai, pandas, matplotlib, python-dotenv, etc.
- **Frontend:** `package.json` with pinned versions: Next.js, React, TypeScript, Tailwind CSS, shadcn/ui, Monaco/CodeMirror, data-grid component, etc.

---

## Epic List (Next.js/React + FastAPI)

### Epic 1: Infrastructure & Backend Foundation
Establish the FastAPI backend server, define the REST API contract, and implement session management so the frontend and backend can be developed in parallel.

**FRs covered:** FR30, FR31, FR32, FR33
**Also addresses:** REST API endpoint definitions, Pydantic models, session state schema, error response format

### Epic 2: Frontend Application Shell & Navigation
Initialize the Next.js frontend project, implement the four-panel layout, and establish the API client for communication with the backend.

**FRs covered:** FR1 (partial - UI), FR2 (partial - UI)
**Also addresses:** React state management setup, layout components, API client hook, session ID generation

### Epic 3: Data Input & Management
Implement CSV upload, editable data table, and session-scoped data retention across frontend and backend.

**FRs covered:** FR1, FR2, FR3, FR4
**Also addresses:** Frontend drag-and-drop uploader, data grid component, backend CSV handling, per-session temp file management

### Epic 4: Natural Language Chat & Intent Classification
Implement the chat interface on the frontend and intent classification logic on the backend, enabling engineers to describe what they want in plain English.

**FRs covered:** FR5, FR6
**Also addresses:** Chat message history, intent classification node, chat panel UI

### Epic 5: Execution Plan Generation & Review
Implement plan generation on the backend and plan display/review on the frontend with user-triggered execution.

**FRs covered:** FR7, FR8, FR9
**Also addresses:** Plan generator node, Plan tab UI, Execute button, status polling

### Epic 6: Code Generation, Validation & Secure Execution
Implement Python code generation, AST allowlist validation, subprocess sandbox execution, and error translation on the backend.

**FRs covered:** FR10, FR11, FR12, FR13, FR14, FR29
**Also addresses:** Code generation node, code validator, executor node with subprocess security, error translation layer

### Epic 7: Autonomous Self-Correction & Retry Loop
Implement the retry and adaptive replan logic in the LangGraph pipeline so standard requests succeed without user intervention.

**FRs covered:** FR15, FR16, FR17, FR18
**Also addresses:** Conditional edge routing in LangGraph, retry counter logic, replan triggering

### Epic 8: Visual Report Rendering & Display
Implement report panel on the frontend to display charts and trend analysis from backend execution results.

**FRs covered:** FR19, FR20, FR21, FR22
**Also addresses:** Chart image rendering (base64 PNG), trend analysis text display, Report panel UI

### Epic 9: Large Data Resilience
Implement large data detection on CSV upload and provide recovery paths (auto-downsample or manual subset) to prevent silent failures.

**FRs covered:** FR26, FR27, FR28
**Also addresses:** Dual threshold detection (backend), uniform stride downsampling (backend), large data warning display (frontend)

### Epic 10: Code Transparency & Editing
Implement the Code tab on the frontend with a code viewer/editor component and backend support for manual code re-execution.

**FRs covered:** FR23, FR24, FR25
**Also addresses:** Monaco/CodeMirror component, code viewer UI, manual re-execution endpoint

### Epic 11: Template System
Implement template save/load functionality so engineers can reuse successful analysis patterns.

**FRs covered:** (cross-cutting; supports all)
**Also addresses:** Template UI in Template tab, `templates.json` persistence (backend), template API endpoints

### Epic 12: Developer Observability & API Resilience
Implement LangSmith tracing integration and error handling for LLM API unavailability so developers can diagnose failures and users see clear errors.

**FRs covered:** FR34, FR35, FR36
**Also addresses:** LangSmith tracing (backend), error message formatting, API resilience, environment variable configuration

---

---

## Epic 1: Infrastructure & Backend Foundation

Establish the FastAPI backend server, define the REST API contract, and implement session management so the frontend and backend can be developed in parallel.

### Story 1.1: Initialize FastAPI Backend Server & Project Structure

As a developer,
I want to set up a FastAPI backend with proper project structure and environment configuration,
So that the REST API server is ready to handle requests from the Next.js frontend.

**Acceptance Criteria:**

**Given** the backend is initialized
**When** I run `uvicorn services.api:app --reload`
**Then** the FastAPI server starts on localhost:8000 and is ready to accept requests

**Given** the backend project
**When** I inspect the file structure
**Then** I see: `services/api.py`, `services/__init__.py`, `pipeline/`, `utils/`, `requirements.txt`, `.env.example`

**Given** `.env.example` exists
**When** I inspect it
**Then** it documents all required env vars: `OPENAI_API_KEY` (required), `LANGSMITH_API_KEY` (optional), `LANGCHAIN_TRACING_V2` (optional)

**Given** `requirements.txt`
**When** I inspect it
**Then** all Python dependencies are explicitly pinned: FastAPI, uvicorn, pydantic, python-dotenv, etc.

**Given** the backend is running
**When** I send a GET request to `/docs`
**Then** the FastAPI automatic OpenAPI documentation is available

---

### Story 1.2: Define REST API Endpoints & Pydantic Models

As a developer,
I want the REST API endpoints defined with Pydantic request/response models,
So that the frontend can be developed independently knowing the exact API contract.

**Acceptance Criteria:**

**Given** `services/api.py`
**When** I inspect the file
**Then** all 14 endpoints are defined (stub implementations OK): `/api/session`, `/api/upload`, `/api/data`, `/api/chat`, `/api/execute`, `/api/status`, `/api/report`, `/api/code`, `/api/rerun`, `/api/templates` (both GET and POST)

**Given** each endpoint
**When** I inspect the signature
**Then** it has request and response Pydantic models with clear field documentation

**Given** all API responses
**When** I send any request
**Then** responses follow the standard format: `{status: "success"|"error", data: {...}, error: {message, code}?}`

**Given** the API specification
**When** I read the docstrings and models
**Then** the frontend can build their API client without waiting for backend implementation

**Given** error responses
**When** an API call fails
**Then** the response includes a user-facing error message and an error code (e.g., `LARGE_DATA_WARNING`, `VALIDATION_ERROR`)

---

### Story 1.3: Implement Backend Session Management

As a developer,
I want session management implemented so each frontend user gets an isolated session,
So that multiple sessions can run simultaneously without interfering with each other.

**Acceptance Criteria:**

**Given** a new session request to `/api/session`
**When** POST is received
**Then** a UUID `session_id` is generated and an in-memory session is created with all required fields: `session_id`, `uploaded_dfs: {}`, `csv_temp_path: None`, `pipeline_state: None`, `pipeline_running: False`

**Given** an existing session_id in subsequent API calls
**When** the request includes `session_id` in headers or body
**Then** the backend retrieves the correct session and uses it for all operations

**Given** a session is active
**When** CSV files are uploaded via `/api/upload`
**Then** the data is stored in `sessions[session_id]["uploaded_dfs"]` and NOT written to permanent disk storage (except per-session temp files)

**Given** a frontend close/refresh
**When** the session_id is no longer sent
**Then** the session data remains in memory until the backend process restarts (no persistence required for MVP)

**Given** session state
**When** I inspect `pipeline_state` in a session
**Then** it is a PipelineState TypedDict with all required fields: `user_query`, `csv_temp_path`, `data_row_count`, `intent`, `plan`, `generated_code`, `validation_errors`, `execution_output`, `execution_success`, `retry_count`, `replan_triggered`, `error_messages`, `report_charts`, `report_text`, `large_data_detected`, `large_data_message`, `recovery_applied`

---

## Epic 2: Frontend Application Shell & Navigation

Initialize the Next.js frontend project, implement the four-panel layout, and establish the API client for communication with the backend.

### Story 2.1: Initialize Next.js Frontend Project & Tailwind CSS

As a developer,
I want a Next.js project initialized with TypeScript and Tailwind CSS,
So that the frontend has a modern, type-safe foundation for building React components.

**Acceptance Criteria:**

**Given** the frontend project
**When** I run `npm install`
**Then** all dependencies install without errors

**Given** the project is initialized
**When** I run `npm run dev`
**Then** the Next.js dev server starts on localhost:3000 and opens to an interactive page

**Given** the project structure
**When** I inspect the files
**Then** I see: `src/app/page.tsx`, `src/app/layout.tsx`, `src/components/`, `src/hooks/`, `src/types/`, `src/lib/`, `tsconfig.json`, `tailwind.config.js`

**Given** TypeScript configuration
**When** I inspect `tsconfig.json`
**Then** strict mode is enabled for type safety

**Given** the Next.js configuration
**When** I inspect `next.config.js`
**Then** it is configured for client-side rendering (no SSR required for MVP)

---

### Story 2.2: Implement Four-Panel Layout Component

As an engineer,
I want to see a four-panel layout on the app with distinct regions for chat, plan/code, data table, and report,
So that I can see all relevant information at once without scrolling.

**Acceptance Criteria:**

**Given** the app loads at localhost:3000
**When** I view it on a 1280px+ wide screen
**Then** I see four panels: chat (top-left 25%), plan/code tabs (top-right 25%), data table (bottom-left 50% width), report (bottom-right 50% width) — no horizontal scrolling

**Given** the layout at desktop resolution
**When** I measure the panels
**Then** they are visually balanced with clear borders or spacing between them

**Given** each panel
**When** I view it
**Then** it has a title/header identifying its purpose (Chat, Plan/Code/Template, Data, Report)

**Given** the four-panel layout component
**When** I inspect `src/components/AppLayout.tsx`
**Then** it uses flexbox or CSS grid to manage the layout, with responsive behavior (stacked on narrow screens is fine)

**Given** the app at startup
**When** no data or results exist yet
**Then** the data and report panels show placeholder text: "Upload data to get started" and "Run an analysis to see results"

---

### Story 2.3: Create API Client Hook & Session Management

As a developer,
I want a `useApi` hook that wraps fetch and handles session_id automatically,
So that all API calls from React components are consistent and session-aware.

**Acceptance Criteria:**

**Given** the frontend app loads
**When** the App component mounts
**Then** a `session_id` is generated (UUID) and stored in React state, and a new session is created via POST `/api/session`

**Given** the `useApi` hook
**When** I call `const { session_id, apiCall } = useApi()`
**Then** I get access to the current session_id and an `apiCall(endpoint, method, body?)` function

**Given** any API call via `apiCall()`
**When** the request is sent
**Then** the `session_id` is automatically included in request headers or body (backend contract specifies location)

**Given** a failed API response
**When** the status is "error"
**Then** the hook extracts `error.message` and returns it to the calling component

**Given** a successful API response
**When** the status is "success"
**Then** the hook returns `data` to the calling component

**Given** the session_id
**When** the frontend is refreshed
**Then** a new session_id is generated and the old session is lost (no persistence required for MVP)

---

## Epic 3: Data Input & Management

Implement CSV upload, editable data table, and session-scoped data retention across frontend and backend.

### Story 3.1: Implement CSV File Upload Endpoint

As an engineer,
I want to upload one or more CSV files from my machine into the app,
So that I can analyze my data without manually entering it.

**Acceptance Criteria:**

**Given** the data panel
**When** I view it
**Then** I see a drag-and-drop area and a "Browse Files" button for CSV selection

**Given** I drag one or more CSV files onto the drop zone
**When** the drop event fires
**Then** the files are uploaded via POST `/api/upload` with `session_id` and file bytes

**Given** CSV files are uploaded
**When** the backend `/api/upload` handler receives them
**Then** each file is parsed into a pandas DataFrame and stored in `sessions[session_id]["uploaded_dfs"][filename]`

**Given** the upload completes successfully
**When** the response returns from `/api/upload`
**Then** the frontend receives `{status: "success", data: {filenames: [...], row_counts: {...}, large_data_warning?: {...}}}`

**Given** large data is detected during upload (≥100K rows OR ≥20MB)
**When** the upload completes
**Then** `large_data_warning` is included in the response with a human-readable message

**Given** the upload fails (invalid CSV, missing columns, etc.)
**When** the error is processed
**Then** a user-facing error message is displayed in the data panel (not a raw traceback)

---

### Story 3.2: Implement Data Preview & Display Table

As an engineer,
I want to view my uploaded data in a table within the UI with column headers and sample rows,
So that I can verify the data loaded correctly before running analysis.

**Acceptance Criteria:**

**Given** CSV files are uploaded
**When** I view the data panel
**Then** a data grid component displays the data with all columns visible (with horizontal scroll if needed)

**Given** the data table
**When** I view it
**Then** the first 10-20 rows are displayed by default (or configurable, with scroll for more)

**Given** the data grid
**When** I hover over column headers
**Then** I see the column name and data type (e.g., "temperature (float)", "timestamp (datetime)")

**Given** multiple CSV files uploaded
**When** I view the data panel
**Then** tabs or a selector shows which file is currently displayed, and I can switch between them

**Given** the data grid component
**When** I inspect the implementation
**Then** it uses a React data grid library (e.g., `tanstack-table`, `react-data-grid`, or similar) for performance

---

### Story 3.3: Implement Editable Data Table & Data Updates

As an engineer,
I want to edit individual cell values in the data table directly,
So that I can correct data errors before running analysis without leaving the app.

**Acceptance Criteria:**

**Given** the data table
**When** I click on a cell
**Then** it enters edit mode (highlighted border, editable input)

**Given** I edit a cell value
**When** I press Enter or click outside the cell
**Then** the change is reflected in the table immediately

**Given** edited data
**When** the user changes are made
**Then** the frontend sends a PUT request to `/api/data` with `session_id` and the updated rows

**Given** the backend receives updated data
**When** it processes the PUT `/api/data` request
**Then** it updates the DataFrame in `sessions[session_id]["uploaded_dfs"][filename]` and returns `{status: "success"}`

**Given** the data is edited
**When** analysis runs after editing
**Then** the pipeline uses the edited data (updated CSV temp file reflects all changes)

**Given** invalid input in a cell (e.g., non-numeric in a numeric column)
**When** I try to confirm the edit
**Then** a validation error message appears inline and the edit is not accepted

---

## Epic 4: Natural Language Chat & Intent Classification

Implement the chat interface on the frontend and intent classification logic on the backend.

### Story 4.1: Implement Chat Interface Component

As an engineer,
I want to type analysis requests in a chat interface with my message history visible,
So that I can describe what I want to analyze and see the conversation flow.

**Acceptance Criteria:**

**Given** the chat panel (top-left)
**When** I view it
**Then** I see a chat message history area (scrollable) and a text input field at the bottom

**Given** the chat input
**When** I type a message and press Enter
**Then** my message appears in the history with role `"user"`, and the input field clears

**Given** a submitted message
**When** the chat component sends it to the backend
**Then** it includes `session_id` in the request to POST `/api/chat`

**Given** a chat message in the history
**When** I view it
**Then** it displays with role styling (user messages aligned right, bot messages aligned left) or color-coded

**Given** the chat history
**When** I navigate to other panels or tabs
**Then** the chat history remains intact and fully visible when I return

**Given** very long chat histories
**When** I view the chat panel
**Then** it scrolls and the latest messages are visible at the bottom automatically

---

### Story 4.2: Implement Intent Classification Node & Chat Responses

As a developer,
I want the backend to classify user intent (report, Q&A, or general chat) and respond appropriately,
So that the pipeline triggers the right workflow for each query type.

**Acceptance Criteria:**

**Given** a user message sent to POST `/api/chat`
**When** the backend receives it with `session_id` and message text
**Then** the `classify_intent` node in the LangGraph pipeline runs

**Given** the `classify_intent` node
**When** it processes the message
**Then** it classifies intent into one of: `"report"`, `"qa"`, or `"chat"`

**Given** a message with intent `"report"` (e.g., "create a chart showing voltage vs time")
**When** classification completes
**Then** the response includes `intent: "report"` and the pipeline triggers plan generation (next epic)

**Given** a message with intent `"qa"` (e.g., "what is the maximum value in column A?")
**When** classification completes
**Then** the pipeline skips plan generation and responds directly with an answer in the `response` field, and no `plan` is included

**Given** a message with intent `"chat"` (e.g., "hello")
**When** classification completes
**Then** the pipeline responds conversationally in the `response` field with no plan or Execute button shown

**Given** any chat response
**When** it returns to the frontend
**Then** it is appended to the chat history with role `"bot"` and displays in the chat panel immediately

---

## Epic 5: Execution Plan Generation & Review

Implement plan generation on the backend and plan display/review on the frontend.

### Story 5.1: Implement Plan Generation Node

As a developer,
I want the backend to generate a numbered step-by-step execution plan from the user's report-type request,
So that users can see and approve the analysis strategy before execution.

**Acceptance Criteria:**

**Given** a user message with `intent: "report"`
**When** the `generate_plan` node runs in the pipeline
**Then** it produces a list of numbered steps (strings) in plain English describing the analysis approach

**Given** generated plan steps
**When** I review them
**Then** each step is clear, actionable, and describes what the system will do (e.g., "1. Load voltage and current data from uploaded CSVs", "2. Calculate summary statistics (mean, median, max, min)", "3. Generate a plot of voltage vs time")

**Given** the plan
**When** it is stored in `pipeline_state["plan"]`
**Then** it is a `list[str]` with 3-7 steps (appropriate length for an analysis task)

**Given** a report request that has been classified
**When** the `generate_plan` node runs with a previous failure context (retry)
**Then** the system prompt includes information about the previous failure to guide a better plan

**Given** the plan is generated
**When** it is returned to the frontend via GET `/api/report` or in a streaming response
**Then** the frontend receives the plan and displays it in the Plan tab

---

### Story 5.2: Implement Plan Display & Execute Button

As an engineer,
I want to see the generated plan in the Plan tab as a numbered list and click Execute to start the analysis,
So that I can verify the approach before committing to running code.

**Acceptance Criteria:**

**Given** the Plan tab
**When** a plan is available (after submitting a report-type request)
**Then** the plan displays as a numbered list of steps in plain English, no code, no jargon

**Given** the Plan tab
**When** I view it
**Then** an "Execute" button is prominently displayed at the bottom or top

**Given** I click the Execute button
**When** the click is processed
**Then** the frontend sends a POST request to `/api/execute` with `session_id`

**Given** the execute request is sent
**When** the backend receives it
**Then** it sets `sessions[session_id]["pipeline_running"] = True` and the pipeline begins code generation and execution (epic 6)

**Given** the Plan tab with a plan displayed
**When** I switch to the Code or Template tab and return to Plan
**Then** the plan content is preserved in React state — no re-fetching or LLM call is triggered (tab state preservation)

**Given** a Q&A or chat intent
**When** the response is displayed
**Then** no plan is shown in the Plan tab and no Execute button appears — the response is shown directly in chat

---

## Epic 6: Code Generation, Validation & Secure Execution

Implement Python code generation, AST allowlist validation, subprocess sandbox execution, and error translation.

### Story 6.1: Implement Code Generation Node

As a developer,
I want the system to generate Python analysis code from an approved execution plan,
So that the plan is translated into executable code that will produce charts and analysis.

**Acceptance Criteria:**

**Given** an approved execution plan in `pipeline_state["plan"]`
**When** the `generate_code` node in `pipeline/nodes/codegen.py` runs
**Then** valid Python code is produced that implements the plan steps

**Given** generated code for chart visualization
**When** I inspect the code
**Then** it includes explicit calls to `plt.xlabel()`, `plt.ylabel()`, `plt.title()`, and `plt.tight_layout()` with descriptive human-readable labels (e.g., "Voltage (V)", not "v")

**Given** the generated code
**When** it is stored in `pipeline_state["generated_code"]`
**Then** the full code string is saved for later display and re-execution

**Given** a code generation attempt that fails validation (next story)
**When** the pipeline retries
**Then** the `generate_code` node's system prompt includes context about the previous validation failure to guide a better attempt

**Given** generated code producing charts
**When** the code runs in the subprocess
**Then** each chart is output as `CHART:<base64_encoded_png>` on stdout (for parsing by the executor)

---

### Story 6.2: Implement AST-Based Code Validator

As a developer,
I want the system to validate generated code before execution to catch syntax errors and unsafe operations,
So that only safe, valid code reaches the subprocess.

**Acceptance Criteria:**

**Given** generated Python code
**When** `validate_code()` runs in `pipeline/nodes/validator.py`
**Then** it returns a tuple: `(is_valid: bool, errors: list[str])`

**Given** code with a syntax error
**When** `validate_code()` runs
**Then** it catches the SyntaxError via AST parsing and returns `(False, ["Syntax error: ..."])`

**Given** code with an import outside the allowlist
**When** `validate_code()` runs with AST analysis
**Then** it detects the import and returns `(False, [error_message])` — only these imports are permitted: `pandas`, `numpy`, `matplotlib`, `matplotlib.pyplot`, `math`, `statistics`, `datetime`, `collections`, `itertools`, `io`, `base64`

**Given** code with blocked patterns
**When** `validate_code()` checks for dangerous operations
**Then** it detects and rejects: `eval()`, `exec()`, `__import__()`, `open()` with write modes, `os.*`, `sys.*`, `subprocess.*`, `socket.*`, `urllib.*`, `requests.*`

**Given** valid, safe code
**When** `validate_code()` runs
**Then** it returns `(True, [])`

**Given** a validation failure
**When** the validator returns `(False, errors)`
**Then** the error message is translated to plain English and the pipeline routes back to `generate_code` to retry (with retry count incremented)

---

### Story 6.3: Implement Subprocess Sandbox Executor

As a developer,
I want validated code executed in an isolated subprocess with timeout protection,
So that malicious or broken generated code cannot affect the host machine.

**Acceptance Criteria:**

**Given** code that passes validation
**When** `execute_code` runs in `pipeline/nodes/executor.py`
**Then** a per-session temp directory is created via `tempfile.mkdtemp()` for this execution

**Given** the subprocess launch
**When** the code is executed
**Then** the working directory is restricted to the temp directory (subprocess cannot access filesystem outside it)

**Given** the subprocess environment
**When** it runs
**Then** it inherits NO parent environment variables except whitelisted ones: `PATH`, `PYTHONPATH`

**Given** code execution
**When** a timeout of 60 seconds is exceeded
**Then** the subprocess is forcefully killed, `subprocess.TimeoutExpired` is caught, and translated to a user-facing error message

**Given** successful subprocess execution
**When** stdout is captured
**Then** lines beginning with `CHART:` are parsed as base64-encoded PNG bytes and stored in `pipeline_state["report_charts"]`; remaining stdout text is stored in `pipeline_state["report_text"]`

**Given** subprocess execution failure (non-zero exit code or exception)
**When** the error is caught
**Then** stderr is captured, translated to plain English via the error translation layer, and `pipeline_state["execution_success"]` is set to `False`

**Given** execution completion (success or failure)
**When** cleanup runs
**Then** the temp directory is deleted, ensuring no CSV or generated data persists beyond the session

---

### Story 6.4: Implement Error Translation Layer

As an engineer,
I want all pipeline failures to surface as clear, human-readable messages in the UI,
So that I always understand what went wrong and what to do next.

**Acceptance Criteria:**

**Given** `utils/error_translation.py`
**When** I inspect it
**Then** it exports a `translate_error(exception) -> str` function

**Given** an `openai.APIError` (LLM unreachable)
**When** `translate_error()` processes it
**Then** it returns: `"Unable to reach the AI service. Check your API key and internet connection."`

**Given** an `openai.RateLimitError`
**When** `translate_error()` processes it
**Then** it returns: `"AI service rate limit reached. Please wait a moment and try again."`

**Given** a `subprocess.TimeoutExpired`
**When** `translate_error()` processes it
**Then** it returns: `"Analysis took too long and was stopped. Try a simpler request or subset your data."`

**Given** a SyntaxError from code validation
**When** `translate_error()` processes it
**Then** it returns: `"Generated code had a syntax error — retrying with a corrected approach."`

**Given** an allowlist validation violation
**When** `translate_error()` processes it
**Then** it returns: `"Generated code used a restricted operation — retrying with safer code."`

**Given** any unhandled exception
**When** `translate_error()` processes it
**Then** it returns: `"An unexpected error occurred. Check the developer console for details."` — never a raw `repr(exception)`

**Given** any error anywhere in the pipeline
**When** I search the codebase
**Then** no direct `st.error(str(e))` or exception propagation exists — all errors are translated before reaching the user

---

## Epic 7: Autonomous Self-Correction & Retry Loop

Implement the retry and adaptive replan logic in the LangGraph pipeline.

### Story 7.1: Implement Conditional Edge Routing in LangGraph

As a developer,
I want the LangGraph pipeline to decide between retrying code generation, replanning, or rendering the report,
So that the system automatically recovers from failures without user intervention.

**Acceptance Criteria:**

**Given** `pipeline/graph.py` with the compiled LangGraph `StateGraph`
**When** I inspect the node connections
**Then** all nodes are properly wired: `classify_intent → generate_plan → generate_code → validate_code → execute_code`, with conditional edges on `execute_code`

**Given** a `route_after_execution` conditional edge function
**When** I inspect it
**Then** it takes `pipeline_state` as input and returns the next node name based on execution success and retry count

**Given** `execution_success = True`
**When** `route_after_execution` runs
**Then** it returns `"render_report"` to proceed to report rendering

**Given** `execution_success = False` and `retry_count < 3`
**When** `route_after_execution` runs
**Then** it returns `"generate_code"` and `retry_count` is incremented in the state

**Given** `execution_success = False` and `retry_count >= 3`
**When** `route_after_execution` runs
**Then** it returns `"generate_plan"` and `replan_triggered` is set to `True` in the state

**Given** the conditional edges setup
**When** I inspect the code
**Then** it matches exactly: `graph.add_conditional_edges("execute_code", route_after_execution, {"render_report": "render_report", "generate_code": "generate_code", "generate_plan": "generate_plan"})`

---

### Story 7.2: Implement Retry & Adaptive Replan Logic

As an engineer,
I want the system to retry failed code generation up to 3 times and replan when all retries are exhausted,
So that standard analysis requests succeed autonomously without my intervention.

**Acceptance Criteria:**

**Given** code execution fails
**When** the `route_after_execution` edge routes back to `generate_code`
**Then** `retry_count` is incremented and the `generate_code` node runs again with context about the previous failure

**Given** a retry attempt in `generate_code`
**When** the system prompt is constructed
**Then** it includes information about the previous failure (error message, code snippet) to guide a better attempt

**Given** three consecutive code generation failures
**When** `retry_count` reaches 3
**Then** `route_after_execution` routes to `generate_plan` instead (adaptive replan)

**Given** the adaptive replan triggered
**When** the `generate_plan` node runs with `replan_triggered = True`
**Then** the system prompt instructs the LLM to devise a completely different analysis approach (not just tweak the code)

**Given** any retry or replan event
**When** the error is caught
**Then** a human-readable message is appended to `pipeline_state["error_messages"]` (translated, never raw exception repr)

**Given** the final plan after replan
**When** code generation continues
**Then** it succeeds and produces executable code, which is validated and executed

---

## Epic 8: Visual Report Rendering & Display

Implement report panel on the frontend to display charts and trend analysis.

### Story 8.1: Implement Report Rendering Node

As a developer,
I want the backend to take successful execution output (charts + text) and format it for display,
So that the frontend can render a complete, polished report.

**Acceptance Criteria:**

**Given** successful code execution with chart output
**When** the subprocess produces `CHART:<base64_png>` lines on stdout
**Then** each chart is decoded from base64 and stored as bytes in `pipeline_state["report_charts"]`

**Given** successful execution with text output (trend analysis, summary statistics)
**When** stdout is captured
**Then** all non-`CHART:` lines are concatenated and stored in `pipeline_state["report_text"]`

**Given** the `render_report` node in `pipeline/nodes/reporter.py`
**When** it runs
**Then** it formats the charts and text into a structured report payload

**Given** large data that was downsampled
**When** the report is rendered
**Then** a note is included: "Downsampled to 10,000 points using uniform stride" (context for the user about data reduction)

**Given** the report payload
**When** it is stored in the pipeline state
**Then** it includes: `report_charts: [bytes]`, `report_text: str`, `pipeline_state["execution_success"] = True`

---

### Story 8.2: Implement Report Display Component & Chart Rendering

As an engineer,
I want to see rendered charts and trend analysis in the Report panel after execution completes,
So that I can immediately see the results and act on the insights.

**Acceptance Criteria:**

**Given** pipeline execution completes successfully
**When** the report is ready
**Then** the frontend polls `/api/report` and receives the charts and text

**Given** the Report panel
**When** a report is available
**Then** base64-encoded PNG images from `report_charts` are decoded and displayed as `<img>` elements

**Given** chart display
**When** I view the charts
**Then** they are sized appropriately (not too large, not too small), with clear labels, axis titles, and readable annotations (from code gen story 6.1 requirements)

**Given** the trend analysis text
**When** it is displayed
**Then** it appears below or beside the charts in a readable format (plain text or markdown if the LLM outputs it)

**Given** multiple charts in a report
**When** I view the Report panel
**Then** they are displayed in a clear grid or list format, not overlapping

**Given** the Report panel initially
**When** no analysis has run yet
**Then** it shows a placeholder: "Run an analysis to see results here"

---

## Epic 9: Large Data Resilience

Implement large data detection on CSV upload and provide recovery paths.

### Story 9.1: Implement Large Data Detection on Upload

As an engineer,
I want the system to detect when my data is too large for visualization,
So that I'm warned upfront and can choose a recovery action before running analysis.

**Acceptance Criteria:**

**Given** CSV file(s) are uploaded
**When** the backend `/api/upload` handler processes them
**Then** `utils/large_data.py` checks the combined dataset size immediately: row count and file size in MB

**Given** the detection logic
**When** I inspect it
**Then** it triggers on dual thresholds: ≥100,000 rows OR ≥20MB (FR26)

**Given** large data is detected
**When** the upload completes
**Then** the response includes `large_data_warning: {detected: true, row_count, size_mb, message: "Your dataset has X rows / Y MB, which exceeds..."}`

**Given** large data is detected
**When** the frontend receives the warning
**Then** it displays immediately in the data panel (inline message, no modal) with recovery options

**Given** the upload detection
**When** I measure the detection time
**Then** it is immediate (< 100ms for typical uploads) — no blocking or frozen UI (NFR5)

---

### Story 9.2: Implement Auto-Downsample Recovery Path

As an engineer,
I want the option to automatically downsample my large dataset so I can still get useful analysis,
So that I'm not blocked from running the analysis without uploading a smaller dataset manually.

**Acceptance Criteria:**

**Given** large data is detected and warning is shown
**When** I view the warning message in the data panel
**Then** at least one recovery action is offered: "Auto-downsample to 10,000 points" button is visible (FR28)

**Given** I click the auto-downsample button
**When** the action is triggered
**Then** the frontend sends a request to the backend to apply downsampling

**Given** the backend receives the downsample request
**When** it applies downsampling via `utils/large_data.py`'s `apply_uniform_stride()` function
**Then** uniform stride sampling reduces the dataset rows to exactly 10,000 points (preserving data distribution)

**Given** downsampling is applied
**When** the updated CSV is written to the session temp file
**Then** the data table in the UI reflects the downsampled data (showing 10,000 rows instead of 100K+)

**Given** downsampling has been applied
**When** analysis runs on the downsampled data
**Then** the pipeline executes successfully and produces charts and analysis on the reduced dataset

**Given** the report after downsampling
**When** I view it
**Then** a note is visible with the charts: "Downsampled to 10,000 points using uniform stride" — so I understand the data reduction tradeoff

**Given** the large data warning
**When** I read it
**Then** it also suggests filtering the data in the editable data table as an alternative recovery path (FR28)

---

## Epic 10: Code Transparency & Editing

Implement the Code tab on the frontend with a code viewer/editor component.

### Story 10.1: Implement Code Viewer Component with Monaco/CodeMirror

As an engineer,
I want to view the Python code generated for any analysis in the Code tab,
So that I can verify the system understood my request correctly and trust the output.

**Acceptance Criteria:**

**Given** a completed analysis
**When** I click the Code tab
**Then** the generated Python code is displayed in a code editor component (Monaco or CodeMirror)

**Given** the code editor
**When** I view it
**Then** syntax highlighting is applied (Python language), making the code readable

**Given** code that produces charts
**When** I view it
**Then** I can clearly see the `plt.xlabel()`, `plt.ylabel()`, `plt.title()` calls with descriptive labels

**Given** the Code tab
**When** I switch to it from the Plan tab and return to Plan
**Then** the code content is preserved without re-generating — it reads from React state, not triggering a fresh LLM call

**Given** no analysis has been run yet
**When** I click the Code tab
**Then** the editor shows a placeholder: "Run an analysis to see the generated code here"

**Given** the code editor
**When** I view it at 1280px+ screen width
**Then** the editor is fully visible without horizontal scrolling and text is readable

---

### Story 10.2: Implement Editable Code & Manual Re-Execution

As an engineer,
I want to edit the generated Python code directly in the Code tab and re-run it,
So that I can refine the analysis without starting the workflow over.

**Acceptance Criteria:**

**Given** code is displayed in the Code tab editor
**When** I edit the code directly in the editor
**Then** my changes are reflected in the editor buffer in real time

**Given** I have edited the code
**When** I click a "Re-run" button in the Code tab
**Then** the modified code is sent to the backend via PUT `/api/code` with the new code string

**Given** the backend receives edited code
**When** it processes the PUT request
**Then** it validates the code (same allowlist rules as generated code)

**Given** the code passes validation
**When** the backend executes it via the subprocess
**Then** new charts and trend analysis are produced and returned

**Given** the re-run succeeds
**When** execution completes
**Then** new output replaces the previous report panel contents, and the Code tab remains showing the edited code

**Given** the re-run fails validation
**When** the validator catches an unsafe operation or syntax error
**Then** a plain-English error message appears inline in the Code tab (not a raw traceback)

**Given** the re-run fails in the subprocess
**When** the error is caught
**Then** a translated error message appears in the report panel via the error translation layer

---

## Epic 11: Template System

Implement template save/load functionality across frontend and backend.

### Story 11.1: Implement Template Persistence & API Endpoints

As a developer,
I want to save successful analyses as templates in `templates.json` and serve them via API,
So that users can reuse their best analysis patterns across sessions.

**Acceptance Criteria:**

**Given** a successful analysis completes
**When** the user clicks "Save as Template" in the Plan tab
**Then** a dialog or input prompts for a template name

**Given** I enter a template name and confirm
**When** the save action is triggered
**Then** the frontend sends a POST request to `/api/templates` with `session_id`, `name`, `plan`, and `code`

**Given** the backend receives the template save request
**When** it processes the POST `/api/templates`
**Then** it calls `utils/templates.py`'s `save_template()` function

**Given** `save_template()` is called
**When** it executes
**Then** the template (name, plan, code) is written to `templates.json` in the backend root directory, formatted as JSON

**Given** the backend starts
**When** it initializes
**Then** `load_templates()` from `utils/templates.py` is called and existing templates are loaded into memory

**Given** a GET request to `/api/templates`
**When** the backend receives it
**Then** all saved templates are returned as `{status: "success", data: {templates: [...]}}`

**Given** the subprocess sandbox
**When** it runs user code
**Then** it cannot write to `templates.json` or any path outside its temp directory — template writes only occur from the backend API layer

---

### Story 11.2: Implement Template UI & Template Application

As an engineer,
I want to view all my saved templates and quickly apply them to new datasets,
So that I can reuse my best analysis patterns without retyping them.

**Acceptance Criteria:**

**Given** the Template tab
**When** I click it
**Then** it displays a list of all previously saved templates, each with a name and optional preview (plan summary or code snippet)

**Given** I select a saved template from the list
**When** I click "Apply" or double-click the template
**Then** the template's plan is loaded into the Plan tab and the template's code is loaded into the Code tab editor

**Given** a template is applied
**When** the content loads
**Then** React state is updated but no API call is re-triggered (the plan and code are already in the template)

**Given** I apply a template
**When** the Plan tab shows the plan
**Then** an "Execute" button is visible to run the templated analysis on the current (new) dataset

**Given** the app loads
**When** React initializes
**Then** the Template tab is automatically populated with saved templates (via GET `/api/templates` on app load)

**Given** a template is deleted (if delete functionality is added)
**When** the user confirms deletion
**Then** the template is removed from `templates.json` and the list is refreshed

---

## Epic 12: Developer Observability & API Resilience

Implement LangSmith tracing integration and error handling for LLM API unavailability.

### Story 12.1: Implement LangSmith Tracing Integration

As a developer,
I want to enable LangSmith tracing via environment variable to see all LLM calls and agent decisions,
So that I can diagnose pipeline failures in minutes and understand system behavior.

**Acceptance Criteria:**

**Given** `LANGSMITH_API_KEY` is set in `.env`
**When** the backend starts
**Then** the LangSmith client is configured via `langsmith` environment variables

**Given** the pipeline runs
**When** `run_pipeline()` in `pipeline/graph.py` is called
**Then** the entire pipeline execution is traced and visible in the LangSmith dashboard

**Given** LangSmith tracing enabled
**When** I view the LangSmith project dashboard
**Then** I see the full invocation chain: classify_intent → generate_plan → generate_code → validate_code → execute_code → render_report, with inputs and outputs for each node

**Given** `LANGSMITH_API_KEY` is NOT set in `.env`
**When** the app starts and runs the standard workflow
**Then** it functions normally with zero impact — no errors, no warnings, no UI impact (NFR15, FR31)

**Given** `pipeline/graph.py`
**When** I inspect the implementation
**Then** `@traceable(name="analysis_pipeline")` is applied only to the top-level `run_pipeline()` function — individual nodes are traced automatically by LangGraph

**Given** a LangSmith connection failure during tracing
**When** the tracing call throws any exception
**Then** it is caught and silently ignored (`try: ... except Exception: pass`) — the pipeline continues without surfacing any error to the user (NFR15)

**Given** `.env.example` in the project root
**When** I inspect it
**Then** it documents all environment keys:  `OPENAI_API_KEY` (required), `LANGSMITH_API_KEY` (optional), `LANGCHAIN_TRACING_V2=true` (optional), `LANGCHAIN_PROJECT` (optional)

---

### Story 12.2: Implement LLM API Resilience & Error Reporting

As a developer,
I want the app to surface clear errors when the LLM API is unavailable,
So that I can quickly diagnose and resolve issues without confusion.

**Acceptance Criteria:**

**Given** the OpenAI API is unreachable or returns `openai.APIError`
**When** the pipeline runs
**Then** the error is caught at the pipeline entry point and translated to: `"Unable to reach the AI service. Check your API key and connection."`

**Given** this error message
**When** the user sees it in the UI
**Then** it is displayed in the chat or report panel (never a raw stack trace), and is actionable

**Given** `OPENAI_API_KEY` is missing from `.env`
**When** the app starts and I submit a query
**Then** the error message identifies the missing key: `"OPENAI_API_KEY is not set. Add it to your .env file."`

**Given** a pipeline failure at any node (LLM timeout, rate limit, etc.)
**When** the error is caught
**Then** `pipeline_state["error_messages"]` is populated with a human-readable description of the failure

**Given** `requirements.txt`
**When** I inspect it
**Then** all Python library dependencies are explicitly pinned to exact versions (e.g., `langchain==0.3.27`, not `langchain>=0.3.0`) — ensuring consistent behavior across local installations (NFR16)

**Given** the app is run without any LangSmith configuration
**When** it starts and I run the standard workflow (upload → query → execute → report)
**Then** startup is clean, the workflow completes successfully, and no warnings about missing optional config appear (NFR15, NFR16)

---

## Summary

**✅ Epic Breakdown Complete:**

- **12 Epics** designed around user value and architectural boundaries
- **35+ Stories** with detailed acceptance criteria
- **Full FR Coverage:** All 36 functional requirements mapped to specific stories
- **Next.js/React + FastAPI Architecture:** Backend and frontend development can proceed in parallel
- **Ready for Implementation:** Each story is sized for single-developer completion

---

**Next Steps:**

Would you like to:

- **[C] Continue to Final Validation** — review the complete epics/stories document
- **[E] Export to Story Files** — create individual story files for dev agent assignment
- **[S] Start Implementation Planning** — organize stories into sprint backlog

Select an option:

