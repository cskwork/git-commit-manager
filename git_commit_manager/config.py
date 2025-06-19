"""설정 관리 모듈"""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import json
from pathlib import Path

load_dotenv()


class Config:
    """애플리케이션 설정"""
    
    # API 키
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # LLM 프로바이더 및 모델 설정
    DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "ollama")
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemma3:1b")
    
    # 디바운스 설정 (초 단위)
    DEBOUNCE_DELAY = float(os.getenv("DEBOUNCE_DELAY", "3.0"))
    
    # 커밋 메시지 언어 설정
    COMMIT_MESSAGE_LANGUAGE = os.getenv("COMMIT_MESSAGE_LANGUAGE", "korean")
    
    # 코드 리뷰 자동 실행 여부
    AUTO_CODE_REVIEW = os.getenv("AUTO_CODE_REVIEW", "true").lower() == "true"
    
    # 캐싱 설정
    ENABLE_CACHE = os.getenv("ENABLE_CACHE", "true").lower() == "true"
    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))  # 5분
    CACHE_DIR = Path(os.getenv("CACHE_DIR", ".git_commit_manager_cache"))
    
    # 청크 크기 설정
    MAX_CHUNK_SIZE = int(os.getenv("MAX_CHUNK_SIZE", "2000"))
    MAX_CONTEXT_LENGTH = int(os.getenv("MAX_CONTEXT_LENGTH", "4000"))
    
    # LLM 설정
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "500"))
    LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
    
    # 재시도 설정
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY = float(os.getenv("RETRY_DELAY", "1.0"))
    
    # 파일 필터링
    IGNORE_PATTERNS = os.getenv("IGNORE_PATTERNS", ".git/,__pycache__/,.pyc,.pyo,.DS_Store,node_modules/,venv/,env/,.env").split(",")
    MAX_FILE_SIZE_MB = float(os.getenv("MAX_FILE_SIZE_MB", "5.0"))
    
    # 커스텀 프롬프트 설정 (환경변수에서 읽기)
    # 커밋 메시지 시스템 프롬프트
    CUSTOM_COMMIT_SYSTEM_PROMPT_KOREAN = os.getenv("CUSTOM_COMMIT_SYSTEM_PROMPT_KOREAN")
    CUSTOM_COMMIT_SYSTEM_PROMPT_ENGLISH = os.getenv("CUSTOM_COMMIT_SYSTEM_PROMPT_ENGLISH")
    
    # 커밋 메시지 사용자 프롬프트
    CUSTOM_COMMIT_USER_PROMPT_KOREAN = os.getenv("CUSTOM_COMMIT_USER_PROMPT_KOREAN")
    CUSTOM_COMMIT_USER_PROMPT_ENGLISH = os.getenv("CUSTOM_COMMIT_USER_PROMPT_ENGLISH")
    
    # 코드 리뷰 시스템 프롬프트
    CUSTOM_REVIEW_SYSTEM_PROMPT_KOREAN = os.getenv("CUSTOM_REVIEW_SYSTEM_PROMPT_KOREAN")
    CUSTOM_REVIEW_SYSTEM_PROMPT_ENGLISH = os.getenv("CUSTOM_REVIEW_SYSTEM_PROMPT_ENGLISH")
    
    # 코드 리뷰 사용자 프롬프트
    CUSTOM_REVIEW_USER_PROMPT_KOREAN = os.getenv("CUSTOM_REVIEW_USER_PROMPT_KOREAN")
    CUSTOM_REVIEW_USER_PROMPT_ENGLISH = os.getenv("CUSTOM_REVIEW_USER_PROMPT_ENGLISH")
    
    @classmethod
    def get_cache_dir(cls) -> Path:
        """캐시 디렉토리 경로 반환 (없으면 생성)"""
        cache_dir = cls.CACHE_DIR
        if not cache_dir.exists():
            cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """현재 설정을 딕셔너리로 반환"""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith('_') and not callable(getattr(cls, key))
        }
    
    @classmethod
    def save_config(cls, filepath: str = ".gcm_config.json"):
        """현재 설정을 파일로 저장"""
        config_dict = cls.to_dict()
        # Path 객체는 JSON 직렬화가 안되므로 문자열로 변환
        config_dict['CACHE_DIR'] = str(config_dict['CACHE_DIR'])
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_config(cls, filepath: str = ".gcm_config.json"):
        """파일에서 설정 로드"""
        if not os.path.exists(filepath):
            return
            
        with open(filepath, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)
            
        for key, value in config_dict.items():
            if hasattr(cls, key):
                # CACHE_DIR은 Path 객체로 변환
                if key == 'CACHE_DIR':
                    value = Path(value)
                setattr(cls, key, value)