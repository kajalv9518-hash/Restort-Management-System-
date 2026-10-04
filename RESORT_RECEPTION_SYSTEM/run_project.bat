@echo off
title Resort Reception Management System

cd /d "%~dp0"

echo ==========================================
echo   RESORT RECEPTION MANAGEMENT SYSTEM
echo ==========================================
echo.
echo Starting application...
echo.

start "" http://127.0.0.1:5000

python app.py

pause