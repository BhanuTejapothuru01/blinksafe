@echo off
REM 🛡️ BlinkSafe Mobile — Windows Setup Script
echo ========================================
echo       BLINKSAFE WINDOWS ENVIRONMENT SETUP
echo ========================================

echo [1/3] Checking Node.js and npm...
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Node.js is not installed. Please install Node.js (v18+).
    exit /b 1
)
echo ✓ Node.js detected

echo [2/3] Checking Python...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Python is not installed. Please install Python 3.10+.
    exit /b 1
)
echo ✓ Python detected

echo [3/3] Installing Python dependencies...
python -m pip install -r requirements.txt --quiet
if exist android_app (
    cd android_app && npm install && cd ..
)

echo ========================================
echo ✅ Windows Setup Complete! Run start-windows.bat to launch.
echo ========================================
