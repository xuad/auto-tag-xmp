@echo off
setlocal

set "SCRIPT_DIR=X:\path-to-auto-tag-xmp"
set "PYTHON=%SCRIPT_DIR%=python.exe"
set "SCRIPT=%SCRIPT_DIR%\tag_photos.py"

if not exist "%PYTHON%" (
    echo Python-Umgebung nicht gefunden: "%PYTHON%"
    pause
    exit /b 1
)

if not exist "%SCRIPT%" (
    echo Tagging-Skript nicht gefunden: "%SCRIPT%"
    pause
    exit /b 1
)

pushd "%~dp0"
if errorlevel 1 (
    echo Kann den Ordner nicht oeffnen: "%~dp0"
    pause
    exit /b 1
)

"%PYTHON%" "%SCRIPT%" "."
set "EXIT_CODE=%ERRORLEVEL%"
popd

echo.
pause
exit /b %EXIT_CODE%
