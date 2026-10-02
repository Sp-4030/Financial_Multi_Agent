Financial Multi-Agent System

A local financial research and risk-analysis system for annual-report PDFs. It stores document chunks in ChromaDB and uses local LLM agents for extraction, research, and red-flag analysis without depending on external cloud services.

Milestone 3 Status

Status: Complete

This project has successfully completed Milestone 3 for the local financial multi-agent workflow, including:

- PDF ingestion and indexing
- Company-aware research retrieval
- Evidence-based red-flag analysis
- End-to-end validation using seeded annual-report documents

Work Diagram

flowchart TD

    A["Annual Report PDF"]
    B["Document Agent"]
    C["PDF Text Extraction"]
    D["Chunking + Embeddings"]
    E[("ChromaDB Vector Store")]

    F["Research Agent"]
    G["Extraction Agent"]
    H["Financial Metrics"]
    I["Red Flag Agent"]

    J["Grounded Financial Q&A"]
    K["Evidence-Based Risk Review"]
    L["Financial Insights"]
    M["Final Report"]

    N["Local LLM via Ollama"]

    A --> B
    B --> C
    C --> D
    D --> E

    E --> F
    E --> G

    G --> H
    H --> I

    F --> J
    I --> K

    J --> L
    K --> L
    L --> M

    N --> F
    N --> I

Architecture Overview

Annual Report PDF
        ↓
Document Agent
        ↓
PDF Text Extraction
        ↓
Chunking + Embeddings
        ↓
ChromaDB Storage
        ↓
Research + Extraction + Red-Flag Agents
        ↓
LangGraph Workflow
        ↓
Financial Analysis + Risk Review
        ↓
Final Report / Insights

Completed Features

- [x] Studied financial document structures
- [x] Finalized system architecture
- [x] Designed multi-agent responsibilities
- [x] Implemented document ingestion and metadata handling
- [x] Implemented PDF extraction
- [x] Implemented text chunking and embedding generation
- [x] Integrated ChromaDB vector database
- [x] Implemented multi-document indexing
- [x] Added company-aware retrieval logic
- [x] Implemented extraction agent for financial metrics
- [x] Implemented financial ratio calculation
- [x] Fixed false-positive red-flag classification logic
- [x] Improved evidence-based research filtering
- [x] Validated workflow on seeded annual-report PDFs
- [x] Completed Milestone 3 requirements

Current Focus

- [ ] Formal milestone regression test suite
- [ ] Additional PDF edge-case validation
- [ ] UI polish and reporting improvements

Upcoming Enhancements

- [ ] Report Agent enhancements
- [ ] Company comparison module
- [ ] Automated report generation
- [ ] Final Streamlit experience refinements
- [ ] End-to-end optimization and validation

---

Installation & Setup

Prerequisites

Make sure the following are installed:

- Python 3.10+
- Git
- Ollama

The project uses Ollama to run the local LLM without depending on external cloud APIs.

---

1. Clone the Repository

git clone https://github.com/Sp-4030/Financial_Multi_Agent.git
cd Financial_Multi_Agent

---

2. Create a Virtual Environment

python -m venv .venv

Windows

.venv\Scripts\activate

Linux / macOS

source .venv/bin/activate

---

3. Install Python Dependencies

Upgrade pip:

python -m pip install --upgrade pip

Install project dependencies:

pip install -r requirements.txt

Main dependencies include:

- PyPDF
- LangChain
- LangChain Text Splitters
- Sentence Transformers
- PyTorch
- Torchvision
- ChromaDB
- Python Dotenv
- FastAPI
- Uvicorn
- Python Multipart
- Streamlit
- LangGraph
- LangChain Community
- Ollama

---

4. Install Ollama

Ollama is used to run the local LLM required by the Research Agent and Red Flag Agent.

Download and install Ollama from:

https://ollama.com/download

After installation, open a new terminal and verify:

ollama --version

If an Ollama version is displayed, the installation was successful.

---

5. Download the Required Local LLM

This project uses the following local model:

llama3.2:latest

Download the model:

ollama pull llama3.2:latest

