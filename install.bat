@echo off
setlocal enabledelayedexpansion

echo =====================================
echo Git Commit Manager Installation
echo =====================================
echo.

REM Python 버전 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed.
    echo Please install Python 3.8 or higher.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% detected

REM pip 확인
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip is not installed.
    echo Please install pip.
    pause
    exit /b 1
)

REM 가상환경 생성 옵션
echo.
set /p CREATE_VENV="Create virtual environment? (y/N): "
if /i "%CREATE_VENV%"=="y" (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [OK] Virtual environment activated
)

REM 의존성 설치
echo.
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

REM 패키지 설치
echo.
echo Installing Git Commit Manager...
pip install -e .
if errorlevel 1 (
    echo [ERROR] Failed to install Git Commit Manager.
    pause
    exit /b 1
)

REM Ollama 확인
echo.
where ollama >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Ollama is not installed.
    echo           Install from: https://ollama.ai
    echo           Or use OpenRouter/Gemini instead.
) else (
    echo [OK] Ollama is installed.
    echo.
    echo Installed Ollama models:
    ollama list
    
    REM gemma3:1b 모델 확인
    ollama list | findstr "gemma3:1b" >nul
    if errorlevel 1 (
        echo.
        set /p INSTALL_MODEL="Install recommended model gemma3:1b? (y/N): "
        if /i "!INSTALL_MODEL!"=="y" (
            echo Downloading gemma3:1b model...
            ollama pull gemma3:1b
        )
    )
)

REM 환경변수 설정 안내
echo.
echo =====================================
echo Environment Variables (Optional):
echo =====================================
echo For OpenRouter: set OPENROUTER_API_KEY=your-key
echo For Gemini: set GEMINI_API_KEY=your-key

REM .env 파일 생성
if not exist .env (
    echo.
    set /p CREATE_ENV="Create .env file? (y/N): "
    if /i "!CREATE_ENV!"=="y" (
        echo # LLM API Keys > .env
        echo OPENROUTER_API_KEY=your-openrouter-api-key-here >> .env
        echo GEMINI_API_KEY=your-gemini-api-key-here >> .env
        echo [OK] .env file created. Please add your API keys.
    )
)

echo.
echo =====================================
echo Installation Complete!
echo =====================================
echo.
echo Usage:
echo   gcm watch    - Real-time monitoring
echo   gcm analyze  - One-time analysis
echo   gcm review   - Code review
echo   gcm config   - Configuration guide
echo.

REM 바로 실행 옵션
set /p START_NOW="Start real-time monitoring now? (y/N): "
if /i "%START_NOW%"=="y" (
    echo.
    echo Starting Git Commit Manager...
    gcm watch
)

pause 