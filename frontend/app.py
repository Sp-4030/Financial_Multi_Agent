"""Streamlit dashboard for the financial multi-agent research system."""

import hashlib
import logging
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from dotenv import load_dotenv
import streamlit as st

load_dotenv()

from utils.gemini_client import is_gemini_configured
from agents.comparison_agent import ComparisonAgent
from agents.red_flag_agent import RedFlagAgent
from agents.report_agent import ReportAgent
from agents.research_agent import ResearchAgent
from utils.paths import UPLOADS_PATH
from workflow.graph import financial_workflow


logger = logging.getLogger(__name__)
PAGES = (
    "Dashboard",
    "Research Chat",
    "Company Comparison",
    "Reports",
    "Indexed Documents",
)
EMPTY_VALUE = "N/A"
RESEARCH_PROGRESS_STEPS = (
    "Understanding your question...",
    "Searching relevant financial documents...",
    "Analyzing financial data...",
    "Verifying evidence and sources...",
    "Preparing your final answer...",
)

st.set_page_config(
    page_title="Financial Multi-Agent",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --navy: #14263d;
        --navy-strong: #0b1f33;
        --blue: #1d4ed8;
        --blue-pale: #eaf2ff;
        --ink: #1b2b42;
        --muted: #52647a;
        --line: #d7e0ea;
        --surface: #ffffff;
        color-scheme: light;
    }
    .stApp {
        background: #f4f7fb;
        color: var(--ink);
    }
    [data-testid="stHeader"] {
        background: rgba(244, 247, 251, 0.96);
    }
    [data-testid="stSidebar"] {
        background: #edf2f8;
        border-right: 1px solid var(--line);
    }
    [data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: var(--ink);
    }
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3,
    [data-testid="stMarkdownContainer"] h4,
    [data-testid="stMarkdownContainer"] h5,
    [data-testid="stMarkdownContainer"] h6,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
        color: var(--navy);
    }
    [data-testid="stCaptionContainer"] {
        color: var(--muted);
    }
    a {
        color: var(--blue);
    }
    a:hover {
        color: var(--navy-strong);
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        border-radius: 9px;
        padding: 0.35rem 0.55rem;
        color: var(--ink);
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        background: #e2eaf4;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section {
        background: #ffffff;
        border-color: var(--line);
        color: var(--ink);
    }
    .brand-mark {
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.11em;
        text-transform: uppercase;
        color: #315b88;
        margin: 0 0 0.35rem;
    }
    .hero {
        background: linear-gradient(120deg, #102a43 0%, #174b70 100%);
        color: #ffffff;
        border-radius: 18px;
        padding: clamp(1.4rem, 4vw, 2.4rem);
        margin: 0.3rem 0 1.35rem;
        box-shadow: 0 10px 28px rgba(16, 42, 67, 0.13);
    }
    .hero h1, .hero p { color: #ffffff; }
    .hero h1 { margin: 0.2rem 0 0.6rem; font-size: clamp(1.65rem, 4vw, 2.45rem); }
    .hero p { margin: 0; max-width: 62rem; color: #e4eef7; }
    .eyebrow {
        color: #c3e0fa;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }
    .section-kicker {
        color: var(--muted);
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
    }
    [data-testid="stButton"] button,
    [data-testid="stDownloadButton"] button {
        background: var(--navy);
        border: 1px solid var(--navy);
        color: #ffffff;
    }
    [data-testid="stButton"] button *,
    [data-testid="stDownloadButton"] button * {
        color: inherit !important;
    }
    [data-testid="stButton"] button:hover,
    [data-testid="stDownloadButton"] button:hover {
        background: var(--navy-strong);
        border-color: var(--navy-strong);
        color: #ffffff;
    }
    [data-testid="stButton"] button:disabled,
    [data-testid="stDownloadButton"] button:disabled {
        background: #e2e8f0;
        border-color: #cbd5e1;
        color: #52647a;
    }
    [data-testid="stButton"] button:disabled *,
    [data-testid="stDownloadButton"] button:disabled * {
        color: #52647a !important;
    }
    [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea,
    [data-testid="stChatInput"] textarea {
        background: #ffffff;
        color: var(--ink);
        border-color: #bdc9d8;
        caret-color: var(--navy);
    }
    [data-baseweb="input"] input::placeholder,
    [data-baseweb="textarea"] textarea::placeholder,
    [data-testid="stChatInput"] textarea::placeholder {
        color: #62748a;
        opacity: 1;
    }
    [data-baseweb="select"] > div {
        background: #ffffff;
        color: var(--ink);
        border-color: #bdc9d8;
    }
    [data-baseweb="select"] [role="combobox"],
    [data-baseweb="select"] [data-testid="stMarkdownContainer"] {
        color: var(--ink);
    }
    [data-baseweb="popover"] [role="listbox"],
    [data-baseweb="popover"] [role="option"] {
        background: #ffffff;
        color: var(--ink);
    }
    [data-baseweb="popover"] [role="option"]:hover {
        background: var(--blue-pale);
    }
    [data-testid="stMultiSelect"] [data-baseweb="tag"] {
        background: var(--blue-pale);
        color: var(--navy);
    }
    [data-testid="stMetric"] {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 13px;
        padding: 1rem 1.1rem;
        box-shadow: 0 3px 12px rgba(16, 42, 67, 0.035);
    }
    [data-testid="stMetricLabel"] { color: var(--muted); }
    [data-testid="stMetricValue"] { color: var(--navy); }
    [data-testid="stDataFrame"], [data-testid="stTable"] {
        border: 1px solid var(--line);
        border-radius: 10px;
        overflow: hidden;
    }
    [data-testid="stChatMessage"] {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 14px;
        margin-bottom: 0.7rem;
    }
    [data-testid="stChatMessage"][data-message-author-role="user"] {
        background: var(--blue-pale);
        border-color: #cbdcf6;
    }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] strong {
        color: var(--ink);
    }
    [data-testid="stTextArea"] textarea,
    [data-testid="stChatInput"] textarea {
        border-radius: 10px;
    }
    [data-testid="stStatusWidget"] {
        background: #ffffff;
        border: 1px solid var(--line);
        color: var(--ink);
    }
    [data-testid="stStatusWidget"] [data-testid="stMarkdownContainer"] {
        color: var(--ink);
    }
    .status-note {
        border: 1px solid var(--line);
        background: #ffffff;
        border-radius: 11px;
        padding: 0.75rem 0.9rem;
        margin: 0.4rem 0;
    }
    @media (max-width: 700px) {
        [data-testid="stMainBlockContainer"] {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        .hero { border-radius: 12px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_agents():
    return {
        "research": ResearchAgent(),
        "comparison": ComparisonAgent(),
        "red_flag": RedFlagAgent(),
        "report": ReportAgent(),
    }


@st.cache_data(ttl=30)
def load_indexed_documents():
    return get_agents()["comparison"].list_indexed_documents()


@st.cache_data(ttl=15)
def check_backend_api():
    try:
        with urlopen("http://127.0.0.1:8000/health", timeout=0.6) as response:
            if response.status != 200:
                return False, f"HTTP {response.status}"
            return True, "FastAPI responding"
    except (URLError, TimeoutError, OSError) as exc:
        logger.info("FastAPI health check unavailable: %s", exc)
        return False, "FastAPI not running (standalone UI remains available)"


def _display_value(value):
    return value if value not in (None, "") else EMPTY_VALUE


def _set_page(page):
    st.session_state["active_page"] = page


def _source_text(sources):
    return "; ".join(
        "{} — {} (chunk {})".format(
            source.get("company", "Unknown"),
            source.get("document", "Unknown"),
            source.get("chunk", "N/A"),
        )
        for source in sources
    )


def _source_documents_text(sources):
    documents = []
    seen = set()
    for source in sources:
        company = str(source.get("company", "Unknown") or "Unknown")
        document = str(source.get("document", "Unknown") or "Unknown")
        key = (company.casefold(), document.casefold())
        if key not in seen:
            seen.add(key)
            documents.append(f"{company} — {document}")
    return "; ".join(documents)


def _progress_updater(status, progress_bar, steps):
    resolved_steps = set()

    def update(step, state):
        label = steps[step - 1]
        if state in ("complete", "skipped"):
            resolved_steps.add(step)
        if state == "running":
            message = (
                f"Step [{step}/{len(steps)}] — Working: {label} Please wait."
            )
        elif state == "skipped":
            message = f"Step [{step}/{len(steps)}] — Skipped: {label}"
        else:
            message = f"Step [{step}/{len(steps)}] — Complete: {label}"

        status.update(label=message, state="running", expanded=True)
        progress_bar.progress(
            len(resolved_steps) / len(steps),
            text=f"{len(resolved_steps)}/{len(steps)} steps resolved",
        )

    return update


def _render_research_message(message):
    answer = message.get("answer") or message.get("content")
    if answer:
        st.markdown(answer)
    if message.get("category"):
        tasks = message.get("tasks", [])
        detail = (
            " · " + ", ".join(task.replace("_", " ") for task in tasks)
            if len(tasks) > 1
            else ""
        )
        st.caption(
            "Analysis: "
            + message["category"].replace("_", " ").title()
            + detail
        )

    results = message.get("results", [])
    if results:
        with st.expander("Research findings and retrieved evidence"):
            for item in results:
                title = item.get("question") or "Research finding"
                st.markdown(f"**{title}**")
                st.markdown(item.get("answer") or "No answer was returned.")
                if item.get("sources"):
                    st.caption("Sources: " + _source_text(item["sources"]))

    comparison_table = message.get("comparison_table") or {}
    if comparison_table.get("rows"):
        st.dataframe(
            comparison_table["rows"],
            width="stretch",
            hide_index=True,
        )
    if message.get("extracted_metrics"):
        with st.expander("Extracted financial metrics"):
            st.json(message["extracted_metrics"])
    if message.get("calculations"):
        st.markdown("**Verified calculations**")
        st.dataframe(
            message["calculations"],
            width="stretch",
            hide_index=True,
        )
        for calculation in message["calculations"]:
            st.caption(
                "{}: {} = {}% · Source: {}".format(
                    calculation.get("metric", "Ratio"),
                    calculation.get("formula", ""),
                    calculation.get("result_percent", EMPTY_VALUE),
                    calculation.get("source", "Unavailable"),
                )
            )

    for company_result in message.get("red_flag_analysis", []):
        st.markdown(
            f"**{company_result.get('company', 'Company')} — "
            f"FY {company_result.get('financial_year') or 'N/A'}**"
        )
        findings = company_result.get("findings", [])
        if not findings:
            st.info("No potential findings were returned for the available evidence.")
        for finding in findings:
            st.warning(
                f"{finding.get('type', 'Potential concern')}: "
                f"{finding.get('message', '')}\n\n"
                f"Evidence: {finding.get('evidence') or 'Unavailable'}"
            )

    report = message.get("report")
    if report:
        st.markdown(f"**{report.get('title', 'Generated report')}**")
        st.markdown(report.get("executive_summary", ""))
        if report.get("key_financials"):
            st.dataframe(report["key_financials"], width="stretch", hide_index=True)
        if report.get("sources"):
            st.caption(
                "Report sources: "
                + "; ".join(
                    str(source.get("document", "Unknown"))
                    for source in report["sources"]
                )
            )

    if message.get("sources"):
        st.caption(
            "Supporting documents: "
            + _source_documents_text(message["sources"])
        )
    if message.get("companies_not_indexed"):
        st.warning(
            "Reports are not indexed for: "
            + ", ".join(message["companies_not_indexed"])
        )


def _render_report(report):
    st.markdown(f"### {report.get('title', 'Financial Research Report')}")
    metrics = report.get("financial_metrics") or {}
    company = metrics.get("company")
    year = metrics.get("financial_year")
    if company or year:
        st.caption(
            "Company: {} · Financial year: {}".format(
                company or EMPTY_VALUE,
                year or EMPTY_VALUE,
            )
        )

    st.markdown("#### Executive summary")
    st.markdown(report.get("executive_summary") or "No summary was generated.")

    st.markdown("#### Key financial metrics")
    financials = report.get("key_financials") or []
    if financials:
        st.dataframe(
            [
                {**item, "value": str(_display_value(item.get("value")))}
                for item in financials
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No financial metrics were extracted for this report.")

    findings = report.get("red_flags") or []
    st.markdown("#### Risks and findings")
    if findings:
        for finding in findings:
            st.warning(
                f"**{finding.get('severity', 'Review')} — "
                f"{finding.get('type', 'Finding')}**: "
                f"{finding.get('message', '')}\n\n"
                f"Evidence: {finding.get('evidence') or 'Unavailable'}"
            )
    else:
        st.info("No potential findings were returned by the available risk review.")

    trends = report.get("trends") or []
    st.markdown("#### Ratios and trends")
    if trends:
        st.dataframe(
            [
                {
                    "Company": trend.get("company", EMPTY_VALUE),
                    "Metric": trend.get("metric", EMPTY_VALUE),
                    "Observations": "; ".join(
                        f"FY {item.get('financial_year', 'N/A')}: "
                        f"{item.get('value', 'N/A')} ({item.get('source', 'N/A')})"
                        for item in trend.get("observations", [])
                    ),
                    "Direction": trend.get("direction", "Not inferred"),
                }
                for trend in trends
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No comparable multi-year trend data was extracted.")

    comparison = report.get("comparison") or []
    if comparison:
        st.markdown("#### Company documents")
        st.dataframe(
            [
                {
                    "Company": item.get("company", EMPTY_VALUE),
                    "Financial year": item.get("financial_year") or EMPTY_VALUE,
                    "Document": item.get("document", EMPTY_VALUE),
                    "Revenue": _display_value(item.get("metrics", {}).get("revenue")),
                    "Net profit": _display_value(
                        item.get("metrics", {}).get("net_profit")
                    ),
                }
                for item in comparison
            ],
            width="stretch",
            hide_index=True,
        )

    research_findings = report.get("research_findings") or []
    if research_findings:
        st.markdown("#### Research findings")
        for finding in research_findings:
            st.markdown(
                f"**{finding.get('question', 'Question')}**  \n"
                f"{finding.get('answer', 'No answer available.')}"
            )
            if finding.get("sources"):
                st.caption("Sources: " + _source_text(finding["sources"]))

    st.markdown("#### Source documents")
    sources = report.get("sources") or []
    if sources:
        st.dataframe(sources, width="stretch", hide_index=True)
    else:
        st.info("No source-document references were attached to this report.")

    limitations = report.get("limitations") or []
    st.markdown("#### Missing information and limitations")
    if limitations:
        for limitation in limitations:
            st.markdown(f"- {limitation}")
    else:
        st.caption("No additional limitations were reported.")


def _report_markdown(report):
    lines = [
        f"# {report.get('title', 'Financial Research Report')}",
        "",
        "## Executive Summary",
        "",
        report.get("executive_summary") or "No summary was generated.",
        "",
        "## Key Financial Metrics",
        "",
        "| Metric | Value | Source |",
        "| --- | --- | --- |",
    ]
    for item in report.get("key_financials") or []:
        lines.append(
            "| {} | {} | {} |".format(
                item.get("metric", EMPTY_VALUE),
                item.get("value", EMPTY_VALUE),
                item.get("source", EMPTY_VALUE),
            )
        )
    lines.extend(["", "## Risks and Findings", ""])
    for finding in report.get("red_flags") or []:
        lines.append(
            "- **{} — {}**: {} Evidence: {}".format(
                finding.get("severity", "Review"),
                finding.get("type", "Finding"),
                finding.get("message", ""),
                finding.get("evidence") or "Unavailable",
            )
        )
    lines.extend(["", "## Research Findings", ""])
    for finding in report.get("research_findings") or []:
        sources = ", ".join(
            source.get("source", source.get("document", "Unknown"))
            for source in finding.get("sources", [])
        )
        lines.append(
            f"- **{finding.get('question', 'Question')}**: "
            f"{finding.get('answer', '')} Sources: {sources or 'Unavailable'}"
        )
    lines.extend(["", "## Source Documents", ""])
    for source in report.get("sources") or []:
        lines.append(
            "- {} (document ID: {})".format(
                source.get("document", "Unknown"),
                source.get("document_id") or "N/A",
            )
        )
    lines.extend(["", "## Missing Information and Limitations", ""])
    lines.extend(
        f"- {limitation}" for limitation in report.get("limitations") or []
    )
    lines.extend(["", "## Ratios and Trends", ""])
    for trend in report.get("trends") or []:
        observations = "; ".join(
            "FY {}: {} ({})".format(
                item.get("financial_year", "N/A"),
                item.get("value", "N/A"),
                item.get("source", "N/A"),
            )
            for item in trend.get("observations", [])
        )
        lines.append(
            "- **{} — {}**: {}. Direction: {}".format(
                trend.get("company", EMPTY_VALUE),
                trend.get("metric", EMPTY_VALUE),
                observations or "No observations",
                trend.get("direction", "Not inferred"),
            )
        )
    return "\n".join(lines)


for key, default in (
    ("last_analysis", None),
    ("last_upload_hash", None),
    ("last_upload_notice", None),
    ("chat_history", []),
    ("active_page", "Dashboard"),
    ("comparison_result", None),
    ("comparison_signature", None),
    ("generated_report", None),
    ("generated_report_document_id", None),
):
    if key not in st.session_state:
        st.session_state[key] = default

try:
    agents = get_agents()
    indexed_documents = load_indexed_documents()
    index_error = None
except Exception as exc:
    logger.exception("Unable to initialize the financial research UI")
    agents = None
    indexed_documents = []
    index_error = str(exc)

company_options = sorted(
    {
        str(item["company"])
        for item in indexed_documents
        if item.get("company")
    },
    key=str.casefold,
)
api_available, api_message = check_backend_api()

with st.sidebar:
    st.markdown('<div class="brand-mark">Financial Research</div>', unsafe_allow_html=True)
    st.markdown("### Financial Multi-Agent AI System")
    st.caption("Evidence-led research across indexed financial reports.")
    st.divider()
    st.markdown("**Workspace**")
    st.radio(
        "Navigation",
        PAGES,
        key="active_page",
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown("**Add a report**")
    uploaded_file = st.file_uploader(
        "Upload an annual report (PDF)",
        type=["pdf"],
        accept_multiple_files=False,
        max_upload_size=50,
        key="report_upload",
        disabled=agents is None,
    )
    st.caption("The PDF is stored locally and indexed for this workspace.")
    if st.session_state.last_upload_notice:
        st.success(st.session_state.last_upload_notice)
    st.divider()
    st.markdown("**System status**")
    if index_error:
        st.error("Document index unavailable")
        st.caption(index_error)
    else:
        st.success(f"Index ready · {len(indexed_documents)} document(s)")
    if api_available:
        st.success("API · " + api_message)
    else:
        st.info("API · " + api_message)
    if is_gemini_configured():
        st.success("Gemini · configured")
    else:
        st.warning("Gemini · not configured")
        st.caption("Document ingestion and built-in concept answers may still work.")

if uploaded_file is not None and agents is not None:
    try:
        content = uploaded_file.getvalue()
        content_hash = hashlib.sha256(content).hexdigest()
        if content_hash != st.session_state.last_upload_hash:
            st.session_state.last_upload_notice = None
            with st.status(
                f"Please wait, we’re processing {uploaded_file.name}...",
                expanded=True,
            ) as status:
                status.write("Please wait, we’re working on your document…")
                progress_bar = st.progress(0, text="0/5 steps complete")
                update_progress = _progress_updater(
                    status,
                    progress_bar,
                    (
                        "Reading and indexing the financial document...",
                        "Extracting financial data...",
                        "Reviewing risks and evidence...",
                        "Preparing the source-linked report...",
                        "Refreshing the indexed workspace...",
                    ),
                )
                update_progress(1, "running")
                pdf_path = (
                    UPLOADS_PATH
                    / "streamlit"
                    / content_hash[:16]
                    / Path(uploaded_file.name).name
                )
                pdf_path.parent.mkdir(parents=True, exist_ok=True)
                pdf_path.write_bytes(content)

                analysis = {}
                for event in financial_workflow.stream(
                    {"pdf_path": str(pdf_path)}
                ):
                    if "document_agent" in event:
                        document = event["document_agent"]["document_result"]
                        analysis.update(event["document_agent"])
                        status.write(
                            f"Indexed {document['chunks']} chunk(s) for "
                            f"{document['company']}."
                        )
                        update_progress(1, "complete")
                        update_progress(2, "running")
                    elif "extraction_agent" in event:
                        analysis.update(event["extraction_agent"])
                        update_progress(2, "complete")
                        update_progress(3, "running")
                    elif "red_flag_agent" in event:
                        analysis.update(event["red_flag_agent"])
                        update_progress(3, "complete")
                        update_progress(4, "running")
                    elif "report_agent" in event:
                        analysis.update(event["report_agent"])
                        update_progress(4, "complete")
                        update_progress(5, "running")

                st.session_state.last_analysis = analysis
                st.session_state.last_upload_hash = content_hash
                load_indexed_documents.clear()
                indexed_documents = load_indexed_documents()
                st.session_state.generated_report = analysis.get("report")
                st.session_state.generated_report_document_id = (
                    analysis.get("document_result", {}).get("document_id")
                )
                update_progress(5, "complete")
                status.update(
                    label="Analysis completed successfully.",
                    state="complete",
                    expanded=False,
                )
                progress_bar.progress(1.0, text="Analysis complete")
            st.session_state.last_upload_notice = (
                f"Successfully indexed {uploaded_file.name}."
            )
            st.rerun()
    except Exception as exc:
        logger.exception("Document processing failed for %s", uploaded_file.name)
        st.error(f"Unable to process this PDF: {exc}")

page = st.session_state.active_page

if agents is None:
    st.error(
        "The financial agents could not be initialized. Check the local "
        "ChromaDB configuration and application logs, then reload the page."
    )
    st.stop()

if page == "Dashboard":
    st.markdown(
        """
        <section class="hero">
          <div class="eyebrow">Financial intelligence workspace</div>
          <h1>Research with evidence, not assumptions.</h1>
          <p>Explore indexed annual reports, compare verified financial metrics,
          review potential risks, and assemble source-linked reports.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    count_columns = st.columns(2)
    count_columns[0].metric("Indexed documents", len(indexed_documents))
    count_columns[1].metric("Indexed companies", len(company_options))

    st.markdown("#### Continue your research")
    quick_columns = st.columns(3)
    with quick_columns[0]:
        st.markdown("**Ask a question**")
        st.caption("Research a company or financial concept with source context.")
        st.button(
            "Open Research Chat",
            use_container_width=True,
            on_click=_set_page,
            args=("Research Chat",),
        )
    with quick_columns[1]:
        st.markdown("**Compare reports**")
        st.caption("Review reported metrics across companies and periods.")
        st.button(
            "Open Company Comparison",
            use_container_width=True,
            on_click=_set_page,
            args=("Company Comparison",),
        )
    with quick_columns[2]:
        st.markdown("**Generate a report**")
        st.caption("Synthesize metrics, risk findings, and source references.")
        st.button(
            "Open Reports",
            use_container_width=True,
            on_click=_set_page,
            args=("Reports",),
        )

    if index_error:
        st.error(f"Indexed-document metadata could not be loaded: {index_error}")
    elif not indexed_documents:
        st.info(
            "No reports are indexed yet. Upload a PDF from the sidebar to begin."
        )
    else:
        st.markdown("#### Indexed reports")
        recent_documents = list(reversed(indexed_documents[-5:]))
        st.dataframe(
            [
                {
                    "Company": item.get("company", EMPTY_VALUE),
                    "Financial year": item.get("financial_year") or EMPTY_VALUE,
                    "Document": item.get("document", EMPTY_VALUE),
                    "Chunks": item.get("chunk_count", EMPTY_VALUE),
                }
                for item in recent_documents
            ],
            width="stretch",
            hide_index=True,
        )

    if st.session_state.chat_history:
        st.markdown("#### Recent research activity")
        for item in reversed(st.session_state.chat_history[-4:]):
            if item.get("role") == "user":
                st.markdown(
                    f"- **Question:** {item.get('content', '').strip()}"
                )

    latest = st.session_state.last_analysis
    if latest:
        document = latest.get("document_result", {})
        metrics = latest.get("extracted_metrics", {})
        risks = latest.get("red_flag_result", {})
        st.markdown("#### Latest document analysis")
        st.caption(
            "{} · {} · {} chunk(s)".format(
                document.get("company", EMPTY_VALUE),
                document.get("document_name", EMPTY_VALUE),
                document.get("chunks", EMPTY_VALUE),
            )
        )
        metric_columns = st.columns(3)
        metric_columns[0].metric("Revenue", _display_value(metrics.get("revenue")))
        metric_columns[1].metric(
            "Net profit",
            _display_value(metrics.get("net_profit")),
        )
        metric_columns[2].metric(
            "Potential risk findings",
            risks.get("potential_red_flags", EMPTY_VALUE),
        )
        with st.expander("Review extracted metrics and risk evidence"):
            st.json(metrics)
            for finding in risks.get("red_flags", []):
                st.markdown(
                    f"**{finding.get('severity', 'Review')} — "
                    f"{finding.get('type', 'Finding')}**: "
                    f"{finding.get('message', '')}"
                )
                st.caption("Evidence: " + (finding.get("evidence") or "Unavailable"))

elif page == "Research Chat":
    st.markdown("## Research Chat")
    st.caption(
        "Ask about financial concepts or indexed reports. Company-specific "
        "answers use available report evidence."
    )
    company_scope = st.selectbox(
        "Company scope",
        ["All indexed companies", *company_options],
        key="research_company",
    )
    company_filter = (
        company_scope if company_scope != "All indexed companies" else None
    )
    document_options = [
        item for item in indexed_documents
        if company_filter is None or item.get("company") == company_filter
    ]
    document_labels = [
        "{} — FY {} — {}".format(
            item.get("company", "Unknown"),
            item.get("financial_year") or "Year unavailable",
            item.get("document", "Unknown"),
        )
        for item in document_options
    ]
    selected_document_label = st.selectbox(
        "Document scope",
        ["All matching documents", *document_labels],
        key="research_document",
    )
    selected_document_id = None
    if selected_document_label != "All matching documents":
        selected_document_id = document_options[
            document_labels.index(selected_document_label)
        ]["document_id"]

    if not is_gemini_configured():
        st.info(
            "Gemini is not configured. Built-in concept answers and local "
            "document retrieval remain available; LLM-backed answers may not."
        )
    if not indexed_documents:
        st.info("No indexed reports yet. Upload a PDF to ask company-specific questions.")

    if st.session_state.chat_history:
        for message in st.session_state.chat_history:
            with st.chat_message(message.get("role", "assistant")):
                if message.get("role") == "user":
                    st.markdown(message.get("content", ""))
                else:
                    if message.get("_ui_status") == "success":
                        st.success("Analysis completed successfully.")
                    elif message.get("_ui_status") == "error":
                        st.error("This research request could not be completed.")
                    _render_research_message(message)
        if st.button("Clear chat history"):
            st.session_state.chat_history = []
            st.rerun()
    else:
        st.caption("Your conversation will appear here. Follow-up questions use recent context.")

    question = st.chat_input(
        "Ask about a report, financial metric, risk, or concept..."
    )
    if question:
        previous_history = st.session_state.chat_history[-10:]
        st.session_state.chat_history.append(
            {"role": "user", "content": question.strip()}
        )
        with st.chat_message("user"):
            st.markdown(question.strip())
        with st.chat_message("assistant"):
            try:
                with st.status(
                    "Please wait, we’re working on your question…",
                    expanded=True,
                ) as status:
                    status.write("Please wait, we’re working on your question…")
                    progress_bar = st.progress(0, text="0/5 steps complete")
                    update_progress = _progress_updater(
                        status,
                        progress_bar,
                        RESEARCH_PROGRESS_STEPS,
                    )
                    result = agents["research"].handle_query(
                        question.strip(),
                        top_k=5,
                        company=company_filter,
                        document_id=selected_document_id,
                        conversation_history=previous_history,
                        progress_callback=update_progress,
                    )
                    st.success("Analysis completed successfully.")
                    status.update(
                        label="Analysis completed successfully.",
                        state="complete",
                        expanded=False,
                    )
                    progress_bar.progress(1.0, text="Analysis complete")
                _render_research_message(result)
                st.session_state.chat_history.append(
                    {"role": "assistant", **result, "_ui_status": "success"}
                )
            except Exception as exc:
                logger.exception("Research chat request failed")
                failure = (
                    "I couldn't complete this research request. "
                    f"Details: {exc}"
                )
                st.error(failure)
                st.session_state.chat_history.append(
                    {
                        "role": "assistant",
                        "category": "error",
                        "answer": failure,
                        "_ui_status": "error",
                    }
                )
        st.rerun()

elif page == "Company Comparison":
    st.markdown("## Company Comparison")
    st.caption(
        "Compare metrics extracted from the selected companies' indexed reports. "
        "Reporting periods and source units are shown for review."
    )
    if not indexed_documents:
        st.info("No reports are indexed. Upload at least one PDF to compare data.")
    else:
        selected_companies = st.multiselect(
            "Companies to include",
            options=company_options,
            default=company_options,
            key="comparison_companies",
        )
        run_comparison = st.button(
            "Compare selected companies",
            type="primary",
            disabled=not selected_companies,
        )
        if run_comparison:
            try:
                with st.status(
                    "Please wait, we’re comparing the selected companies…",
                    expanded=True,
                ) as status:
                    status.write("Please wait, we’re working on your question…")
                    progress_bar = st.progress(0, text="0/5 steps complete")
                    update_progress = _progress_updater(
                        status,
                        progress_bar,
                        (
                            "Understanding the selected companies...",
                            "Searching relevant financial documents...",
                            "Analyzing financial data...",
                            "Verifying evidence and sources...",
                            "Preparing your comparison results...",
                        ),
                    )
                    update_progress(1, "running")
                    update_progress(1, "complete")

                    def comparison_progress(phase):
                        if phase == "searching":
                            update_progress(2, "running")
                        elif phase == "analyzing":
                            update_progress(2, "complete")
                            update_progress(3, "running")
                        elif phase == "sources":
                            update_progress(3, "complete")
                            update_progress(4, "running")

                    result = agents["comparison"].compare(
                        selected_companies,
                        progress_callback=comparison_progress,
                    )
                    update_progress(4, "complete")
                    update_progress(5, "running")
                    update_progress(5, "complete")
                    status.update(
                        label="Analysis completed successfully.",
                        state="complete",
                        expanded=False,
                    )
                    progress_bar.progress(1.0, text="Analysis complete")
                st.success("Analysis completed successfully.")
                st.session_state.comparison_result = result
                st.session_state.comparison_signature = tuple(selected_companies)
            except Exception as exc:
                logger.exception("Company comparison failed")
                st.session_state.comparison_result = None
                st.error(f"Unable to compare the selected companies: {exc}")

        comparison_result = st.session_state.comparison_result
        if comparison_result and st.session_state.comparison_signature == tuple(
            selected_companies
        ):
            missing_companies = comparison_result.get("companies_not_indexed", [])
            if missing_companies:
                st.warning(
                    "No indexed report for: " + ", ".join(missing_companies)
                )
            documents = comparison_result.get("documents", [])
            if documents:
                rows = []
                for document in documents:
                    metrics = document.get("metrics", {})
                    ratios = metrics.get("financial_ratios", {})
                    rows.append(
                        {
                            "Company": document.get("company", EMPTY_VALUE),
                            "Financial year": document.get("financial_year") or EMPTY_VALUE,
                            "Document": document.get("document", EMPTY_VALUE),
                            "Revenue": _display_value(metrics.get("revenue")),
                            "Net profit": _display_value(metrics.get("net_profit")),
                            "Operating profit": _display_value(
                                metrics.get("operating_profit")
                            ),
                            "EPS": _display_value(metrics.get("eps")),
                            "Profit margin (%)": _display_value(
                                ratios.get("profit_margin")
                            ),
                            "ROE (%)": _display_value(ratios.get("roe")),
                            "ROA (%)": _display_value(ratios.get("roa")),
                            "Debt": _display_value(metrics.get("debt")),
                            "Total assets": _display_value(metrics.get("total_assets")),
                            "Total liabilities": _display_value(
                                metrics.get("total_liabilities")
                            ),
                            "Units": "Not separately identified",
                        }
                    )
                st.dataframe(rows, width="stretch", hide_index=True)
                st.caption(
                    "Values preserve their extracted representation; units are "
                    "not normalized. Compare reporting periods before interpreting."
                )
            else:
                st.info("No indexed documents match the selected companies.")
        elif not selected_companies:
            st.info("Select at least one indexed company to enable comparison.")
        elif not comparison_result:
            st.info("Choose companies and run a comparison to view results.")

elif page == "Reports":
    st.markdown("## Financial Reports")
    st.caption(
        "Generate a source-linked report from one indexed document and the "
        "available metrics, evidence, risk review, and company history."
    )
    if not indexed_documents:
        st.info("No indexed reports are available. Upload a PDF to generate a report.")
    else:
        report_company = st.selectbox(
            "Company",
            company_options,
            key="report_company",
        )
        report_documents = [
            item for item in indexed_documents
            if item.get("company") == report_company
        ]
        report_labels = [
            "{} — FY {} — {}".format(
                item.get("company", "Unknown"),
                item.get("financial_year") or "Year unavailable",
                item.get("document", "Unknown"),
            )
            for item in report_documents
        ]
        default_report_index = next(
            (
                index for index, item in enumerate(report_documents)
                if item.get("document_id")
                == st.session_state.generated_report_document_id
            ),
            0,
        )
        selected_report_label = st.selectbox(
            "Source document",
            report_labels,
            index=default_report_index,
            key="report_document",
        )
        selected_report = report_documents[
            report_labels.index(selected_report_label)
        ]
        if st.button("Generate financial report", type="primary"):
            try:
                with st.status(
                    "Please wait, we’re generating your financial report…",
                    expanded=True,
                ) as status:
                    status.write("Please wait, we’re working on your question…")
                    progress_bar = st.progress(0, text="0/5 steps complete")
                    update_progress = _progress_updater(
                        status,
                        progress_bar,
                        (
                            "Understanding the selected report...",
                            "Searching relevant financial documents...",
                            "Analyzing financial data...",
                            "Verifying evidence and sources...",
                            "Preparing your final report...",
                        ),
                    )
                    update_progress(1, "running")
                    update_progress(1, "complete")
                    latest_analysis = st.session_state.last_analysis or {}
                    if (
                        selected_report["document_id"]
                        == latest_analysis.get("document_result", {}).get("document_id")
                        and latest_analysis.get("report")
                    ):
                        for step in (2, 3, 4):
                            update_progress(step, "skipped")
                        update_progress(5, "running")
                        report = latest_analysis["report"]
                    else:
                        def report_progress(phase):
                            if phase == "searching":
                                update_progress(2, "running")
                            elif phase == "analyzing":
                                update_progress(2, "complete")
                                update_progress(3, "running")
                            elif phase == "sources":
                                update_progress(3, "complete")
                                update_progress(4, "running")

                        company_documents = agents[
                            "comparison"
                        ].get_company_documents(
                            report_company,
                            progress_callback=report_progress,
                        )
                        selected_data = next(
                            (
                                item for item in company_documents
                                if item.get("document_id")
                                == selected_report["document_id"]
                            ),
                            None,
                        )
                        if selected_data is None:
                            raise ValueError(
                                "The selected report is no longer available in the index."
                            )
                        chunks = agents["research"].collection.get(
                            include=["documents"],
                            where={"document_id": selected_report["document_id"]},
                        )
                        report_text = "\n".join(chunks.get("documents") or [])
                        if not report_text.strip():
                            raise ValueError(
                                "No indexed text is available for the selected report."
                            )
                        status.write("Reviewing risk evidence from indexed text.")
                        prior_documents = [
                            item for item in company_documents
                            if item["document_id"] != selected_report["document_id"]
                            and item.get("financial_year")
                            and selected_report.get("financial_year")
                            and str(item["financial_year"]).isdigit()
                            and str(selected_report["financial_year"]).isdigit()
                            and int(item["financial_year"])
                            < int(selected_report["financial_year"])
                        ]
                        prior_document = max(
                            prior_documents,
                            key=lambda item: int(item["financial_year"]),
                            default=None,
                        )
                        red_flag_result = agents["red_flag"].analyze(
                            report_text,
                            selected_data["metrics"],
                            prior_document["metrics"] if prior_document else None,
                        )
                        update_progress(4, "complete")
                        update_progress(5, "running")
                        report = agents["report"].generate(
                            selected_data["metrics"],
                            red_flag_result,
                            selected_report["document"],
                            comparison={"documents": company_documents},
                            sources=[
                                {
                                    "company": selected_report["company"],
                                    "financial_year": selected_report.get(
                                        "financial_year"
                                    ),
                                    "document": selected_report["document"],
                                    "document_id": selected_report["document_id"],
                                }
                            ],
                        )
                    if not isinstance(report, dict) or not report.get(
                        "executive_summary"
                    ):
                        raise ValueError(
                            "The report agent returned an incomplete report."
                        )
                    update_progress(5, "complete")
                    status.update(
                        label="Analysis completed successfully.",
                        state="complete",
                        expanded=False,
                    )
                    progress_bar.progress(1.0, text="Analysis complete")
                st.session_state.generated_report = report
                st.session_state.generated_report_document_id = selected_report[
                    "document_id"
                ]
                st.success("Analysis completed successfully.")
            except Exception as exc:
                logger.exception("Report generation failed")
                st.error(f"Unable to generate the report: {exc}")

        report = st.session_state.generated_report
        if (
            report
            and st.session_state.generated_report_document_id
            == selected_report["document_id"]
        ):
            _render_report(report)
            st.download_button(
                "Download financial report",
                data=_report_markdown(report),
                file_name="financial-report.md",
                mime="text/markdown",
                use_container_width=True,
            )
        else:
            st.info("Select a source document and generate a report to begin.")

elif page == "Indexed Documents":
    st.markdown("## Indexed Documents")
    st.caption(
        "Browse document metadata currently stored in the local ChromaDB index."
    )
    if index_error:
        st.error(f"Unable to read the document index: {index_error}")
    elif not indexed_documents:
        st.info(
            "The document index is empty. Upload a readable PDF from the sidebar "
            "to add a report."
        )
    else:
        st.metric("Indexed documents", len(indexed_documents))
        st.dataframe(
            [
                {
                    "Company": item.get("company", EMPTY_VALUE),
                    "Document": item.get("document", EMPTY_VALUE),
                    "Financial year": item.get("financial_year") or EMPTY_VALUE,
                    "Indexed chunks": item.get("chunk_count", EMPTY_VALUE),
                    "Document ID": item.get("document_id", EMPTY_VALUE),
                }
                for item in indexed_documents
            ],
            width="stretch",
            hide_index=True,
        )
