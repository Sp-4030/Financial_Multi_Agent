# Financial Multi-Agent System

A local financial-report research application for PDF annual reports. It uses
SentenceTransformers to create embeddings, ChromaDB for persistent semantic
retrieval, SQLite for API upload/session metadata, LangGraph to orchestrate
document analysis, Streamlit for the user interface, FastAPI for REST access,
and Google Gemini for source-grounded research and contextual risk analysis.

The agents do not establish audited facts: extracted values are pattern-based,
and annual-report layouts vary. Review every extracted metric and potential
finding against the cited source document. Unsupported values remain `N/A` or
`null`; a research answer is not generated without retrieved evidence.

## Architecture and workflow

```text
PDF upload
  -> PDF text extraction
  -> recursive text chunking
  -> SentenceTransformer embeddings
  -> persistent ChromaDB chunks and metadata
  -> financial metric extraction
  -> evidence-backed red-flag review and available prior-document comparisons
  -> source-linked report sections

Indexed chunks -> company/document-filtered research -> Gemini answer + citations
Indexed companies/documents -> financial metric comparison table
```

The Streamlit frontend invokes the LangGraph workflow and agents directly. The
FastAPI backend uses the same workflow, ChromaDB collection and shared
workspace-rooted SQLite database.

## Agent responsibilities

| Component | Responsibility |
| --- | --- |
| Document Agent | Extract PDF text, split it into chunks, generate embeddings, and upsert chunks and company/document/year metadata. |
| Extraction Agent | Extract reported revenue, net and operating profit, assets, liabilities, debt, EPS and financial year; calculate profit margin, ROE and ROA only when required inputs exist. |
| Red Flag Agent | Review available statement comparisons, financial ratios, auditor opinions, going-concern statements and other risk language with nearby source evidence. |
| Research Agent | Classify concepts, report research, extraction, comparisons, trends, calculations, risk review, summaries and report requests; retrieve separately for named companies; retain short follow-up context; and return citations or retrieved excerpts when Gemini is unavailable. |
| Comparison Agent | Group indexed chunks by document and compare extracted metrics across companies and financial years. |
| Report Agent | Assemble executive summary, extracted metrics, risk findings, optional research answers, comparison data and source documents without inventing missing values. |
| LangGraph workflow | Run document ingestion, extraction, risk review and report generation in order. |

## Requirements

- Windows, macOS or Linux
- Python 3.10 or newer
- A Google Gemini API key for LLM-backed research and contextual risk analysis
- Internet access on first embedding-model use to download the configured model

The app can ingest PDFs, extract metrics, compare indexed financial figures and
generate deterministic report sections without a Gemini key. Gemini-dependent
features report a configuration error when the key is missing.

## Installation and configuration

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set the actual key in `.env` (never commit that file):

```dotenv
GEMINI_API_KEY=your_google_ai_studio_key
GEMINI_MODEL=gemini-2.5-flash
```

`GOOGLE_API_KEY` is also accepted by the client. `GEMINI_MODEL` is optional;
the application default is `gemini-2.5-flash`, and the model must be enabled
for your Google AI account. The service uses Google's
`google-genai` client; Ollama is not the configured LLM provider.

Optional local data path overrides can be set in `.env`:

