from agents.extraction_agent import ExtractionAgent
from utils.pdf_parser import extract_text_from_pdf

pdf_path = r"C:\\Users\\Shantanu\\Desktop\\Reports\\Epam.pdf"


# PDF → Text
text = extract_text_from_pdf(pdf_path)


# Create Extraction Agent
agent = ExtractionAgent()


# Extract metrics
result = agent.extract_metrics(text)


print("\nFinancial Metrics:")
print(result)
