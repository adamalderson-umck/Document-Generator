from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel, Field
import json
import shutil
import os
from uuid import uuid4
from extractors import parse_source_doc, parse_email_text
from generators import generate_word_docs, get_missing_variables
from site_config import merge_site_config

app = FastAPI()

# 1. Setup Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
inputs_dir = os.path.join(BASE_DIR, "inputs")
outputs_dir = os.path.join(BASE_DIR, "outputs")
# Note: We renamed the docx folder to 'docx_templates' to avoid conflict
docx_templates_dir = os.path.join(BASE_DIR, "docx_templates")

# Ensure dirs exist
os.makedirs(inputs_dir, exist_ok=True)
os.makedirs(outputs_dir, exist_ok=True)
session_store_dir = os.path.join(inputs_dir, ".sessions")
last_session_file = os.path.join(session_store_dir, "last_session_id.txt")

# 2. Mount Static & Templates (HTML)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Simple in-memory run store for this local single-user tool.
sessions = {}
last_session_id = None


class GenerateFinalPayload(BaseModel):
    session_id: str | None = Field(default=None, min_length=1)
    extra_fields: dict[str, str] = Field(default_factory=dict)


def resolve_session(session_id):
    global last_session_id
    if session_id:
        session = sessions.get(session_id) or load_session(session_id)
        if session:
            last_session_id = session_id
        return session

    if last_session_id and last_session_id in sessions:
        return sessions[last_session_id]

    remembered_session_id = last_session_id or load_last_session_id()
    if remembered_session_id:
        session = sessions.get(remembered_session_id) or load_session(remembered_session_id)
        if session:
            last_session_id = remembered_session_id
            return session

    if len(sessions) == 1:
        last_session_id = next(iter(sessions.keys()))
        return next(iter(sessions.values()))
    return None


def _is_safe_session_id(session_id):
    return isinstance(session_id, str) and bool(session_id) and all(
        char.isalnum() or char in ("-", "_") for char in session_id
    )


def _session_path(session_id):
    if not _is_safe_session_id(session_id):
        return None
    return os.path.join(session_store_dir, f"{session_id}.json")


def load_last_session_id():
    try:
        with open(last_session_file, encoding="utf-8") as file:
            session_id = file.read().strip()
    except FileNotFoundError:
        return None
    return session_id if _is_safe_session_id(session_id) else None


def load_session(session_id):
    session_path = _session_path(session_id)
    if not session_path or not os.path.exists(session_path):
        return None

    with open(session_path, encoding="utf-8") as file:
        session = json.load(file)
    sessions[session_id] = session
    return session


def save_session(session_id, session):
    global last_session_id
    session_path = _session_path(session_id)
    if not session_path:
        return

    os.makedirs(session_store_dir, exist_ok=True)
    with open(session_path, "w", encoding="utf-8") as file:
        json.dump(session, file)
    with open(last_session_file, "w", encoding="utf-8") as file:
        file.write(session_id)
    sessions[session_id] = session
    last_session_id = session_id


def verify_generated_files(generated_files):
    if not generated_files:
        raise HTTPException(
            status_code=500,
            detail=f"Generation finished but no files were created in {outputs_dir}.",
        )

    missing_files = [path for path in generated_files if not os.path.exists(path)]
    if missing_files:
        raise HTTPException(
            status_code=500,
            detail="Generation finished but these output files were not found: "
            + ", ".join(missing_files),
        )


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    asset_version = str(max(
        os.path.getmtime(os.path.join(BASE_DIR, "static", "script.js")),
        os.path.getmtime(os.path.join(BASE_DIR, "static", "style.css")),
    ))
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "asset_version": asset_version},
    )

@app.get("/favicon.ico")
async def favicon():
    return HTMLResponse(content="", status_code=204)


@app.post("/upload_source")
async def upload_source(file: UploadFile = File(...)):
    """
    Step 1: User uploads the Source Word Doc.
    We save it and run the initial parsing.
    """
    try:
        file_path = os.path.join(inputs_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Parse immediately
        extracted_data = parse_source_doc(file_path)

        session_id = uuid4().hex
        sessions[session_id] = {
            "data": extracted_data,
            "filename": file.filename,
        }
        save_session(session_id, sessions[session_id])

        return {
            "status": "success",
            "session_id": session_id,
            "filename": file.filename,
            "data": extracted_data,
            "warnings": extracted_data.get("_parse_warnings", []),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze_inputs")
async def analyze_inputs(
    session_id: str | None = Form(None),
    email_1: str = Form(""),
    email_2: str = Form("")
):
    """
    Step 2a: Analyze inputs and detect missing fields.
    """
    try:
        session = resolve_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Upload a source document before analyzing inputs.")

        current_data = dict(session["data"])

        # 1. Parse Emails
        music_1 = parse_email_text(email_1, source_type="organist")
        music_2 = parse_email_text(email_2, source_type="choir")

        current_data.update(music_1)
        current_data.update(music_2)
        current_data = merge_site_config(current_data)
        session["data"] = current_data
        if session_id or last_session_id:
            save_session(session_id or last_session_id, session)

        # 3. Detect Missing Variables
        missing_fields = get_missing_variables(current_data, docx_templates_dir)
        warnings = current_data.get("_parse_warnings", [])

        if missing_fields:
            return {
                "status": "needs_input",
                "missing_fields": missing_fields,
                "current_data": current_data,
                "warnings": warnings,
            }
        else:
            # No missing fields? We can signal frontend to proceed or just return success
            return {
                "status": "ready",
                "current_data": current_data,
                "warnings": warnings,
            }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate_final")
async def generate_final(payload: GenerateFinalPayload):
    """
    Step 2b: Receive final data (including manual inputs) and generate.
    We expect a JSON body now, not Form data, to easily handle dynamic fields.
    """
    try:
        extra_fields = dict(payload.extra_fields)

        session = resolve_session(payload.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Upload a source document before generating.")

        current_data = dict(session["data"])

        # Update global data with manual inputs
        # NEW: Apply formatting to hymn numbers if they appear in extra_fields
        from extractors import format_hymn_number

        for key, value in extra_fields.items():
            if (key.endswith("_num") or key == "communion_hymn_num" or key == "doxology_num") and value:
                # Apply format
                extra_fields[key] = format_hymn_number(value)

        current_data.update(extra_fields)
        current_data = merge_site_config(current_data)
        session["data"] = current_data
        if payload.session_id or last_session_id:
            save_session(payload.session_id or last_session_id, session)

        # Generate Docs
        generated_files = generate_word_docs(current_data, docx_templates_dir, outputs_dir)
        verify_generated_files(generated_files)

        return {
            "status": "success",
            "message": "Documents Generated Successfully!",
            "output_dir": outputs_dir,
            "generated_files": generated_files or [],
            "warnings": current_data.get("_parse_warnings", []),
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        with open("server_error.log", "w") as f:
            f.write(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
