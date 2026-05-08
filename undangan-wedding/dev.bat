@echo off
REM ==========================================================
REM Dev server launcher for undangan-wedding
REM ==========================================================
REM Sets PATH to include Node.js (in case it's not in user PATH)
REM then runs the Next.js dev server.
REM
REM Usage: double-click this file, or run from cmd/powershell:
REM   .\dev.bat
REM
REM Press Ctrl+C to stop the server.
REM ==========================================================

set "PATH=C:\Program Files\nodejs;%PATH%"
cd /d "%~dp0"
echo.
echo === Starting Next.js dev server ===
echo === Open http://localhost:3000 ===
echo.
call npm run dev
pause
