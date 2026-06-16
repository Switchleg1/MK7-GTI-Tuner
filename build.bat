@echo off
setlocal

cd /d "%~dp0"

set "APP_NAME=MK7-GTI-Tuner"
set "ENTRY=mk7_gti_tuner.py"
set "PY=python"

%PY% --version >nul 2>nul
if errorlevel 1 set "PY=python"

if not exist "%ENTRY%" (
    echo ERROR: Missing %ENTRY%
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

%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --name "%APP_NAME%" "%ENTRY%"

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
