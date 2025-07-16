@echo off
echo Rolling back to production version (origin/main)...
git fetch origin
git reset --hard origin/main
echo Rollback complete. Current commit:
git log -1 --oneline
echo Starting development server...
start /B .\run_weave_dev.bat
