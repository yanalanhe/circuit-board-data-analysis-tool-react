---
epic: 1
story: 3
status: review
story_key: 1-3-implement-backend-session-management
created: 2026-03-26
last_updated: 2026-03-26
---

# Story 1.3: Implement Backend Session Management

**Status:** ready-for-dev

**Epic:** 1 - Infrastructure & Backend Foundation

**Dependencies:** Story 1.1, Story 1.2 (API endpoints must be defined first)

**Unblocks:** All Stories in Epics 3-12 (session data needed for all pipeline operations)

## Story Statement

As a developer,
I want session management implemented so each frontend user gets an isolated session,
So that multiple sessions can run simultaneously without interfering with each other.

## Acceptance Criteria

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

## Technical Requirements & Architecture Compliance

### Session State Schema

**Global Session Store (In-Memory Dict):**
```python
# File: services/session.py
sessions: dict[str, SessionData] = {}

class SessionData(TypedDict):
    session_id: str
    uploaded_dfs: dict[str, pd.DataFrame]  # filename → DataFrame
    csv_temp_path: Optional[str]            # path to per-session temp CSV
    pipeline_state: Optional[PipelineState] # from pipeline/state.py
    pipeline_running: bool                  # True while pipeline executing
```

**PipelineState TypedDict (Shared Across All Pipeline Nodes):**
```python
# File: pipeline/state.py
from typing import TypedDict, Optional, Literal

class PipelineState(TypedDict):
    # Input & context
    user_query: str
    csv_temp_path: str                      # nodes load CSV from file
    data_row_count: int

    # Intent classification
    intent: Literal["report", "qa", "chat"]

    # Plan generation
    plan: list[str]                         # numbered step list

    # Code generation & execution
    generated_code: str
    validation_errors: list[str]            # from AST validator
    execution_output: str                   # stdout from subprocess
    execution_success: bool

    # Retry & replan
    retry_count: int                        # max 3 before replan
    replan_triggered: bool

    # Error tracking
    error_messages: list[str]               # translated errors

    # Report output
    report_charts: list[bytes]              # PNG bytes from subprocess
    report_text: str                        # trend analysis text

    # Large data handling
    large_data_detected: bool
    large_data_message: str
    recovery_applied: str                   # "downsampled", "filtered", etc.
```

### Session Management Functions

**In services/session.py:**

```python
import uuid
from typing import Optional
from pipeline.state import PipelineState

sessions: dict[str, dict] = {}

def create_session(session_id: Optional[str] = None) -> dict:
    """Create new session and return session_id."""
    if session_id is None:
        session_id = str(uuid.uuid4())

    sessions[session_id] = {
        "session_id": session_id,
        "uploaded_dfs": {},
        "csv_temp_path": None,
        "pipeline_state": None,
        "pipeline_running": False,
    }
    return sessions[session_id]

def get_session(session_id: str) -> Optional[dict]:
    """Retrieve session by ID."""
    return sessions.get(session_id)

def update_session(session_id: str, updates: dict) -> bool:
    """Update session fields."""
    if session_id not in sessions:
        return False
    sessions[session_id].update(updates)
    return True

def delete_session(session_id: str) -> bool:
    """Clean up session (optional for MVP)."""
    if session_id in sessions:
        del sessions[session_id]
        return True
    return False

def session_exists(session_id: str) -> bool:
    """Check if session exists."""
    return session_id in sessions
```

**Update /api/session endpoint:**
```python
@app.post("/api/session", response_model=CreateSessionResponse)
async def create_session() -> dict:
    """Create new session with UUID."""
    from services.session import create_session as create_sess
    session = create_sess()
    return {
        "status": "success",
        "data": {"session_id": session["session_id"]}
    }
```

### Session ID Propagation Pattern

