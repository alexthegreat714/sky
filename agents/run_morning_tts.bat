@echo off
setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXECUTION

set TORCH_COMPILE_DISABLE=1
echo [Sky TTS] Generating morning digest speech...

rem Change to repo root (this script is in Sky\agents)
pushd %~dp0..

python "%~dp0tts_morning_cli.py" --voice vctk/p225_023.wav --device cpu
set ERR=%ERRORLEVEL%

popd

if not %ERR%==0 (
  echo [Sky TTS] Failed with exit code %ERR%.
  pause
  exit /b %ERR%
)

echo [Sky TTS] Completed. Output is under delayed-streams-modeling\unmute\output\morning-<DATE>.wav
pause

