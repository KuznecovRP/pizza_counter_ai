@echo off
chcp 65001
title Pizza Counter App

:: Проверка, установлен ли Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ОШИБКА] Python не найден. Пожалуйста, установите Python с сайта:
    echo https://www.python.org/downloads/
    pause
    exit /b
)

:: Установка зависимостей
echo Установка необходимых библиотек...
python -m pip install --upgrade pip
python -m pip install flask ultralytics opencv-python numpy reportlab openpyxl

:: Открытие браузера
start http://127.0.0.1:5000

:: Запуск Flask-приложения
echo Запуск приложения...
python app.py

pause
