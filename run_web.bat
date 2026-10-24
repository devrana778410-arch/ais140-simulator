@echo off
title AIS-140 Web App & Socket Gateway
cd /d "%~dp0"
echo Starting AIS-140 Simulator Web App on http://localhost:8080 ...
start "" "http://localhost:8080"
python web/server.py 8080
pause
