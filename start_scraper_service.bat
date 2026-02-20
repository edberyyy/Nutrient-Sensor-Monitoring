@echo off
REM Start Data Scraper in background
cd /d "C:\Users\Edber John\Programming\Web Scrap"
call venv\Scripts\activate.bat
python monitor.py --watch
pause
