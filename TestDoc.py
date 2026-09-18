from agents.document_agent import DocumentAgent

agent = DocumentAgent()

result = agent.process_document("data/seed_documents/Infosys.pdf")

print(result)
