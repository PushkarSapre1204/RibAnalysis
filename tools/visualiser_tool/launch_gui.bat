@echo off
REM Exploratory Data Visualiser GUI Launcher
REM This script activates the virtual environment and launches the visualiser GUI

cd /d "%~dp0..\.."
call .venv\Scripts\activate.bat

python tools\visualiser_tool\visualiser_gui.py

pause
