@echo off
REM One-click setup for Microstock Helper: venv + dependencies + editable install + doctor.
setlocal

cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo [FAIL] python not found in PATH. Install Python 3.10+ first.
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [*] Creating venv...
  python -m venv .venv || exit /b 1
) else (
  echo [*] venv already exists, reusing.
)

call ".venv\Scripts\activate.bat"

echo [*] Upgrading pip...
python -m pip install --upgrade pip || exit /b 1

echo [*] Installing requirements...
python -m pip install -r requirements.txt || exit /b 1

echo [*] Installing package (editable)...
python -m pip install -e . || exit /b 1

echo.
echo [*] Running doctor diagnostic...
python -m microstock doctor

echo.
echo [DONE] Setup complete!
echo [DONE] Run anytime: run.bat <command>
echo [DONE] Example: run.bat doctor
