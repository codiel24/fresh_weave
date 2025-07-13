@echo off
echo === Force Push to GitHub ===
echo This will override any remote changes with your local changes.

echo.
echo === Adding Files ===
git add db_operations.py migrate_date_format.py inspect_db.py run_inspect.py README.md
git add migrate_add_fake_dates.py migrate_reverse_ids.py check_null_dates.py deploy_to_production.bat git_push.bat

echo.
echo === Committing Changes ===
git commit -m "Fix navigation issues by migrating date format from dd.mm.yy to YYYY-MM-DD"

echo.
echo === Force Pushing to Remote ===
for /f "tokens=*" %%a in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%a
echo Current branch: %BRANCH%
git push --force origin %BRANCH%

echo.
echo === Done ===
pause
