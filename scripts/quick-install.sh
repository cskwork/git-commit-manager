#!/bin/bash

# Git Commit Manager 빠른 설치 스크립트
# 가상환경 없이 바로 설치하고 실행

echo "🚀 Git Commit Manager 빠른 설치..."

# 의존성 및 패키지 설치
pip3 install -r requirements.txt && pip3 install -e .

# Ollama 모델 자동 설치 (있는 경우)
if command -v ollama &> /dev/null; then
    if ! ollama list | grep -q "gemma3:1b"; then
        echo "🤖 gemma3:1b 모델 설치 중..."
        ollama pull gemma3:1b
    fi
fi

echo "✅ 설치 완료!"
echo "🔍 실행: gcm watch"

# 바로 실행
gcm watch 