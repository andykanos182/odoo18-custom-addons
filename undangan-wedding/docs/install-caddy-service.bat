@echo off
REM ==========================================================
REM Install Caddy sebagai Windows Service
REM ==========================================================
REM Jalankan di mesin SERVER (192.168.1.47), BUKAN di laptop dev.
REM Run as Administrator.
REM
REM Prasyarat:
REM   1. caddy.exe sudah ada di C:\Caddy\
REM   2. Caddyfile sudah ada di C:\Caddy\
REM   3. nssm sudah ter-install (winget install nssm)
REM ==========================================================

echo.
echo === Installing Caddy as Windows Service ===
echo.

REM Verify nssm available
where nssm >nul 2>nul
if errorlevel 1 (
  echo ERROR: nssm tidak ditemukan di PATH.
  echo Install dulu: winget install nssm
  echo Atau download: https://nssm.cc/download
  pause
  exit /b 1
)

REM Verify caddy.exe exists
if not exist "C:\Caddy\caddy.exe" (
  echo ERROR: C:\Caddy\caddy.exe tidak ditemukan.
  echo Download Caddy dari: https://caddyserver.com/download
  echo Lalu pindahkan ke C:\Caddy\caddy.exe
  pause
  exit /b 1
)

REM Verify Caddyfile exists
if not exist "C:\Caddy\Caddyfile" (
  echo ERROR: C:\Caddy\Caddyfile tidak ditemukan.
  echo Copy file Caddyfile dari folder docs project.
  pause
  exit /b 1
)

REM Stop & remove existing service if any
sc query Caddy >nul 2>nul
if not errorlevel 1 (
  echo Service Caddy sudah ada. Menghapus dulu...
  nssm stop Caddy
  nssm remove Caddy confirm
)

REM Install service
echo Installing service...
nssm install Caddy "C:\Caddy\caddy.exe" "run --config C:\Caddy\Caddyfile"
nssm set Caddy AppDirectory "C:\Caddy"
nssm set Caddy DisplayName "Caddy Web Server (undangan.gopokaja.com)"
nssm set Caddy Description "Static file server untuk undangan pernikahan"
nssm set Caddy Start SERVICE_AUTO_START

REM Setup log redirection
if not exist "C:\Caddy\logs" mkdir "C:\Caddy\logs"
nssm set Caddy AppStdout "C:\Caddy\logs\stdout.log"
nssm set Caddy AppStderr "C:\Caddy\logs\stderr.log"
nssm set Caddy AppRotateFiles 1
nssm set Caddy AppRotateBytes 10485760

REM Start service
echo Starting service...
nssm start Caddy

REM Wait & verify
timeout /t 3 /nobreak >nul
sc query Caddy

echo.
echo === Done! ===
echo Caddy sekarang jalan otomatis saat Windows startup.
echo Test di browser: http://localhost:8080
echo.
pause
