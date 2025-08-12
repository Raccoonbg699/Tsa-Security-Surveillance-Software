@echo off
setlocal

rem --- ПРОМЯНА 1: Задаваме глобална кодова таблица за Python ---
set PYTHONIOENCODING=UTF-8

rem --- ПРОМЯНА 2: Сменяме кодовата таблица на конзолата на UTF-8 ---
chcp 65001 >nul

echo ===============================================================
echo  TSA-Security Startup Script
echo  (No requirements.txt needed)
echo ===============================================================
echo.
REM --- Търсене на Python ---
echo Searching for Python installation...
for /f "delims=" %%p in ('where python.exe') do (
    set "PYTHON_PATH=%%p"
    goto :found_python
)

echo.
echo ERROR: Python installation not found in your system's PATH.
echo Please install Python from python.org and ensure it is added to the PATH.
pause
exit /b 1

:found_python
echo Found Python at: %PYTHON_PATH%
echo.

REM --- Инсталиране на зависимости директно ---
echo Checking and installing required libraries...
echo.
echo Installing/Verifying PySide6...
rem --- ПРОМЯНА 3: Използваме --progress-bar off, за да избегнем проблемния символ ---
"%PYTHON_PATH%" -m pip install PySide6 --progress-bar off
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to install PySide6.
    echo Please check your internet connection and try again.
    pause
    exit /b 1
)

echo.
echo Installing/Verifying OpenCV...
rem --- ПРОМЯНА 4: И тук изключваме progress bar-a за всеки случай ---
"%PYTHON_PATH%" -m pip install opencv-python --progress-bar off
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to install opencv-python.
    echo Please check your internet connection and try again.
    pause
    exit /b 1
)

echo.
echo All libraries are ready.
echo.

REM --- Стартиране на приложението без конзола ---
echo Starting TSA-Security application...
echo.
REM --- ПРОМЯНА 1: Създаваме пътя до pythonw.exe ---
set "PYTHONW_PATH=%PYTHON_PATH:python.exe=pythonw.exe%"

REM --- ПРОМЯНА 2: Стартираме с pythonw.exe, за да скрием конзолата ---
start "" "%PYTHONW_PATH%" main.py

endlocal
exit /b 0