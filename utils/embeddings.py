import os
import warnings
from functools import lru_cache

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
warnings.filterwarnings("ignore", message=".*unauthenticated requests to the HF Hub.*")
warnings.filterwarnings("ignore", message=".*HF_TOKEN.*")


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(
        os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    )


def create_embeddings(chunks: list[str], show_progress_bar: bool = False):
    """Generate dense vector embeddings for text chunks."""
    if not chunks:
        return []
    embeddings = _get_model().encode(
        chunks,
        show_progress_bar=show_progress_bar,
    )
    return embeddings