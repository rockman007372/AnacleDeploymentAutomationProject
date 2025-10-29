@echo off
setlocal enabledelayedexpansion

rem Get start date/time
for /f %%a in ('powershell -Command "Get-Date -Format 'yyyyMMdd'"') do set datetrf=%%a

rem Define source and destination directories. Space in path is allowed. 
set "SolutionDirectory=C:\Anacle\v10-Utility-Testing\abell.v10.0\abell.root\abell"
set "DestinationDirectory=D:\deployment\UtilityTesting\UAT_%datetrf%"
set "LogFilePath=%DestinationDirectory%\UAT_%datetrf%.log"
set "ZipFilePath=%DestinationDirectory%\UAT_%datetrf%.zip"
set "SEVENZIP=C:\Program Files\7-Zip\7z.exe"

rem Ensure log directory exists
for %%I in ("%LogFilePath%") do set "LogDir=%%~dpI"
if not exist "%LogDir%" (
    echo Creating log directory: "%LogDir%"
    mkdir "%LogDir%"
)

rem Initialize log file with header
for /f %%a in ('powershell -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"') do set MyDATE=%%a
echo ============================================================================ > %LogFilePath%
echo                        UAT DEPLOYMENT BUILD LOG                             >> %LogFilePath%
echo ============================================================================ >> %LogFilePath%
echo Start Time: %MyDATE% >> %LogFilePath%
echo. >> %LogFilePath%

rem Log configuration
echo [CONFIGURATION] >> %LogFilePath%
echo   Solution Directory : %SolutionDirectory% >> %LogFilePath%
echo   Destination Directory : %DestinationDirectory% >> %LogFilePath%
echo   Log File Path : %LogFilePath% >> %LogFilePath%
echo   Zip File Path : %ZipFilePath% >> %LogFilePath%
echo. >> %LogFilePath%

rem Validate source directory
echo [VALIDATION] >> %LogFilePath%
if not exist "%SolutionDirectory%" (
    echo   [ERROR] Solution directory does not exist: %SolutionDirectory% >> %LogFilePath%
    goto CompleteWithError
)
echo   [OK] Solution directory exists >> %LogFilePath%
echo. >> %LogFilePath%

rem 1. Create destination directory structure
echo [STEP 1/5] Creating Directory Structure >> %LogFilePath%
echo ---------------------------------------------------------------------------- >> %LogFilePath%

call:CreateDirectory "%DestinationDirectory%"

cd "%DestinationDirectory%"
call:CreateDirectory "%DestinationDirectory%\webapp\"
call:CreateDirectory "%DestinationDirectory%\service\"
call:CreateDirectory "%DestinationDirectory%\TPAPI\"
call:CreateDirectory "%DestinationDirectory%\ConfigFiles\"
echo. >> %LogFilePath%

rem 2. Copy files from source to destination
echo [STEP 2/5] Copying Files >> %LogFilePath%
echo ---------------------------------------------------------------------------- >> %LogFilePath%

call :CopyAndLog "webapp" "%SolutionDirectory%\webapp" "%DestinationDirectory%\webapp"
call :CopyAndLog "service" "%SolutionDirectory%\service\bin\debug" "%DestinationDirectory%\service"
call :CopyAndLog "TPAPI" "%SolutionDirectory%\AnacleAPI.Interface\bin\app.publish" "%DestinationDirectory%\TPAPI"

rem 3. Delete config files (Move to ConfigFiles folder)
echo [STEP 3/5] Managing Configuration Files >> %LogFilePath%
echo ---------------------------------------------------------------------------- >> %LogFilePath%

call:DeleteConfigFile "%DestinationDirectory%\webapp\web.config"
call:DeleteConfigFile "%DestinationDirectory%\webapp\web.config.bak"
call:DeleteConfigFile "%DestinationDirectory%\webapp\website.publishproj"
call:DeleteConfigFile "%DestinationDirectory%\webapp\vwdF722.tmp"
call:DeleteConfigFile "%DestinationDirectory%\webapp\temp\."

call:DeleteConfigFile "%DestinationDirectory%\service\Service.exe.config"
call:DeleteConfigFile "%DestinationDirectory%\service\LogicLayer.dll.config"

call:DeleteConfigFile "%DestinationDirectory%\TPAPI\Web.config"
echo. >> %LogFilePath%

