@echo off
title AIS-140 Client Simulator
cd /d "%~dp0"
if exist "dist\AIS140-Simulator-Portable.exe" (
    start "" "dist\AIS140-Simulator-Portable.exe" %*
) else (
    python main.py %*
)
