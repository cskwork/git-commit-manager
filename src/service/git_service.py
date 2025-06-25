"""Git 분석 서비스 인터페이스"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class IGitService(ABC):
    """Git 저장소 분석 서비스 인터페이스"""
    
    @abstractmethod
    def get_all_changes(self) -> Dict[str, List[Any]]:
        """모든 변경사항 조회"""
        pass
    
    @abstractmethod
    def get_diff_chunks(self) -> List[Dict[str, Any]]:
        """변경사항을 청크 단위로 분할하여 반환"""
        pass
    
    @abstractmethod
    def validate_repository(self) -> bool:
        """Git 저장소 유효성 검증"""
        pass