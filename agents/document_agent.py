from pathlib import Path
import hashlib
from datetime import datetime, timezone
import re
import chromadb

from utils.pdf_parser import extract_text_from_pdf
from utils.chunking import split_text
from utils.embeddings import create_embeddings

class DocumentAgent:

    def __init__(self):

        # Connect to ChromaDB
        self.client = chromadb.PersistentClient(path="vector_db")

        # Get collection
        self.collection = self.client.get_or_create_collection(
            name="financial_documents"
        )

    @staticmethod
    def company_from_filename(filename):
        company = re.sub(
            r"(?i)[\s_-]*(?:annual[\s_-]+report|10-k|20-f)[\s_-]*",
            " ",
            Path(filename).stem,
        ).strip()
        company = re.sub(r"(?:[\s_-]+20\d{2})+$", "", company).strip(" _-")
        company = re.sub(r"[_-]+", " ", company).strip()
        return company or Path(filename).stem

    def process_document(self, pdf_path):

        pdf_path = Path(pdf_path)

        # Dynamic company name
        company = self.company_from_filename(pdf_path.name)

        # 1. PDF → Text
        text = extract_text_from_pdf(str(pdf_path))

        if not text.strip():
            raise ValueError("No text found in PDF")

        # 2. Text → Chunks
        chunks = split_text(text)

        if not chunks:
            raise ValueError("No chunks created from PDF")

        # 3. Chunks → Embeddings
        embeddings = create_embeddings(chunks)

        # 4. Create unique document ID
        file_hash = hashlib.md5(pdf_path.read_bytes()).hexdigest()[:12]

        document_id = f"{company}_{file_hash}"

        # 5. Create unique chunk IDs
        ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]

        # 6. Metadata
        indexed_at = datetime.now(timezone.utc).isoformat()
        metadatas = [
            {
                "document_id": document_id,
                "company": company,
                "document_name": pdf_path.name,
                "chunk_number": i,
                "indexed_at": indexed_at,
            }
            for i in range(len(chunks))
        ]

        # 7. Store in ChromaDB
        self.collection.upsert(
            ids=ids,
            documents=chunks,
            embeddings=embeddings.tolist(),
            metadatas=metadatas,
        )

        return {
            "document_id": document_id,
            "company": company,
            "document_name": pdf_path.name,
            "chunks": len(chunks),
            "status": "indexed",
        }
