"""FastAPI backend entry point."""

from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel

from agents.document_agent import DocumentAgent
from database import get_connection, create_tables

app = FastAPI(title="Financial Multi-Agent API")


# Create database tables
create_tables()


# Upload folder
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

    return {"session_id": session_id, "name": session.name, "status": "created"}


# Upload Document
@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and index a financial PDF."""

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    file_path = UPLOAD_FOLDER / file.filename

    contents = await file.read()

    with open(file_path, "wb") as f:
        f.write(contents)

    result = document_agent.process_document(str(file_path))

    return {
        "message": "Document uploaded and indexed successfully",
        "filename": file.filename,
        "result": result,
    }
