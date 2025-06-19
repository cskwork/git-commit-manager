"""Git 변경사항 분석 모듈"""

import os
from typing import List, Dict, Tuple, Optional
from git import Repo
from pathlib import Path


class GitAnalyzer:
    """Git 저장소 변경사항 분석 클래스"""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        try:
            self.repo = Repo(self.repo_path)
        except Exception as e:
            raise ValueError(f"유효한 Git 저장소가 아닙니다: {repo_path}") from e
            
    def get_staged_changes(self) -> Dict[str, List[str]]:
        """스테이징된 변경사항 가져오기"""
        changes = {
            'added': [],
            'modified': [],
            'deleted': [],
            'renamed': []
        }
        
        # 스테이징된 변경사항
        diff = self.repo.index.diff("HEAD")
        for item in diff:
            if item.new_file:
                changes['added'].append(item.a_path)
            elif item.deleted_file:
                changes['deleted'].append(item.a_path)
            elif item.renamed:
                changes['renamed'].append((item.rename_from, item.rename_to))
            else:
                changes['modified'].append(item.a_path)
                
        return changes
        
    def get_unstaged_changes(self) -> Dict[str, List[str]]:
        """스테이징되지 않은 변경사항 가져오기"""
        changes = {
            'modified': [],
            'deleted': []
        }
        
        # 워킹 디렉토리 변경사항
        diff = self.repo.index.diff(None)
        for item in diff:
            if item.deleted_file:
                changes['deleted'].append(item.a_path)
            else:
                changes['modified'].append(item.a_path)
                
        # 추적되지 않은 파일
        changes['untracked'] = self.repo.untracked_files
        
        return changes
        
    def get_all_changes(self) -> Dict[str, List[str]]:
        """모든 변경사항 가져오기 (스테이징 + 비스테이징)"""
        staged = self.get_staged_changes()
        unstaged = self.get_unstaged_changes()
        
        all_changes = {}
        for key in set(staged.keys()) | set(unstaged.keys()):
            all_changes[key] = staged.get(key, []) + unstaged.get(key, [])
            
        return all_changes
        
    def get_file_diff(self, file_path: str, staged: bool = True) -> Optional[str]:
        """특정 파일의 diff 가져오기"""
        try:
            if staged:
                # 스테이징된 변경사항
                diff = self.repo.git.diff('--cached', file_path)
            else:
                # 워킹 디렉토리 변경사항
                diff = self.repo.git.diff(file_path)
                
            return diff if diff else None
        except Exception:
            return None
            
    def get_diff_chunks(self, max_chunk_size: int = 1000) -> List[Dict[str, str]]:
        """변경사항을 작은 청크로 분할"""
        chunks = []
        all_changes = self.get_all_changes()
        
        for change_type, files in all_changes.items():
            if change_type == 'renamed':
                # renamed는 튜플 리스트
                for old_name, new_name in files:
                    chunks.append({
                        'type': 'renamed',
                        'old_path': old_name,
                        'new_path': new_name,
                        'diff': f"Renamed: {old_name} -> {new_name}"
                    })
            else:
                for file_path in files:
                    # 스테이징된 diff 먼저 확인
                    diff = self.get_file_diff(file_path, staged=True)
                    if not diff:
                        # 스테이징되지 않은 diff 확인
                        diff = self.get_file_diff(file_path, staged=False)
                        
                    if diff:
                        # diff가 너무 크면 청크로 분할
                        if len(diff) > max_chunk_size:
                            lines = diff.split('\n')
                            current_chunk = []
                            current_size = 0
                            
                            for line in lines:
                                current_chunk.append(line)
                                current_size += len(line) + 1
                                
                                if current_size >= max_chunk_size:
                                    chunks.append({
                                        'type': change_type,
                                        'path': file_path,
                                        'diff': '\n'.join(current_chunk)
                                    })
                                    current_chunk = []
                                    current_size = 0
                                    
                            if current_chunk:
                                chunks.append({
                                    'type': change_type,
                                    'path': file_path,
                                    'diff': '\n'.join(current_chunk)
                                })
                        else:
                            chunks.append({
                                'type': change_type,
                                'path': file_path,
                                'diff': diff
                            })
                    elif change_type == 'untracked':
                        # 추적되지 않은 파일의 내용
                        try:
                            file_full_path = self.repo_path / file_path
                            with open(file_full_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if len(content) > max_chunk_size:
                                    # 내용이 너무 크면 일부만
                                    content = content[:max_chunk_size] + "\n... (truncated)"
                                chunks.append({
                                    'type': 'untracked',
                                    'path': file_path,
                                    'diff': f"New file:\n{content}"
                                })
                        except Exception:
                            chunks.append({
                                'type': 'untracked',
                                'path': file_path,
                                'diff': "New file (content unavailable)"
                            })
                            
        return chunks
        
    def get_current_branch(self) -> str:
        """현재 브랜치 이름 가져오기"""
        try:
            return self.repo.active_branch.name
        except Exception:
            return "HEAD (detached)"
            
    def get_last_commit_message(self) -> str:
        """마지막 커밋 메시지 가져오기"""
        try:
            return self.repo.head.commit.message.strip()
        except Exception:
            return "No commits yet" 