@echo off
echo Stopping the services...

net stop "Anacle.EAM v10.0 Simplicity Service (MyBill v10)"

if %ERRORLEVEL% EQU 0 (
    echo Service stopped successfully!
) else (
    echo Failed to stop service. Error code: %ERRORLEVEL%
    exit /b 1
)

net stop "Anacle.EAM v10.0 Simplicity Service (MyBill v10 - SP)"
if %ERRORLEVEL% EQU 0 (
    echo Service stopped successfully!
) else (
    echo Failed to stop service. Error code: %ERRORLEVEL%
    exit /b 1
)
