@echo off
REM Syrian Airport Data Engine - Automated Daily Refresh Task Runner
cd /d "c:\Users\fahad\OneDrive\Desktop\syria damascus airport"
set PYTHONPATH=.
set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

if not exist "logs" mkdir "logs"

echo ======================================================== >> logs\daily_refresh.log
echo Ingestion run started at: %date% %time% >> logs\daily_refresh.log
echo ======================================================== >> logs\daily_refresh.log

"C:\Users\fahad\AppData\Local\Programs\Python\Python313\python.exe" scripts\daily_refresh.py >> logs\daily_refresh.log 2>&1
set EXIT_CODE=%ERRORLEVEL%

echo Ingestion run finished with exit code %EXIT_CODE% at %date% %time% >> logs\daily_refresh.log
echo. >> logs\daily_refresh.log

exit /b %EXIT_CODE%
