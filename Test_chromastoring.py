import chromadb
from pathlib import Path

from agents.document_agent import DocumentAgent

# ChromaDB Client
client = chromadb.PersistentClient(path="vector_db")

collection = client.get_or_create_collection(name="financial_documents")


# Document Agent
document_agent = DocumentAgent()


# PDF to Test
pdf_path = Path("data/seed_documents/Infosys.pdf")

if not pdf_path.exists():
    print("PDF not found:", pdf_path)
    exit()


# Process PDF using DocumentAgent
print("=" * 60)
print("Processing:", pdf_path.name)

result = document_agent.process_document(str(pdf_path))


# Print DocumentAgent Result
print("\nDocument Agent Result:")
print(result)


# Check ChromaDB
print("\n" + "=" * 60)
print("ChromaDB Check")

print("Total chunks:", collection.count())


# Get stored data
data = collection.get(
    where={"document_name": pdf_path.name}, include=["documents", "metadatas"]
)


# Display Results
print("\nStored Chunks:", len(data["ids"]))

for i, chunk_id in enumerate(data["ids"][:5]):

    print("\n-----------------------------")
    print("ID:", chunk_id)
    print("Metadata:", data["metadatas"][i])