**Request Pattern:**
```python
# Option 1: Header (recommended for REST)
@app.post("/api/upload")
async def upload_files(
    session_id: str = Header(...),  # X-Session-ID header
    files: list[UploadFile] = File(...)
) -> dict:
    session = get_session(session_id)
    if not session:
        return {
            "status": "error",
            "error": {
                "message": "Session not found",
                "code": "INVALID_SESSION"
            }
        }
    # ... process upload

# Option 2: Request body (for POST with JSON)
class UploadRequest(BaseModel):
    session_id: str

@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict:
    session = get_session(request.session_id)
    # ... process chat
```

**Frontend Usage (Story 2.3 will implement):**
```javascript
// Frontend generates session_id on app load
const sessionId = generateUUID();

// All API calls include session_id
const response = await fetch('/api/upload', {
    method: 'POST',
    headers: {
        'X-Session-ID': sessionId,
    },
    body: formData
});
```

### Session Lifecycle

**Creation:**
1. Frontend loads app → generates UUID session_id
2. Frontend calls POST /api/session (optional, for server-side init)
3. Backend creates in-memory session dict

**Active Use:**
1. Frontend includes session_id in all API calls
2. Backend retrieves session for each request
3. Data accumulates in session dict (upload_dfs, pipeline_state, etc.)

**Cleanup (End of Session):**
1. Browser refresh → new session_id generated, old session abandoned
2. Backend session orphaned in memory (cleaned on process restart)
3. No explicit cleanup needed for MVP

### Data Isolation

**CSV Data Storage:**
```python
# After CSV upload in Story 3.1
sessions[session_id]["uploaded_dfs"] = {
    "voltage.csv": pd.DataFrame(...),
    "current.csv": pd.DataFrame(...),
    # ... one entry per uploaded file
}

# Data never written to disk (except temp files in Story 3.1)
# Data only in memory
# No persistence across server restarts
```

**Pipeline State Isolation:**
```python
# Each session has independent pipeline_state
# So two simultaneous requests don't interfere:

# Request A (session_1)
sessions["session_1"]["pipeline_state"]["retry_count"] = 1

# Request B (session_2)
sessions["session_2"]["pipeline_state"]["retry_count"] = 0
# No conflict - independent states
```

### Error Handling for Sessions

**Invalid Session:**
```python
def require_session(session_id: str) -> dict:
    """Helper to validate session exists, return error if not."""
    session = get_session(session_id)
    if not session:
        return {
            "status": "error",
            "error": {
                "message": "Session not found. Please refresh the page.",
                "code": "INVALID_SESSION"
            }
        }
    return session

# Usage in endpoint:
@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict:
    session = require_session(request.session_id)
    if "error" in session:  # Error response
        return session
    # ... proceed with chat
```

---

## Developer Context

### Files to Create/Modify

**Create:**
- `services/session.py` (NEW FILE) - Session management functions
- `pipeline/state.py` (NEW FILE) - PipelineState TypedDict definition

**Modify:**
- `services/api.py` - Update endpoints to use session management

### Implementation Strategy

**Step 1: Create pipeline/state.py**
```python
from typing import TypedDict, Optional, Literal

class PipelineState(TypedDict):
    user_query: str
    csv_temp_path: str
    data_row_count: int
    intent: Literal["report", "qa", "chat"]
    plan: list[str]
    generated_code: str
    validation_errors: list[str]
    execution_output: str
    execution_success: bool
    retry_count: int
    replan_triggered: bool
    error_messages: list[str]
    report_charts: list[bytes]
    report_text: str
    large_data_detected: bool
    large_data_message: str
    recovery_applied: str
```

**Step 2: Create services/session.py**
```python
import uuid
from typing import Optional

sessions: dict[str, dict] = {}

def create_session(session_id: Optional[str] = None) -> dict:
    """Create session and return session dict."""
    if session_id is None:
        session_id = str(uuid.uuid4())

    sessions[session_id] = {
        "session_id": session_id,
        "uploaded_dfs": {},
        "csv_temp_path": None,
        "pipeline_state": None,
        "pipeline_running": False,
    }
    return sessions[session_id]

# ... remaining functions
```

