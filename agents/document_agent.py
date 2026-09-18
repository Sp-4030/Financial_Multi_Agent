from pathlib import Path
import hashlib
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

    def process_document(self, pdf_path):

        pdf_path = Path(pdf_path)

        # Dynamic company name
        company = pdf_path.stem

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
        metadatas = [
            {
                "document_id": document_id,
                "company": company,
                "document_name": pdf_path.name,
                "chunk_number": i,
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
