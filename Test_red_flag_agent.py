from pathlib import Path
from agents.red_flag_agent import RedFlagAgent
from utils.pdf_parser import extract_text_from_pdf


pdf_path = Path(r"C:\Users\Shantanu\Desktop\Reports\Epam.pdf")
if not pdf_path.exists():
    pdf_path = Path("data/seed_documents/Epam.pdf")
if not pdf_path.exists():
    pdf_path = Path("data/uploads/Epam.pdf")


# Read PDF
text = extract_text_from_pdf(str(pdf_path))


# Create agent
agent = RedFlagAgent()


# Analyze document
result = agent.analyze(text)


# Display result
print("\n" + "=" * 60)
print("RED FLAG ANALYSIS")
print("=" * 60)

print("\nTotal Flags:", result["total_flags"])

for flag in result["red_flags"]:

    print("\nType:", flag["type"])
    print("Severity:", flag["severity"])
    print("Message:", flag["message"])