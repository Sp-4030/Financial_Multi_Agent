import chromadb
from pathlib import Path

from utils.pdf_parser import extract_text_from_pdf
from utils.chunking import split_text
from utils.embeddings import create_embeddings


# Seed PDF folder
seed_folder = Path("data/seed_documents")


# Create ChromaDB client
client = chromadb.PersistentClient(
    path="vector_db"
)


# Create collection
collection = client.get_or_create_collection(
    name="financial_documents"
)


# Find all PDFs dynamically
pdf_files = list(seed_folder.glob("*.pdf"))

if not pdf_files:
    print("No PDF files found!")
    exit()


# Process every PDF
for pdf_path in pdf_files:

    print("\n" + "=" * 60)
    print("Processing:", pdf_path.name)

    # Dynamic company name
    company = pdf_path.stem

    # 1. PDF → Text
    text = extract_text_from_pdf(str(pdf_path))

    if not text.strip():
        print("No text found. Skipping:", company)
        continue

    # 2. Text → Chunks
    chunks = split_text(text)

    print("Chunks:", len(chunks))

    # 3. Chunks → Embeddings
    embeddings = create_embeddings(chunks)

    # 4. Dynamic IDs
    ids = [
        f"{company}_chunk_{i}"
        for i in range(len(chunks))
    ]

    # 5. Metadata
    metadatas = [
        {
            "company": company,
            "document_name": pdf_path.name,
            "chunk_number": i
        }
        for i in range(len(chunks))
    ]

    # 6. Store in ChromaDB
    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings.tolist(),
        metadatas=metadatas
    )

    print("Successfully stored:", company)



print("All PDFs processed successfully!")
print("Total chunks in ChromaDB:", collection.count())