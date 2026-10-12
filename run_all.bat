@echo off
echo Dang khoi dong AI-Video (Web Server va Render Worker)...
start "AI-Video: Web Server" "%~dp0start_server.bat"
start "AI-Video: Render Worker" "%~dp0start_worker.bat"
echo.
echo Da khoi dong ca 2 tien trinh trong cua so rieng!
echo Mo trinh duyet tai: http://localhost:8000
timeout /t 3 >nul
start http://localhost:8000

