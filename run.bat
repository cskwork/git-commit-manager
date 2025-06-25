@echo off
setlocal enabledelayedexpansion

echo =====================================
echo Git Commit Manager - Complete Setup
echo =====================================
echo.

REM Check if already installed in the virtual environment
if exist "%~dp0venv\Scripts\gcm.exe" (
    call venv\Scripts\activate.bat
    echo [INFO] Git Commit Manager is already installed in the virtual environment.
    goto :run_options
)

REM Warn if a global installation exists (will not be used)
where gcm >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] A global installation of Git Commit Manager is detected.
    echo Proceeding with setup in the virtual environment.
)

REM Python version check
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed.
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% detected

REM pip check
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip is not installed.
    echo Please install pip or reinstall Python.
    pause
    exit /b 1
)

REM Virtual environment setup
echo.
echo =====================================
echo Virtual Environment Setup
echo =====================================
if exist venv (
    echo [INFO] Virtual environment already exists.
    set /p USE_EXISTING="Use existing virtual environment? (Y/n): "
    if /i "!USE_EXISTING!"=="n" (
        echo Removing existing virtual environment...
        rmdir /s /q venv
        goto :create_venv
    )
    call venv\Scripts\activate.bat
    echo [OK] Existing virtual environment activated
    goto :install_deps
) else (
    :create_venv
    set /p CREATE_VENV="Create virtual environment? (Y/n): "
    if /i "!CREATE_VENV!"=="n" (
        echo [WARNING] Running without virtual environment.
        goto :install_deps
    )
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    call venv\Scripts\activate.bat
    echo [OK] Virtual environment created and activated
)

:install_deps
REM Install dependencies
echo.
echo =====================================
echo Installing Dependencies
echo =====================================
echo Installing required packages...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    echo Make sure requirements.txt exists and try again.
    pause
    exit /b 1
)

REM Install package in development mode
echo.
echo Installing Git Commit Manager...
pip install -e .
if errorlevel 1 (
    echo [ERROR] Failed to install Git Commit Manager.
    pause
    exit /b 1
)

REM Ollama Setup (Optional)
echo.
echo =====================================
echo Ollama Setup (Optional)
echo =====================================
where ollama >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Ollama is not installed.
    echo           Install from: https://ollama.ai
    echo           Or configure OpenRouter/Gemini API keys instead.
    set /p INSTALL_OLLAMA="Would you like to open Ollama download page? (y/N): "
    if /i "!INSTALL_OLLAMA!"=="y" (
        start https://ollama.ai
    )
)
if not errorlevel 1 (
    echo [OK] Ollama is installed.
    echo.
    echo Current Ollama models:
    ollama list

    REM Check for recommended model
    ollama list | findstr "gemma3:1b" >nul
    if errorlevel 1 (
        echo.
        set /p INSTALL_MODEL="Install recommended model gemma3:1b (~1GB)? (y/N): "
        if /i "!INSTALL_MODEL!"=="y" (
            echo Downloading gemma3:1b model (this may take a few minutes)...
            ollama pull gemma3:1b
            if errorlevel 1 (
                echo [WARNING] Failed to download model. You can try again later.
            )
        )
    )
    if not errorlevel 1 (
        echo [OK] Recommended model gemma3:1b is already installed.
    )
)

REM Environment configuration
echo.
echo =====================================
echo Environment Configuration
echo =====================================
if not exist .env (
    echo Creating .env configuration file...
    copy env.example .env >nul
    echo [OK] .env file created from template.
    echo [INFO] Edit .env file to add your API keys if using OpenRouter or Gemini.
) else (
    echo [INFO] .env file already exists.
)

echo.
echo =====================================
echo Setup Complete!
echo =====================================
echo.
echo Available commands:
echo   gcm watch    - Real-time file monitoring with commit message generation
echo   gcm analyze  - Analyze current changes once
echo   gcm review   - Perform code review on changes
echo   gcm config   - Show configuration guide
echo.
echo Note: Code review is now disabled by default.
echo      You'll be prompted whether to run it during monitoring.
echo.

:run_options
REM Run options
set /p RUN_CHOICE="What would you like to do? (w)atch/(a)nalyze/(r)eview/(q)uit: "

if /i "%RUN_CHOICE%"=="w" goto :run_watch
if /i "%RUN_CHOICE%"=="watch" goto :run_watch
if /i "%RUN_CHOICE%"=="a" goto :run_analyze
if /i "%RUN_CHOICE%"=="analyze" goto :run_analyze
if /i "%RUN_CHOICE%"=="r" goto :run_review
if /i "%RUN_CHOICE%"=="review" goto :run_review
if /i "%RUN_CHOICE%"=="q" goto :end
if /i "%RUN_CHOICE%"=="quit" goto :end

goto :run_watch

:run_watch
echo.
echo Starting real-time monitoring...
echo Press Ctrl+C to stop monitoring.
echo.
gcm watch
goto :end

:run_analyze
echo.
echo Analyzing current changes...
gcm analyze
echo.
goto :run_options

:run_review
echo.
echo Running code review...
gcm review
echo.
goto :run_options

:end
echo.
echo Thank you for using Git Commit Manager!
pause