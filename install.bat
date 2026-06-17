@echo off
setlocal
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not on PATH.
    echo Install Python 3.10+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

call .venv\Scripts\activate.bat

echo Installing Python packages...
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo Package installation failed.
    pause
    exit /b 1
)

echo Installing Playwright browser...
playwright install chromium
if errorlevel 1 (
    echo Playwright browser install failed.
    pause
    exit /b 1
)

echo.
echo Done. Run run.bat to start the app.
pause
