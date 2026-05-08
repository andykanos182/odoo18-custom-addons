@echo off
REM ==========================================================
REM Production build for undangan-wedding
REM ==========================================================
REM Outputs static files to ./out directory.
REM Copy ./out contents to network share for deployment.
REM ==========================================================

set "PATH=C:\Program Files\nodejs;%PATH%"
cd /d "%~dp0"
echo.
echo === Building production bundle ===
echo.
call npm run build
if errorlevel 1 (
  echo.
  echo === BUILD FAILED ===
  pause
  exit /b 1
)
echo.
echo === Build complete ===
echo === Static files: %~dp0out ===
echo.
pause
