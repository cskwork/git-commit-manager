# Git Commit Manager

AI 기반 Git 커밋 메시지 생성 및 코드 리뷰 도구

## 빠른 설치

### 🚀 원클릭 설치 (추천)

#### macOS/Linux

```bash
# 전체 설치 (대화형)
./install.sh

# 빠른 설치 (자동)
./quick-install.sh
```

#### Windows

```cmd
# 배치 파일 (CMD)
install.bat

# PowerShell (추천)
.\install.ps1
```

### 📦 수동 설치

```bash
pip install -r requirements.txt
pip install -e .
gcm watch  # 실행
```

## 기능

- 🔍 **실시간 변경사항 감시**: Git 저장소의 파일 변경을 자동으로 감지
- 🤖 **AI 커밋 메시지 생성**: 변경사항을 분석하여 적절한 커밋 메시지 제안
- 📝 **코드 리뷰**: 변경된 코드에 대한 AI 기반 리뷰 제공
- 🔧 **다양한 LLM 지원**: Ollama (로컬), OpenRouter, Google Gemini
- 🎯 **스마트 모델 선택**: 설치된 Ollama 모델 자동 감지 및 추천
- 🌐 **다국어 지원**: 한국어, 영어, 일본어, 중국어, 스페인어, 프랑스어, 독일어
- ⚙️ **유연한 설정**: .env 파일을 통한 기본 설정 및 동작 사용자화
- 🔄 **중복 처리 방지**: 동일한 변경사항에 대한 중복 분석 자동 방지
- 🎛️ **자동 리뷰 토글**: 필요에 따라 자동 코드 리뷰 활성화/비활성화

## 상세 설치 가이드

### 1. 저장소 클론 및 설치

```bash
git clone https://github.com/yourusername/git-commit-manager.git
cd git-commit-manager
pip install -e .
```

또는 requirements.txt 사용:

```bash
pip install -r requirements.txt
python setup.py install
```

### 2. LLM 프로바이더 설정

#### Ollama (로컬 모델) - 추천

```bash
# Ollama 설치
curl -fsSL https://ollama.ai/install.sh | sh

# 추천 모델 설치 (자동으로 제안됨)
ollama pull gemma3:1b
```

#### OpenRouter

