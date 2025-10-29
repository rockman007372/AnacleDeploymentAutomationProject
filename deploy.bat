@echo off

:: Step 1: Back up the folders
echo Starting backup process...
echo.

call backup.bat "D:\MyBill_v10" || goto :error
echo.

call backup.bat "D:\MyBill_v10-SP" || goto :error
echo.

echo All backups completed!

:: Step 2: Stop the services
call stop_services.bat || goto :error

:: Step 3: Extract deployment file in respective folders

:: Step 4: Enable services again
call enable_services.bat || goto :error

:error
echo.
echo ERROR: Backup process terminated due to failure.
pause
exit /b 1