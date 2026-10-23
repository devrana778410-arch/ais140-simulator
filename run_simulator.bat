@echo off
title AIS-140 Client Simulator
cd /d C:\ais140-simulator
python main.py
if %errorlevel% neq 0 (
    echo.
    echo Application stopped with error code %errorlevel%.
    pause
)
