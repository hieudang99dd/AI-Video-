@echo off
echo ========================================================
echo   KHOI DONG AI-VIDEO: WEB INTERFACE & API SERVER
echo ========================================================
cd /d "%~dp0"
set PYTHONPATH=apps\api;packages
echo Dang khoi dong Web UI tai http://localhost:8000 ...
.\.venv\Scripts\uvicorn.exe app.main:app --app-dir apps\api --host 0.0.0.0 --port 8000 --reload
pause
