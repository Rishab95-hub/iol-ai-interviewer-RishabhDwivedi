@echo off
REM Stop Podman containers for IOL AI Interviewer

echo Stopping IOL AI Interviewer containers...
echo.

podman stop iol-postgres iol-redis 2>nul

if %ERRORLEVEL% EQU 0 (
    echo [OK] Containers stopped successfully
) else (
    echo [INFO] Containers were not running or already stopped
)

echo.
echo To start containers again, run bootstrap.ps1 or use:
echo   podman start iol-postgres iol-redis
echo.
pause
