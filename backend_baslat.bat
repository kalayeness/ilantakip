@echo off
title İlan Takip - Backend API
cd /d C:\ilantakip

:loop
echo [%date% %time%] Backend baslatiliyor...
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
echo [%date% %time%] Backend durdu. 5 saniye sonra yeniden baslatiliyor...
timeout /t 5 /nobreak
goto loop
