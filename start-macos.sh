#!/usr/bin/env bash
# 🛡️ BlinkSafe Mobile — macOS Startup Launcher
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "========================================"
echo "      BLINKSAFE MACOS ONE-CLICK START   "
echo "========================================"

if [ -f "start.py" ]; then
    python3 start.py
else
    echo "❌ start.py not found."
    exit 1
fi
