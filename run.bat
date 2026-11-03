@echo off
REM Run the Microstock Helper CLI inside the project venv.
setlocal

cd /d "%~dp0"

set "VENV_PY=.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
  set "VENV_PY=microstock-metadata-generator\.venv\Scripts\python.exe"
)

if not exist "%VENV_PY%" (
  echo [FAIL] venv not found. Run setup.bat first.
  exit /b 1
)

"%VENV_PY%" -m microstock %*
