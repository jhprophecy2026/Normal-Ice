@echo off
echo ========================================
echo Starting Healthcare FHIR Backend Server
echo ========================================
echo.

cd backend
call venv\Scripts\activate.bat
python -m app.main

pause
