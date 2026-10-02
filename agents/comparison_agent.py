"""Compare extracted financial metrics across indexed company documents."""

from collections import defaultdict
from typing import Any

import chromadb

from agents.extraction_agent import ExtractionAgent


class ComparisonAgent:
    def __init__(self, collection: Any | None = None) -> None:
        if collection is None:
            client = chromadb.PersistentClient(path="vector_db")
            collection = client.get_or_create_collection(name="financial_documents")
        self.collection = collection
        self.extraction_agent = ExtractionAgent()

    def get_company_documents(self, company: str) -> list[dict[str, Any]]:
        """Return indexed documents and metrics for an exact company-name match."""
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
                    "indexed_at": metadata.get("indexed_at", ""),
                    "chunks": [],
                },
            )
            group["chunks"].append((metadata.get("chunk_number", index), text or ""))
            if metadata.get("indexed_at", "") > group["indexed_at"]:
                group["indexed_at"] = metadata["indexed_at"]

        results = []
        for group in grouped.values():
            ordered_chunks = sorted(
                group.pop("chunks"),
                key=lambda item: (0, int(item[0])) if isinstance(item[0], (int, str)) and str(item[0]).isdigit() else (1, str(item[0])),
            )
            text = "\n".join(chunk for _, chunk in ordered_chunks)
            group["metrics"] = self.extraction_agent.extract_metrics(text)
            group["chunk_count"] = len(ordered_chunks)
            results.append(group)

        return sorted(results, key=lambda item: (item["indexed_at"], item["document"]))

    def compare(self, companies: list[str] | None = None) -> dict[str, Any]:
        """Build side-by-side financial rows from indexed documents."""
        result = self.collection.get(include=["documents", "metadatas"])
        names = sorted(
            {
                str(metadata.get("company", "")).strip()
                for metadata in (result.get("metadatas") or [])
                if metadata and str(metadata.get("company", "")).strip()
            },
            key=str.casefold,
        )
        if companies is not None:
            requested = {name.casefold() for name in companies}
            names = [name for name in names if name.casefold() in requested]

        documents = [
            document
            for company in names
            for document in self.get_company_documents(company)
        ]
        comparisons: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for document in documents:
            comparisons[document["company"]].append(
                {
                    "document": document["document"],
                    "document_id": document["document_id"],
                    "metrics": document["metrics"],
                    "indexed_at": document["indexed_at"],
                }
            )

        return {
            "companies": names,
            "documents": documents,
            "side_by_side": dict(comparisons),
            "document_count": len(documents),
        }