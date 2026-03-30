"""Backend session management for isolated user sessions.

Each frontend user gets a unique session_id (UUID) with in-memory session storage.
Session data includes uploaded DataFrames, pipeline state, and temporary file paths.

Architecture: In-memory only (no database required for MVP). Sessions lost on
process restart. Session data isolated per session_id to prevent cross-session interference.
"""

import uuid
from typing import Optional, Dict, Any
from pipeline.state import PipelineState


# Global in-memory session store
# Key: session_id (UUID string)
# Value: SessionData dict with uploaded_dfs, pipeline_state, etc.
sessions: Dict[str, Dict[str, Any]] = {}


class SessionData(dict):
    """TypedDict-like dict for session data structure.

    Fields:
    - session_id: str - Unique session identifier
    - uploaded_dfs: dict[str, DataFrame] - Filename → DataFrame mapping
    - csv_temp_path: Optional[str] - Path to per-session temp CSV file
    - pipeline_state: Optional[PipelineState] - Current pipeline state (None until first execution)
    - pipeline_running: bool - Whether pipeline is currently executing
    """
    pass


def create_session(session_id: Optional[str] = None) -> Dict[str, Any]:
    """Create new session with UUID and return session dict.

    Args:
        session_id: Optional. If provided, use this ID. Otherwise generate new UUID.

    Returns:
        Dict with session_id and initial empty state for uploaded_dfs, pipeline_state, etc.

    Example:
        >>> session = create_session()
        >>> session['session_id']  # New UUID
        '550e8400-e29b-41d4-a716-446655440000'
    """
    if session_id is None:
        session_id = str(uuid.uuid4())

    sessions[session_id] = {
        "session_id": session_id,
        "uploaded_dfs": {},           # {filename: DataFrame}
        "csv_temp_path": None,         # Path to temp CSV file (created in Story 3.1)
        "chat_history": [],            # Chat messages (Story 4.1)
        "pipeline_state": None,        # PipelineState dict (populated during execution)
        "pipeline_running": False,     # True while pipeline is executing
    }
    return sessions[session_id]


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve session by ID.

    Args:
        session_id: Session identifier

    Returns:
        Session dict if exists, None otherwise

    Example:
        >>> session = get_session("550e8400-e29b-41d4-a716-446655440000")
        >>> if session:
        ...     print(f"Session {session['session_id']} loaded")
    """
    return sessions.get(session_id)


def session_exists(session_id: str) -> bool:
    """Check if session exists.

    Args:
        session_id: Session identifier

    Returns:
        True if session exists, False otherwise
    """
    return session_id in sessions


def update_session(session_id: str, updates: Dict[str, Any]) -> bool:
    """Update session fields with new values.

    Args:
        session_id: Session identifier
        updates: Dict of fields to update

    Returns:
        True if update succeeded, False if session not found

    Example:
        >>> update_session(session_id, {"pipeline_running": True})
        True
    """
    if session_id not in sessions:
        return False
    sessions[session_id].update(updates)
    return True


def delete_session(session_id: str) -> bool:
    """Delete session (cleanup).

    Optional for MVP. Use to manually cleanup sessions.

    Args:
        session_id: Session identifier

    Returns:
        True if session was deleted, False if not found
    """
    if session_id in sessions:
        del sessions[session_id]
        return True
    return False


def require_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Helper: Validate session exists and return it, or return error dict.

    This is a convenience helper for endpoint handlers. Returns either the
    session dict (truthy) or an error response dict (falsy with 'error' key).

    Args:
        session_id: Session identifier to validate

    Returns:
        Session dict if valid, or error response dict if invalid.
        Check with: `if 'error' in result: ...handle error...`

    Example:
        >>> @app.post("/api/chat")
        ... async def chat(request: ChatRequest):
        ...     session = require_session(request.session_id)
        ...     if "error" in session:  # Error case
        ...         return session
        ...     # Session valid, proceed with logic
    """
    session = get_session(session_id)
    if session is None:
        return {
            "status": "error",
            "error": {
                "message": "Session not found. Please refresh the page and try again.",
                "code": "INVALID_SESSION"
            }
        }
    return session


def get_all_sessions_for_testing() -> Dict[str, Dict[str, Any]]:
    """Return all sessions for testing/debugging purposes.

    WARNING: Only use in tests. This exposes all session data.
    """
    return dict(sessions)


def clear_all_sessions_for_testing():
    """Clear all sessions for test cleanup.

    WARNING: Only use in tests. This destroys all session data.
    """
    global sessions
    sessions.clear()
