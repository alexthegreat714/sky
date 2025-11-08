@echo off
REM Sky Agent Launcher
REM Starts Sky agent and API server

echo ========================================
echo    SKY AGENT - Phase 0 to Phase 1
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please install Python 3.9+ and try again
    pause
    exit /b 1
)

echo [1/3] Checking configuration...
if not exist "config\sky.yaml" (
    echo WARNING: config\sky.yaml not found
    echo Using default configuration
)

echo [2/3] Starting Sky Agent...
echo.

REM Run Sky agent
cd /d "%~dp0"
python agent\sky_agent.py

REM If agent exits, pause to see error messages
if errorlevel 1 (
    echo.
    echo ERROR: Sky Agent exited with error code %errorlevel%
    pause
    exit /b %errorlevel%
)

echo.
echo Sky Agent terminated successfully
pause
