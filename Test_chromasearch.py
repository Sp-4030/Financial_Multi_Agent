import chromadb

client = chromadb.PersistentClient(path="./vector_db")
collection = client.get_collection(name="financial_documents")

company = collection.get()

result = {}

for metadata, id in zip(company["metadatas"], company["ids"]):
    name = metadata["company"]
    result.setdefault(name, []).append(id)

for name, ids in result.items():
    print("\nTotal chunk Pdf :-", name, len(ids))
    print(name, ids[:3])
