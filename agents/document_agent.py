from pathlib import Path
import hashlib
from datetime import datetime, timezone
import re
import chromadb

from utils.pdf_parser import extract_text_from_pdf, extract_pages_from_pdf
from utils.chunking import split_text, split_pages
from utils.embeddings import create_embeddings
from utils.paths import VECTOR_DB_PATH

class DocumentAgent:

    def __init__(self, collection=None):
        self.client = None
        if collection is None:
            self.client = chromadb.PersistentClient(path=str(VECTOR_DB_PATH))
            collection = self.client.get_or_create_collection(
                name="financial_documents"
            )
        self.collection = collection

    @staticmethod
    def company_from_filename(filename):
        company = re.sub(
            r"(?i)[\s_-]*(?:annual[\s_-]+report|10-k|20-f)[\s_-]*",
            " ",
            Path(filename).stem,
        ).strip()
        company = re.sub(
            r"(?i)(?:[\s_-]+FY[\s_-]*20\d{2}|[\s_-]+20\d{2})+$",
            "",
            company,
        ).strip(" _-")
        company = re.sub(r"(?:[\s_-]+20\d{2})+$", "", company).strip(" _-")
        company = re.sub(r"[_-]+", " ", company).strip()
        return company or Path(filename).stem

    def process_document(self, pdf_path):

        pdf_path = Path(pdf_path)
        if not pdf_path.is_file():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Dynamic company name
        company = self.company_from_filename(pdf_path.name)

        # 1. PDF → Pages & Text
        try:
            pages = extract_pages_from_pdf(str(pdf_path))
            text = "\n\n".join(p["text"] for p in pages)
            chunk_items = split_pages(pages)
        except Exception:
            text = extract_text_from_pdf(str(pdf_path))
            raw_chunks = split_text(text)
            chunk_items = [{"text": c, "page_number": 1} for c in raw_chunks]

        if not text.strip():
            raise ValueError("No text found in PDF")

        # 2. Text → Chunks
        chunks = [item["text"] for item in chunk_items]

        if not chunks:
            raise ValueError("No chunks created from PDF")

        # 3. Chunks → Embeddings
        embeddings = create_embeddings(chunks)
        if hasattr(embeddings, "tolist"):
            embeddings = embeddings.tolist()

        # 4. Create unique document ID
        file_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()[:16]

        document_id = f"{company}_{file_hash}"
        year_match = re.search(
            r"\b(?:financial\s+year|fiscal\s+year|FY)\s*[:.]?\s*"
            r"(20\d{2})(?:\s*[-/]\s*(?:20)?\d{2})?\b",
            text,
            re.IGNORECASE,
        )
        if not year_match:
            year_match = re.search(
                r"\b(?:fiscal\s+year|financial\s+year|years?)\s+ended\s+[A-Za-z]+\s+\d{1,2},?\s*(20\d{2})\b",
                text,
                re.IGNORECASE,
            )
        if not year_match:
            year_match = re.search(
                r"\b(?:annual\s+report|10-k|form\s+10-k|integrated\s+report)[^\n\r]{0,80}?\b(20\d{2})\b",
                text,
                re.IGNORECASE,
            )
        financial_year = year_match.group(1) if year_match else ""
        if not financial_year:
            file_year = re.search(r"\b(?:FY\s*)?(20\d{2})\b", pdf_path.name, re.IGNORECASE)
            if file_year:
                financial_year = file_year.group(1)

        # 5. Create unique chunk IDs
        ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]

        # 6. Metadata (including page_number)
        indexed_at = datetime.now(timezone.utc).isoformat()
        metadatas = [
            {
                "document_id": document_id,
                "company": company,
                "document_name": pdf_path.name,
                "chunk_number": i,
                "page_number": chunk_items[i].get("page_number", 1),
                "indexed_at": indexed_at,
                "financial_year": financial_year,
            }
            for i in range(len(chunks))
        ]

        # 7. Store in ChromaDB
        self.collection.upsert(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        return {
            "document_id": document_id,
            "company": company,
            "document_name": pdf_path.name,
            "chunks": len(chunks),
            "financial_year": financial_year or None,
            "status": "indexed",
        }
