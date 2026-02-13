@echo off
cd /d C:\Project\88.MyProject\voice-chat\android
wsl -d Ubuntu-22.04 -e bash -c "cd /mnt/c/Project/88.MyProject/voice-chat/android && export ANDROID_HOME=/home/lab/android-sdk && export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 && ./gradlew assembleDebug 2>&1"
