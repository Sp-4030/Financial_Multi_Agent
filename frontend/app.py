"""Streamlit frontend for the financial multi-agent system powered by Google Gemini API."""

import hashlib
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
import streamlit as st
from pypdf.errors import PdfReadError

load_dotenv()

from utils.gemini_client import (
    GeminiError,
    is_gemini_configured,
)
from agents.comparison_agent import ComparisonAgent
from agents.report_agent import ReportAgent
from agents.research_agent import ResearchAgent
from workflow.graph import financial_workflow


st.set_page_config(
    page_title="Financial Multi-Agent",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)
st.title("Financial Multi-Agent Research Console")
st.caption(
    "Upload annual reports, review evidence-based risk findings with Google Gemini, "
    "and research indexed documents with source citations."
)


@st.cache_resource
def get_agents():
    return {
        "research": ResearchAgent(),
        "comparison": ComparisonAgent(),
        "report": ReportAgent(),
    }


# Session State Initialization
for key, default in (
    ("last_analysis", None),
    ("last_upload_hash", None),
    ("chat_history", []),
):
    if key not in st.session_state:
        st.session_state[key] = default

with st.sidebar:
    st.header("Document Workflow")
    uploaded_file = st.file_uploader(
        "Upload an annual report",
        type=["pdf"],
        accept_multiple_files=False,
    )
    st.caption("Documents are processed into ChromaDB and analyzed with Google Gemini.")

# Retrieve agents
agents = get_agents()

if uploaded_file is not None:
    content = uploaded_file.getvalue()
    content_hash = hashlib.sha256(content).hexdigest()
    if content_hash != st.session_state.last_upload_hash:
        try:
            with st.status(f"Ingesting and analyzing {uploaded_file.name}...", expanded=True) as status:
                st.write("📄 **Step 1/3: Document Ingestion** — Reading PDF, chunking, and embedding...")
                with tempfile.TemporaryDirectory() as temp_dir:
                    pdf_path = Path(temp_dir) / Path(uploaded_file.name).name
                    pdf_path.write_bytes(content)

                    analysis = {}
                    for event in financial_workflow.stream({"pdf_path": str(pdf_path)}):
                        if "document_agent" in event:
                            doc_res = event["document_agent"]["document_result"]
                            analysis.update(event["document_agent"])
                            st.write(
                                f"✔️ **Document Agent**: Indexed **{doc_res['chunks']} chunks** for company **{doc_res['company']}** in ChromaDB."
                            )
                            st.write("📊 **Step 2/3: Financial Extraction** — Extracting revenue, profit, debt, and balance sheet metrics...")
                        elif "extraction_agent" in event:
                            analysis.update(event["extraction_agent"])
                            metrics = event["extraction_agent"]["extracted_metrics"]
                            rev_str = metrics.get("revenue") or "Not found"
                            net_str = metrics.get("net_profit") or "Not found"
                            st.write(
                                f"✔️ **Extraction Agent**: Extracted Revenue: `{rev_str}`, Net Profit: `{net_str}`."
                            )
                            st.write("🤖 **Step 3/3: Risk Review** — Running Google Gemini AI analysis on keywords and audit disclosures...")
                        elif "red_flag_agent" in event:
                            analysis.update(event["red_flag_agent"])
                            rf = event["red_flag_agent"]["red_flag_result"]
                            st.write(
                                f"✔️ **Red-Flag Agent**: Identified **{rf.get('potential_red_flags', 0)} potential concern(s)** and {rf.get('review_items', 0)} generic disclosure(s)."
                            )

                status.update(label="✅ Document analysis complete!", state="complete", expanded=False)
                st.session_state.last_analysis = analysis
                st.session_state.last_upload_hash = content_hash
                st.success(f"Successfully processed and indexed {uploaded_file.name}!")
        except (OSError, PdfReadError, ValueError, RuntimeError, GeminiError, Exception) as exc:
            st.error(f"Document processing failed: {exc}")

if st.session_state.last_analysis:
    analysis = st.session_state.last_analysis
    document = analysis["document_result"]
    metrics = analysis["extracted_metrics"]
    red_flags = analysis["red_flag_result"]
    st.success(
        f"Indexed {document['document_name']} for {document['company']} "
        f"({document['chunks']} chunks)."
    )
    metric_columns = st.columns(3)
    metric_columns[0].metric("Revenue", metrics.get("revenue") or "Not found")
    metric_columns[1].metric("Net profit", metrics.get("net_profit") or "Not found")
    metric_columns[2].metric(
        "Potential red flags", red_flags.get("potential_red_flags", 0)
    )
    with st.expander("Review extracted metrics and red flags"):
        st.subheader("Extracted financial metrics")
        st.json(metrics)
        st.subheader("Red-flag findings")
        for flag in red_flags.get("red_flags", []):
            st.markdown(
                f"**{flag['severity']} — {flag['type']}**  \n"
                f"{flag['message']}"
            )
            if flag.get("evidence"):
                st.caption(f"Evidence: {flag['evidence']}")
            if flag.get("ai_analysis"):
                st.caption(f"Gemini Analysis: {flag['ai_analysis']}")
else:
    st.info("Upload a financial report in the sidebar to start the document-analysis workflow.")

research_tab, comparison_tab, report_tab = st.tabs(
    ["Research chat", "Company comparison", "Report"]
)

