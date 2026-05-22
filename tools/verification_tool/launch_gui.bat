@echo off
setlocal enabledelayedexpansion

REM Navigate to root directory
cd /d "%~dp0..\.."

REM Activate virtual environment
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo Error: Failed to activate virtual environment
    pause
    exit /b 1
)

REM Set Python path to include the root directory for ribs_core module
set PYTHONPATH=%cd%;%PYTHONPATH%

REM Run the verification GUI from the root directory
python tools\verification_tool\verification_gui.py
if errorlevel 1 (
    echo Error: Failed to run verification GUI
    pause
    exit /b 1
)
