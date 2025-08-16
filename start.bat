@echo off
setlocal

rem --- Задаваме кодова таблица UTF-8 за правилно показване на кирилица ---
set PYTHONIOENCODING=UTF-8
chcp 65001 >nul

rem --- Сменяме текущата директория към тази на скрипта ---
cd /d "%~dp0"

echo ===============================================================
echo  TSA-Security Startup Script
echo ===============================================================
echo.

rem --- Търсене на Python ---
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

rem --- Инсталиране на зависимости ---
echo Checking and installing required libraries...
echo.

echo Installing/Verifying PySide6...
"%PYTHON_PATH%" -m pip install PySide6 --progress-bar off --user >nul
if %errorlevel% neq 0 ( echo ERROR: Failed to install PySide6. & pause & exit /b 1 )

echo.
echo Installing/Verifying OpenCV...
"%PYTHON_PATH%" -m pip install opencv-python --progress-bar off --user >nul
if %errorlevel% neq 0 ( echo ERROR: Failed to install opencv-python. & pause & exit /b 1 )

echo.
echo Installing/Verifying Requests...
"%PYTHON_PATH%" -m pip install requests --progress-bar off --user >nul
if %errorlevel% neq 0 ( echo ERROR: Failed to install requests. & pause & exit /b 1 )

echo.
echo Installing/Verifying NumPy...
"%PYTHON_PATH%" -m pip install numpy --progress-bar off --user >nul
if %errorlevel% neq 0 ( echo ERROR: Failed to install numpy. & pause & exit /b 1 )


echo.
echo All libraries are ready.
echo.

rem --- Стартиране на приложението без конзола (по надежден начин) ---
echo Starting TSA-Security application...
echo.

start "TSA-Security" /B "%PYTHON_PATH%" main.py

endlocal
exit /b 0