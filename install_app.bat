@echo off
title Install AIS-140 Simulator
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_app.ps1"
pause
