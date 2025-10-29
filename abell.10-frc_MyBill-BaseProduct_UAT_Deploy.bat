rem @echo off
rem Get start date/time
for /f %%a in ('powershell -Command "Get-Date -Format 'yyyyMMdd'"') do set datetrf=%%a

rem 1. Define source and destination directories. Space in path is allowed. 
set "SolutionDirectory=C:\Anacle\SP\simplicity\abell.root\abell"
set "DestinationDirectory=D:\deployment\SP\UAT_%datetrf%\"
set "LogFilePath=D:\deployment\SP\UAT_%datetrf%.log"

for /f %%a in ('powershell -Command "Get-Date -Format 'yyyyMMddHHmmss'"') do set MyDATE=%%a
echo ^<---- Start at %MyDATE% ----^> >> %LogFilePath%

echo SolutionDirectory: %SolutionDirectory% >> %LogFilePath%
echo DestinationDirectory: %DestinationDirectory% >> %LogFilePath%
echo LogFilePath: %LogFilePath% >> %LogFilePath%

rem 2. Create destination directory structure.
echo ^<---- Create folders ----^> >> %LogFilePath%

if exist "%DestinationDirectory%" (
	echo Destination Folder %DestinationDirectory% already exists    >> %LogFilePath% 2>&1
	goto CompleteWithError
)

call:CreateDirectory "%DestinationDirectory%"

rem Open destination folder and create subfolders
cd "%DestinationDirectory%"

call:CreateDirectory "%DestinationDirectory%\webapp\"
call:CreateDirectory "%DestinationDirectory%\service\"
call:CreateDirectory "%DestinationDirectory%\TPAPI\"
call:CreateDirectory "%DestinationDirectory%\ConfigFiles\"

rem 3. Copy files from source to destination.
echo ^<---- Copy files ----^> >> %LogFilePath%
xcopy "%SolutionDirectory%\webapp\." "%DestinationDirectory%\webapp\" 	/e	/f				  					>> %LogFilePath% 2>&1
xcopy "%SolutionDirectory%\service\bin\debug\." "%DestinationDirectory%\service\"  /e /f          				>> %LogFilePath% 2>&1
xcopy "%SolutionDirectory%\AnacleAPI.Interface\bin\app.publish\." "%DestinationDirectory%\TPAPI\"  /e /f      	>> %LogFilePath% 2>&1

rem 4. Delete config files (Move to ConfigFiles folder).
echo ^<---- Delete config files ----^> >> %LogFilePath%
call:DeleteConfigFile "%DestinationDirectory%\webapp\web.config"
call:DeleteConfigFile "%DestinationDirectory%\webapp\web.config.bak"
call:DeleteConfigFile "%DestinationDirectory%\webapp\website.publishproj"
call:DeleteConfigFile "%DestinationDirectory%\webapp\vwdF722.tmp"
call:DeleteConfigFile "%DestinationDirectory%\webapp\temp\."

call:DeleteConfigFile "%DestinationDirectory%\service\Service.exe.config"
call:DeleteConfigFile "%DestinationDirectory%\service\LogicLayer.dll.config"

call:DeleteConfigFile "%DestinationDirectory%\TPAPI\Web.config"

rem 5. Complete
:Complete
for /f %%a in ('powershell -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"') do set EndDATE=%%a
echo ^<---- Complete at %EndDATE% ----^> >> %LogFilePath%
echo .>> %LogFilePath%
start notepad "%LogFilePath%"
start "" "%DestinationDirectory%"
exit


:CompleteWithError
for /f %%a in ('powershell -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"') do set EndDATE=%%a
echo ^<---- Complete With Error at %EndDATE% ----^> >> %LogFilePath%
echo .>> %LogFilePath%
start notepad "%LogFilePath%"
exit

:CreateDirectory
set tempDirectoryToCreate=%1
if not exist "%tempDirectoryToCreate%" (
	mkdir "%tempDirectoryToCreate%"
	if "%errorlevel%"=="0" (
		echo Destionation Folder %tempDirectoryToCreate% is created    >> %LogFilePath% 2>&1
	) else (
		echo ErrorLevel: %errorlevel%	   >> %LogFilePath% 2>&1
		echo Destionation Folder %tempDirectoryToCreate% is unable to be created    >> %LogFilePath% 2>&1
		goto CompleteWithError
	)
)
goto :eof

:DeleteConfigFile
set tempConfigFileToDelete=%1
if exist "%tempConfigFileToDelete%" (
	move "%tempConfigFileToDelete%" "%DestinationDirectory%\ConfigFiles\"	>> %LogFilePath% 2>&1
	echo %tempConfigFileToDelete% is moved 		>> %LogFilePath% 2>&1
) else (
	echo %tempConfigFileToDelete% is not found 	>> %LogFilePath% 2>&1
)
goto :eof
