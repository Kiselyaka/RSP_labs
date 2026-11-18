@echo off
if "%~1"=="" (
    echo Usage: restore-db.cmd backups\survey_tool-TIMESTAMP.dump
    exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\restore-db.ps1" %*
exit /b %ERRORLEVEL%
