# Git Commit Manager 설치 스크립트 (PowerShell)

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Git Commit Manager Installation" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Python 버전 확인
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] $pythonVersion detected" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python is not installed." -ForegroundColor Red
    Write-Host "Please install Python 3.8 or higher." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# pip 확인
try {
    $pipVersion = pip --version 2>&1
    Write-Host "[OK] pip is installed" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] pip is not installed." -ForegroundColor Red
    Write-Host "Please install pip." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# 가상환경 생성 옵션
Write-Host ""
$createVenv = Read-Host "Create virtual environment? (y/N)"
if ($createVenv -eq 'y' -or $createVenv -eq 'Y') {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    & ".\venv\Scripts\Activate.ps1"
    Write-Host "[OK] Virtual environment activated" -ForegroundColor Green
}

# 의존성 설치
Write-Host ""
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to install dependencies." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# 패키지 설치
Write-Host ""
Write-Host "Installing Git Commit Manager..." -ForegroundColor Yellow
pip install -e .
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to install Git Commit Manager." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Ollama 확인
Write-Host ""
$ollamaPath = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaPath) {
    Write-Host "[OK] Ollama is installed." -ForegroundColor Green
    Write-Host ""
    Write-Host "Installed Ollama models:" -ForegroundColor Cyan
    ollama list
    
    # gemma3:1b 모델 확인
    $models = ollama list | Out-String
    if ($models -notmatch "gemma3:1b") {
        Write-Host ""
        $installModel = Read-Host "Install recommended model gemma3:1b? (y/N)"
        if ($installModel -eq 'y' -or $installModel -eq 'Y') {
            Write-Host "Downloading gemma3:1b model..." -ForegroundColor Yellow
            ollama pull gemma3:1b
        }
    }
} else {
    Write-Host "[WARNING] Ollama is not installed." -ForegroundColor Yellow
    Write-Host "          Install from: https://ollama.ai" -ForegroundColor Yellow
    Write-Host "          Or use OpenRouter/Gemini instead." -ForegroundColor Yellow
}

# 환경변수 설정 안내
Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Environment Variables (Optional):" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "For OpenRouter: `$env:OPENROUTER_API_KEY='your-key'" -ForegroundColor Yellow
Write-Host "For Gemini: `$env:GEMINI_API_KEY='your-key'" -ForegroundColor Yellow

# .env 파일 생성
if (!(Test-Path .env)) {
    Write-Host ""
    $createEnv = Read-Host "Create .env file? (y/N)"
    if ($createEnv -eq 'y' -or $createEnv -eq 'Y') {
        @"
# LLM API Keys
OPENROUTER_API_KEY=your-openrouter-api-key-here
GEMINI_API_KEY=your-gemini-api-key-here
"@ | Out-File -FilePath .env -Encoding UTF8
        Write-Host "[OK] .env file created. Please add your API keys." -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Usage:" -ForegroundColor Cyan
Write-Host "  gcm watch    - Real-time monitoring" -ForegroundColor White
Write-Host "  gcm analyze  - One-time analysis" -ForegroundColor White
Write-Host "  gcm review   - Code review" -ForegroundColor White
Write-Host "  gcm config   - Configuration guide" -ForegroundColor White
Write-Host ""

# 바로 실행 옵션
$startNow = Read-Host "Start real-time monitoring now? (y/N)"
if ($startNow -eq 'y' -or $startNow -eq 'Y') {
    Write-Host ""
    Write-Host "Starting Git Commit Manager..." -ForegroundColor Green
    gcm watch
}

Read-Host "Press Enter to exit" 