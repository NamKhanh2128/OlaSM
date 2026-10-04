@echo off
echo Starting OlaSM Dev Environment...

:: Set project root to script directory
set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

:: Terminal 1: Backend
start "OlaSM Backend" cmd /k "cd /d %PROJECT_ROOT% && uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000"

:: Wait 2 seconds
timeout /t 2 /nobreak >nul

:: Terminal 2: Frontend
start "OlaSM Frontend" cmd /k "cd /d %PROJECT_ROOT%src\frontend && npm run dev"

echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
pause
