@echo off
title Library Management System
cd /d "%~dp0"
echo ===================================================
echo   Starting Library Management System (SQLite)
echo ===================================================
echo.
echo Opening: http://localhost:3000
echo.
python app.py
pause