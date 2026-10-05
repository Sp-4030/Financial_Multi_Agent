# Financial Multi-Agent System

A financial research and risk-analysis multi-agent system for annual-report PDFs. It stores document chunks in ChromaDB and uses Google Gemini API agents for extraction, research, red-flag analysis, cross-company benchmarking, and report generation using LangGraph, FastAPI, and Streamlit.

## Milestone Status

Status: Complete (Powered by Google Gemini API)

This project has successfully implemented all 7 Milestone 3 requirements:

- **Red Flag Agent**: Automated detection of rising debt, falling profit margins, revenue decline, net profit decline, auditor qualifications, and unusual financial patterns with Google Gemini reasoning.
- **Multi-Agent Orchestration Layer**: LangGraph workflow chaining Document Agent ➜ Extraction Agent ➜ Red Flag Agent with shared state and graceful error handling.
- **Testing & Validation**: End-to-end verification covering agents, LangGraph workflow, FastAPI endpoints, and source faithfulness guarantees.
- **Research Agent**: Multi-part question decomposition, ChromaDB vector retrieval using SentenceTransformers, fact extraction, and Google Gemini synthesized answers with verifiable citations.
- **Comparison Agent**: Cross-company metric benchmarking across 10 financial metrics, side-by-side Markdown tables, and safe missing-value handling (`N/A`).
- **Conversational Research Interface**: Interactive Streamlit UI with `st.chat_input` and `st.chat_message`, presenting reasoned answers, evidence bullet points, and source citations.
- **Initial Report Agent**: Grounded report synthesis featuring Executive Summary, Key Financials, Red Flags, Peer Comparison, Research Findings, and Sources.

## Work Diagram

```mermaid
flowchart LR
    A[Annual Report PDF] --> B[Document Agent]
    B --> C[PDF Text Extraction]
    C --> D[Chunking + Embeddings]
    D --> E[ChromaDB Vector Store]

    B --> G[Extraction Agent]
    G --> H[Financial Metrics & Ratios]
    H --> I[Red Flag Agent]

    E --> F[Research Agent]
    E --> M[Comparison Agent]
    H --> N[Report Agent]
    I --> N
    M --> N

    F --> J[Grounded Financial Q&A]
    I --> K[Evidence-Based Risk Review]
    M --> L[Cross-Company Benchmarking]
    N --> R[Final Financial Report]

    J --> S[Streamlit Conversational UI]
    K --> S
    L --> S
    R --> S

    P[Google Gemini API] --> F
    P --> I
    P --> N
```

## Low-Level Design

The application has two entry points: the Streamlit UI invokes the workflow and agents directly, while the FastAPI service exposes REST endpoints for uploads, research, comparison, and reports. Both entry points share the financial workflow, agents, and persistent ChromaDB collection.

