from typing import Any, TypedDict

from langgraph.graph import StateGraph, END

from agents.comparison_agent import ComparisonAgent
from agents.document_agent import DocumentAgent
from agents.extraction_agent import ExtractionAgent
from agents.red_flag_agent import RedFlagAgent

# Workflow State


class FinancialState(TypedDict, total=False):

    pdf_path: str
    document_result: dict
    text: str
    extracted_metrics: dict
    red_flag_result: dict
    historical_documents: list[dict[str, Any]]


# Initialize Agents

document_agent = DocumentAgent()
extraction_agent = ExtractionAgent()
red_flag_agent = RedFlagAgent()
comparison_agent = ComparisonAgent()


# Document Agent
def document_node(state: FinancialState):

    pdf_path = state["pdf_path"]
    company = DocumentAgent.company_from_filename(pdf_path)
    historical_documents = comparison_agent.get_company_documents(company)

    result = document_agent.process_document(pdf_path)

    # Read PDF text for next agents
    from utils.pdf_parser import extract_text_from_pdf

    text = extract_text_from_pdf(pdf_path)

    return {
        "document_result": result,
        "text": text,
        "historical_documents": historical_documents,
    }


# Extraction Agent
def extraction_node(state: FinancialState):

    text = state["text"]

    result = extraction_agent.extract_metrics(text)

    return {"extracted_metrics": result}


# Red Flag Agent
def red_flag_node(state: FinancialState):

    text = state["text"]

    extracted_metrics = state.get("extracted_metrics", {})
    historical_documents = state.get("historical_documents", [])
    prior_metrics = (
        historical_documents[-1]["metrics"] if historical_documents else None
    )

    result = red_flag_agent.analyze(text, extracted_metrics, prior_metrics)

    return {"red_flag_result": result}


# Build LangGraph
graph = StateGraph(FinancialState)


graph.add_node("document_agent", document_node)

graph.add_node("extraction_agent", extraction_node)

graph.add_node("red_flag_agent", red_flag_node)


# Workflow Connections
graph.set_entry_point("document_agent")

graph.add_edge("document_agent", "extraction_agent")

graph.add_edge("extraction_agent", "red_flag_agent")

graph.add_edge("red_flag_agent", END)


# Compile Workflow
financial_workflow = graph.compile()
