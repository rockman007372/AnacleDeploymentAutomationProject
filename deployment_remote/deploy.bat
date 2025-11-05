@echo off

:: Set log file
@REM set "LOGFILE=%~dp0deployment_%date:~-4,4%%date:~-10,2%%date:~-7,2%.log"

REM Store the script's directory
set SCRIPT_DIR=%~dp0

:: =========================================
:: Ensure the script runs as Administrator
:: =========================================
:: Check for admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo Requesting administrative privileges...
    echo.
    powershell -Command "Start-Process '%~f0' -Verb RunAs -ArgumentList '%CD%'"
    exit /b
)

:: Start logging from here
call :main 
exit /b

:: =========================================
:: Main Script
:: =========================================
:main

REM Change to script directory to ensure relative paths work
pushd "%SCRIPT_DIR%"

:: Step 1: Back up the folders
call backup.bat "D:\MyBill_v10" || goto :error
echo.

call backup.bat "D:\MyBill_v10-SP" || goto :error
echo.

echo All backups completed!
echo.

:: Step 2: Stop the services
call stop_services.bat "Anacle.EAM v10.0 Simplicity Service (MyBill v10)" "Anacle.EAM v10.0 Simplicity Service (MyBill v10 - SP)" || goto :error

:: Step 3: Extract deployment file in respective folders
call extract.bat "YOUR_DEPLOYMENT_ZIP_FILE" "D:\MyBill_v10" || goto :error
echo.

call extract.bat "YOUR_DEPLOYMENT_ZIP_FILE" "D:\MyBill_v10-SP" || goto :error
echo.

:: Step 4: Enable services again
call start_services.bat "Anacle.EAM v10.0 Simplicity Service (MyBill v10)" "Anacle.EAM v10.0 Simplicity Service (MyBill v10 - SP)" || goto :error

echo "Done!"
pause
exit /b 0

:error
echo.
echo ERROR: Backup process terminated due to failure.
pause
exit /b 1