<!-- mermaid-checked: no \n, no em-dash/en-dash, no {} in labels, subgraphs are id["label"], arrows are -->|"label"|, all subgraphs closed by end, ids unique -->
```mermaid
flowchart LR
    subgraph ClientLayer["Client Layer"]
        cStreamlit["Streamlit UI"]
        cFastAPI["FastAPI REST API"]
    end
    subgraph OrchestrationLayer["Orchestration Layer"]
        cWorkflow["LangGraph Workflow"]
        cDocumentNode["Document Node"]
        cExtractionNode["Extraction Node"]
        cRedFlagNode["Red Flag Node"]
    end
    subgraph AgentLayer["Agent Layer"]
        cDocumentAgent["Document Agent"]
        cExtractionAgent["Extraction Agent"]
        cRedFlagAgent["Red Flag Agent"]
        cResearchAgent["Research Agent"]
        cComparisonAgent["Comparison Agent"]
        cReportAgent["Report Agent"]
    end
    subgraph DataLayer["Data Layer"]
        cPDFParser["PDF Parser"]
        cChunkEmbed["Chunking and Embeddings"]
        cChroma[("ChromaDB")]
        cSQLite[("SQLite Metadata DB")]
    end
    subgraph ExternalLayer["External Services"]
        cGemini["Google Gemini API"]
    end

    cStreamlit -->|"runs analysis"| cWorkflow
    cStreamlit -->|"uses"| cResearchAgent
    cStreamlit -->|"uses"| cComparisonAgent
    cStreamlit -->|"uses"| cReportAgent
    cFastAPI -->|"uploads and analyzes"| cWorkflow
    cFastAPI -->|"serves research"| cResearchAgent
    cFastAPI -->|"serves comparisons"| cComparisonAgent
    cFastAPI -->|"serves reports"| cReportAgent
    cFastAPI -->|"stores sessions and document records"| cSQLite

    cWorkflow --> cDocumentNode
    cDocumentNode --> cExtractionNode
    cExtractionNode --> cRedFlagNode
    cDocumentNode --> cDocumentAgent
    cDocumentNode -->|"loads prior company reports"| cComparisonAgent
    cExtractionNode --> cExtractionAgent
    cRedFlagNode --> cRedFlagAgent
    cDocumentAgent --> cPDFParser
    cPDFParser --> cChunkEmbed
    cChunkEmbed -->|"upserts chunks and vectors"| cChroma
    cResearchAgent -->|"retrieves evidence"| cChroma
    cResearchAgent -->|"generates grounded answers"| cGemini
    cComparisonAgent -->|"reads indexed reports"| cChroma
    cComparisonAgent -->|"extracts comparison metrics"| cExtractionAgent
    cRedFlagAgent -->|"analyzes evidence"| cGemini
```

### Component Inventory

| Component | Layer | Type | Responsibility |
|---|---|---|---|
| Streamlit UI | Client | Web interface | Accepts PDFs and presents extracted metrics, risk findings, research answers, comparisons, and reports. |
| FastAPI REST API | Client/API | REST service | Validates requests and provides health, configuration, session, document, upload, research, comparison, and report endpoints. |
| LangGraph Workflow | Orchestration | State graph | Runs document processing, metric extraction, and red-flag analysis in sequence using shared workflow state. |
| Document Agent | Agent | Ingestion | Extracts PDF text, chunks and embeds it, and upserts chunks with company and document metadata into ChromaDB. |
| Extraction Agent | Agent | Metric extraction | Extracts financial metrics and ratios from report text; also supplies metrics for company comparisons. |
| Red Flag Agent | Agent | Risk analysis | Evaluates report evidence, extracted metrics, and prior-period metrics; uses Gemini for contextual reasoning. |
| Research Agent | Agent | Retrieval-augmented research | Retrieves relevant ChromaDB chunks and generates answers with source evidence using Gemini. |
| Comparison Agent | Agent | Benchmarking | Groups indexed report chunks by company and compares extracted financial metrics. |
| Report Agent | Agent | Report synthesis | Builds source-grounded report sections from provided metrics and red-flag findings. |
| PDF Parser | Data processing | Utility | Extracts text from uploaded annual-report PDFs. |
| Chunking and Embeddings | Data processing | Utilities | Splits extracted text and creates vectors for semantic retrieval. |
| ChromaDB | Persistence | Vector store | Persists report chunks, embeddings, and metadata used by ingestion, research, and comparison. |
| SQLite Metadata DB | Persistence | Relational database | Stores research sessions and uploaded-document metadata for the FastAPI service. |
| Google Gemini API | External service | LLM API | Provides language-model reasoning for research answers and red-flag analysis. |

### Data Storage and External Services

ChromaDB persists indexed document chunks and embeddings in `vector_db/`; SentenceTransformers (`all-MiniLM-L6-v2`) creates embeddings. SQLite persists research sessions and document records in `research.db`. Research and risk analysis call Google Gemini using the configured API key and model.

### Key Design Decisions

- LangGraph makes PDF analysis a sequential, stateful workflow: document ingestion, metric extraction, then red-flag analysis.
- The Streamlit UI and FastAPI API are separate application entry points that reuse shared workflow and agent code.
- Research is grounded in retrieved report chunks; ChromaDB metadata supports company-level filtering, comparison, and citations.


## ✅ Completed Features

