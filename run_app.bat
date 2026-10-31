@echo off
rem Starts the performance scheduling page. Double-click this file.
rem It must stay in the project folder: the page reads .streamlit\config.toml from there
rem (decision D53). Close this window to stop the page.

cd /d "%~dp0"
title Performance scheduling

if not exist ".venv\Scripts\python.exe" (
    echo The page is not set up on this computer yet.
    echo Ask whoever set it up to follow "Setup" in README.md, then try again.
    echo.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -c "import streamlit, ortools, performance_scheduling" >nul 2>&1
if errorlevel 1 (
    echo The page is missing something it needs.
    echo Ask whoever set it up to run this command in this folder:
    echo.
    echo     .venv\Scripts\python -m pip install -e ".[ui]"
    echo.
    pause
    exit /b 1
)

echo Starting the page. Your browser will open in a few seconds.
echo Keep this window open while you use the page. Close it to stop.
echo.
".venv\Scripts\python.exe" -m streamlit run src\performance_scheduling\app.py
if errorlevel 1 (
    echo.
    echo The page stopped with an error. Please tell whoever set it up.
    pause
)
