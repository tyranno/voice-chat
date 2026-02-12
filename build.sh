#!/bin/bash
set -e

export ANDROID_HOME=/opt/android-sdk
export PATH=/opt/android-sdk/cmdline-tools/latest/bin:/opt/android-sdk/platform-tools:/usr/bin:/bin
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64

cd /mnt/e/Project/My/voice-chat/android
chmod +x gradlew
./gradlew assembleDebug

echo ""
echo "=== BUILD COMPLETE ==="
echo "APK: android/app/build/outputs/apk/debug/app-debug.apk"