The model will be downloaded and stored locally.

Verify the Model

ollama list

Expected model:

llama3.2:latest

Test the Model

Run:

ollama run llama3.2:latest

Then enter a simple question:

What is financial analysis?

If Ollama responds, the local LLM is working correctly.

Exit the interactive session with:

Ctrl + C

---

6. Run the Backend

From the project root:

python -m uvicorn backend.main:app --reload

Backend URL:

http://127.0.0.1:8000

FastAPI documentation:

http://127.0.0.1:8000/docs

---

7. Run the Frontend

Open a second terminal.

Navigate to the project:

cd Financial_Multi_Agent

Activate the virtual environment:

Windows

.venv\Scripts\activate

Run Streamlit:

python -m streamlit run frontend/app.py

Frontend URL:

http://localhost:8501

---

Verify the Setup

Backend Health Check

Open:

http://127.0.0.1:8000/health

Expected response:

{
  "status": "ok"
}

---

Check Ollama

Run:

ollama list

The required model should be available:

llama3.2:latest

---

Check Streamlit

Open:

http://localhost:8501

The Financial Multi-Agent System interface should appear.

---

Project Workflow

Once the application is running, the typical workflow is:

Upload Annual Report PDF
        ↓
Document Agent
        ↓
Extract Text from PDF
        ↓
Split Text into Chunks
        ↓
Generate Embeddings
        ↓
Store in ChromaDB
        ↓
Retrieve Relevant Documents
        ↓
Research Agent
        ↓
Extraction Agent
        ↓
Financial Metrics
        ↓
Red Flag Agent
        ↓
Evidence-Based Risk Review
        ↓
Financial Insights
        ↓
Final Report

---

Multi-Agent Workflow

The system uses multiple specialized agents.

Document Agent

Responsible for:

- PDF processing
- Text extraction
- Text chunking
- Embedding generation
- ChromaDB indexing
- Document metadata

---

Extraction Agent

Responsible for extracting financial information such as:

- Revenue
- Net profit
- Operating profit
- Total assets
- Total liabilities
- Debt
- EPS
- Profit margin
- ROA
- ROE
- Financial KPIs

---

Research Agent

Responsible for:

- Financial document retrieval
- Semantic search
- Multi-part financial questions
- Evidence-based answers
- Source citation
- Grounded financial research

The Research Agent uses indexed financial documents to provide document-grounded responses.

---

Red Flag Agent

Responsible for identifying potential financial concerns such as:

- Unusual financial patterns
- Low profit margins
- Debt-related concerns
- Auditor-related issues
- Going-concern disclosures
- Impairment-related information
- Restructuring-related information
- Potential financial anomalies

The system also attempts to distinguish generic disclosures from actual financial red flags to reduce false positives.

---

LangGraph Workflow

The agents can be orchestrated using LangGraph:

Document Agent
       ↓
Extraction Agent
       ↓
Red Flag Agent
       ↓
Financial Analysis

The workflow provides a structured sequence for document processing and financial analysis.

---

Technology Stack

Technology| Purpose
Python| Core programming language
FastAPI| Backend API
Streamlit| Frontend UI
LangChain| Document and LLM integration
LangGraph| Multi-agent workflow orchestration
ChromaDB| Vector database
Sentence Transformers| Text embeddings
PyTorch| ML/embedding runtime
Torchvision| PyTorch dependency
PyPDF| PDF text extraction
Ollama| Local LLM runtime
Llama 3.2| Local language model
SQLite| Research/session data storage

---

Local AI Architecture

The system is designed to run locally.

Financial PDF
      ↓
Document Processing
      ↓
Embeddings
      ↓
ChromaDB
      ↓
Relevant Document Retrieval
      ↓
Local LLM
      ↓
Research / Risk Analysis
      ↓
Financial Insights

The local LLM is provided through Ollama:

Ollama
   ↓
llama3.2:latest
   ↓
Research Agent
   ↓
Red Flag Agent

---

Project Structure