with research_tab:
    st.subheader("Ask questions about indexed reports")
    if not is_gemini_configured():
        st.warning(
            "Please set your `GEMINI_API_KEY` in the `.env` file to enable AI research."
        )

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            for item in message.get("results", []):
                st.markdown(
                    f"**{item['question_number']}. {item['question']}**  \n"
                    f"{item['answer']}"
                )
                if item.get("sources"):
                    st.caption(
                        "Sources: "
                        + "; ".join(
                            f"[{source['source']}] {source['company']} — "
                            f"{source['document']} (chunk {source['chunk']})"
                            for source in item["sources"]
                        )
                    )
    with st.form("research_form", clear_on_submit=True):
        query = st.text_area(
            "Question or numbered multi-part query",
            placeholder=(
                "1. What was revenue for Accenture in 2025?\n"
                "2. How did its net income change?"
            ),
        )
        submitted = st.form_submit_button("Research indexed documents")
    if submitted:
        if not query.strip():
            st.warning("Enter a question before starting research.")
        else:
            st.session_state.chat_history.append(
                {"role": "user", "content": query.strip()}
            )
            try:
                with st.status("🔍 Researching indexed financial documents...", expanded=True) as status:
                    st.write("📋 **Step 1/4: Analyzing Query** — Decomposing question and identifying company entities...")
                    questions = agents["research"].split_query(query.strip())
                    st.write(f"✔️ Found **{len(questions)}** research inquiry/inquiries.")

                    results = []
                    for idx, q in enumerate(questions, start=1):
                        st.write(f"📚 **Step 2/4: Retrieving Evidence (Q{idx}/{len(questions)})** — Querying ChromaDB vector database...")
                        retrieved = agents["research"].retrieve(q, top_k=5)
                        st.write(f"✔️ Retrieved **{len(retrieved)}** relevant chunk(s) from indexed reports.")

                        st.write(f"🤖 **Step 3/4: Reasoning with Google Gemini (Q{idx}/{len(questions)})** — Synthesizing answer with source citations...")
                        ans_dict = agents["research"].generate_answer(q, retrieved)
                        ans_dict["question_number"] = idx
                        ans_dict["question"] = q
                        ans_dict["retrieved_chunks"] = len(retrieved)
                        results.append(ans_dict)

                    st.write("📑 **Step 4/4: Citation Verification** — Validating source attributions...")
                    result = {
                        "query": query.strip(),
                        "questions": questions,
                        "results": results,
                        "total_questions": len(questions),
                    }
                    status.update(label=f"✅ Research completed ({len(questions)} question(s) answered)!", state="complete", expanded=False)

                st.session_state.chat_history.append(
                    {
                        "role": "assistant",
                        "content": (
                            f"Completed retrieval and analysis for "
                            f"{result['total_questions']} question(s)."
                        ),
                        "results": result["results"],
                    }
                )
                st.rerun()
            except (
                GeminiError,
                RuntimeError,
                ValueError,
                KeyError,
                Exception,
            ) as exc:
                st.error(f"Research failed: {exc}")

with comparison_tab:
    st.subheader("Benchmark indexed company documents")
    with st.spinner("Loading indexed company documents..."):
        comparison = agents["comparison"].compare()

    if comparison["document_count"] == 0:
        st.info("Index at least one report before comparing companies.")
    else:
        selected_companies = st.multiselect(
            "Companies",
            options=comparison["companies"],
            default=comparison["companies"],
        )
        with st.spinner("Filtering comparison metrics..."):
            filtered = agents["comparison"].compare(selected_companies)
        rows = []
        for document in filtered["documents"]:
            metric = document["metrics"]
            ratios = metric.get("financial_ratios", {})
            rows.append(
                {
                    "Company": document["company"],
                    "Document": document["document"],
                    "Revenue": metric.get("revenue"),
                    "Net profit": metric.get("net_profit"),
                    "Profit margin (%)": ratios.get("profit_margin"),
                    "Debt": metric.get("debt"),
                    "Total assets": metric.get("total_assets"),
                    "Total liabilities": metric.get("total_liabilities"),
                }
            )
        if rows:
            st.dataframe(rows, width="stretch", hide_index=True)
        else:
            st.info("No indexed documents match the selected companies.")

with report_tab:
    st.subheader("Executive summary and key financials")
    if not st.session_state.last_analysis:
        st.info("Upload a report in the sidebar to generate its initial report sections.")
    else:
        with st.spinner("Generating executive summary and financial report sections..."):
            analysis = st.session_state.last_analysis
            report = agents["report"].generate(
                analysis["extracted_metrics"],
                analysis["red_flag_result"],
                analysis["document_result"]["document_name"],
            )
        st.markdown(f"### {report['title']}")
        st.markdown(report["executive_summary"])
        st.markdown("#### Key Financials")
        if report["key_financials"]:
            display_financials = [
                {**item, "value": str(item["value"])}
                for item in report["key_financials"]
            ]
            st.dataframe(
                display_financials,
                width="stretch",
                hide_index=True,
            )
            report_lines = [
                f"# {report['title']}",
                "",
                "## Executive Summary",
                "",
                report["executive_summary"],
                "",
                "## Key Financials",
                "",
                "| Metric | Value | Source |",
                "| --- | --- | --- |",
            ]
            report_lines.extend(
                f"| {item['metric']} | {item['value']} | {item['source']} |"
                for item in report["key_financials"]
            )
            st.download_button(
                "Download report sections",
                data="\n".join(report_lines),
                file_name="financial-report.md",
                mime="text/markdown",
            )
        else:
            st.info("No key financial figures were extracted from this report.")
