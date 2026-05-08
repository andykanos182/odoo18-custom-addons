@echo off
REM ==========================================================
REM Deploy to network share at 192.168.1.47
REM ==========================================================
REM Builds, then mirrors ./out to the network share.
REM Run AFTER cloudflared + serve are set up on the home server.
REM ==========================================================

set "PATH=C:\Program Files\nodejs;%PATH%"
cd /d "%~dp0"

echo.
echo === Step 1: Building production bundle ===
echo.
call npm run build
if errorlevel 1 (
  echo BUILD FAILED. Aborting deploy.
  pause
  exit /b 1
)

echo.
echo === Step 2: Copying to \\192.168.1.47\GeForce D\MyServer\Undangan\ ===
echo.

set "DEST=\\192.168.1.47\GeForce D\MyServer\Undangan\out"

REM Create destination if it doesn't exist
if not exist "%DEST%" (
  mkdir "%DEST%"
)

REM Mirror local ./out to network share
robocopy ".\out" "%DEST%" /MIR /NFL /NDL /NJH /NJS /R:3 /W:5

REM robocopy exit codes < 8 are success
if errorlevel 8 (
  echo.
  echo === DEPLOY FAILED ===
  pause
  exit /b 1
)

echo.
echo === Deploy complete ===
echo === Visit https://undangan.gopokaja.com ===
echo.
pause
