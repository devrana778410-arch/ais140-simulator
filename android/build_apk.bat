@echo off
title Build AIS-140 Android APK
echo ===================================================
echo Building AIS-140 Simulator Android Application (APK)
echo ===================================================

if "%JAVA_HOME%"=="" (
    set "JAVA_HOME=C:\Program Files\Microsoft\jdk-17.0.20.101-hotspot"
    set "PATH=%JAVA_HOME%\bin;%PATH%"
)

echo Using Java:
java -version

if exist gradlew.bat (
    call gradlew.bat assembleRelease
) else (
    echo Note: Open this folder in Android Studio to build APK or run:
    echo gradlew assembleRelease
)

pause
