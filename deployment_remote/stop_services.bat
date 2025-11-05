@echo off
setlocal enabledelayedexpansion

if "%~1"=="" (
    echo Usage: %~nx0 "Service1" "Service2" ...
    exit /b 1
)

set failedCount=0
set serviceCount=0

echo ==================================================
echo                Stopping Services...
echo ==================================================
echo.

:loop_args
if "%~1"=="" goto :after_loop
set "serviceName=%~1"
echo [%serviceCount%] Stopping: %serviceName%
net stop "%serviceName%" >nul 2>&1

if !errorlevel! EQU 0 (
    echo [SUCCESS] Service stopped successfully
) else (
    echo [FAILED] Error code: !errorlevel!
    set /a failedCount+=1
)
echo.
set /a serviceCount+=1
shift
goto :loop_args

:after_loop
if %failedCount% GTR 0 (
    echo.
    echo [WARNING] Some services failed to stop!
    exit /b 1
) else (
    echo.
    echo All services stopped successfully!
    exit /b 0
)
