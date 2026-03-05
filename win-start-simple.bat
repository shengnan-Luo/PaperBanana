@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

:: ============================================================
::  PaperBanana Windows Startup Script
:: ============================================================

:: --- Config ---
set "PYTHON_MIN_VER=3.10"
set "VENV_DIR=.venv"
set "PORT=8501"
set "APP_NAME=PaperBanana"

:: --- Enter project directory ---
cd /d "%~dp0"

echo.
echo ==========================================
echo   %APP_NAME% Startup
echo ==========================================
echo.

:: ============================================================
:: Step 1: Find Python
:: ============================================================
set "PYTHON_CMD="

:: Check system Python
call :try_system_python python  && goto :found_python
call :try_system_python python3 && goto :found_python
call :try_system_python py      && goto :found_python

:: Try winget install
where winget >nul 2>&1 || goto :skip_winget
echo   [..] Installing Python via winget...
winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements >nul 2>&1 || goto :skip_winget
set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
call :try_system_python python && goto :found_python
:skip_winget

:: Manual installation required
echo.
echo   [!!] Python 3.10+ not found. Please install manually:
echo.
echo       Method 1: Microsoft Store - search "Python 3.12"
echo       Method 2: Visit https://www.python.org/downloads/
echo                 Check "Add Python to PATH" during installation
echo.
pause
exit /b 1

:found_python

:: ============================================================
:: Step 2: Create virtual environment
:: ============================================================
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo   [..] Creating Python virtual environment...
    "%PYTHON_CMD%" -m venv "%VENV_DIR%"
    if !errorlevel! neq 0 (
        echo   [!!] Virtual environment creation failed
        pause
        exit /b 1
    )
    echo   [OK] Virtual environment created
) else (
    echo   [OK] Virtual environment exists
)

set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "VENV_PIP=%VENV_DIR%\Scripts\pip.exe"

:: ============================================================
:: Step 3: Install dependencies
:: ============================================================
echo   [..] Installing Python dependencies...
"%VENV_PIP%" install -r requirements.txt --quiet --disable-pip-version-check 2>nul
echo   [OK] Dependencies ready

:: ============================================================
:: Step 4: Create data directories
:: ============================================================
if not exist "data\PaperBananaBench\diagram" mkdir "data\PaperBananaBench\diagram"
if not exist "data\PaperBananaBench\plot" mkdir "data\PaperBananaBench\plot"
if not exist "data\PaperBananaBench\diagram\ref.json" (
    echo [] > "data\PaperBananaBench\diagram\ref.json"
)
if not exist "data\PaperBananaBench\plot\ref.json" (
    echo [] > "data\PaperBananaBench\plot\ref.json"
)

:: ============================================================
:: Step 5: Clean port and start application
:: ============================================================
echo   [..] Checking port %PORT%...
for /f "tokens=5" %%A in ('netstat -ano 2^>nul ^| findstr ":%PORT% " ^| findstr "LISTENING"') do (
    echo   [!!] Port %PORT% occupied ^(PID: %%A^), cleaning...
    taskkill /F /PID %%A >nul 2>&1
    timeout /t 1 /nobreak >nul
    echo   [OK] Port released
)

echo.
echo ==========================================
echo   Starting %APP_NAME%
echo   Browser will open http://localhost:%PORT%
echo   Close this window to stop service
echo ==========================================
echo.

:: Delayed browser opening
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://localhost:%PORT%"

:: Start Streamlit
"%VENV_DIR%\Scripts\streamlit.exe" run demo.py --server.port %PORT% --server.address 0.0.0.0 --server.headless true

pause
exit /b 0

:: ============================================================
:: Subroutine: Check Python version >= 3.10
:: ============================================================
:check_python_ver
%~1 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" 2>nul
exit /b !errorlevel!

:: ============================================================
:: Subroutine: Try system Python
:: ============================================================
:try_system_python
where %~1 >nul 2>&1 || exit /b 1
%~1 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" 2>nul || exit /b 1
set "PYTHON_CMD=%~1"
for /f "delims=" %%V in ('%~1 --version 2^>^&1') do echo   [OK] Found system %%V
exit /b 0
