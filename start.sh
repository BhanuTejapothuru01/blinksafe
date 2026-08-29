#!/usr/bin/env bash
# 🛡️ BlinkSafe - Startup Script (macOS / Linux)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v python3 &> /dev/null; then
    echo "❌ ERROR: Python 3 is required to run BlinkSafe."
    echo "Please install Python 3 and run:"
    echo "  ./start.sh"
    exit 1
fi

# Ensure venv directory exists
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate venv
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Hand off to master launcher start.py
exec python start.py "$@"
