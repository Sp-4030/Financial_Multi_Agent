"""Compare extracted financial metrics across indexed company documents."""

from collections import defaultdict
from typing import Any, Callable

import chromadb

from agents.extraction_agent import ExtractionAgent
from utils.paths import VECTOR_DB_PATH


class ComparisonAgent:
    def __init__(self, collection: Any | None = None) -> None:
        if collection is None:
            client = chromadb.PersistentClient(path=str(VECTOR_DB_PATH))
            collection = client.get_or_create_collection(name="financial_documents")
        self.collection = collection
        self.extraction_agent = ExtractionAgent()

    def get_company_documents(
        self,
        company: str,
        progress_callback: Callable[[str], None] | None = None,
    ) -> list[dict[str, Any]]:
        """Return indexed documents and metrics for an exact company-name match."""
        if progress_callback is not None:
            progress_callback("searching")
        result = self.collection.get(include=["documents", "metadatas"])
        grouped: dict[str, dict[str, Any]] = {}
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []

        for index, text in enumerate(documents):
            metadata = (metadatas[index] or {}) if index < len(metadatas) else {}
            if str(metadata.get("company", "")).casefold() != company.casefold():
                continue

            document_id = str(metadata.get("document_id", metadata.get("document_name", "unknown")))
            group = grouped.setdefault(
                document_id,
                {
                    "document_id": document_id,
                    "company": metadata.get("company", company),
                    "document": metadata.get("document_name", "Unknown"),
                    "financial_year": metadata.get("financial_year") or None,
                    "indexed_at": metadata.get("indexed_at", ""),
                    "chunks": [],
                },
            )
            group["chunks"].append((metadata.get("chunk_number", index), text or ""))
            if metadata.get("indexed_at", "") > group["indexed_at"]:
                group["indexed_at"] = metadata["indexed_at"]

        if progress_callback is not None:
            progress_callback("analyzing")
        results = []
        for group in grouped.values():
            ordered_chunks = sorted(
                group.pop("chunks"),
                key=lambda item: (0, int(item[0])) if isinstance(item[0], (int, str)) and str(item[0]).isdigit() else (1, str(item[0])),
            )
            text = "\n".join(chunk for _, chunk in ordered_chunks)
            group["metrics"] = self.extraction_agent.extract_metrics(text)
            group["financial_year"] = (
                group["financial_year"] or group["metrics"].get("financial_year")
            )
            group["chunk_count"] = len(ordered_chunks)
            results.append(group)

        if progress_callback is not None:
            progress_callback("sources")
        return sorted(
            results,
            key=lambda item: (
                item["company"].casefold(),
                item["financial_year"] or "",
                item["indexed_at"],
                item["document"],
            ),
        )

    def list_indexed_documents(self) -> list[dict[str, Any]]:
        """List document metadata without loading all chunk text or extracting metrics."""
        result = self.collection.get(include=["metadatas"])
        documents: dict[str, dict[str, Any]] = {}
        for index, metadata in enumerate(result.get("metadatas") or []):
            metadata = metadata or {}
            document_id = str(
                metadata.get("document_id", metadata.get("document_name", index))
            )
            document = documents.setdefault(
                document_id,
                {
                    "document_id": document_id,
                    "company": metadata.get("company", "Unknown"),
                    "document": metadata.get("document_name", "Unknown"),
                    "financial_year": metadata.get("financial_year") or None,
                    "chunk_count": 0,
                },
            )
            document["chunk_count"] += 1
        return sorted(
            documents.values(),
            key=lambda item: (
                str(item["company"]).casefold(),
                str(item["financial_year"] or ""),
                str(item["document"]),
            ),
        )

    def compare(
        self,
        companies: list[str] | None = None,
        progress_callback: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        """Build side-by-side financial rows from indexed documents."""
        if progress_callback is not None:
            progress_callback("searching")
        requested_companies = list(companies or [])
        names = sorted(
            {
                str(document.get("company", "")).strip()
                for document in self.list_indexed_documents()
                if str(document.get("company", "")).strip()
            },
            key=str.casefold,
        )
        if companies is not None:
            requested = {name.casefold() for name in companies}
            names = [name for name in names if name.casefold() in requested]
        indexed_names = {
            str(document.get("company", "")).casefold()
            for document in self.list_indexed_documents()
            if document.get("company")
        }
        companies_not_indexed = [
            company
            for company in requested_companies
            if company.casefold() not in indexed_names
        ]

        if progress_callback is not None:
            progress_callback("analyzing")
        documents = [
            document
            for company in names
            for document in self.get_company_documents(company)
        ]
        if progress_callback is not None:
            progress_callback("sources")
        comparisons: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for document in documents:
            comparisons[document["company"]].append(
                {
                    "document": document["document"],
                    "document_id": document["document_id"],
                    "financial_year": document.get("financial_year"),
                    "metrics": document["metrics"],
                    "indexed_at": document["indexed_at"],
                }
            )

        return {
            "companies": names,
            "companies_not_indexed": companies_not_indexed,
            "documents": documents,
            "side_by_side": dict(comparisons),
            "rows": [
                {
                    "company": document["company"],
                    "financial_year": document.get("financial_year"),
                    "document": document["document"],
                    "metrics": document["metrics"],
                }
                for document in documents
            ],
            "document_count": len(documents),
        }