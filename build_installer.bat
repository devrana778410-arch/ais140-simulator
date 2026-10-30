@echo off
title Build AIS-140 Windows Installer
echo ===================================================
echo Building AIS-140 Simulator Windows Installer (.exe)
echo ===================================================

set "ISCC_PATH=C:\Users\PC\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC_PATH%" set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC_PATH%" set "ISCC_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
if not exist "%ISCC_PATH%" set "ISCC_PATH=C:\Users\pinky\AppData\Local\Programs\Antigravity IDE\resources\app\node_modules\innosetup\bin\ISCC.exe"

if not exist "%ISCC_PATH%" (
    echo [ERROR] Inno Setup compiler (ISCC.exe) not found at:
    echo "%ISCC_PATH%"
    pause
    exit /b 1
)

if not exist "dist\AIS140-Simulator-Portable.exe" (
    echo [ERROR] dist\AIS140-Simulator-Portable.exe not found!
    pause
    exit /b 1
)

echo Compiling installer.iss...
"%ISCC_PATH%" installer.iss

if %ERRORLEVEL% equ 0 (
    echo.
    echo ===================================================
    echo [SUCCESS] Windows Installer created successfully!
    echo Output: dist\AIS140-Simulator-Setup.exe
    echo ===================================================
) else (
    echo.
    echo [ERROR] Inno Setup compilation failed with code %ERRORLEVEL%
)

pause