- [x] Studied financial document structures & finalized multi-agent architecture
- [x] Implemented Document Agent with PDF parsing, text chunking, and ChromaDB vector indexing
- [x] Implemented Extraction Agent for 10 core financial metrics & ratios (Revenue, Net Profit, Operating Profit, Total Assets, Total Liabilities, Debt, EPS, Profit Margin, ROE, ROA)
- [x] Added comparative prior-period extraction and YoY revenue trend calculations
- [x] Implemented Red Flag Agent for rising debt, falling margins, revenue decline, profit decline, auditor qualifications, and unusual patterns
- [x] Integrated Google Gemini API for deep financial reasoning and risk analysis
- [x] Implemented Multi-Agent Orchestration using LangGraph StateGraph (`DocumentAgent` ➜ `ExtractionAgent` ➜ `RedFlagAgent`)
- [x] Implemented Research Agent with multi-part query decomposition, semantic search, and grounded chunk citations
- [x] Implemented Comparison Agent for cross-company financial benchmarking with Markdown tables
- [x] Implemented initial Report Agent with Executive Summary, Key Financials, Red Flags, Comparison, and Sources
- [x] Implemented Conversational Research UI in Streamlit with `st.chat_input` and `st.chat_message`
- [x] Built FastAPI REST endpoints (`/upload`, `/research`, `/compare`, `/report`, `/companies`, `/documents`, `/health`)
- [x] Enforced Source Faithfulness: strictly returns `N/A` or `"No supporting information was found in the indexed documents."` without hallucinating numbers
- [x] Validated full end-to-end workflow on seed annual-report PDFs
- [x] Completed all Milestone 3 requirements

## 🔄 Current Focus

- [ ] Additional PDF edge-case validation across diverse accounting layouts
- [ ] UI polish and styling refinements

## 📋 Upcoming Enhancements

- [ ] Advanced graphical chart generation for multi-year trends
- [ ] Direct PDF export for synthesized financial research reports
- [ ] End-to-end performance optimization

---

## ⚙️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Sp-4030/Financial_Multi_Agent.git
cd Financial_Multi_Agent
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it:

Windows:

```bash
.venv\Scripts\activate
```

Linux / macOS:

```bash
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Google Gemini API Key

Create a `.env` file in the project root directory and set your Gemini API key:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.8-flash
```

Get your free Gemini API key from [Google AI Studio](https://aistudio.google.com/).

### 5. Run the Backend (FastAPI)

From the project root:

```bash
python -m uvicorn backend.main:app --reload
```

Access:

```text
http://127.0.0.1:8000
```

FastAPI Interactive Docs (Swagger UI):

```text
http://127.0.0.1:8000/docs
```

### 6. Run the Frontend (Streamlit)

Open a second terminal, activate the virtual environment, and run:

```bash
python -m streamlit run frontend/app.py
```

Access:

```text
http://localhost:8501
```

Or on Windows, launch both backend and frontend together using:

```cmd
run_app.cmd
```

### 7. Verify the Setup

Check the backend health:

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "milestone": "3"
}
```

Open the frontend:

```text
http://localhost:8501
```

---

## Project Workflow

Once the app is running, the typical flow is:

```text
Upload Annual Report PDF
        ↓
Document Agent (Text Extraction + Chunking + Embeddings)
        ↓
Store in ChromaDB Vector Database
        ↓
Extraction Agent (Extract 10 Core Metrics & Ratios)
        ↓
Red Flag Agent (Analyze Risks, Auditor Language & Patterns)
        ↓
Research / Comparison Agent (Multi-Part Q&A or Peer Benchmarking)
        ↓
Report Agent (Synthesize Executive Summary + Key Financials)
        ↓
Streamlit Conversational UI (Answer + Evidence + Sources)
```

## Notes

- The system runs using ChromaDB vector database, SentenceTransformers (`all-MiniLM-L6-v2`) embeddings, and Google Gemini API (`gemini-3.8-flash`) for deep financial reasoning and risk analysis.
- The workflow enforces source faithfulness: answers and evidence are strictly tied to indexed PDF chunks, and unsupported figures are never fabricated.
- Older or incompatible local database files may cause errors after changing database dependencies. If this happens, stop the application and remove the `vector_db/` folder and `research.db` file, then restart the application to create fresh databases. Back up these files first if you need to keep existing data.
