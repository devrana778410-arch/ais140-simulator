@echo off
title AIS-140 HMAC Key Sniffer & Interceptor
cd /d "%~dp0"
python hmac_sniffer.py %*
pause
