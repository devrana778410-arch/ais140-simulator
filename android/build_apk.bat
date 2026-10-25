@echo off
title Build AIS-140 Android APK
echo ===================================================
echo Building AIS-140 Simulator Android Application (APK)
echo ===================================================

if "%JAVA_HOME%"=="" (
    set "JAVA_HOME=C:\Program Files\Microsoft\jdk-17.0.20.101-hotspot"
)
set "PATH=%JAVA_HOME%\bin;%PATH%"

if "%ANDROID_HOME%"=="" (
    if exist "%LOCALAPPDATA%\Android\Sdk" (
        set "ANDROID_HOME=%LOCALAPPDATA%\Android\Sdk"
    )
)

echo Using Java: %JAVA_HOME%
echo Using Android SDK: %ANDROID_HOME%
echo.

cd /d "%~dp0"

if exist gradlew.bat (
    call gradlew.bat assembleDebug
    if %ERRORLEVEL% equ 0 (
        echo.
        echo ===================================================
        echo [SUCCESS] APK built successfully!
        echo APK Location:
        echo app\build\outputs\apk\debug\app-debug.apk
        echo ===================================================
    ) else (
        echo.
        echo [ERROR] Gradle build failed with code %ERRORLEVEL%
    )
) else (
    echo [ERROR] gradlew.bat not found in %CD%
)

pause
