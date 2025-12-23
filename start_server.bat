@echo off
echo ================================
echo    ClipCut Backend Server
echo ================================
echo.

:: Check if virtual environment exists
if not exist ".venv" (
    echo Creating virtual environment...
    py -3.12 -m venv .venv
    echo.
)

:: Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

:: Install/update dependencies
echo Installing dependencies...
pip install -r backend/requirements.txt
echo.

:: Create necessary directories
if not exist "backend\data\videos" mkdir backend\data\videos
if not exist "backend\data\audio" mkdir backend\data\audio
if not exist "backend\data\artifacts" mkdir backend\data\artifacts
if not exist "backend\db" mkdir backend\db

:: Start the server
echo.
echo ================================
echo Starting FastAPI server...
echo Server will be available at:
echo http://localhost:8000
echo API docs at: http://localhost:8000/docs
echo ================================
echo.

cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
