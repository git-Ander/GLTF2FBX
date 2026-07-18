@echo off
cd /d "%~dp0"

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. https://www.python.org/downloads/
    pause & exit /b 1
)

python -c "import customtkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing customtkinter...
    pip install customtkinter -q
)

python -c "import tkinterdnd2" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing tkinterdnd2...
    pip install tkinterdnd2 -q
)

start "" pythonw "%~dp0gui.py"
exit