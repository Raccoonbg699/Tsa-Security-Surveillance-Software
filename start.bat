@echo off
setlocal

:: --- Главният Python скрипт ---
set PYTHON_SCRIPT=main.py

:: --- Списък с необходимите библиотеки ---
set "LIBRARIES=PySide6 opencv-python onvif-zeep PySide6-Addons"

:: Проверка дали Python е инсталиран и достъпен
python --version >nul 2>nul
if errorlevel 1 (
    echo.
    echo =================================================================
    echo  ERROR: Python not found.
    echo  Please make sure Python is installed and added to your system's PATH.
    echo =================================================================
    echo.
    pause
    exit /b
)

echo Checking for required Python libraries...
echo.

:check_libs
for %%L in (%LIBRARIES%) do (
    python -c "import %%L" >nul 2>nul
    if errorlevel 1 (
        echo Library %%L is missing. Installing...
        pip install %%L
        if errorlevel 1 (
            echo.
            echo =================================================================
            echo  ERROR: Failed to install %%L.
            echo  Please try to install it manually with 'pip install %%L'
            echo =================================================================
            echo.
            pause
            exit /b
        )
    )
)

echo All libraries are installed. Starting the application...
echo.

:: --- Стартираме Python скрипта без конзолен прозорец ---
start "" pythonw "%PYTHON_SCRIPT%"

exit