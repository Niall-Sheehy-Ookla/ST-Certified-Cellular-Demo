@echo off
REM Cellular Certification Dashboard - Quick Start Setup (Windows)
REM This script sets up the environment and launches the application

echo.
echo ==========================================
echo. 📡 Cellular Certification Dashboard
echo. Quick Start Setup
echo. ==========================================
echo.

REM Check Python version
echo. ✓ Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo. ❌ Python not found. Please install Python 3.8+
    pause
    exit /b 1
)
python --version
echo.

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo. 📦 Creating virtual environment...
    python -m venv venv
    echo.   ✓ Virtual environment created
) else (
    echo. ✓ Virtual environment already exists
)
echo.

REM Activate virtual environment
echo. 🔌 Activating virtual environment...
call venv\Scripts\activate.bat
echo.   ✓ Environment activated
echo.

REM Install dependencies
echo. 📥 Installing dependencies...
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt >nul 2>&1
echo.   ✓ Dependencies installed
echo.

REM Verify files exist
echo. ✓ Verifying application files...
if not exist "app.py" (
    echo.   ❌ Missing: app.py
    exit /b 1
)
echo.   ✓ app.py
if not exist "metrics_processor.py" (
    echo.   ❌ Missing: metrics_processor.py
    exit /b 1
)
echo.   ✓ metrics_processor.py
if not exist "certification_scorer.py" (
    echo.   ❌ Missing: certification_scorer.py
    exit /b 1
)
echo.   ✓ certification_scorer.py
if not exist "dashboard_ui.py" (
    echo.   ❌ Missing: dashboard_ui.py
    exit /b 1
)
echo.   ✓ dashboard_ui.py
echo.

REM Launch Streamlit
echo. 🚀 Launching Cellular Certification Dashboard...
echo.
echo. The dashboard will open in your default browser at:
echo. http://localhost:8501
echo.
echo. To stop the application, press Ctrl+C in the terminal
echo.
echo. ==========================================
echo.

streamlit run app.py
