@echo off
rem OSINT-REILLY launcher: no arguments = window, otherwise console commands
rem   reilly                      window
rem   reilly profile war_ua       console run of a profile
cd /d "%~dp0"
if "%~1"=="" (
    start "" ".venv\Scripts\pythonw.exe" main.py
) else (
    chcp 65001 >nul
    set PYTHONIOENCODING=utf-8
    ".venv\Scripts\python.exe" main.py %*
)
