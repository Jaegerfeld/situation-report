@echo off
set "D=%~dp0"
if exist "%D%.venv\Scripts\python.exe" (
    "%D%.venv\Scripts\python.exe" -m launcher
) else (
    python -m launcher
)
if %ERRORLEVEL% neq 0 (
    echo.
    echo Fehler beim Starten. Bitte den roten Text oben notieren.
    pause
)
