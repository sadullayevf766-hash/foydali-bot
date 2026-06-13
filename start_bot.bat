@echo off
REM Foydali Bot - qo'lda ishga tushirish (avtomatik qayta yonadi)
cd /d D:\foydali-bot
:loop
echo [%date% %time%] Bot ishga tushmoqda...
venv\Scripts\python.exe bot.py
echo [%date% %time%] Bot to'xtadi. 5 soniyada qayta ishga tushadi (to'xtatish: oynani yoping)
timeout /t 5 /nobreak >nul
goto loop
