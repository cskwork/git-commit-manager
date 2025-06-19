#!/bin/bash
set -e

# Git Commit Manager 설치 스크립트 (macOS/Linux)

# --- Helper Functions ---
error() {
    echo "❌ Error: $1" >&2
    exit 1
}

# --- Main Script ---

echo "🚀 Git Commit Manager 설치를 시작합니다..."
echo ""

# Python 버전 확인
if ! command -v python3 &> /dev/null; then
    error "Python 3이 설치되어 있지 않습니다. Python 3.8 이상을 설치하고 다시 시도하세요."
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python $PYTHON_VERSION 감지됨"

# pip 확인
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3가 설치되어 있지 않습니다."
    echo "pip를 설치하고 다시 시도하세요."
    exit 1
fi

# 가상환경 생성 (선택사항)
VENV_PATH="venv"
if [ ! -d "$VENV_PATH" ]; then
    read -p "가상환경을 생성하시겠습니까? (y/N): " create_venv
    if [[ $create_venv =~ ^[Yy]$ ]]; then
        echo "📦 가상환경 생성 중... ($VENV_PATH)"
        python3 -m venv "$VENV_PATH"
        echo "✅ 가상환경 생성됨. 활성화하려면 'source $VENV_PATH/bin/activate'를 실행하세요."
    fi
fi

# 가상환경이 있다면 pip는 venv의 것을 사용
PIP_CMD="python3 -m pip"
if [ -d "$VENV_PATH" ] && [ -f "$VENV_PATH/bin/activate" ]; then
    echo "💡 가상환경이 감지되었습니다. 가상환경 내부의 pip를 사용합니다."
    source "$VENV_PATH/bin/activate"
    PIP_CMD="pip"
fi

# 의존성 설치
echo ""
echo "📦 의존성 설치 중..."
$PIP_CMD install -r requirements.txt

# 패키지 설치
echo ""
echo "📦 Git Commit Manager 설치 중..."
$PIP_CMD install -e .

# gcm 명령어 확인
if ! command -v gcm &> /dev/null; then
    echo ""
    error "gcm 명령어를 찾을 수 없습니다. PATH 환경변수를 확인해주세요. 'source venv/bin/activate'를 실행했는지 확인하세요."
fi

# Ollama 확인
echo ""
if command -v ollama &> /dev/null; then
    echo "✅ Ollama가 설치되어 있습니다."
    
    # 설치된 모델 확인
    echo "📋 설치된 Ollama 모델:"
    ollama list
    
    # gemma3:1b 모델 확인 및 설치 제안
    if ! ollama list | grep -q "gemma3:1b"; then
        echo ""
        read -p "추천 모델 gemma3:1b를 설치하시겠습니까? (y/N): " install_model
        if [[ $install_model =~ ^[Yy]$ ]]; then
            echo "🤖 gemma3:1b 모델 다운로드 중..."
            ollama pull gemma3:1b
        fi
    fi
else
    echo "⚠️  Ollama가 설치되어 있지 않습니다."
    echo "   Ollama를 설치하려면: https://ollama.ai"
    echo "   또는 OpenRouter/Gemini를 사용할 수 있습니다."
fi

# 환경변수 설정 안내
echo ""
echo "📝 환경변수 설정 (선택사항):"
echo "   OpenRouter 사용: export OPENROUTER_API_KEY='your-key'"
echo "   Gemini 사용: export GEMINI_API_KEY='your-key'"

# .env 파일 생성 제안
if [ ! -f .env ]; then
    echo ""
    read -p ".env 파일을 생성하시겠습니까? (y/N): " create_env
    if [[ $create_env =~ ^[Yy]$ ]]; then
        echo "# LLM API Keys" > .env
        echo "OPENROUTER_API_KEY=your-openrouter-api-key-here" >> .env
        echo "GEMINI_API_KEY=your-gemini-api-key-here" >> .env
        echo "✅ .env 파일이 생성되었습니다. API 키를 입력하세요."
    fi
fi

echo ""
echo "✅ 설치가 완료되었습니다!"
echo ""
echo "🎯 사용 방법:"
echo "   gcm watch    # 실시간 감시 모드"
echo "   gcm analyze  # 일회성 분석"
echo "   gcm review   # 코드 리뷰"
echo "   gcm config   # 설정 가이드"
echo ""
if [ -d "$VENV_PATH" ]; then
    echo "👉 가상환경을 사용 중입니다. 새 터미널에서는 'source $VENV_PATH/bin/activate'를 먼저 실행하세요."
fi

# 바로 실행 옵션
read -p "지금 실시간 감시 모드를 시작하시겠습니까? (y/N): " start_now
if [[ $start_now =~ ^[Yy]$ ]]; then
    echo ""
    echo "🔍 Git Commit Manager를 시작합니다..."
    gcm watch
fi 