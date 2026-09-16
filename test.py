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

print("Total chunks:", len(chunks))
print("Embedding shape:", embeddings.shape)
print("First embedding:")
print(embeddings[0])