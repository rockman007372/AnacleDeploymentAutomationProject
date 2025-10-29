@echo off
setlocal enabledelayedexpansion

REM ===== CONFIGURATION =====
REM Set your base destination directory
set "BASE_DEST_DIR=D:\Deployment Backup"

REM Set the path to 7-Zip (adjust if needed)
set "SEVENZIP=C:\Program Files\7-Zip\7z.exe"

REM ===== SCRIPT =====
REM Check if source directory was provided as argument
if "%~1"=="" (
    echo ERROR: No source directory provided
    echo Usage: %~nx0 "C:\Path\To\Source\Directory"
    echo.
    echo Example: %~nx0 "D:\MyBill_v10"
    exit /b 1
)

set "SOURCE_DIR=%~1"

REM Get today's date in YYYYMMDD format
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set "TODAY=%datetime:~0,4%%datetime:~4,2%%datetime:~6,2%"

REM Get the name of the source directory
for %%I in ("%SOURCE_DIR%") do set "DIR_NAME=%%~nxI"

REM Create folder name with date and folder name
set "FOLDER_NAME=%TODAY%_%DIR_NAME%"

REM Create destination folder path
set "DEST_DIR=%BASE_DEST_DIR%\%FOLDER_NAME%"

REM Set the output zip file path (same name as the folder)
set "OUTPUT_ZIP=%DEST_DIR%\%FOLDER_NAME%.zip"

REM Check if 7-Zip exists
if not exist "%SEVENZIP%" (
    echo ERROR: 7-Zip not found at %SEVENZIP%
    echo Please install 7-Zip or update the SEVENZIP variable
    exit /b 1
)

REM Check if source directory exists
if not exist "%SOURCE_DIR%" (
    echo ERROR: Source directory not found: %SOURCE_DIR%
    exit /b 1
)

REM Check if base destination directory exists
if not exist "%BASE_DEST_DIR%" (
    echo ERROR: Base destination directory not found: %BASE_DEST_DIR%
    exit /b 1
)

REM Create destination folder with today's date
if not exist "%DEST_DIR%" (
    echo Creating destination directory: %DEST_DIR%
    mkdir "%DEST_DIR%"
)

REM Change to source directory
cd /d "%SOURCE_DIR%"

REM Create zip file with the 3 folders
echo Creating zip file: %OUTPUT_ZIP%
echo Compressing: webapp, service, TPAPI
"%SEVENZIP%" a -tzip "%OUTPUT_ZIP%" webapp service TPAPI

REM Check if compression was successful
if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS: Zip file created at %OUTPUT_ZIP%
) else (
    echo.
    echo ERROR: Failed to create zip file
)
