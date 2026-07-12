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

start "" pythonw "%~dp0gui.py"
exit