**Step 3: Update services/api.py endpoints**
- Import session management functions
- Add session_id parameter to each endpoint
- Validate session exists before processing
- Update session data as needed

### Module Boundary Notes

**services/session.py:**
- Owns in-memory session store
- Provides CRUD operations on sessions
- Can import from pipeline/ (for PipelineState type hints)

**pipeline/state.py:**
- Defines PipelineState TypedDict only
- No imports from services/ (avoid circular dependencies)
- Pure data schema definition

### Testing & Validation

After implementation:
```python
# Test session creation
from services.session import create_session, get_session

session = create_session()
assert session["session_id"]
assert session["uploaded_dfs"] == {}
assert session["pipeline_state"] is None
assert session["pipeline_running"] is False

# Test retrieval
retrieved = get_session(session["session_id"])
assert retrieved == session

# Test isolation
session2 = create_session()
assert session2["session_id"] != session["session_id"]
assert session2["uploaded_dfs"] != session["uploaded_dfs"]
```

### Source References

- [Architecture: REST API Contract](../planning-artifacts/architecture.md#rest-api-contract-critical)
- [Architecture: Data Architecture](../planning-artifacts/architecture.md#data-architecture)
- [Architecture: Backend Session State](../planning-artifacts/architecture.md#backend-session-state-in-memory-dict-per-session)
- [Epic 1: Story 1.3](../planning-artifacts/epics.md#story-13-implement-backend-session-management)

---

## Tasks / Subtasks

- [x] Create `pipeline/state.py` with PipelineState TypedDict
  - [x] All required fields defined
  - [x] Proper type hints (Optional, Literal, list, etc.)
  - [x] Docstring explaining each field
- [x] Create `services/session.py` with session management
  - [x] Global `sessions` dict
  - [x] `create_session()` function
  - [x] `get_session()` function
  - [x] `update_session()` function
  - [x] `delete_session()` function (optional)
  - [x] `session_exists()` function
  - [x] Import uuid library
- [x] Update endpoints in `services/api.py`
  - [x] Import session functions
  - [x] Add session_id parameter to POST /api/session
  - [x] Update POST /api/upload to use session management
  - [x] Update GET/PUT /api/data to use session management
  - [x] Update POST /api/chat to use session management
  - [x] Update other endpoints to validate session exists
- [x] Create helper function `require_session()` for validation
- [x] Test session isolation - multiple sessions don't interfere
- [x] Verify session data persists for duration of session
- [x] Test invalid session_id returns proper error response
- [x] Document session_id passing pattern (headers vs body)

---

## Dev Notes

### Key Implementation Points

1. **In-Memory Only:** No database needed. Sessions lost on process restart (OK for MVP).
2. **UUID Generation:** frontend generates session_id, backend just stores it
3. **PipelineState:** Define schema now (will be populated by pipeline nodes in later stories)
4. **Error Responses:** Invalid sessions always return standard error format

### Constraints & Patterns

- No authentication (session_id is just an opaque identifier)
- No session timeout (sessions live until process restart)
- No session recovery (refreshing page = new session)
- DataFrame storage is in-memory only (no persistence)
- CSV temp files created per-session (story 3.1)

### Dependencies

- `uuid` library (built-in Python) for generating session IDs
- `pandas` (already in requirements.txt) for DataFrame type hints
- No database framework needed
- No ORM needed

## File List

### Created Files
- `services/session.py` - Complete session management module with CRUD operations and helper functions

### Modified Files
- `services/api.py` - Updated all endpoints to use session management with require_session() validation
- `pipeline/state.py` - Already existed with compatible PipelineState definition

## Change Log

**2026-03-26:**
- Created services/session.py with in-memory session store and all required functions
- Updated all 14 REST API endpoints in services/api.py to validate sessions
- Implemented require_session() helper for consistent error handling across endpoints
- Added session isolation tests - verified multiple concurrent sessions work independently
- Verified invalid sessions return proper INVALID_SESSION error response
- Session data persists in memory for API response tracking

## Completion Notes

**Story 1.3 - COMPLETE (2026-03-26)**

**What was implemented:**
1. ✅ Created services/session.py with:
   - Global in-memory sessions dictionary
   - create_session(session_id=None) - generates UUID if not provided
   - get_session(session_id) - retrieves session by ID
   - session_exists(session_id) - checks if session exists
   - update_session(session_id, updates) - updates session fields
   - delete_session(session_id) - manual cleanup (optional for MVP)
   - require_session(session_id) - validation helper returning session or error dict

2. ✅ Updated all 14 endpoints in services/api.py:
   - POST /api/session - Now creates real session using create_session()
   - POST /api/upload - Validates session, stores in sessions dict
   - GET/PUT /api/data - Validates session, retrieves uploaded_dfs metadata
   - POST /api/chat - Validates session before processing
   - POST /api/execute - Validates session before execution
   - GET /api/status - Validates session, returns pipeline_running status
   - GET /api/report - Validates session, returns pipeline_state results or 404
   - PUT /api/code - Validates session before code validation
   - POST /api/rerun - Validates session before re-execution
   - GET/POST /api/templates - Validates session for template operations

3. ✅ Session isolation and error handling:
   - Each session_id has isolated state (uploaded_dfs, pipeline_state, etc.)
   - Multiple sessions cannot interfere with each other
   - Invalid session_id returns standard error: {status: "error", error: {code: "INVALID_SESSION", message: "..."}}
   - Session data persists for duration of session
   - Session cleanup on process restart (no persistence required for MVP)

4. ✅ Testing verified:
   - Session creation works (generates unique UUIDs)
   - Session retrieval works (get_session returns correct data)
   - Session isolation verified (multiple sessions are independent)
   - Invalid sessions return proper error responses
   - Session updates persist (pipeline_running, pipeline_state, etc.)

**Architecture compliance:**
- ✅ In-memory session store as per specification
- ✅ No database required (MVP)
- ✅ Module boundaries maintained (services/session.py imported by services/api.py)
- ✅ PipelineState TypedDict available for pipeline nodes
- ✅ Session data accessible across all endpoints and future pipeline nodes

**Tests:**
- Session creation test ✅
- Session retrieval test ✅
- Session isolation test ✅
- Invalid session error test ✅
- Session update persistence test ✅
- FastAPI app integration test ✅
- All 14 endpoints with session validation ✅

**Ready for:** Epic 2 (Frontend) - Backend API now complete with all 14 endpoints and session management. Frontend can begin development knowing exact API contract and session handling patterns.

---

### Next Stories Impact

- **Story 3.1:** Will store DataFrames in `sessions[session_id]["uploaded_dfs"]`
- **Story 6.3:** Will create temp directories in `sessions[session_id]["csv_temp_path"]`
- **All Pipeline Stories:** Will read/write `sessions[session_id]["pipeline_state"]`
- **Story 4.1:** Will store chat history in session (new field)

---

## Completion Criteria

✅ When this story is DONE:
- Sessions created on `/api/session` POST with UUID and all required fields
- Each session is isolated from others
- DataFrames stored in session dict (no disk persistence)
- PipelineState TypedDict defined with all required fields
- All endpoints can validate and retrieve sessions
- Invalid sessions return standard error response
- Multiple simultaneous sessions work independently
- Session data available to all pipeline stories (Epic 3-12)

---

**Previous Story:** Story 1.2 - Define REST API Endpoints
**Next Epic:** Epic 2 - Frontend Application Shell (can now proceed in parallel)

**Critical Path:** This story COMPLETES Epic 1. Both Epic 1 and Epic 2 can be worked in parallel after this story is done.
