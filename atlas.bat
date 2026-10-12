@echo off
rem Render the worlds and publish the atlas. Extra arguments go to atlas.py (e.g. --full).
cd /d "%~dp0"
python tools\atlas.py publish %*
pause
