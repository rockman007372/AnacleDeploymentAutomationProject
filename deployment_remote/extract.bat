@echo off
setlocal enabledelayedexpansion

:: =========================================
:: EXTRACT DEPLOYMENT FUNCTION
:: =========================================
:extract_deployment
set "ZIP_FOLDER=D:\Deployments\ENTER_YOUR_FOLDER_HERE" 
set "EXTRACT_TO_DIR1=D:\MyBill_v10"
set "EXTRACT_TO_DIR2=D:\MyBill_v10-SP"

echo ==================================================
echo                    Extracting...
echo ==================================================
echo.

if "%~1"=="" (
    echo [ERROR] No source directory provided
    echo Usage: %~nx0 "D:\Path\To\Source\Directory"
    echo.
    echo Example: %~nx0 "D:\Deployment\20251105_mybill_v10"
    exit /b 1
)

if "%~2"=="" (
    echo [ERROR] No destination directory provided
    echo Usage: %~nx0 "D:\Path\To\Source\Directory"
    echo.
    echo Example: %~nx0 "D:\MyBill_v10"
    exit /b 1
)

set "ZIP_FILE=%~1"
set "DESTINATION=%~2"

:: Check if zip file exists
if not exist "%ZIP_FILE%" (
    echo [ERROR] Zip file not found: "%ZIP_FILE%"
    exit /b 1
)

:found_zip
echo Found zip file: %ZIP_FILE%

:: Extract to first directory
echo Extracting to: %DESTINATION%
powershell -Command "Expand-Archive -Path '%ZIP_FILE%' -DestinationPath '%DESTINATION%' -Force"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to extract to %DESTINATION%
    exit /b 1
)
echo [SUCCESS] Extraction completed.
echo.

exit /b 0