@echo off
rem Runs Python with the packages live-carousel needs (numpy, opencv): the skill's private venv
rem made by setup.ps1 with the signed Python 3.12. Usage: py.cmd <script.py> [args...]
setlocal
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "LC_SKILL=%~dp0.."
if defined LIVE_CAROUSEL_PYTHON (
  "%LIVE_CAROUSEL_PYTHON%" %*
  exit /b %ERRORLEVEL%
)
if exist "%LC_SKILL%\.venv\Scripts\python.exe" (
  "%LC_SKILL%\.venv\Scripts\python.exe" %*
  exit /b %ERRORLEVEL%
)
echo live-carousel: no venv yet. Run: powershell -ExecutionPolicy Bypass -File .claude\skills\live-carousel\scripts\setup.ps1 1>&2
exit /b 1
