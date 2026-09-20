"""FastAPI backend entry point."""

from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException

from agents.document_agent import DocumentAgent


app = FastAPI(
    title="Financial Multi-Agent API"
)


# Upload folder
UPLOAD_FOLDER = Path("data/uploads")
UPLOAD_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)


# Document Agent
document_agent = DocumentAgent()


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return service health information."""

    return {
        "status": "ok"
    }


@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...)
):
    """Upload and index a financial PDF."""

    # Check file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )


    # Save uploaded PDF
    file_path = UPLOAD_FOLDER.joinpath(file.filename)

    contents = await file.read()

    with open(file_path, "wb") as f:
        f.write(contents)


    # Process PDF using Document Agent
    result = document_agent.process_document(
        str(file_path)
    )


    return {
        "message": "Document uploaded and indexed successfully",
        "filename": file.filename,
        "result": result
    }