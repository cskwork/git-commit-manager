"""커밋 분석 서비스 인터페이스"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class ICommitService(ABC):
    """커밋 메시지 생성 및 코드 리뷰 서비스 인터페이스"""
    
    @abstractmethod
    def generate_commit_message(self, chunks: List[Dict[str, Any]]) -> str:
        """커밋 메시지 생성"""
        pass
    
    @abstractmethod
    def review_code_changes(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """코드 변경사항 리뷰"""
        pass