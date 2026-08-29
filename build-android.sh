#!/usr/bin/env bash
# 🛡️ BlinkSafe Mobile — Android APK Build Script
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "========================================"
echo "      BLINKSAFE ANDROID APK BUILDER     "
echo "========================================"

mkdir -p release

if [ ! -d "android_app/android" ]; then
    echo "📦 Prebuilding Android native project..."
    cd android_app && npx expo prebuild --platform android --clean && cd ..
fi

echo "🔨 Building Debug APK with Gradle..."
cd android_app/android
./gradlew assembleDebug --no-daemon

APK_SRC="app/build/outputs/apk/debug/app-debug.apk"
APK_DEST="../../release/BlinkSafe.apk"

if [ -f "$APK_SRC" ]; then
    cp "$APK_SRC" "$APK_DEST"
    echo "========================================"
    echo "✅ APK BUILD SUCCESSFUL!"
    echo "Location: $SCRIPT_DIR/release/BlinkSafe.apk"
    echo "Size: $(du -h "$APK_DEST" | cut -f1)"
    echo "========================================"
else
    echo "❌ ERROR: APK file was not generated at $APK_SRC"
    exit 1
fi
