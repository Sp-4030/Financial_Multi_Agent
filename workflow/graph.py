"""LangGraph financial workflow orchestrating multi-agent analysis and report generation."""

from pathlib import Path
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
    company: str
    companies: list[str]
    document_result: dict
    text: str
    extracted_metrics: dict
    red_flag_result: dict
    historical_documents: list[dict[str, Any]]
    research_findings: list[dict[str, Any]]
    comparison_documents: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    report: dict[str, Any]
    report_pdf_path: str
    error: str


# Initialize Agents
document_agent = DocumentAgent()
extraction_agent = ExtractionAgent()
red_flag_agent = RedFlagAgent()
comparison_agent = ComparisonAgent()
report_agent = ReportAgent()


# Single-Document: Document Node
def document_node(state: FinancialState):
    pdf_path = state.get("pdf_path")
    if not pdf_path:
        return {"error": "pdf_path is required for document processing"}

    company = DocumentAgent.company_from_filename(pdf_path)
    historical_documents = comparison_agent.get_company_documents(company)
    result = document_agent.process_document(pdf_path)

    from utils.pdf_parser import extract_text_from_pdf
    text = extract_text_from_pdf(pdf_path)

    return {
        "company": company,
        "document_result": result,
        "text": text,
        "historical_documents": historical_documents,
    }


# Single-Document: Extraction Node
def extraction_node(state: FinancialState):
    text = state.get("text", "")
    company = state.get("company")
    doc_name = (state.get("document_result") or {}).get("document_name")
    historical = state.get("historical_documents") or []
    prior_metrics = historical[-1].get("metrics") if historical else None

    result = extraction_agent.extract_metrics(
        text,
        company=company,
        document_name=doc_name,
        prior_metrics=prior_metrics,
    )

    return {"extracted_metrics": result}


# Single-Document: Red Flag Node
def red_flag_node(state: FinancialState):
    text = state.get("text", "")
    extracted_metrics = state.get("extracted_metrics", {})
    historical_documents = state.get("historical_documents", [])
    prior_metrics = (
        historical_documents[-1]["metrics"] if historical_documents else None
    )

    result = red_flag_agent.analyze(text, extracted_metrics, prior_metrics)
    return {"red_flag_result": result}


# Multi-Company: Comparison & Retrieval Node
def multi_company_node(state: FinancialState):
    companies = state.get("companies") or []
    if not companies and state.get("company"):
        companies = [state["company"]]

    comparison = comparison_agent.compare(companies)
    documents = comparison.get("documents", [])

    all_flags = []
    combined_sources = []
    for doc in documents:
        doc_metrics = doc.get("metrics", {})
        doc_flags = red_flag_agent.analyze("", doc_metrics)
        for item in doc_flags.get("red_flags", []):
            item["company"] = doc.get("company")
            item["source"] = doc.get("document")
            all_flags.append(item)

        combined_sources.append({
            "company": doc.get("company"),
            "document": doc.get("document"),
            "document_id": doc.get("document_id"),
            "financial_year": doc.get("financial_year"),
        })

    # Pick the primary metrics from the first document if available, or aggregate
    primary_metrics = documents[0].get("metrics", {}) if documents else {}

    return {
        "comparison_documents": documents,
        "extracted_metrics": primary_metrics,
        "red_flag_result": {
            "red_flags": all_flags,
            "potential_red_flag_items": [f for f in all_flags if f.get("severity") in ("High", "Moderate")],
        },
        "sources": combined_sources,
    }


# Report Node (handles both single-company and multi-company inputs)
def report_node(state: FinancialState):
    document_result = state.get("document_result") or {}
    is_multi = bool(state.get("companies") and len(state["companies"]) > 1)

    if is_multi:
        comparison_docs = state.get("comparison_documents") or []
        doc_name = "Multi-Company Comparison"
        primary_metrics = state.get("extracted_metrics", {})
        sources = state.get("sources") or []
    else:
        doc_name = document_result.get("document_name", "Source document")
        current_document = {
            "company": document_result.get("company") or state.get("company"),
            "financial_year": state.get("extracted_metrics", {}).get("financial_year")
            or document_result.get("financial_year"),
            "document": doc_name,
            "document_id": document_result.get("document_id"),
            "metrics": state.get("extracted_metrics", {}),
        }
        comparison_docs = [
            *state.get("historical_documents", []),
            current_document,
        ]
        sources = state.get("sources") or [
            {
                "company": document_result.get("company") or state.get("company"),
                "document": doc_name,
                "document_id": document_result.get("document_id"),
            }
        ]
        primary_metrics = state.get("extracted_metrics", {})

    report = report_agent.generate(
        primary_metrics,
        red_flags=state.get("red_flag_result", {}),
        document_name=doc_name,
        comparison={"documents": comparison_docs},
        research_findings=state.get("research_findings"),
        sources=sources,
        create_pdf=True,
    )

    return {
        "report": report,
        "report_pdf_path": report.get("pdf_path"),
    }


# Workflow Entry Router
def route_workflow(state: FinancialState) -> str:
    if state.get("companies") and len(state.get("companies", [])) > 1:
        return "multi_company_node"
    return "document_agent"


# Build LangGraph
graph = StateGraph(FinancialState)

graph.add_node("document_agent", document_node)
graph.add_node("extraction_agent", extraction_node)
graph.add_node("red_flag_agent", red_flag_node)
graph.add_node("multi_company_node", multi_company_node)
graph.add_node("report_agent", report_node)

# Workflow Connections
graph.set_conditional_entry_point(
    route_workflow,
    {
        "document_agent": "document_agent",
        "multi_company_node": "multi_company_node",
    },
)

graph.add_edge("document_agent", "extraction_agent")
graph.add_edge("extraction_agent", "red_flag_agent")
graph.add_edge("red_flag_agent", "report_agent")
graph.add_edge("multi_company_node", "report_agent")
graph.add_edge("report_agent", END)

# Compile Workflow
financial_workflow = graph.compile()
