"""FastAPI backend entry point."""

from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel

from agents.document_agent import DocumentAgent
from database import get_connection, create_tables


# FastAPI App
app = FastAPI(title="Financial Multi-Agent API")


# Create Database Tables
create_tables()


# Upload Folder
UPLOAD_FOLDER = Path("data/uploads")
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


# Document Agent
document_agent = DocumentAgent()


# Research Session Model
class SessionCreate(BaseModel):
    name: str


# Health Check
@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


# Create Research Session
@app.post("/sessions")
def create_session(session: SessionCreate):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO research_sessions (name)
        VALUES (?)
        """,
        (session.name,),
    )

    session_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return {
        "session_id": session_id,
        "name": session.name,
        "status": "created",
    }


# Upload Document
@app.post("/upload")
async def upload_document(
    session_id: int,
    file: UploadFile = File(...),
):
    """Upload and index a financial PDF."""

    # Check Research Session
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT session_id
        FROM research_sessions
        WHERE session_id = ?
        """,
        (session_id,),
    )

    session = cursor.fetchone()

    if not session:
        connection.close()
        raise HTTPException(
            status_code=404,
            detail="Research session not found",
        )

    # Check PDF File
    if not file.filename.lower().endswith(".pdf"):
        connection.close()
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed",
        )

    # Save Uploaded PDF
    file_path = UPLOAD_FOLDER / file.filename

    contents = await file.read()

    with open(file_path, "wb") as f:
        f.write(contents)

    # Process PDF
    result = document_agent.process_document(str(file_path))

    # Generate UNIQUE database document ID
    database_document_id = str(uuid4())

    # Save Document Information
    cursor.execute(
        """
        INSERT INTO documents (
            document_id,
            session_id,
            filename,
            company,
            file_path,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            database_document_id,
            session_id,
            file.filename,
            result["company"],
            str(file_path),
            result["status"],
        ),
    )

    connection.commit()
    connection.close()

    # Response
    return {
        "message": "Document uploaded successfully",
        "session_id": session_id,
        "document_id": database_document_id,
        "filename": file.filename,
        "result": result,
    }