@echo off
cd /d "%~dp0"

REM First run: creates the virtual environment (.venv) and installs the dependencies.
if not exist ".venv\Scripts\python.exe" (
    echo [radial] First run: creating the virtual environment in .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [radial] Could not create .venv. Is Python installed and on PATH?
        pause
        exit /b 1
    )
)

REM Installs the dependencies if they are still missing.
".venv\Scripts\python.exe" -c "import PySide6, pynput" 2>nul
if errorlevel 1 (
    echo [radial] Installing dependencies: PySide6 and pynput ...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [radial] Installation failed. See the message above.
        pause
        exit /b 1
    )
)

echo [radial] Starting the radial menu. Close this window to quit.
".venv\Scripts\python.exe" -m radial %*
pause
