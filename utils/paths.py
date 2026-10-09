"""Shared, workspace-rooted paths for persistent application data."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def configured_path(environment_variable: str, default: Path) -> Path:
    """Resolve an optional path relative to the project root."""
    configured = os.getenv(environment_variable)
    if not configured:
        return default
    path = Path(configured).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


DATABASE_PATH = configured_path("FINANCIAL_DB_PATH", PROJECT_ROOT / "research.db")
VECTOR_DB_PATH = configured_path("CHROMA_DB_PATH", PROJECT_ROOT / "vector_db")
UPLOADS_PATH = configured_path("FINANCIAL_UPLOAD_DIR", PROJECT_ROOT / "data" / "uploads")
