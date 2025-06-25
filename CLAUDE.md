# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Git Commit Manager는 AI 기반 Git 커밋 메시지 생성 및 코드 리뷰 도구입니다. Python으로 작성되었으며 여러 LLM 프로바이더(Ollama, OpenRouter, Gemini)를 지원합니다.

### 핵심 아키텍처

- **GitAnalyzer**: Git 저장소 변경사항 분석 및 diff 생성
- **CommitAnalyzer**: LLM을 사용한 커밋 메시지 생성 및 코드 리뷰
- **LLMProvider**: 다양한 LLM 프로바이더 추상화 (Ollama, OpenRouter, Gemini)
- **GitWatcher**: 실시간 파일 변경 감시 (watchdog 기반)
- **CLI**: Click 기반 명령줄 인터페이스

### 새로운 모듈 구조 (개선된 아키텍처)

- `src/config/`: 설정 파일 모듈
- `src/controller/cli.py`: CLI 인터페이스 및 API 엔드포인트
- `src/entity/`: DTO 및 엔티티 클래스
- `src/service/`: 서비스 인터페이스 정의
- `src/serviceImpl/`: 서비스 구현체 (Git 분석, 커밋 분석, LLM 프로바이더)
- `src/utils/watcher.py`: 공통 유틸리티 (파일 감시)
- `src/test/`: 테스트 케이스
- `backup/`: 백업 파일
- `logs/`: 로깅 디렉토리
- `docs/`: 프로젝트 문서

## Development Commands

### 설치 및 환경 설정
```bash
# 개발 모드 설치
pip install -e .

# 또는 requirements로 설치
pip install -r requirements.txt
python setup.py install
```

### 테스트 실행
이 프로젝트에는 현재 테스트 프레임워크가 설정되어 있지 않습니다. 테스트를 추가할 때는 pytest를 사용하는 것을 권장합니다.

### 애플리케이션 실행
```bash
# 실시간 감시 모드 (기본 - Ollama)
gcm watch

# 특정 프로바이더 및 모델 지정
gcm watch -p ollama -m codellama
gcm watch -p openrouter -m openai/gpt-3.5-turbo
gcm watch -p gemini -m gemini-pro

# 현재 변경사항 분석
gcm analyze

# 코드 리뷰
gcm review

# 설정 가이드
gcm config
```

## Environment Variables

프로젝트 루트에 `.env` 파일을 생성하거나 환경변수로 설정:

```
OPENROUTER_API_KEY=your-openrouter-api-key
GEMINI_API_KEY=your-gemini-api-key
```

## Development Notes

### LLM Provider 추가시
새로운 LLM 프로바이더를 추가할 때는 `LLMProvider` 추상 클래스를 상속받아 `generate` 메서드를 구현해야 합니다.

### Git 분석 로직
변경사항은 청크 단위로 분할되어 처리되며, 컨텍스트 길이 제한을 고려하여 설계되었습니다.

### 파일 감시 제외 대상
`.git/`, `__pycache__/`, `.DS_Store` 등은 자동으로 감시 대상에서 제외됩니다.

### Rich 라이브러리 사용
콘솔 출력은 Rich 라이브러리를 사용하여 시각적으로 향상된 인터페이스를 제공합니다.