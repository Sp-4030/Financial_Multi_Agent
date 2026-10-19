from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_text(text):
    if not text or not text.strip():
        return []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    chunks = splitter.split_text(text)

    return chunks


def split_pages(pages):
    """Split page dictionaries into chunks while preserving page numbers."""
    if not pages:
        return []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    result = []
    for page in pages:
        text = page.get("text", "")
        page_num = page.get("page_number", 1)
        if not text or not text.strip():
            continue
        sub_chunks = splitter.split_text(text)
        for chunk in sub_chunks:
            result.append({
                "text": chunk,
                "page_number": page_num,
            })
    return result