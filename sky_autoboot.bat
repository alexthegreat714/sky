@echo off
cd /d "C:\Users\blyth\Desktop\Engineering\Sky"
echo [Sky Autoboot] Starting Flask dialog server...
start "" python sky_dialog.py
timeout /t 2 >nul
start "" "http://127.0.0.1:6060"
echo [Sky Autoboot] Log: ..\logs\flask_agent_status.log
