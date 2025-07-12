@echo off
echo Activating virtual environment...
call .\venv\Scripts\activate.bat

echo Setting Flask environment variables...
set FLASK_APP=app.py
REM Optional: Uncomment next line for debug mode, which provides more error details and auto-reloads
set FLASK_DEBUG=1 

echo Checking for existing database...
IF NOT EXIST instance\sujets.db (
    echo Database not found. Initializing...
    flask init-db
) ELSE (
    echo Database already exists. Skipping initialization.
)

echo Starting Flask development server...
REM The command below should take over this window and run the server.
REM All output from the server will appear here.
REM To stop the server, press CTRL+C in this window.
python -m flask run

echo If you see this message, the server failed to start.