@echo off
REM 🛡️ BlinkSafe Mobile — Windows Startup Launcher
echo ========================================
echo       BLINKSAFE WINDOWS ONE-CLICK START
echo ========================================

python start.py
if %errorlevel% neq 0 (
    echo ❌ Failed to start BlinkSafe.
    pause
)
