"""Data Analysis Copilot - FastAPI REST API Backend

This module serves as the main FastAPI application entry point.
All REST API endpoints are defined here.

Architecture Notes:
- services/ = REST API layer ONLY (no pipeline imports for clean separation)
- pipeline/ = AI logic ONLY (no FastAPI imports, no Streamlit imports)
- utils/ = Shared utilities accessible from both layers
"""

import os
import io
import uuid
import tempfile
from dotenv import load_dotenv
from fastapi import FastAPI, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd

# Import all Pydantic models
from services.models import (
    CreateSessionResponse,
    UploadResponse,
    DataPreviewResponse,
    DataUpdateRequest,
    ChatRequest,
    ChatResponse,
    ExecuteRequest,
    ExecuteResponse,
    StatusResponse,
    ReportResponse,
    CodeRequest,
    CodeResponse,
    ReruncodeRequest,
    TemplatesResponse,
    SaveTemplateRequest,
)

# Import session management
from services.session import (
    create_session as create_session_db,
    get_session,
    require_session,
)

# Import error translation layer
from utils.error_translation import translate_error

# Import large data utilities
from utils.large_data import detect_large_data, apply_uniform_stride

# Import template utilities (aliased to avoid collision with save_template endpoint function)
from utils.templates import load_templates, save_template as _write_template

# In-memory templates cache — populated at startup via load_templates(), updated on POST /api/templates
_templates: list[dict] = []

# Load environment variables from .env file
load_dotenv()

# Validate required environment variables on startup
def validate_startup_config():
    """Validate critical configuration on application startup."""
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable is required but not set. "
            "Please set OPENAI_API_KEY in .env file or environment."
        )


# Initialize FastAPI application
app = FastAPI(
    title="data-analysis-copilot",
    version="0.1.0",
    description="AI-powered data analysis assistant with natural language query interface"
)

