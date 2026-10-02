"""Streamlit frontend for the local financial multi-agent system."""

import hashlib
import tempfile
from pathlib import Path

import streamlit as st

from agents.document_agent import DocumentAgent
from agents.extraction_agent import ExtractionAgent
from agents.red_flag_agent import RedFlagAgent
from agents.research_agent import ResearchAgent
from utils.pdf_parser import extract_text_from_pdf


st.set_page_config(
    page_title="Financial Multi-Agent",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)

st.title("Financial Multi-Agent Research Console")
st.caption("Upload annual reports, index them locally, and ask grounded financial questions.")


@st.cache_resource
def get_agents():
    return {
        "document": DocumentAgent(),
        "extraction": ExtractionAgent(),
        "red_flag": RedFlagAgent(),
        "research": ResearchAgent(),
    }


agents = get_agents()


if "last_uploaded_file" not in st.session_state:
    st.session_state.last_uploaded_file = None
if "indexed_company" not in st.session_state:
    st.session_state.indexed_company = None
if "last_metrics" not in st.session_state:
    st.session_state.last_metrics = {}
if "last_red_flags" not in st.session_state:
    st.session_state.last_red_flags = {}
if "last_document_result" not in st.session_state:
    st.session_state.last_document_result = None
if "last_processed_upload_hash" not in st.session_state:
    st.session_state.last_processed_upload_hash = None


st.sidebar.header("Project Overview")
st.sidebar.markdown(
    """
    - Local PDF ingestion
    - ChromaDB document indexing
    - Financial metric extraction
    - Research Q&A and risk review
    - Local Ollama-powered analysis
    """
)


uploaded_file = st.file_uploader(
    "Upload a financial annual report (PDF)",
    type=["pdf"],
    accept_multiple_files=False,
)


if uploaded_file is not None:
    uploaded_content = uploaded_file.getvalue()
    upload_hash = hashlib.sha256(uploaded_content).hexdigest()

if uploaded_file is not None and upload_hash != st.session_state.last_processed_upload_hash:
    progress_bar = st.progress(0)
    status_text = st.empty()
    status_text.info("Please wait — working on your PDF. This can take a few moments.")

    temp_dir = Path(tempfile.mkdtemp())
    local_path = temp_dir / uploaded_file.name
    local_path.write_bytes(uploaded_content)

    st.session_state.last_document_result = None
    st.session_state.last_uploaded_file = None
    st.session_state.indexed_company = None
    st.session_state.last_metrics = {}
    st.session_state.last_red_flags = {}

    with st.spinner("Please wait — processing and analyzing your PDF..."):
        try:
            status_text.text("Step 1/4: Indexing document...")
            progress_bar.progress(10)
            result = agents["document"].process_document(str(local_path))

            status_text.text("Step 2/4: Extracting financial text...")
            progress_bar.progress(45)
            text = extract_text_from_pdf(str(local_path))

            status_text.text("Step 3/4: Calculating financial metrics...")
            progress_bar.progress(65)
            metrics = agents["extraction"].extract_metrics(text)
            st.session_state.last_metrics = metrics

            status_text.text("Step 4/4: Checking for financial red flags...")
            progress_bar.progress(85)
            red_flags = agents["red_flag"].analyze(text, metrics)
            st.session_state.last_red_flags = red_flags

            st.session_state.last_uploaded_file = uploaded_file.name
            st.session_state.indexed_company = result.get("company", local_path.stem)
            st.session_state.last_document_result = result
            st.session_state.last_processed_upload_hash = upload_hash

            status_text.success("Processing complete. Results are ready.")
            progress_bar.progress(100)
        except Exception as exc:  # pragma: no cover - UI path only
            status_text.error("Processing failed. Please try again.")
            st.error(f"Failed to process PDF: {exc}")

if st.session_state.last_document_result:
    result = st.session_state.last_document_result
    st.success(f"Document indexed successfully: {result['document_name']}")

    col1, col2, col3 = st.columns(3)
    col1.metric("Company", result.get("company", "Unknown"))
    col2.metric("Chunks", result.get("chunks", 0))
    col3.metric("Status", result.get("status", "indexed"))

    with st.expander("Extracted Metrics", expanded=False):
        st.json(st.session_state.last_metrics)

    with st.expander("Red Flag Summary", expanded=False):
        st.json(st.session_state.last_red_flags)


st.markdown("---")

st.subheader("Ask a Financial Question")

question = st.text_area(
    "Question",
    value="What was EPAM's revenue in 2025?",
    height=120,
)

if st.button("Run Research") and question.strip():
    with st.spinner("Please wait — searching the indexed documents and preparing your answer..."):
        response = agents["research"].research(question, top_k=5)

    if not response.get("results"):
        st.warning("No relevant results were found for that question.")
    else:
        for item in response["results"]:
            st.markdown(f"### Question {item.get('question_number', '')}")
            st.markdown(f"**Question:** {item['question']}")
            st.markdown(f"**Answer:** {item['answer']}")

            if item.get("sources"):
                st.markdown("**Sources:**")
                for source in item["sources"]:
                    st.markdown(
                        f"- {source['company']} | {source['document']} | Chunk {source['chunk']}"
                    )

            st.markdown("---")


if st.session_state.last_uploaded_file:
    st.markdown("---")
    st.subheader("Latest Indexed Document")
    st.write(st.session_state.last_uploaded_file)
