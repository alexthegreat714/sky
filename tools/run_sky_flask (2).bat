@echo off
setlocal

REM --- Config ---
set "FLASK_APP=C:\Users\blyth\Desktop\Engineering\Sky\app.py"
set "FLASK_RUN_HOST=127.0.0.1"
set "FLASK_RUN_PORT=5011"
set "PYTHON_EXE=python"
REM -------------

echo [Sky] Launching Flask app
echo   APP : %FLASK_APP%
echo   HOST: %FLASK_RUN_HOST%
echo   PORT: %FLASK_RUN_PORT%
echo.

REM Prefer python -m flask to avoid PATH surprises
"%PYTHON_EXE%" -m flask --app "%FLASK_APP%" run --host %FLASK_RUN_HOST% --port %FLASK_RUN_PORT%
endlocal
