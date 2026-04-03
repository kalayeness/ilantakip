@echo off
title İlan Takip - Baslatici
echo İlan Takip sistemi baslatiliyor...

start "Telegram Bot" cmd /k "C:\ilantakip\bot_baslat.bat"
timeout /t 3 /nobreak
start "Backend API" cmd /k "C:\ilantakip\backend_baslat.bat"

echo.
echo Her iki servis ayri pencerelerde calisiyor.
echo Kapatmak icin ilgili pencereyi kapat.
pause
