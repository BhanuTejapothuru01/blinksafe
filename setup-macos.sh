#!/usr/bin/env bash
# 🛡️ BlinkSafe Mobile — macOS Setup Script
set -e

echo "========================================"
echo "      BLINKSAFE MACOS ENVIRONMENT SETUP "
echo "========================================"

echo "[1/4] Checking Node.js & npm..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js (v18+)."
    exit 1
fi
echo "✓ Node.js $(node -v) detected"

if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm."
    exit 1
fi
echo "✓ npm $(npm -v) detected"

echo "[2/4] Checking Python 3..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.10+."
    exit 1
fi
echo "✓ Python 3 detected"

echo "[3/4] Installing project dependencies..."
if [ -f "requirements.txt" ]; then
    python3 -m pip install -r requirements.txt --quiet || true
fi

if [ -d "android_app" ]; then
    cd android_app && npm install && cd ..
fi

echo "[4/4] Checking Android CLI & SDK..."
if command -v android &> /dev/null; then
    echo "✓ Android CLI detected"
else
    echo "ℹ️ Android CLI not found in PATH. Run: curl -fsSL https://dl.google.com/android/cli/latest/darwin_arm64/install.sh | bash"
fi

echo "========================================"
echo "✅ macOS Setup Complete! Run ./start-macos.sh to launch."
echo "========================================"
