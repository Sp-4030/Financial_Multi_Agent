import chromadb
from utils.pdf_parser import extract_text_from_pdf
from utils.chunking import split_text
from utils.embeddings import create_embeddings

pdf_path = "data/seed_documents/Capgemini.pdf"

# 1. PDF → Text
text = extract_text_from_pdf(pdf_path)

# 2. Text → Chunks
chunks = split_text(text)

# 3. Chunks → Embeddings
embeddings = create_embeddings(chunks)


# 4. Create ChromaDB client
client = chromadb.PersistentClient(path="vector_db")


# 5. Create collection
collection = client.get_or_create_collection(name="financial_documents")


# 6. Store chunks + embeddings
collection.add(
    ids=[f"chunk_{i}" for i in range(len(chunks))],
    documents=chunks,
    embeddings=embeddings.tolist(),
)


print("Successfully stored in ChromaDB!")
print("Total documents:", collection.count())