rem 4. Zip the deployment folders (webapp, service, TPAPI)
echo [STEP 4/5] Creating Deployment Package >> %LogFilePath%
echo ---------------------------------------------------------------------------- >> %LogFilePath%
echo   Compressing: webapp, service, TPAPI >> %LogFilePath%
echo   Output: %ZipFilePath% >> %LogFilePath%
echo   Compression Level: Ultra (mx=9) >> %LogFilePath%
echo. >> %LogFilePath%

"%SEVENZIP%" a -tzip "%ZipFilePath%" "%DestinationDirectory%\webapp" "%DestinationDirectory%\service" "%DestinationDirectory%\TPAPI" -mx=9 

if %errorlevel%==0 (
    echo   [OK] Deployment package created successfully >> %LogFilePath%
) else (
    echo   [ERROR] Failed to create deployment package >> %LogFilePath%
    goto CompleteWithError
)
echo. >> %LogFilePath%

rem 5. Complete
:Complete
for /f %%a in ('powershell -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"') do set EndDATE=%%a
echo [STEP 5/5] Build Completed >> %LogFilePath%
echo ---------------------------------------------------------------------------- >> %LogFilePath%
echo. >> %LogFilePath%
echo ============================================================================ >> %LogFilePath%
echo                          BUILD SUCCESSFUL                                   >> %LogFilePath%
echo ============================================================================ >> %LogFilePath%
echo End Time: %EndDATE% >> %LogFilePath%
echo. >> %LogFilePath%
echo Deployment package is ready at: >> %LogFilePath%
echo %DestinationDirectory% >> %LogFilePath%
echo. >> %LogFilePath%

start notepad "%LogFilePath%"
start "" "%DestinationDirectory%"
exit /b 0

:CompleteWithError
for /f %%a in ('powershell -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"') do set EndDATE=%%a
echo. >> %LogFilePath%
echo ============================================================================ >> %LogFilePath%
echo                          BUILD FAILED                                       >> %LogFilePath%
echo ============================================================================ >> %LogFilePath%
echo End Time: %EndDATE% >> %LogFilePath%
echo. >> %LogFilePath%
echo Please check the errors above and try again. >> %LogFilePath%
echo. >> %LogFilePath%

start notepad "%LogFilePath%"
exit /b 1

:CreateDirectory
set tempDirectoryToCreate=%1
if not exist "%tempDirectoryToCreate%" (
    mkdir "%tempDirectoryToCreate%" 2>nul
    if "%errorlevel%"=="0" (
        echo   [CREATED] %tempDirectoryToCreate% >> %LogFilePath%
    ) else (
        echo   [ERROR] Unable to create: %tempDirectoryToCreate% >> %LogFilePath%
        echo   ErrorLevel: %errorlevel% >> %LogFilePath%
        goto CompleteWithError
    )
)
goto :eof

:DeleteConfigFile
set tempConfigFileToDelete=%1
if exist "%tempConfigFileToDelete%" (
    move "%tempConfigFileToDelete%" "%DestinationDirectory%\ConfigFiles\" >nul 2>&1
    if "%errorlevel%"=="0" (
        echo   [MOVED] %tempConfigFileToDelete% >> %LogFilePath%
    ) else (
        echo   [ERROR] Failed to move: %tempConfigFileToDelete% >> %LogFilePath%
		echo   ErrorLevel: %errorlevel% >> %LogFilePath%
		goto CompleteWithError
    )
) else (
    echo   [SKIPPED] Not found: %tempConfigFileToDelete% >> %LogFilePath%
)
goto :eof

:CopyAndLog
setlocal
set "NAME=%~1"
set "SRC=%~2"
set "DST=%~3"

echo   Copying %NAME% files... >> "%LogFilePath%"

rem Ensure source exists
if not exist "%SRC%\" (
    echo   [ERROR] Source folder missing: %SRC% >> "%LogFilePath%"
    echo. >> "%LogFilePath%"
    endlocal
    goto :eof
)

rem Perform actual copy quietly
xcopy "%SRC%\." "%DST%\" /e /y /i /q >nul 2>&1
set "XCOPY_RESULT=!errorlevel!"

if "!XCOPY_RESULT!"=="0" (
    echo   [OK] %NAME% files copied >> "%LogFilePath%"
) else (
    echo   [ERROR] Failed to copy %NAME% files (errorlevel=!XCOPY_RESULT!) >> "%LogFilePath%"
)

echo. >> "%LogFilePath%"
endlocal
goto :eof