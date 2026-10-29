@echo off
setlocal
cd /d "C:\Users\DELL-3501\Documents\sistema-wayuu"

REM Inicia el sitio principal de Wayuuwaa en segundo plano.
start "Wayuuwaa Django" /b "C:\Users\DELL-3501\Documents\sistema-wayuu\backend\.venv\Scripts\python.exe" "C:\Users\DELL-3501\Documents\sistema-wayuu\backend\manage.py" runserver 127.0.0.1:8000

REM Da tiempo a Django y MySQL para responder antes de abrir el navegador.
timeout /t 5 /nobreak >nul
start "" "http://127.0.0.1:8000/"
endlocal
