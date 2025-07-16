@echo off
echo Rolling back to development snapshot (2025-07-15)...
git reset --hard dev-snapshot-2025-07-15
echo Rollback complete. Current commit:
git log -1 --oneline
echo Starting development server...
start /B .\run_weave_dev.bat
