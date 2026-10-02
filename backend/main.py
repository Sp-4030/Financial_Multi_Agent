"""FastAPI backend entry point with Google Gemini API support."""

from contextlib import closing
import os
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pypdf.errors import PdfReadError

load_dotenv()

from utils.gemini_client import (
    GeminiError,
    get_api_key,
    is_gemini_configured,
    set_api_key,
)
from agents.comparison_agent import ComparisonAgent
from agents.report_agent import ReportAgent
from agents.research_agent import ResearchAgent
from database import get_connection, create_tables
from workflow.graph import financial_workflow


# FastAPI App
app = FastAPI(
    title="Financial Multi-Agent API",
    description="Financial research, extraction, and comparison powered by Google Gemini API.",
    version="2.0.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create Database Tables
create_tables()

# Upload folder
UPLOAD_FOLDER = Path("data/uploads")
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


research_agent = ResearchAgent()
comparison_agent = ComparisonAgent()
report_agent = ReportAgent()


# Request Models
class SessionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ResearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=5000)
    top_k: int = Field(default=5, ge=1, le=20)


class ComparisonRequest(BaseModel):
    companies: list[str] | None = None


class ReportRequest(BaseModel):
    metrics: dict[str, Any]
    red_flags: dict[str, Any] = Field(default_factory=dict)
    document_name: str = "Source document"


class ConfigRequest(BaseModel):
    gemini_api_key: str | None = None
    gemini_model: str | None = None


# Health Check
@app.get("/health")
def health_check() -> dict[str, Any]:
    return {
        "status": "ok",
        "llm_provider": "google_gemini",
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        "gemini_configured": is_gemini_configured(),
    }


# Configuration Endpoints
@app.get("/config")
def get_config() -> dict[str, Any]:
    key = get_api_key() or ""
    if not is_gemini_configured():
        masked_key = "not_configured"
    else:
        masked_key = (key[:6] + "..." + key[-4:]) if len(key) > 10 else "configured"
    return {
        "llm_provider": "google_gemini",
        "gemini_configured": is_gemini_configured(),
        "gemini_api_key": masked_key,
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
    }


@app.post("/config")
def update_config(config: ConfigRequest) -> dict[str, Any]:
    if config.gemini_api_key and config.gemini_api_key.strip():
        set_api_key(config.gemini_api_key.strip())
    if config.gemini_model and config.gemini_model.strip():
        os.environ["GEMINI_MODEL"] = config.gemini_model.strip()
    return {
        "message": "Configuration updated successfully",
        "gemini_configured": is_gemini_configured(),
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
    }


# Sessions Endpoints
@app.get("/sessions")
def list_sessions():
    with closing(get_connection()) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.execute(
            "SELECT session_id, name, created_at FROM research_sessions ORDER BY session_id DESC"
        )
        return [dict(row) for row in cursor.fetchall()]


@app.post("/sessions")
def create_session(session: SessionCreate):
    with closing(get_connection()) as connection, connection:
        cursor = connection.execute(
            "INSERT INTO research_sessions (name) VALUES (?)",
            (session.name,),
        )
        session_id = cursor.lastrowid

    return {
        "session_id": session_id,
        "name": session.name,
        "status": "created",
    }


# Documents Endpoints
@app.get("/documents")
def list_documents(session_id: int | None = None):
    with closing(get_connection()) as connection:
        connection.row_factory = sqlite3.Row
        if session_id is not None:
            cursor = connection.execute(
                "SELECT document_id, session_id, filename, company, file_path, status, created_at "
                "FROM documents WHERE session_id = ? ORDER BY created_at DESC",
                (session_id,),
            )
        else:
            cursor = connection.execute(
                "SELECT document_id, session_id, filename, company, file_path, status, created_at "
                "FROM documents ORDER BY created_at DESC"
            )
        return [dict(row) for row in cursor.fetchall()]


# Upload Document
@app.post("/upload")
async def upload_document(
    session_id: int,
    file: UploadFile = File(...),
):
    """Upload and index a financial PDF."""
    with closing(get_connection()) as connection:
        session = connection.execute(
            "SELECT session_id FROM research_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    if not session:
        raise HTTPException(status_code=404, detail="Research session not found")

    filename = Path(file.filename or "").name
    if not filename or Path(filename).suffix.casefold() != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    contents = await file.read(50 * 1024 * 1024 + 1)
    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded PDF is empty")
    if len(contents) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="PDF files must be 50 MB or smaller")

    session_upload_folder = UPLOAD_FOLDER / str(session_id)
    file_path = session_upload_folder / uuid4().hex / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(contents)

    try:
        analysis = financial_workflow.invoke({"pdf_path": str(file_path)})
    except (PdfReadError, ValueError) as exc:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail=f"Unable to process the uploaded PDF: {exc}",
        ) from exc
    except Exception as exc:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing document: {exc}",
        ) from exc

    result = analysis["document_result"]
    database_document_id = str(uuid4())

    with closing(get_connection()) as connection, connection:
        connection.execute(
            """
            INSERT INTO documents (
                document_id, session_id, filename, company, file_path, status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                database_document_id,
                session_id,
                filename,
                result["company"],
                str(file_path),
                result["status"],
            ),
        )

    return {
        "message": "Document uploaded successfully",
        "session_id": session_id,
        "document_id": database_document_id,
        "filename": filename,
        "result": result,
        "extracted_metrics": analysis["extracted_metrics"],
        "red_flag_result": analysis["red_flag_result"],
    }


@app.post("/research")
def research_documents(request: ResearchRequest):
    try:
        return research_agent.research(request.query, top_k=request.top_k)
    except GeminiError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Research failed: {exc}") from exc


@app.post("/compare")
def compare_documents(request: ComparisonRequest):
    return comparison_agent.compare(request.companies)


@app.post("/report")
def generate_report(request: ReportRequest):
    return report_agent.generate(
        request.metrics,
        request.red_flags,
        request.document_name,
    )