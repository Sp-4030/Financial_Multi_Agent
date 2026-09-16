"""FastAPI backend entry point."""

from fastapi import FastAPI

app = FastAPI(title="Financial Multi-Agent API")


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return service health information."""
    return {"status": "ok"}
