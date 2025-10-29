@echo off
echo Starting the services...

net start "Anacle.EAM v10.0 Simplicity Service (MyBill v10)"

if %ERRORLEVEL% EQU 0 (
    echo Service starts successfully!
) else (
    echo Failed to start service. Error code: %ERRORLEVEL%
    exit /b 1
)

net start "Anacle.EAM v10.0 Simplicity Service (MyBill v10 - SP)"
if %ERRORLEVEL% EQU 0 (
    echo Service starts successfully!
) else (
    echo Failed to start service. Error code: %ERRORLEVEL%
    exit /b 1
)
