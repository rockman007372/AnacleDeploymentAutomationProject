@echo off
setlocal enabledelayedexpansion

:: =========================================
:: EXTRACT DEPLOYMENT FUNCTION
:: =========================================
:extract_deployment
echo ==================================================
echo                    Extracting...
echo ==================================================
echo.

:: Check if ZIP file is provided
if "%~1"=="" (
    echo [ERROR] No source ZIP file provided
    echo Usage: %~nx0 "path\to\file.zip" "destination1" "destination2" [...]
    echo Example: %~nx0 "D:\Deploy.zip" "D:\MyBill_v10" "D:\MyBill_v10-SP"
    exit /b 1
)

set "ZIP_FILE=%~1"

:: Check if zip file exists
if not exist "%ZIP_FILE%" (
    echo [ERROR] Zip file not found: "%ZIP_FILE%"
    exit /b 1
)

echo Found zip file: %ZIP_FILE%
echo.

:: Check if at least one destination is provided
if "%~2"=="" (
    echo [ERROR] No destination directories provided
    echo Usage: %~nx0 "path\to\file.zip" "destination1" "destination2" [...]
    exit /b 1
)

:: Count destinations and store them
set DEST_COUNT=0
set ARG_INDEX=2

:count_destinations
if not "%~2"=="" (
    set /a DEST_COUNT+=1
    set "DEST_!DEST_COUNT!=%~2"
    echo Destination !DEST_COUNT!: %~2
    shift
    goto count_destinations
)

echo.

:: Extract once to temp location
set "TEMP_EXTRACT=%TEMP%\mybill_extract_%RANDOM%"
echo [STEP 1/2] Extracting archive to temporary location...
powershell -Command "Expand-Archive -Path '%ZIP_FILE%' -DestinationPath '%TEMP_EXTRACT%' -Force"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to extract archive
    rmdir /s /q "%TEMP_EXTRACT%" 2>nul
    exit /b 1
)
echo [SUCCESS] Archive extracted.
echo.

:: Copy to all destinations in parallel
echo [STEP 2/2] Copying to %DEST_COUNT% destination(s) in parallel...
echo.

:: Create log directory for parallel operations
set "LOG_DIR=%TEMP%\mybill_logs_%RANDOM%"
mkdir "%LOG_DIR%"

:: Start parallel copy processes
for /l %%i in (1,1,%DEST_COUNT%) do (
    set "DEST=!DEST_%%i!"
    set "LOG_FILE=%LOG_DIR%\copy_%%i.log"
    
    :: Create destination if it doesn't exist
    if not exist "!DEST!" (
        echo Creating directory: !DEST!
        mkdir "!DEST!"
    )
    
    :: Start robocopy in a new window (minimized) - /IS /IT overwrites existing files
    start "Copying to !DEST!" /min cmd /c "robocopy "%TEMP_EXTRACT%" "!DEST!" /E /IS /IT /NFL /NDL /NJH /NJS /NC /NS /NP > "!LOG_FILE!" 2>&1 & echo ERRORLEVEL=%%errorlevel%% >> "!LOG_FILE!""
    
    echo Started copy job %%i to: !DEST!
)

echo.
echo Waiting for all copy operations to complete...
echo.

:: Wait for all robocopy processes to finish
:wait_loop
set RUNNING=0
for /l %%i in (1,1,%DEST_COUNT%) do (
    set "LOG_FILE=%LOG_DIR%\copy_%%i.log"
    if exist "!LOG_FILE!" (
        findstr /C:"ERRORLEVEL=" "!LOG_FILE!" >nul 2>&1
        if errorlevel 1 (
            set /a RUNNING+=1
        )
    ) else (
        set /a RUNNING+=1
    )
)

if %RUNNING% gtr 0 (
    echo Still running: %RUNNING% of %DEST_COUNT% jobs...
    timeout /t 2 /nobreak >nul
    goto wait_loop
)

echo.
echo All copy operations completed!
echo.
echo ==================================================
echo                    Results
echo ==================================================
echo.

:: Check results
set FAILED=0
for /l %%i in (1,1,%DEST_COUNT%) do (
    set "LOG_FILE=%LOG_DIR%\copy_%%i.log"
    set "DEST=!DEST_%%i!"
    
    :: Extract error level from log
    for /f "tokens=2 delims==" %%e in ('findstr /C:"ERRORLEVEL=" "!LOG_FILE!"') do set "EXIT_CODE=%%e"
    
    :: Robocopy exit codes: 0-7 are success, 8+ are failures
    if !EXIT_CODE! geq 8 (
        echo [FAILED] Destination %%i: !DEST!
        set /a FAILED+=1
    ) else (
        echo [SUCCESS] Destination %%i: !DEST!
    )
)

:: Cleanup
rmdir /s /q "%TEMP_EXTRACT%" 2>nul
rmdir /s /q "%LOG_DIR%" 2>nul

if %FAILED% gtr 0 (
    echo [ERROR] %FAILED% destinations failed.
    exit /b 1
) else (
    echo [SUCCESS] All %DEST_COUNT% destinations copied successfully!
    exit /b 0
)