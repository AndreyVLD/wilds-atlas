@echo off
rem Update the atlas every night at 23:00, or at the time given: schedule.bat 03:00
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\schedule.ps1" %*
pause
