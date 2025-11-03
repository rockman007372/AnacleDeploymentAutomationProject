@echo off
setlocal enabledelayedexpansion

:: =========================================
:: EXTRACT DEPLOYMENT FUNCTION
:: =========================================
:extract_deployment
set "ZIP_FOLDER=C:\Deployments\ENTER_YOUR_FOLDER_HERE" 
set "EXTRACT_TO_DIR1=D:\MyBill_v10"
set "EXTRACT_TO_DIR2=D:\MyBill_v10-SP"

echo.
echo ========================================
echo Extracting Deployment Files
echo ========================================
echo.

:: Find the zip file in the folder
echo Searching for deployment zip file in: %ZIP_FOLDER%
for %%f in ("%ZIP_FOLDER%\*.zip") do (
    set "ZIP_FILE=%%f"
    goto :found_zip
)

:: No zip file found
echo WARNING: No zip file found in %ZIP_FOLDER%
echo Skipping extraction...
exit /b 0

:found_zip
echo Found zip file: %ZIP_FILE%
echo.

:: Extract to first directory
echo Extracting to: %EXTRACT_TO_DIR1%
powershell -Command "Expand-Archive -Path '%ZIP_FILE%' -DestinationPath '%EXTRACT_TO_DIR1%' -Force"
if %errorlevel% neq 0 (
    echo ERROR: Failed to extract to %EXTRACT_TO_DIR1%
    exit /b 1
)
echo Extraction completed successfully.
echo.

:: Extract to second directory
echo Extracting to: %EXTRACT_TO_DIR2%
powershell -Command "Expand-Archive -Path '%ZIP_FILE%' -DestinationPath '%EXTRACT_TO_DIR2%' -Force"
if %errorlevel% neq 0 (
    echo ERROR: Failed to extract to %EXTRACT_TO_DIR2%
    exit /b 1
)
echo Extraction completed successfully.
echo.

echo All deployments extracted successfully!
exit /b 0