1. [OpenRouter](https://openrouter.ai)에서 API 키 발급
2. 환경변수 설정:

```bash
export OPENROUTER_API_KEY='your-api-key'
```

#### Google Gemini

1. [Google AI Studio](https://makersuite.google.com/app/apikey)에서 API 키 발급
2. 환경변수 설정:

```bash
export GEMINI_API_KEY='your-api-key'
```

### 3. 환경변수 설정 (선택사항)

프로젝트 루트에 `.env` 파일 생성:

```bash
# 기본 LLM 프로바이더 및 모델 설정
DEFAULT_PROVIDER=ollama
DEFAULT_MODEL=gemma3:1b

# API 키
OPENROUTER_API_KEY=your-openrouter-key
GEMINI_API_KEY=your-gemini-key

# 고급 설정
DEBOUNCE_DELAY=3.0  # 파일 변경 후 대기 시간(초)
COMMIT_MESSAGE_LANGUAGE=korean  # 커밋 메시지 언어
AUTO_CODE_REVIEW=true  # 자동 코드 리뷰 활성화
```

**설정 가능한 언어**: korean, english, japanese, chinese, spanish, french, german

#### 커스텀 프롬프트 설정 (고급)

AI의 응답을 커스터마이징하려면 다음 환경변수를 설정할 수 있습니다:

```bash
# 커밋 메시지 프롬프트 커스터마이징
CUSTOM_COMMIT_SYSTEM_PROMPT_KOREAN="당신은 Git 커밋 메시지 전문가입니다..."
CUSTOM_COMMIT_USER_PROMPT_KOREAN="다음 변경사항에 대한 커밋 메시지를 작성해주세요:\n\n{changes_summary}"

# 코드 리뷰 프롬프트 커스터마이징
CUSTOM_REVIEW_SYSTEM_PROMPT_KOREAN="당신은 시니어 개발자로서 코드를 리뷰합니다..."
CUSTOM_REVIEW_USER_PROMPT_KOREAN="파일: {file_path}\n변경 유형: {change_type}\n\n{diff_content}\n\n위 코드를 리뷰해주세요."
```

**주의사항**:

- 사용자 프롬프트에는 반드시 필요한 플레이스홀더를 포함해야 합니다
  - 커밋 메시지: `{changes_summary}`
  - 코드 리뷰: `{file_path}`, `{change_type}`, `{diff_content}`
- 영어 버전은 `_KOREAN`을 `_ENGLISH`로 변경하여 설정

`.env.example` 파일을 참고하여 필요한 설정을 복사하세요.

## 사용법

### 실시간 감시 모드

저장소의 변경사항을 실시간으로 감시하고 자동으로 커밋 메시지와 코드 리뷰를 생성합니다:

```bash
# Ollama 사용 (기본, 모델 자동 선택)
gcm watch

# 특정 모델 지정
gcm watch -p ollama -m codellama

# OpenRouter 사용
gcm watch -p openrouter -m openai/gpt-3.5-turbo

# Gemini 사용
gcm watch -p gemini -m gemini-pro

# 특정 저장소 경로 지정
gcm watch -r /path/to/repo
```

### 일회성 분석

현재 변경사항을 분석하여 커밋 메시지를 생성합니다:

```bash
gcm analyze
```

### 코드 리뷰

변경된 코드에 대한 리뷰를 수행합니다:

```bash
# 모든 변경사항 리뷰
gcm review

# 특정 파일만 리뷰
gcm review -f src/main.py
```

### 설정 가이드 확인

```bash
gcm config
```

## 명령어 옵션

### 공통 옵션

- `-p, --provider`: LLM 프로바이더 선택 (ollama, openrouter, gemini) - 미지정시 .env의 DEFAULT_PROVIDER 사용
- `-m, --model`: 사용할 모델 이름 - 미지정시 .env의 DEFAULT_MODEL 사용
- `-r, --repo`: Git 저장소 경로 (기본값: 현재 디렉토리)

### watch 명령어

실시간으로 변경사항을 감시하고 분석합니다.

### analyze 명령어

현재 변경사항을 분석하고 커밋 메시지를 제안합니다.

### review 명령어

- `-f, --file`: 특정 파일만 리뷰

## 작동 방식

1. **변경사항 감지**: watchdog을 사용하여 파일 시스템 변경 모니터링
2. **Git 분석**: GitPython으로 변경사항 추출 및 diff 생성
3. **청크 분할**: 컨텍스트 제한을 고려하여 변경사항을 작은 단위로 분할
4. **AI 분석**: 선택한 LLM으로 커밋 메시지 생성 및 코드 리뷰 수행
5. **결과 표시**: Rich 라이브러리로 보기 좋게 결과 출력

## 주의사항

- Git 저장소에서만 작동합니다
- 큰 변경사항은 자동으로 청크로 분할되어 처리됩니다
- API 키가 필요한 서비스는 사용 전 설정이 필요합니다
- `.git/`, `__pycache__/` 등의 디렉토리는 자동으로 무시됩니다

## 문제 해결

### "유효한 Git 저장소가 아닙니다" 오류

현재 디렉토리가 Git 저장소인지 확인하세요:

```bash
git init
```

### API 키 오류

환경변수가 올바르게 설정되었는지 확인하세요:

```bash
echo $OPENROUTER_API_KEY
echo $GEMINI_API_KEY
```

### Ollama 연결 오류

Ollama 서비스가 실행 중인지 확인하세요:

```bash
ollama list
```

## 라이선스

MIT License