```dotenv
FINANCIAL_DB_PATH=research.db
CHROMA_DB_PATH=vector_db
FINANCIAL_UPLOAD_DIR=data/uploads
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

Relative paths resolve from the project root. The defaults preserve the
existing `research.db`, `vector_db/` and `data/uploads/` locations. These may
contain private financial documents or metadata and are ignored by Git. Back
them up before manually changing or moving them; the application does not
delete them.

## Run the application

Run the FastAPI service and Streamlit UI in separate terminals from the
project root after activating `.venv`:

```powershell
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
python -m streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501
```

Open <http://127.0.0.1:8501> for the Streamlit application,
<http://127.0.0.1:8000/docs> for interactive API documentation, or
<http://127.0.0.1:8000/health> to check backend status.

On Windows, `run_app.cmd` opens separate backend and frontend console windows.
The first PDF processing run may take longer while the embedding model loads.

The Streamlit interface is organized into Dashboard, Research Chat, Company
Comparison, Reports, and Indexed Documents pages, with upload controls and
service status in the sidebar. Dashboard counts and document lists come from
the local ChromaDB index; recent research activity is shown only for the
current Streamlit session. Each long-running action displays a native
processing status while its agent call is active. Research Chat reports live
workflow steps from the research agent; steps that do not apply are marked as
skipped. Comparison, report generation and PDF processing also show progress
at their actual processing stages. Successful requests display their results
and citations, while failures display an error. Chat's supporting-document
summary lists each company/document once rather than repeating every retrieved
chunk; individual research findings retain their source citations. The UI uses
a consistent light theme and can run standalone: the FastAPI health status is
shown separately and is not required for direct agent access from Streamlit.

Upload a PDF in the sidebar. The UI saves it under the configured upload
directory, displays workflow progress, then shows extracted metrics and risk
findings. Research chat routes educational financial definitions without
requiring a report; company-specific questions use indexed evidence.
It supports multi-intent requests and follow-ups, company/document filters,
comparisons, trend views, calculations, evidence-based risk review, summaries
and report requests. When a cited Gemini response cannot be produced, the
system shows retrieved excerpts and source metadata instead of inventing an
answer. Comparison values retain their extracted representation; units that
cannot be identified are marked as unavailable/not normalized, and reporting
period differences are called out. The standalone comparison and report tabs
remain available independently of chat. The report tab extracts metrics from
the selected indexed document, runs risk review against its indexed text, and
includes explicit missing-information and limitation notes.

## FastAPI endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/health` | Backend status, configured provider/model and key-presence status (never returns the key). |
| `POST` | `/sessions` | Create a document-upload session. Body: `{"name":"Research"}`. |
| `GET` | `/sessions` | List upload sessions. |
| `POST` | `/upload?session_id=1` | Upload, validate and analyze a PDF; maximum file size is 50 MiB. |
| `GET` | `/documents` | List uploaded document records; optional `session_id` and `company` filters. |
| `GET` | `/companies` | List company names from indexed ChromaDB documents. |
| `POST` | `/research` | Route a natural-language request. Body accepts `query`, optional `top_k` (1-20), `company`, `document_id` and up to 20 `conversation_history` messages. Concepts work without Gemini; document questions use indexed evidence and cite sources or return source excerpts if Gemini is unavailable. |
| `POST` | `/compare` | Compare indexed documents. Body: `{"companies":["Company A","Company B"]}`; omit the list to include all companies. |
| `POST` | `/report` | Assemble report sections from supplied metrics, risk findings, comparisons, research findings and sources. |
| `GET`, `POST` | `/config` | Read non-secret model configuration or update the in-process Gemini key/model. Prefer `.env` for local configuration. |

FastAPI validates malformed requests with standard `422` responses. Upload
errors return appropriate client errors for missing sessions, non-PDF files,
empty files, oversized files or unreadable PDFs. LLM and internal service
failures are reported explicitly; detailed unexpected exceptions are logged
server-side rather than returned to clients.

## Tests

Run the deterministic unit and service-contract tests:

```powershell
python -m pytest -q test_financial_agents.py test_service_contracts.py
```

Question routing and conversation behavior are covered separately:

```powershell
python -m pytest -q test_question_handling.py
```

The focused unit tests use an in-memory vector collection and mock LLM calls;
the service-contract tests use a temporary SQLite database and mocked Gemini
response. They do not contact Gemini or alter the existing database/vector
index. The script-style `Test_extraction_agent.py`,
`Test_red_flag_agent.py`, `Test_workflow.py` and `Test_research_agent.py`
depend on real PDF processing, persistent ChromaDB and/or Gemini. Run those
only when you intend to use the real integrations and their local data.

## Limitations and troubleshooting

- Extraction uses document-label/number patterns, not a financial-statement
  OCR/table understanding model. Image-only/scanned PDFs without extractable
  text are rejected; missing or ambiguous numbers remain `null`.
- A financial year is inferred from explicit `FY`/financial-year text when
  available. If it cannot be found, comparison displays `N/A`.
- Multi-period red flags compare against the most recently indexed document
  for the same inferred company, not necessarily the immediately preceding
  financial year. Review the cited values and document names.
- ROE is calculated only when shareholder equity is extracted. Debt and other
  values preserve their source representation and units; comparisons across
  different currencies/reporting units therefore need human review.
- Google Gemini API availability, model access, quotas and network access are
  required for research answers and contextual LLM analysis. Add
  `GEMINI_API_KEY` to `.env` and verify `GEMINI_MODEL` is enabled for your key.
- ChromaDB and the SQLite database are local persistent stores. If a store
  reports a compatibility or corruption error, stop the app and back up the
  named data directory/file before considering recovery; do not delete them
  without confirming that the stored data is disposable.
- Check that the virtual environment is active, `pip install -r
  requirements.txt` completed, and ports 8000/8501 are available if either
  service fails to start.
