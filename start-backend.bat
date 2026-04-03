@echo off
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║       AgentMesh AI — Backend             ║
echo  ║       FastAPI  +  Redis  +  LangGraph    ║
echo  ╚══════════════════════════════════════════╝
echo.

cd /d "%~dp0MOM-Orchestrator"

:: Check Redis
echo [1/2] Checking Redis on localhost:6379...
redis-cli ping >nul 2>&1
if %errorlevel% neq 0 (
    echo  ⚠  Redis is not running. Start Redis first:
    echo     - If installed: run  redis-server
    echo     - Or start the Redis service in Windows Services
    echo.
    pause
    exit /b 1
)
echo  ✓  Redis is running.
echo.

:: Start FastAPI
echo [2/2] Starting FastAPI on http://localhost:8000 ...
echo.
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