Financial_Multi_Agent/
│
├── agents/
│   ├── document_agent.py
│   ├── extraction_agent.py
│   ├── red_flag_agent.py
│   ├── comparison_agent.py
│   ├── research_agent.py
│   └── report_agent.py
│
├── backend/
│   └── main.py
│
├── frontend/
│   └── app.py
│
├── workflow/
│   └── graph.py
│
├── utils/
│   ├── pdf_parser.py
│   ├── chunking.py
│   └── embeddings.py
│
├── data/
│   ├── seed_documents/
│   └── uploads/
│
├── vector_db/
│
├── database.py
├── research.db
├── chroma_ingest.py
├── test_extraction_agent.py
├── test_red_flag_agent.py
├── test_workflow.py
├── requirements.txt
├── .gitignore
└── README.md

---

Testing

The project includes tests for the major components.

Test Extraction Agent

python test_extraction_agent.py

Test Red Flag Agent

python test_red_flag_agent.py

Test LangGraph Workflow

python test_workflow.py

---

Seed Documents

Financial annual reports used for testing can be stored in:

data/seed_documents/

Run the ingestion script:

python chroma_ingest.py

The documents are processed and stored in:

vector_db/

---

ChromaDB

The project uses ChromaDB as a local vector database.

Collection:

financial_documents

The database stores:

- Document chunks
- Embeddings
- Company name
- Document name
- Chunk number
- Document ID

This allows the Research Agent to retrieve relevant sections from financial documents.

---

Research Sessions

The project uses SQLite for research session information.

Database:

research.db

The database stores information such as:

- Research sessions
- Uploaded documents
- Document metadata
- Processing status

---

Important Notes

- The system is designed to work locally with Ollama and ChromaDB.
- Ollama must be installed before using the local LLM agents.
- The "llama3.2:latest" model must be downloaded using "ollama pull".
- The local Ollama workflow does not require external LLM API keys.
- The system is designed for document-grounded financial research and risk analysis.
- Answers are intended to remain tied to the indexed source PDFs.
- Financial results should be reviewed against the original financial reports before making financial decisions.

---

Database Reset

Older or incompatible local database files may cause errors after changing or upgrading database dependencies.

If this happens:

1. Stop the backend and frontend.
2. Back up the existing database files if required.
3. Remove:

vector_db/
research.db

4. Restart the application.
5. Recreate or re-index the documents.
6. Re-upload documents if required.

Windows

rmdir /s /q vector_db
del research.db

Linux / macOS

rm -rf vector_db
rm research.db

Warning: Removing these files permanently deletes indexed document data and saved research records. Back up the files first if you need to preserve them.

---

Troubleshooting

Ollama Command Not Found

If:

ollama --version

does not work:

1. Install Ollama.
2. Close the terminal.
3. Open a new terminal.
4. Run:

ollama --version

---

Model Not Found

If the application reports that "llama3.2:latest" is unavailable:

ollama pull llama3.2:latest

Then verify:

ollama list

---

Torchvision Missing

If you see:

ModuleNotFoundError: No module named 'torchvision'

activate the virtual environment:

.venv\Scripts\activate

Then install:

python -m pip install torch torchvision

Verify:

python -c "import torch; import torchvision; print('Torch:', torch.__version__); print('Torchvision:', torchvision.__version__)"

---

Backend Not Connecting

Start the backend:

python -m uvicorn backend.main:app --reload

Then check:

http://127.0.0.1:8000/health

---

Streamlit Command Not Found

Instead of:

streamlit run frontend/app.py

use:

python -m streamlit run frontend/app.py

This ensures Streamlit runs from the active Python environment.

---

Development Status

Milestone 3: Complete

The project has completed the core Milestone 3 requirements:

- Document processing
- Financial extraction
- Research retrieval
- Red-flag analysis
- Multi-agent orchestration
- Seed-document validation

Current development focuses on:

- Streamlit UI integration
- Company comparison
- Report generation
- UI refinement
- Regression testing
- End-to-end validation

---

Internship Project

Infosys Springboard Virtual Internship

Project

Financial Multi-Agent System

Focus

Financial Research, Document Analysis, Risk Detection and Business Insights

---

License

This project is developed for educational and internship purposes.
