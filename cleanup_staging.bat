@echo off
REM Cleanup batch file for RibAnalysis Staging directory
REM Removes all clean_data.csv, clean_data_log.csv, and clean_data_master.csv files

setlocal enabledelayedexpansion

REM Get the script directory
cd /d "%~dp0"

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Run the cleanup script
python cleanup_staging.py

REM Pause so user can see output
pause
