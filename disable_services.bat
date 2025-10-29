@echo off
setlocal enabledelayedexpansion

rem Define service names (add or remove as needed)
set "services[0]=Anacle.EAM v10.0 Simplicity Service (MyBill v10)"
set "services[1]=Anacle.EAM v10.0 Simplicity Service (MyBill v10 - SP)"
rem Add more services here if needed:
rem set "services[2]=Another Service Name"
rem set "services[3]=Yet Another Service"

set serviceCount=2

echo ==================================================
echo Stopping Services...
echo ==================================================
echo.

set failedCount=0

rem Loop through all services
for /L %%i in (0,1,%serviceCount%-1) do (
    set "serviceName=!services[%%i]!"
    echo [%%i] Stopping: !serviceName!
    
    net stop "!serviceName!" >nul 2>&1
    
    if !ERRORLEVEL! EQU 0 (
        echo     [SUCCESS] Service stopped successfully
    ) else (
        echo     [FAILED] Error code: !ERRORLEVEL!
        set /a failedCount+=1
    )
    echo.
)

echo ==================================================
echo Summary:
echo ==================================================
set /a successCount=%serviceCount%-%failedCount%
echo Total services: %serviceCount%
echo Successfully stopped: %successCount%
echo Failed to stop: %failedCount%
echo ==================================================

if %failedCount% GTR 0 (
    echo.
    echo WARNING: Some services failed to stop!
    exit /b 1
) else (
    echo.
    echo All services stopped successfully!
    exit /b 0
)