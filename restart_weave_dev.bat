@echo off
echo Starting Weave development server...

echo Step 1: Stopping any existing Flask processes...
taskkill /F /IM python.exe 2>nul
if %errorlevel% equ 0 (
    echo - Killed existing Python processes
    timeout /t 2 /nobreak >nul
) else (
    echo - No existing Python processes found
)

echo Step 2: Activating virtual environment...
call .\venv\Scripts\activate.bat

echo Step 3: Setting Flask environment variables...
set FLASK_APP=app.py
set FLASK_DEBUG=1 

echo Step 4: Checking for existing database...
IF NOT EXIST instance\sujets.db (
    echo - Database not found. Initializing...
    flask init-db
) ELSE (
    echo - Database already exists. Skipping initialization.
)

echo Step 5: Starting Flask development server...
echo ========================================
echo Server starting on http://localhost:5000
echo Press CTRL+C to stop the server
echo ========================================
python -m flask run

echo.
echo Server stopped. If this was unexpected, check for errors above.
pause
