@echo off
title İlan Takip - Telegram Bot
cd /d C:\ilantakip

:loop
echo [%date% %time%] Bot baslatiliyor...
python bot.py
echo [%date% %time%] Bot durdu. 5 saniye sonra yeniden baslatiliyor...
timeout /t 5 /nobreak
goto loop
