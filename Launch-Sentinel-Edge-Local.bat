@echo off
title Sentinel Edge - Local Source
echo.
echo ========================================
echo   Sentinel Edge - Local Source
echo ========================================
echo.
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Launch-Sentinel-Edge-Local.ps1" %*
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" (
  echo.
  echo Sentinel Edge local launcher exited with code %EXITCODE%.
  pause
)
exit /b %EXITCODE%
