@echo off
setlocal
echo Starting Document Generator...
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Run: python -m venv .venv
    pause
    exit /b 1
)
start http://localhost:8000
".venv\Scripts\python.exe" -m uvicorn server:app --reload
pause
