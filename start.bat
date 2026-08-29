@echo off
REM 🛡️ BlinkSafe - Startup Script (Windows Command Prompt)

cd /d "%~dp0"

set PYTHON_CMD=

python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
) else (
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=py
    )
)

if "%PYTHON_CMD%"=="" (
    echo.
    echo ❌ ERROR: Python 3 is required to run BlinkSafe.
    echo Please install Python 3 from:
    echo https://www.python.org/downloads/
    echo Make sure "Add Python to PATH" is enabled.
    echo Then run:
    echo start.bat
    echo.
    pause
    exit /b 1
)

if not exist venv (
    echo Creating virtual environment (venv)...
    %PYTHON_CMD% -m venv venv
)

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

python start.py %*
if errorlevel 1 (
    echo.
    echo ❌ BlinkSafe startup encountered an error.
    pause
)
