rem @echo off
rem for /F "tokens=2-4 delims=/- " %%A in ('date/T') do set DATE=%%C%%A%%B
for /f "skip=1" %%x in ('wmic os get localdatetime') do if not defined MyDATE set MyDATE=%%x
set year=%MyDATE:~0,4%
set month=%MyDATE:~4,2%
set day=%MyDATE:~6,2%
set datetrf=%year%%month%%day%

rem Day of week
rem Mon,	Tue,		Wed,		Thu,		Fri,		Sat,		Sun
rem 1,		2,		3,		4,		5,		6,		0
for /F "tokens=2 skip=2 delims=," %%D in ('WMIC Path Win32_LocalTime Get DayOfWeek /Format:csv') do set dow=%%D

rem space in path is allowed 
set "SourceSolutionSLNDirectory=C:\Anacle\SP\simplicity\abell.root\abell"
set "DestinationDirectory=D:\deployment\SP\UAT_%datetrf%\"
set "LogFilePath=D:\deployment\SP\UAT_%datetrf%.log"

echo ^<---- Start at %MyDATE% ----^> >> %LogFilePath%

echo SourceSolutionSLNDirectory: %SourceSolutionSLNDirectory% >> %LogFilePath%
echo DestinationDirectory: %DestinationDirectory% >> %LogFilePath%
echo LogFilePath: %LogFilePath% >> %LogFilePath%

rem call AdjustDate.bat -1 > previousDate.txt   
rem set /p PreviousDate= < previousDate.txt 
rem call AdjustDate.bat +0 > currentDate.txt   
rem set /p CurrentDate= < currentDate.txt 
rem call AdjustDate.bat +1 > nextDate.txt   
rem set /p NextDate= < nextDate.txt 
rem 
rem echo Previous Date: %PreviousDate%  >> %LogFilePath%
rem echo Current Date: %CurrentDate%  >> %LogFilePath%
rem echo Next Date: %NextDate%  >> %LogFilePath%

rem 
echo ^<---- Create folders ----^> >> %LogFilePath%

if exist "%DestinationDirectory%" (
	echo Destination Folder %DestinationDirectory% already exists    >> %LogFilePath% 2>&1
	goto CompleteWithError
)

call:CreateDirectory "%DestinationDirectory%"

rem open destination folder 
cd "%DestinationDirectory%"
start .


call:CreateDirectory "%DestinationDirectory%\webapp\"
call:CreateDirectory "%DestinationDirectory%\service\"
call:CreateDirectory "%DestinationDirectory%\TPAPI\"
rem call:CreateDirectory "%DestinationDirectory%\WebServiceToCRM\"
rem call:CreateDirectory "%DestinationDirectory%\WebServiceToEBT\"
rem call:CreateDirectory "%DestinationDirectory%\WebServiceToMSSL\"
call:CreateDirectory "%DestinationDirectory%\ConfigFiles\"

echo ^<---- Copy files ----^> >> %LogFilePath%
xcopy "%SourceSolutionSLNDirectory%\webapp\." "%DestinationDirectory%\webapp\" 	/e	/f				  >> %LogFilePath% 2>&1
xcopy "%SourceSolutionSLNDirectory%\service\bin\debug\." "%DestinationDirectory%\service\"  /e /f          >> %LogFilePath% 2>&1
xcopy "%SourceSolutionSLNDirectory%\AnacleAPI.Interface\bin\app.publish\." "%DestinationDirectory%\TPAPI\"  /e /f      >> %LogFilePath% 2>&1
rem xcopy "%SourceSolutionSLNDirectory%\WebServiceToCRM\." "%DestinationDirectory%\WebServiceToCRM\" /e /f     >> %LogFilePath% 2>&1
rem xcopy "%SourceSolutionSLNDirectory%\WebServiceToEBT\." "%DestinationDirectory%\WebServiceToEBT\"  /e /f    >> %LogFilePath% 2>&1
rem xcopy "%SourceSolutionSLNDirectory%\WebServiceToMSSL\." "%DestinationDirectory%\WebServiceToMSSL\" /e /f   >> %LogFilePath% 2>&1

rem delete config files
echo ^<---- Delete config files ----^> >> %LogFilePath%
call:DeleteConfigFile "%DestinationDirectory%\webapp\web.config"
call:DeleteConfigFile "%DestinationDirectory%\webapp\web.config.bak"
call:DeleteConfigFile "%DestinationDirectory%\webapp\website.publishproj"
call:DeleteConfigFile "%DestinationDirectory%\webapp\vwdF722.tmp"
call:DeleteConfigFile "%DestinationDirectory%\webapp\temp\."

call:DeleteConfigFile "%DestinationDirectory%\service\Service.exe.config"
call:DeleteConfigFile "%DestinationDirectory%\service\LogicLayer.dll.config"

call:DeleteConfigFile "%DestinationDirectory%\TPAPI\Web.config"

rem call:DeleteConfigFile "%DestinationDirectory%\WebServiceToCRM\WebServiceToCRM.csproj"
rem call:DeleteConfigFile "%DestinationDirectory%\WebServiceToCRM\WebServiceToCRM.csproj.user"
rem call:DeleteConfigFile "%DestinationDirectory%\WebServiceToCRM\Web.config"
rem call:DeleteConfigFile "%DestinationDirectory%\WebServiceToCRM\Web.Debug.config"
rem call:DeleteConfigFile "%DestinationDirectory%\WebServiceToCRM\Web.Release.config"

rem call:DeleteConfigFile "%DestinationDirectory%\WebServiceToEBT\WebServiceToEBT.csproj"
rem call:DeleteConfigFile "%DestinationDirectory%\WebServiceToEBT\WebServiceToEBT.csproj.user"
rem call:DeleteConfigFile "%DestinationDirectory%\WebServiceToEBT\Web.config"
rem call:DeleteConfigFile "%DestinationDirectory%\WebServiceToEBT\Web.Debug.config"
rem call:DeleteConfigFile "%DestinationDirectory%\WebServiceToEBT\Web.Release.config"

rem call:DeleteConfigFile "%DestinationDirectory%\WebServiceToMSSL\WebServiceToMSSL.csproj"
rem call:DeleteConfigFile "%DestinationDirectory%\WebServiceToMSSL\WebServiceToMSSL.csproj.user"
rem call:DeleteConfigFile "%DestinationDirectory%\WebServiceToMSSL\Web.config"
rem call:DeleteConfigFile "%DestinationDirectory%\WebServiceToMSSL\Web.Debug.config"
rem call:DeleteConfigFile "%DestinationDirectory%\WebServiceToMSSL\Web.Release.config"

:Complete
for /f "skip=1" %%x in ('wmic os get localdatetime') do if not defined EndDATE set EndDATE=%%x
echo ^<---- Complete at %EndDATE% ----^> >> %LogFilePath%
echo .>> %LogFilePath%
rem open log file 
start notepad "%LogFilePath%"

exit

:CompleteWithError
for /f "skip=1" %%x in ('wmic os get localdatetime') do if not defined EndDATE set EndDATE=%%x
echo ^<---- Complete With Error at %EndDATE% ----^> >> %LogFilePath%
echo .>> %LogFilePath%
rem open log file 
start notepad "%LogFilePath%"
cd %DestinationDirectory%
start .

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



