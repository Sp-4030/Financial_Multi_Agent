# Set the current working directory to the folder where this script is located
Set-Location $PSScriptRoot

# Launch the Financial Multi-Agent Backend in a new window
Start-Process powershell.exe -ArgumentList "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", "& .venv\Scripts\Activate.ps1; python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000"

# Launch the Financial Multi-Agent Frontend in a new window
Start-Process powershell.exe -ArgumentList "-ExecutionPolicy", "Bypass", "-NoExit", "-Command", "& .venv\Scripts\Activate.ps1; python -m streamlit run frontend\app.py --server.address 127.0.0.1 --server.port 8501"
