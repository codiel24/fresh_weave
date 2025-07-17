@echo off
echo Stopping Weave Flask server...

echo Killing any existing Python processes...
taskkill /F /IM python.exe 2>nul

echo Waiting for port to clear...
timeout /t 2 /nobreak >nul

echo Checking if port 5000 is free...
netstat -ano | findstr :5000 | findstr LISTENING >nul
if %errorlevel% equ 0 (
    echo Warning: Port 5000 still has listeners, but should clear shortly
) else (
    echo Port 5000 is now free
)

echo Weave server stopped.
pause
