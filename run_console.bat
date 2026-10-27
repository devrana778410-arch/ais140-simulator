@echo off
title AIS-140 & GPS Interactive Command Console
cd /d "%~dp0"
python device_console.py
if %errorlevel% neq 0 (
    echo.
    echo Console closed.
    pause
)
