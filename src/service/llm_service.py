"""LLM 프로바이더 서비스 인터페이스"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class ILLMService(ABC):
    """LLM 프로바이더 서비스 인터페이스"""
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """텍스트 생성"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """서비스 가용성 확인"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[Dict[str, Any]]:
        """사용 가능한 모델 목록"""
        pass