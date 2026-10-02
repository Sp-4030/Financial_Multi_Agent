import os
import warnings
from sentence_transformers import SentenceTransformer

# Suppress Hugging Face Hub unauthenticated request notice and tokenizer warnings
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
warnings.filterwarnings("ignore", message=".*unauthenticated requests to the HF Hub.*")
warnings.filterwarnings("ignore", message=".*HF_TOKEN.*")

# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")


def create_embeddings(chunks, show_progress_bar: bool = False):
    """Generate dense vector embeddings for text chunks."""
    embeddings = model.encode(
        chunks,
        show_progress_bar=show_progress_bar,
    )
    return embeddings