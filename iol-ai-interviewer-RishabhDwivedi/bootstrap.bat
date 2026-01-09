@echo off
REM IOL AI Interviewer - Bootstrap Launcher
REM This script runs the PowerShell bootstrap script

echo ========================================
echo IOL AI Interviewer - Bootstrap Setup
echo ========================================
echo.
echo This will set up everything you need:
echo   - Python virtual environment
echo   - All dependencies
echo   - Database initialization
echo   - Startup scripts
echo.
echo This may take 5-10 minutes depending on your internet connection.
echo.
pause

powershell -ExecutionPolicy Bypass -File "%~dp0bootstrap.ps1"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Bootstrap completed successfully!
    echo ========================================
    echo.
    echo You can now start the application with:
    echo   start-all.bat
    echo.
) else (
    echo.
    echo ========================================
    echo Bootstrap failed!
    echo ========================================
    echo.
    echo Please check the error messages above.
    echo.
)

pause
