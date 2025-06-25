"""커밋 관련 엔티티 및 DTO 클래스"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class ReviewSeverity(Enum):
    """리뷰 심각도 레벨"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class CommitMessage:
    """커밋 메시지 데이터"""
    title: str
    body: Optional[str] = None
    language: str = "korean"
    
    def to_string(self) -> str:
        """문자열로 변환"""
        if self.body:
            return f"{self.title}\n\n{self.body}"
        return self.title
    
    def get_git_command(self) -> str:
        """Git 커밋 명령어 생성"""
        if self.body:
            # 여러 줄 커밋 메시지
            body_clean = self.body.strip().replace('"', '\\"')
            return f'git commit -m "{self.title}" -m "{body_clean}"'
        else:
            # 단일 줄 커밋 메시지
            return f'git commit -m "{self.title}"'


@dataclass
class CodeReview:
    """코드 리뷰 결과"""
    file_path: str
    change_type: str
    review_content: str
    severity: ReviewSeverity
    suggestions: Optional[List[str]] = None
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            'file': self.file_path,
            'type': self.change_type,
            'review': self.review_content,
            'severity': self.severity.value,
            'suggestions': self.suggestions or []
        }