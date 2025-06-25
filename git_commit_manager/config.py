"""설정 관리 모듈"""

import os
import re
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import json
from pathlib import Path
import logging

load_dotenv()


class Config:
    """애플리케이션 설정"""
    
    # API 키 (검증된 형태로 저장)
    OPENROUTER_API_KEY = None
    GEMINI_API_KEY = None
    
    @classmethod
    def _validate_api_key(cls, key: Optional[str], provider: str) -> Optional[str]:
        """API 키 유효성 검사"""
        if not key:
            return None
            
        # 기본 보안 검사
        if len(key) < 10:
            logging.warning(f"API key for {provider} seems too short")
            return None
            
        # 특수문자 확인 (안전한 API 키 패턴 - 경로 순회 공격 방지)
        if not re.match(r'^[A-Za-z0-9\-_.+=]+$', key):
            logging.warning(f"API key for {provider} contains invalid characters")
            return None
            
        # 프로바이더별 형식 검증
        if provider == "openrouter" and not key.startswith(("sk-or-", "sk-")):
            logging.warning(f"OpenRouter API key format may be invalid")
            
        if provider == "gemini" and len(key) < 35:
            logging.warning(f"Gemini API key format may be invalid")
            
        return key
    
    @classmethod
    def _initialize_api_keys(cls):
        """API 키 초기화 및 검증"""
        raw_openrouter_key = os.getenv("OPENROUTER_API_KEY")
        raw_gemini_key = os.getenv("GEMINI_API_KEY")
        
        cls.OPENROUTER_API_KEY = cls._validate_api_key(raw_openrouter_key, "openrouter")
        cls.GEMINI_API_KEY = cls._validate_api_key(raw_gemini_key, "gemini")
        
        # 검증 결과 로깅 (키 값은 로깅하지 않음)
        if raw_openrouter_key and not cls.OPENROUTER_API_KEY:
            logging.error("OpenRouter API key validation failed")
        if raw_gemini_key and not cls.GEMINI_API_KEY:
            logging.error("Gemini API key validation failed")
    
    # LLM 프로바이더 및 모델 설정
    DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "ollama")
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemma3:1b")
    
    # 디바운스 설정 (초 단위)
    DEBOUNCE_DELAY = float(os.getenv("DEBOUNCE_DELAY", "3.0"))
    
    # 커밋 메시지 언어 설정
    COMMIT_MESSAGE_LANGUAGE = os.getenv("COMMIT_MESSAGE_LANGUAGE", "korean")
    
    # 코드 리뷰 자동 실행 여부
    AUTO_CODE_REVIEW = os.getenv("AUTO_CODE_REVIEW", "false").lower() == "true"
    
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
            cls._initialize_api_keys()  # API 키 검증 실행
            return
            
        with open(filepath, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)
            
        for key, value in config_dict.items():
            if hasattr(cls, key):
                # CACHE_DIR은 Path 객체로 변환
                if key == 'CACHE_DIR':
                    value = Path(value)
                # API 키는 별도 검증 과정을 거침
                elif key in ['OPENROUTER_API_KEY', 'GEMINI_API_KEY']:
                    continue
                setattr(cls, key, value)
                
        cls._initialize_api_keys()  # API 키 검증 실행
    
    @classmethod
    def validate_file_path(cls, file_path: str, repo_path: str) -> bool:
        """파일 경로 보안 검증"""
        try:
            # 절대 경로로 변환
            abs_file_path = os.path.abspath(os.path.join(repo_path, file_path))
            abs_repo_path = os.path.abspath(repo_path)
            
            # 경로 순회 공격 방지
            if not abs_file_path.startswith(abs_repo_path):
                logging.warning(f"Path traversal attempt detected: {file_path}")
                return False
                
            return True
        except Exception as e:
            logging.error(f"Path validation error: {e}")
            return False


# API 키 초기화 실행
Config._initialize_api_keys()