@echo off
cd /d "C:\Users\DELL-3501\Documents\sistema-wayuu\backend"
call ".venv\Scripts\activate.bat"
python manage.py runserver 0.0.0.0:8000 --noreload
