@echo off
echo ========================================================
echo   KHOI DONG AI-VIDEO: BACKGROUND RENDER WORKER
echo ========================================================
cd /d "%~dp0"
set PYTHONPATH=apps\api;packages
echo Dang khoi dong Render Worker de xu ly video ngam ...
.\.venv\Scripts\python.exe -m app.workers.render_worker
pause

