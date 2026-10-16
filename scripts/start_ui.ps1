Write-Host "Starting ORBIT Mission Control Streamlit Dashboard on http://localhost:8501..." -ForegroundColor Magenta
.\.venv\Scripts\python.exe -m streamlit run ui/app.py --server.port 8501 --server.headless true
