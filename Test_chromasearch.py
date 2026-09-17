import chromadb

client = chromadb.PersistentClient(path="./vector_db")
collection = client.get_collection(name="financial_documents")

result = collection.get()

for metadata,ids in zip(result["metadatas"], result["ids"]):
    print(f"id :{ids}")
    print(f"company :{metadata.get("company")} ")
