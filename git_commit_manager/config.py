"""설정 관리 모듈"""

import os
from typing import Optional
from dotenv import load_dotenv

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
    
    @classmethod
    def get_default_provider(cls) -> str:
        """기본 LLM 프로바이더 반환"""
        return cls.DEFAULT_PROVIDER
    
    @classmethod
    def get_default_model(cls) -> str:
        """기본 모델 반환"""
        return cls.DEFAULT_MODEL
    
    @classmethod
    def get_debounce_delay(cls) -> float:
        """디바운스 지연 시간 반환"""
        return cls.DEBOUNCE_DELAY
    
    @classmethod
    def get_commit_language(cls) -> str:
        """커밋 메시지 언어 반환"""
        return cls.COMMIT_MESSAGE_LANGUAGE
    
    @classmethod
    def is_auto_review_enabled(cls) -> bool:
        """자동 코드 리뷰 활성화 여부 반환"""
        return cls.AUTO_CODE_REVIEW
    
    @classmethod
    def get_language_instruction(cls) -> str:
        """언어별 지시사항 반환"""
        language = cls.get_commit_language().lower()
        
        language_instructions = {
            "korean": "응답은 한국어로 작성해주세요.",
            "english": "Please respond in English.",
            "japanese": "日本語で回答してください。",
            "chinese": "请用中文回答。",
            "spanish": "Por favor responde en español.",
            "french": "Veuillez répondre en français.",
            "german": "Bitte antworten Sie auf Deutsch.",
        }
        
        return language_instructions.get(language, language_instructions["korean"])