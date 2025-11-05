echo Starting backup process...
echo.

call backup.bat "D:\MyBill_v10" || goto :error
echo.

call backup.bat "D:\MyBill_v10-SP" || goto :error
echo.

echo All backups completed!
pause
exit

:error
echo.
echo ERROR: Backup process terminated due to failure.
pause
exit /b 1