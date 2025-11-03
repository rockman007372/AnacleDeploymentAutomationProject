@echo off

:: Set log file
set "LOGFILE=%~dp0deployment_%date:~-4,4%%date:~-10,2%%date:~-7,2%.log"

:: =========================================
:: Ensure the script runs as Administrator
:: =========================================
:: Check for admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo Requesting administrative privileges...
    echo.
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: Start logging from here
call :main 2>&1 | powershell -Command "$input | Tee-Object -FilePath '%LOGFILE%'"
exit /b

:: =========================================
:: Main Script
:: =========================================
:main
:: Step 1: Back up the folders
echo Starting backup process...
echo.

call backup.bat "D:\MyBill_v10" || goto :error
echo.

call backup.bat "D:\MyBill_v10-SP" || goto :error
echo.

echo All backups completed!

:: Step 2: Stop the services
call stop_services.bat "Anacle.EAM v10.0 Simplicity Service (MyBill v10)" "Anacle.EAM v10.0 Simplicity Service (MyBill v10 - SP)" || goto :error

:: Step 3: Extract deployment file in respective folders
call extract_deployment.bat || goto :error

:: Step 4: Enable services again
call start_services.bat "Anacle.EAM v10.0 Simplicity Service (MyBill v10)" "Anacle.EAM v10.0 Simplicity Service (MyBill v10 - SP)" || goto :error

:error
echo.
echo ERROR: Backup process terminated due to failure.
pause
exit /b 1