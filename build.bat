@echo off
setlocal

cd /d "%~dp0"

set "APP_NAME=MK7-GTI-Tuner"
set "ENTRY=mk7_gti_tuner.py"
set "PY="

where py >nul 2>nul
if not errorlevel 1 (
    py -3 -c "import sys" >nul 2>nul
    if not errorlevel 1 set "PY=py -3"
)

if not defined PY (
    where python >nul 2>nul
    if not errorlevel 1 set "PY=python"
)

if not defined PY (
    echo ERROR: Python 3 was not found.
    echo Install Python from python.org and check "Add python.exe to PATH".
    pause
    exit /b 1
)

if not exist "%ENTRY%" (
    echo ERROR: Missing %ENTRY%
    pause
    exit /b 1
)

%PY% -m pip --version >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python was found, but pip is not available.
    echo Install Python from python.org and check "Add python.exe to PATH".
    pause
    exit /b 1
)

echo Building %APP_NAME%.exe...
echo.

%PY% -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (
    echo.
    echo Dependency install failed.
    pause
    exit /b 1
)

%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --collect-all panda3d --collect-all direct --name "%APP_NAME%" "%ENTRY%"

if errorlevel 1 (
    echo.
    echo Build failed.
    pause
    exit /b 1
)

echo.
echo Done: "%CD%\dist\%APP_NAME%.exe"
echo.
pause
