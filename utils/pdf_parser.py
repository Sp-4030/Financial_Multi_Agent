from pypdf import PdfReader
from pypdf.errors import PdfReadError


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from every readable page or report an invalid/empty PDF."""
    try:
        reader = PdfReader(pdf_path, strict=False)
    except (OSError, PdfReadError) as exc:
        raise ValueError(f"Unable to read PDF: {exc}") from exc

    if reader.is_encrypted:
        try:
            if not reader.decrypt(""):
                raise ValueError("Encrypted PDFs are not supported.")
        except PdfReadError as exc:
            raise ValueError("Encrypted PDFs are not supported.") from exc

    pages = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text and page_text.strip():
            pages.append(page_text.strip())

    text = "\n\n".join(pages)
    if not text:
        raise ValueError("No extractable text was found in the PDF.")
    return text
