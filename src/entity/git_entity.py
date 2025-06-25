"""Git 관련 엔티티 및 DTO 클래스"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum


class ChangeType(Enum):
    """변경 타입 열거형"""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    UNTRACKED = "untracked"


@dataclass
class GitDiffChunk:
    """Git diff 청크 데이터"""
    path: str
    content: str
    change_type: ChangeType
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    context: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'path': self.path,
            'content': self.content,
            'type': self.change_type.value,
            'line_start': self.line_start,
            'line_end': self.line_end,
            'context': self.context
        }


@dataclass
class GitFileChange:
    """파일 변경 정보"""
    path: str
    change_type: ChangeType
    old_path: Optional[str] = None
    additions: Optional[int] = None
    deletions: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'path': self.path,
            'change_type': self.change_type.value,
            'old_path': self.old_path,
            'additions': self.additions,
            'deletions': self.deletions
        }


@dataclass
class GitChanges:
    """Git 변경사항 집합"""
    added: List[str]
    modified: List[str]
    deleted: List[str]
    renamed: List[tuple]
    untracked: List[str]
    
    def to_dict(self) -> Dict[str, List[Any]]:
        """딕셔너리로 변환"""
        return {
            'added': self.added,
            'modified': self.modified,
            'deleted': self.deleted,
            'renamed': self.renamed,
            'untracked': self.untracked
        }
    
    def has_changes(self) -> bool:
        """변경사항 존재 여부 확인"""
        return any([self.added, self.modified, self.deleted, self.renamed, self.untracked])