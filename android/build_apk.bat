@echo off
set "JAVA_HOME=C:\Program Files\Microsoft\jdk-17.0.20.101-hotspot"
set "ANDROID_HOME=C:\Users\pinky\AppData\Local\Android\Sdk"
cd /d "C:\ais140-simulator\android"
call gradlew.bat assembleDebug
