@echo off
setlocal

cd /d "%~dp0"

start "Financial Multi-Agent Backend" cmd /k "call .venv\Scripts\activate.bat && python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000"

start "Financial Multi-Agent Frontend" cmd /k "call .venv\Scripts\activate.bat && python -m streamlit run frontend\app.py --server.address 127.0.0.1 --server.port 8501"

endlocal