# Add CORS middleware for localhost:3000 (Next.js frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Run validations and setup on application startup."""
    global _templates
    try:
        validate_startup_config()
    except ValueError as e:
        print(f"❌ Startup validation failed: {e}")
        raise
    _templates.extend(load_templates())


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint - confirms API is running."""
    return {
        "message": "Data Analysis Copilot API",
        "version": "0.1.0",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# ============================================================================
# Session Management Endpoints
# ============================================================================

@app.post("/api/session", response_model=dict)
async def create_session_endpoint() -> dict:
    """Create new session with UUID.

    Returns a unique session identifier that must be included in all subsequent API calls.

    Session includes:
    - Unique session_id (UUID)
    - In-memory storage for uploaded DataFrames
    - Pipeline state tracking
    - Temporary file path storage

    Story 1.3: Real session storage with in-memory dict

    Returns:
        Dict with status and session_id
    """
    session = create_session_db()
    return {
        "status": "success",
        "data": {"session_id": session["session_id"]}
    }


# ============================================================================
# CSV Upload Endpoints
# ============================================================================

@app.post("/api/upload", response_model=dict)
async def upload_files(
    session_id: str = Header(...),
    files: list[UploadFile] = File(...)
) -> dict:
    """Upload CSV files for analysis.

    - **session_id**: Session identifier from /api/session (via X-Session-ID header)
    - **files**: One or more CSV files to upload

    Returns filenames, row counts, and optional large data warning.

    Story 3.1: CSV parsing and storage implemented
    """
    session = require_session(session_id)
    if "error" in session:
        return session

    filenames = []
    row_counts = {}
    total_size_mb = 0.0

    # Parse each uploaded file
    for file in files:
        try:
            # Read file content into memory
            content = await file.read()

            # Check file size (sanity check: max 500MB)
            file_size_mb = len(content) / (1024 * 1024)
            if file_size_mb > 500:
                return {
                    "status": "error",
                    "error": {
                        "message": f"File too large: {file.filename} is {file_size_mb:.1f}MB (max 500MB)",
                        "code": "FILE_TOO_LARGE"
                    }
                }

            total_size_mb += file_size_mb

            # Check if file is empty
            if len(content) == 0:
                return {
                    "status": "error",
                    "error": {
                        "message": f"File is empty: {file.filename}",
                        "code": "EMPTY_FILE"
                    }
                }

            # Parse CSV into DataFrame
            try:
                df = pd.read_csv(io.BytesIO(content))
            except Exception as e:
                return {
                    "status": "error",
                    "error": {
                        "message": translate_error(e),
                        "code": "INVALID_CSV"
                    }
                }

            # Check if DataFrame is empty (only headers, no data)
            if len(df) == 0:
                return {
                    "status": "error",
                    "error": {
                        "message": f"File contains no data: {file.filename}",
                        "code": "EMPTY_FILE"
                    }
                }

            # Store in session
            session["uploaded_dfs"][file.filename] = df
            filenames.append(file.filename)
            row_counts[file.filename] = len(df)

        except Exception as e:
            return {
                "status": "error",
                "error": {
                    "message": translate_error(e),
                    "code": "FILE_UPLOAD_ERROR"
                }
            }

    # Combined large data detection — after ALL files processed (FR26)
    combined_rows = sum(len(df) for df in session["uploaded_dfs"].values())

    # Build response
    response_data = {
        "status": "success",
        "data": {
            "filenames": filenames,
            "row_counts": row_counts
        }
    }

    # Add large data warning if combined dataset exceeds thresholds
    if detect_large_data(combined_rows, total_size_mb):
        response_data["data"]["large_data_warning"] = {
            "detected": True,
            "row_count": combined_rows,
            "size_mb": round(total_size_mb, 1),
            "message": (
                f"Your dataset has {combined_rows:,} rows / {total_size_mb:.1f} MB, "
                "which exceeds the visualization threshold."
            )
        }

    return response_data


@app.post("/api/downsample", response_model=dict)
async def downsample_data(session_id: str = Header(...)) -> dict:
    """Apply uniform stride downsampling to all uploaded DataFrames.

    Reduces all uploaded DataFrames to ≤10,000 rows via apply_uniform_stride().
    Updates session uploaded_dfs, csv_temp_paths, and marks recovery_applied.
    Prerequisite: CSV files must have been uploaded via /api/upload first.

    Story 9.2: Auto-downsample recovery path (FR28)
    """
    session = require_session(session_id)
    if "error" in session:
        return session

    uploaded_dfs = session.get("uploaded_dfs", {})
    if not uploaded_dfs:
        return {
            "status": "error",
            "error": {
                "message": "No uploaded data to downsample. Please upload a CSV file first.",
                "code": "NO_DATA"
            }
        }

    filenames = []
    row_counts = {}
    new_temp_paths = {}

    for filename, df in uploaded_dfs.items():
        downsampled_df = apply_uniform_stride(df)
        session["uploaded_dfs"][filename] = downsampled_df
        filenames.append(filename)
        row_counts[filename] = len(downsampled_df)

        # Write downsampled DataFrame to temp CSV file for pipeline use (FR28)
        with tempfile.NamedTemporaryFile(
            suffix=".csv", delete=False, mode='w', newline=''
        ) as tmp:
            downsampled_df.to_csv(tmp, index=False)
            new_temp_paths[filename] = tmp.name

    session["csv_temp_paths"] = new_temp_paths
    session["recovery_applied"] = "uniform_stride_10k"

    return {
        "status": "success",
        "data": {
            "filenames": filenames,
            "row_counts": row_counts,
            "downsampled": True
        }
    }


# ============================================================================
# Data Management Endpoints
# ============================================================================

@app.get("/api/data", response_model=dict)
async def get_data(session_id: str = Header(...)) -> dict:
    """Get preview of uploaded data files.

    - **session_id**: Session identifier (via session-id header)

    Returns list of files with metadata, column types, and preview rows.

    Story 3.2: Data preview with rows and types implemented

    Returns:
        Dict with status and list of files with preview data, or error response
    """
    session = require_session(session_id)
    if "error" in session:
        return session

    # Return uploaded DataFrames with metadata and preview rows
    files = []
    for filename, df in session.get("uploaded_dfs", {}).items():
        # Get column names and data types
        columns = list(df.columns) if hasattr(df, 'columns') else []
        dtypes = [str(dtype) for dtype in df.dtypes] if hasattr(df, 'dtypes') else []

        # Get preview rows (first 10-20 rows, but at most all rows if < 10)
        preview_limit = min(20, max(10, len(df)))
        preview_df = df.head(preview_limit)
        preview_rows = preview_df.fillna("").to_dict('records')

        files.append({
            "name": filename,
            "columns": columns,
            "dtypes": dtypes,
            "rows": len(df) if hasattr(df, '__len__') else 0,
            "preview": preview_rows
        })

    return {
        "status": "success",
        "data": {"files": files}
    }


@app.put("/api/data", response_model=dict)
async def update_data(request: DataUpdateRequest) -> dict:
    """Update data with manual edits (cell value updates).

    - **session_id**: Session identifier
    - **filename**: Name of the CSV file to update
    - **row_index**: Index of the row to update
    - **column**: Column name to update
    - **value**: New value for the cell

    Applies user edits to uploaded data with data type validation.

    Story 3.3: Data editing with validation implemented
    """
    session = require_session(request.session_id)
    if "error" in session:
        return session

    # Validate file exists in session
    uploaded_dfs = session.get("uploaded_dfs", {})
    if request.updates.get("filename") not in uploaded_dfs:
        return {
            "status": "error",
            "error": {
                "message": f"File not found: {request.updates.get('filename')}",
                "code": "FILE_NOT_FOUND"
            }
        }

    df = uploaded_dfs[request.updates.get("filename")]
    row_index = request.updates.get("row_index")
    column = request.updates.get("column")
    value = request.updates.get("value")

    # Validate row index
    if not isinstance(row_index, int) or row_index < 0 or row_index >= len(df):
        return {
            "status": "error",
            "error": {
                "message": f"Invalid row index: {row_index}",
                "code": "INVALID_ROW_INDEX"
            }
        }

    # Validate column exists
    if column not in df.columns:
        return {
            "status": "error",
            "error": {
                "message": f"Column not found: {column}",
                "code": "COLUMN_NOT_FOUND"
            }
        }

    # Get column dtype
    col_dtype = str(df[column].dtype)

    # Validate data type
    validation_error = _validate_cell_value(value, col_dtype, column, row_index)
    if validation_error:
        return validation_error

    # Update the cell in the DataFrame
    try:
        # Convert value to appropriate type if needed
        converted_value = _convert_value(value, col_dtype)
        df.loc[row_index, column] = converted_value
    except Exception as e:
        return {
            "status": "error",
            "error": {
                "message": translate_error(e),
                "code": "UPDATE_FAILED"
            }
        }

    return {
        "status": "success",
        "data": {
            "filename": request.updates.get("filename"),
            "updated_rows": 1,
            "row_index": row_index,
            "column": column
        }
    }


def _validate_cell_value(value: any, dtype: str, column: str, row_index: int) -> dict | None:
    """Validate that a value matches the column data type.

    Returns error dict if invalid, None if valid.
    """
    if value is None:
        return None  # Allow None/null values

    # Integer validation
    if "int" in dtype.lower():
        if isinstance(value, bool):  # bool is subclass of int, reject it
            return {
                "status": "error",
                "error": {
                    "message": f"Invalid value for column '{column}': expected integer, got boolean",
                    "code": "VALIDATION_ERROR",
                    "field": column,
                    "row_index": row_index
                }
            }
        try:
            int(value)
        except (ValueError, TypeError):
            return {
                "status": "error",
                "error": {
                    "message": f"Invalid value for column '{column}': expected integer, got '{value}'",
                    "code": "VALIDATION_ERROR",
                    "field": column,
                    "row_index": row_index
                }
            }

    # Float validation
    elif "float" in dtype.lower():
        try:
            float(value)
        except (ValueError, TypeError):
            return {
                "status": "error",
                "error": {
                    "message": f"Invalid value for column '{column}': expected float, got '{value}'",
                    "code": "VALIDATION_ERROR",
                    "field": column,
                    "row_index": row_index
                }
            }

    # Boolean validation
    elif "bool" in dtype.lower():
        if not isinstance(value, (bool, str)):
            return {
                "status": "error",
                "error": {
                    "message": f"Invalid value for column '{column}': expected boolean, got '{value}'",
                    "code": "VALIDATION_ERROR",
                    "field": column,
                    "row_index": row_index
                }
            }
        if isinstance(value, str) and value.lower() not in ("true", "false"):
            return {
                "status": "error",
                "error": {
                    "message": f"Invalid value for column '{column}': expected 'true' or 'false', got '{value}'",
                    "code": "VALIDATION_ERROR",
                    "field": column,
                    "row_index": row_index
                }
            }

    # String/object validation - accept anything
    # datetime validation - just check it's a reasonable string
    elif "datetime" in dtype.lower():
        if not isinstance(value, str):
            return {
                "status": "error",
                "error": {
                    "message": f"Invalid value for column '{column}': expected datetime string, got {type(value).__name__}",
                    "code": "VALIDATION_ERROR",
                    "field": column,
                    "row_index": row_index
                }
            }

    return None  # Valid


def _convert_value(value: any, dtype: str) -> any:
    """Convert value to the appropriate type based on column dtype."""
    if value is None:
        return None

    if "int" in dtype.lower():
        return int(value)
    elif "float" in dtype.lower():
        return float(value)
    elif "bool" in dtype.lower():
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() == "true"
        return bool(value)
    else:
        return value  # Keep as-is for string/object types


# ============================================================================
# Chat & Interaction Endpoints
# ============================================================================

@app.post("/api/chat", response_model=dict)
async def chat(request: ChatRequest) -> dict:
    """Submit natural language query and run intent classification.

    - **session_id**: Session identifier (in request body)
    - **message**: Natural language query from user

    Story 4.1: Chat interface - store messages in session
    Story 4.2: Intent classification with response generation
      - Routes "report" through full analysis pipeline
      - Responds immediately for "qa" and "chat" intents
    """
    from datetime import datetime
    from pipeline.graph import run_pipeline
    from pipeline.state import PipelineState

    session = require_session(request.session_id)
    if "error" in session:
        return session

    # Validate message is non-empty
    message_text = request.message.strip() if request.message else ""
    if not message_text:
        return {
            "status": "error",
            "error": {
                "message": "Message cannot be empty",
                "code": "EMPTY_MESSAGE"
            }
        }

    try:
        # Create user message
        user_message_id = str(uuid.uuid4())
        user_message = {
            "id": user_message_id,
            "role": "user",
            "content": message_text,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        # Append user message to chat history
        session["chat_history"].append(user_message)

        # Initialize pipeline state with user query and session data
        pipeline_state: PipelineState = {
            "user_query": message_text,
            "csv_temp_paths": session.get("csv_temp_paths", {}),
            "csv_metadata": session.get("csv_metadata", ""),
            "intent": "chat",  # default, will be updated by classify_intent
            "response": "",
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
            "recovery_applied": session.get("recovery_applied", ""),
        }

        # Run the pipeline (intent classification, response generation, etc.)
        result_state = run_pipeline(pipeline_state)

        intent = result_state.get("intent", "chat")
        response_text = result_state.get("response", "")
        plan_steps = result_state.get("plan", [])

        # Create bot message
        bot_message_id = str(uuid.uuid4())
        # For reports, indicate that plan is ready; for others, use generated response
        bot_content = "Plan ready for your analysis." if intent == "report" else (
            response_text or "I've processed your request."
        )
        bot_message = {
            "id": bot_message_id,
            "role": "bot",
            "content": bot_content,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        # Append bot message to chat history
        session["chat_history"].append(bot_message)

        # Store pipeline state in session for future reference
        session["pipeline_state"] = result_state
        session["last_intent"] = intent
        if intent == "report" and plan_steps:
            session["current_plan"] = plan_steps

        # Format response based on intent
        response_data = {
            "chat_history": session["chat_history"],
            "intent": intent,
        }

        if intent == "report" and plan_steps:
            response_data["plan"] = plan_steps
        elif intent in ("qa", "chat") and response_text:
            response_data["response"] = response_text

        return {
            "status": "success",
            "data": response_data
        }

    except Exception as e:
        from utils.error_translation import translate_error
        error_msg = translate_error(e)
        return {
            "status": "error",
            "error": {
                "message": error_msg,
                "code": "PIPELINE_ERROR"
            }
        }


# ============================================================================
# Pipeline Execution Endpoints
# ============================================================================

@app.post("/api/execute", response_model=dict)
async def execute_plan(request: ExecuteRequest) -> dict:
    """Trigger execution of generated plan.

    - **session_id**: Session identifier (in request body)

    Starts pipeline execution for code generation and execution.
    Frontend polls /api/status for completion status.

    Story 5.2: Plan execution endpoint
    - Validates session exists
    - Validates plan exists in pipeline_state
    - Sets pipeline_running = True
    - Continues pipeline execution (AC #4)
    """
    from pipeline.graph import run_pipeline

    session = require_session(request.session_id)
    if "error" in session:
        return session

    # Get pipeline state from session
    pipeline_state = session.get("pipeline_state")

    # Validate plan exists (AC #4 requirement)
    if not pipeline_state or not pipeline_state.get("plan"):
        return {
            "status": "error",
            "error": {
                "message": "No plan available to execute. Please generate a plan first.",
                "code": "NO_PLAN_AVAILABLE"
            }
        }

    # Set pipeline_running flag (AC #4)
    session["pipeline_running"] = True

    try:
        # Continue pipeline execution from plan generation
        # The pipeline will proceed: generate_code → validate_code → execute_code → render_report
        final_state = run_pipeline(pipeline_state)

        # Store final state back to session
        session["pipeline_state"] = final_state
        session["pipeline_running"] = False

        return {
            "status": "success",
            "data": {
                "execution_status": "started",
                "message": "Pipeline execution started"
            }
        }
    except Exception as e:
        # Set flag to False on error
        session["pipeline_running"] = False

        # Translate error to user-friendly message
        from utils.error_translation import translate_error
        error_msg = translate_error(e)

        return {
            "status": "error",
            "error": {
                "message": error_msg,
                "code": "EXECUTION_FAILED"
            }
        }


@app.get("/api/status", response_model=dict)
async def get_status(session_id: str = Header(...)) -> dict:
    """Poll pipeline execution status.

    - **session_id**: Session identifier (via X-Session-ID header)

    Returns current execution state: running (bool), current step (str), progress (0-100).

    Story 1.3: Session validation implemented
    """
    session = require_session(session_id)
    if "error" in session:
        return session

    # Get pipeline state from session
    pipeline_state = session.get("pipeline_state")
    return {
        "status": "success",
        "data": {
            "running": session.get("pipeline_running", False),
            "step": pipeline_state.get("user_query") if pipeline_state else None,
            "progress": None  # Will be implemented in later stories
        }
    }


# ============================================================================
# Report & Results Endpoints
# ============================================================================

@app.get("/api/report", response_model=dict)
async def get_report(session_id: str = Header(...)) -> dict:
    """Get execution results and generated report.

    - **session_id**: Session identifier (via X-Session-ID header)

    Returns charts (base64-encoded PNG), text analysis, and generated code.
    Returns 404 if execution not yet complete.

    Story 1.3: Session validation implemented
    """
    session = require_session(session_id)
    if "error" in session:
        return session

    # Get pipeline state from session
    pipeline_state = session.get("pipeline_state")
    if not pipeline_state:
        return {
            "status": "error",
            "error": {
                "message": "No execution results available yet. Please run execute first.",
                "code": "NOT_FOUND"
            }
        }

    return {
        "status": "success",
        "data": {
            "charts": pipeline_state.get("report_charts", []),
            "text": pipeline_state.get("report_text", ""),
            "code": pipeline_state.get("generated_code", "")
        }
    }


# ============================================================================
# Code Review & Editing Endpoints
# ============================================================================

@app.put("/api/code", response_model=dict)
async def update_code(request: CodeRequest) -> dict:
    """Submit edited code for validation and re-execution.

    - **session_id**: Session identifier (in request body)
    - **code**: Modified Python code

    Validates code via AST allowlist (same rules as generated code), then executes
    in the subprocess sandbox. Returns report data on success, or error details.

    Error codes:
    - VALIDATION_ERROR: code failed AST allowlist check (inline in Code tab)
    - EXECUTION_ERROR:  code valid but failed at runtime (shown in Report panel)
    - NO_PIPELINE_STATE: no prior analysis to re-run against

    Story 10.2: Full validation + execution implemented
    """
    from pipeline.nodes.validator import validate_code
    from pipeline.nodes.executor import execute_code
    from utils.reexec import build_reexec_state
    from utils.error_translation import translate_error, AllowlistViolationError

    session = require_session(request.session_id)
    if "error" in session:
        return session

    pipeline_state = session.get("pipeline_state")
    if not pipeline_state:
        return {
            "status": "error",
            "error": {
                "message": "No analysis to re-run. Please run an analysis first.",
                "code": "NO_PIPELINE_STATE",
            },
        }

    # Layer 1: AST allowlist validation (same rules as generated code)
    is_valid, errors = validate_code(request.code)
    if not is_valid:
        translated = []
        for err in errors:
            if err.startswith("Syntax error:"):
                translated.append(translate_error(SyntaxError(err)))
            else:
                translated.append(translate_error(AllowlistViolationError(err)))
        return {
            "status": "error",
            "error": {
                "message": "\n".join(translated),
                "code": "VALIDATION_ERROR",
            },
        }

    # Layer 2: Subprocess execution via sandboxed executor
    reexec_state = build_reexec_state(pipeline_state, request.code)
    try:
        result = execute_code(reexec_state)
    except Exception as e:
        return {
            "status": "error",
            "error": {
                "message": translate_error(e),
                "code": "EXECUTION_ERROR",
            },
        }

    if not result.get("execution_success"):
        msgs = result.get("error_messages", [])
        return {
            "status": "error",
            "error": {
                "message": msgs[-1] if msgs else "Execution failed.",
                "code": "EXECUTION_ERROR",
            },
        }

    # Persist updated results into session pipeline_state
    pipeline_state["generated_code"] = request.code
    pipeline_state["report_charts"] = result.get("report_charts", [])
    pipeline_state["report_text"] = result.get("report_text", "")
    pipeline_state["execution_success"] = True
    session["pipeline_state"] = pipeline_state

    return {
        "status": "success",
        "data": {
            "charts": pipeline_state["report_charts"],
            "text": pipeline_state["report_text"],
            "code": request.code,
        },
    }


@app.post("/api/rerun", response_model=dict)
async def rerun_code(request: ReruncodeRequest) -> dict:
    """Re-execute edited code.

    - **session_id**: Session identifier (in request body)

    Triggers execution of edited code. Use /api/status to track completion.

    Story 1.3: Session validation implemented
    """
    session = require_session(request.session_id)
    if "error" in session:
        return session

    # Real execution will be implemented in Story 10.2
    return {
        "status": "success",
        "data": {"status": "started"}
    }


# ============================================================================
# Template Management Endpoints
# ============================================================================

@app.get("/api/templates", response_model=dict)
async def list_templates() -> dict:
    """List all saved analysis templates.

    Returns list of template objects with name, plan, and code.
    No session required — templates are global (not session-scoped).

    Story 11.1: Returns from in-memory cache populated at startup
    """
    return {
        "status": "success",
        "data": {"templates": _templates}
    }


@app.post("/api/templates", response_model=dict)
async def save_template(request: SaveTemplateRequest) -> dict:
    """Save current analysis as a reusable template.

    - **session_id**: Session identifier (in request body)
    - **name**: Name for the template
    - **plan**: Execution plan steps to save
    - **code**: Python code to save

    Writes to templates.json in backend root and updates in-memory cache.
    Template writes only occur from this API layer — subprocess sandbox cannot
    write to templates.json (open() is blocked by AST allowlist validator).

    Story 11.1: Full implementation — writes to templates.json + updates cache
    """
    global _templates

    session = require_session(request.session_id)
    if "error" in session:
        return session

    name = request.name.strip() if request.name else ""
    if not name:
        return {
            "status": "error",
            "error": {
                "message": "Template name cannot be empty",
                "code": "VALIDATION_ERROR"
            }
        }

    try:
        _write_template(name, request.plan, request.code)
    except OSError:
        return {
            "status": "error",
            "error": {
                "message": "Failed to save template. Check disk permissions.",
                "code": "SAVE_ERROR"
            }
        }

    _templates.append({"name": name, "plan": request.plan, "code": request.code})

    return {
        "status": "success",
        "data": {"saved": True, "name": name}
    }


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle validation errors."""
    return {
        "status": "error",
        "error": {
            "message": str(exc),
            "code": "VALIDATION_ERROR"
        }
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected errors."""
    return {
        "status": "error",
        "error": {
            "message": "An unexpected error occurred",
            "code": "API_ERROR"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "services.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
