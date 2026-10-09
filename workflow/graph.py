from typing import Any, TypedDict

from langgraph.graph import StateGraph, END

from agents.comparison_agent import ComparisonAgent
from agents.document_agent import DocumentAgent
from agents.extraction_agent import ExtractionAgent
from agents.red_flag_agent import RedFlagAgent
from agents.report_agent import ReportAgent

# Workflow State


class FinancialState(TypedDict, total=False):

    pdf_path: str
    document_result: dict
    text: str
    extracted_metrics: dict
    red_flag_result: dict
    historical_documents: list[dict[str, Any]]
    report: dict[str, Any]


# Initialize Agents

document_agent = DocumentAgent()
extraction_agent = ExtractionAgent()
red_flag_agent = RedFlagAgent()
comparison_agent = ComparisonAgent()
report_agent = ReportAgent()


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


def report_node(state: FinancialState):
    document_result = state["document_result"]
    current_document = {
        "company": document_result.get("company"),
        "financial_year": state.get("extracted_metrics", {}).get("financial_year")
        or document_result.get("financial_year"),
        "document": document_result.get("document_name", "Source document"),
        "document_id": document_result.get("document_id"),
        "metrics": state.get("extracted_metrics", {}),
    }
    report = report_agent.generate(
        state.get("extracted_metrics", {}),
        state.get("red_flag_result", {}),
        document_result.get("document_name", "Source document"),
        comparison={
            "documents": [
                *state.get("historical_documents", []),
                current_document,
            ]
        },
        sources=[
            {
                "document": document_result.get("document_name", "Unknown"),
                "document_id": document_result.get("document_id"),
            }
        ],
    )
    return {"report": report}


# Build LangGraph
graph = StateGraph(FinancialState)


graph.add_node("document_agent", document_node)

graph.add_node("extraction_agent", extraction_node)

graph.add_node("red_flag_agent", red_flag_node)
graph.add_node("report_agent", report_node)


# Workflow Connections
graph.set_entry_point("document_agent")

graph.add_edge("document_agent", "extraction_agent")

graph.add_edge("extraction_agent", "red_flag_agent")

graph.add_edge("red_flag_agent", "report_agent")
graph.add_edge("report_agent", END)


# Compile Workflow
financial_workflow = graph.compile()
