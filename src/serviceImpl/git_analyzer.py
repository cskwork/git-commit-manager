"""Git 변경사항 분석 모듈"""

import os
from typing import List, Dict, Tuple, Optional, Iterator
from git import Repo, diff
from pathlib import Path
from ..config.config import Config


class GitAnalyzer:
    """Git 저장소 변경사항 분석 클래스"""
    
    EMPTY_TREE_SHA = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        try:
            self.repo = Repo(self.repo_path)
        except Exception as e:
            raise ValueError(f"유효한 Git 저장소가 아닙니다: {repo_path}") from e
        
        self.head_commit = self.repo.head.commit if self.repo.head.is_valid() else self.EMPTY_TREE_SHA
        self.ignore_patterns = Config.IGNORE_PATTERNS
        self.max_file_size = Config.MAX_FILE_SIZE_MB * 1024 * 1024  # MB를 바이트로 변환

    def should_ignore_file(self, file_path: str) -> bool:
        """파일을 무시해야 하는지 확인"""
        for pattern in self.ignore_patterns:
            if pattern in file_path:
                return True
        
        # 파일 크기 확인
        full_path = self.repo_path / file_path
        if full_path.exists() and full_path.is_file():
            if full_path.stat().st_size > self.max_file_size:
                return True
                
        return False

    def get_all_changes(self) -> Dict[str, List[str]]:
        """모든 변경사항 가져오기 (스테이징 + 비스테이징)"""
        
        all_changes: Dict[str, set] = {
            'added': set(),
            'modified': set(),
            'deleted': set(),
            'renamed': set(),
            'untracked': set(),
        }

        # Staged changes
        staged_diff = self.repo.index.diff(self.head_commit)
        for d in staged_diff:
            if self.should_ignore_file(d.a_path or d.b_path):
                continue
                
            if d.new_file:
                all_changes['added'].add(d.a_path)
            elif d.deleted_file:
                all_changes['deleted'].add(d.a_path)
            elif d.renamed:
                all_changes['renamed'].add((d.rename_from, d.rename_to))
            else:
                all_changes['modified'].add(d.a_path)

        # Unstaged changes
        unstaged_diff = self.repo.index.diff(None)
        for d in unstaged_diff:
            if self.should_ignore_file(d.a_path or d.b_path):
                continue
                
            if d.change_type == 'D':
                # Already staged for deletion, now removed from filesystem
                if d.a_path not in all_changes['deleted']:
                    all_changes['deleted'].add(d.a_path)
            else: # A, M
                 # If a file was added and then modified, it is still 'added'
                if d.a_path not in all_changes['added']:
                    all_changes['modified'].add(d.a_path)
        
        # Untracked files
        for f in self.repo.untracked_files:
            if not self.should_ignore_file(f):
                all_changes['untracked'].add(f)
            
        # Convert sets to lists
        return {k: sorted(list(v)) for k, v in all_changes.items()}
        
    def get_diff_chunks(self, max_chunk_size: int = None) -> List[Dict[str, str]]:
        """변경사항을 의미있는 청크로 분할"""
        if max_chunk_size is None:
            max_chunk_size = Config.MAX_CHUNK_SIZE
            
        chunks = []
        
        # Staged diffs
        staged_diff = self.repo.index.diff(self.head_commit, create_patch=True)
        for d in staged_diff:
            if self.should_ignore_file(d.a_path or d.b_path):
                continue
                
            chunks.extend(self._process_diff_item(d, max_chunk_size))

        # Unstaged diffs
        unstaged_diff = self.repo.index.diff(None, create_patch=True)
        for d in unstaged_diff:
            if self.should_ignore_file(d.a_path or d.b_path):
                continue
                
            chunks.extend(self._process_diff_item(d, max_chunk_size))

        # Untracked files
        for file_path in self.repo.untracked_files:
            if self.should_ignore_file(file_path):
                continue
                
            chunks.extend(self._process_untracked_file(file_path, max_chunk_size))

        return chunks

    def _process_diff_item(self, d: diff.Diff, max_chunk_size: int) -> List[Dict[str, str]]:
        """개별 diff 항목 처리"""
        chunks = []
        change_type = self._get_change_type(d)
        path = d.a_path or d.b_path
        
        if d.renamed:
            chunks.append({
                'type': 'renamed',
                'old_path': d.rename_from,
                'new_path': d.rename_to,
                'diff': f"파일 이름 변경: {d.rename_from} → {d.rename_to}"
            })
        else:
            # diff 내용을 스트림으로 처리하여 메모리 효율성 향상
            try:
                diff_text = d.diff.decode('utf-8', 'ignore')
                if diff_text:
                    self._split_diff_into_chunks(chunks, change_type, path, diff_text, max_chunk_size)
            except Exception:
                chunks.append({
                    'type': change_type,
                    'path': path,
                    'diff': f"{change_type} 파일 (diff 내용을 읽을 수 없음)",
                    'binary': True
                })
                
        return chunks

    def _process_untracked_file(self, file_path: str, max_chunk_size: int) -> List[Dict[str, str]]:
        """추적되지 않은 파일 처리 (보안 강화 및 메모리 최적화)"""
        chunks = []
        
        try:
            # 파일 경로 보안 검증
            if not Config.validate_file_path(file_path, str(self.repo_path)):
                return [{
                    'type': 'untracked',
                    'path': file_path,
                    'diff': "보안상 처리할 수 없는 파일 경로",
                    'security_blocked': True
                }]
            
            full_path = self.repo_path / file_path
            
            # 파일 존재 여부 및 크기 확인
            if not full_path.exists() or not full_path.is_file():
                return []
                
            file_size = full_path.stat().st_size
            if file_size > self.max_file_size:
                return [{
                    'type': 'untracked',
                    'path': file_path,
                    'diff': f"파일이 너무 큽니다 ({file_size // (1024*1024)}MB > {self.max_file_size // (1024*1024)}MB)",
                    'size_exceeded': True
                }]
            
            # 바이너리 파일 확인
            if self._is_binary_file(full_path):
                chunks.append({
                    'type': 'untracked',
                    'path': file_path,
                    'diff': "새 바이너리 파일",
                    'binary': True
                })
                return chunks
            
            # 텍스트 파일 처리 (메모리 효율적 스트리밍)
            return self._process_file_streaming(full_path, file_path, max_chunk_size)
                    
        except (OSError, IOError, PermissionError) as e:
            chunks.append({
                'type': 'untracked',
                'path': file_path,
                'diff': f"파일 읽기 오류: {type(e).__name__}"
            })
        except Exception as e:
            import logging
            logging.error(f"Unexpected error processing {file_path}: {e}")
            chunks.append({
                'type': 'untracked',
                'path': file_path,
                'diff': "파일 처리 중 오류 발생"
            })
            
        return chunks
    
    def _process_file_streaming(self, full_path: Path, file_path: str, max_chunk_size: int) -> List[Dict[str, str]]:
        """메모리 효율적인 파일 스트리밍 처리"""
        chunks = []
        
        with full_path.open('r', encoding='utf-8', errors='ignore') as f:
            chunk_buffer = []
            current_size = 0
            line_count = 0
            
            for line in f:
                line_count += 1
                line_with_prefix = f"+{line}"
                line_size = len(line_with_prefix)
                
                # 청크 크기 제한 확인
                if current_size + line_size > max_chunk_size and chunk_buffer:
                    # 현재 청크 저장
                    chunks.append({
                        'type': 'untracked',
                        'path': file_path,
                        'diff': ''.join(chunk_buffer),
                        'chunk_info': f"라인 {line_count - len(chunk_buffer)}-{line_count - 1}"
                    })
                    chunk_buffer.clear()
                    current_size = 0
                
                chunk_buffer.append(line_with_prefix)
                current_size += line_size
                
                # 매우 긴 라인 처리
                if line_size > max_chunk_size:
                    # 긴 라인을 별도 청크로 분리
                    if len(chunk_buffer) > 1:
                        # 이전 라인들을 먼저 저장
                        chunk_buffer.pop()  # 긴 라인 제거
                        chunks.append({
                            'type': 'untracked',
                            'path': file_path,
                            'diff': ''.join(chunk_buffer)
                        })
                        chunk_buffer = [line_with_prefix]  # 긴 라인만 남김
                
                # 라인 수 제한 (DOS 방지)
                if line_count > 10000:
                    chunk_buffer.append("\n... (파일이 너무 깁니다. 처음 10000라인만 표시)")
                    break
            
            # 마지막 청크 저장
            if chunk_buffer:
                chunks.append({
                    'type': 'untracked',
                    'path': file_path,
                    'diff': ''.join(chunk_buffer)
                })
        
        return chunks

    def _is_binary_file(self, file_path: Path) -> bool:
        """파일이 바이너리인지 확인"""
        try:
            with file_path.open('rb') as f:
                # 첫 1024 바이트만 읽어서 확인
                chunk = f.read(1024)
                return b'\0' in chunk
        except Exception:
            return False

    def _split_diff_into_chunks(self, chunks: list, change_type: str, path: str, diff_text: str, max_chunk_size: int):
        """diff 텍스트를 청크로 분할"""
        if not diff_text:
            return

        if len(diff_text) <= max_chunk_size:
            chunks.append({
                'type': change_type, 
                'path': path, 
                'diff': diff_text
            })
            return

        # 헤더와 변경사항을 분리
        lines = diff_text.split('\n')
        header_lines = []
        content_lines = []
        
        for line in lines:
            if line.startswith(('---', '+++', '@@')):
                header_lines.append(line)
            else:
                content_lines.append(line)
        
        # 함수/클래스 단위로 청크 분할 시도
        chunks_by_function = self._split_by_logical_units(content_lines, header_lines, change_type, path, max_chunk_size)
        if chunks_by_function:
            chunks.extend(chunks_by_function)
        else:
            # 논리적 단위로 분할할 수 없으면 크기 기준으로 분할
            self._split_by_size(chunks, header_lines, content_lines, change_type, path, max_chunk_size)

    def _split_by_logical_units(self, lines: List[str], header_lines: List[str], 
                                change_type: str, path: str, max_chunk_size: int) -> List[Dict[str, str]]:
        """함수/클래스 등 논리적 단위로 분할"""
        chunks = []
        current_chunk_lines = header_lines.copy()
        current_size = sum(len(line) + 1 for line in current_chunk_lines)
        
        # 언어별 함수/클래스 시작 패턴
        function_patterns = [
            'def ', 'class ', 'function ', 'func ', 'const ', 'let ', 'var ',
            'public ', 'private ', 'protected ', 'static '
        ]
        
        for i, line in enumerate(lines):
            # 함수/클래스 시작 감지
            is_new_unit = any(pattern in line for pattern in function_patterns)
            line_size = len(line) + 1
            
            if is_new_unit and current_size > len('\n'.join(header_lines)) + 100:  # 최소 크기
                if current_size + line_size > max_chunk_size:
                    # 현재 청크 저장
                    chunks.append({
                        'type': change_type,
                        'path': path,
                        'diff': '\n'.join(current_chunk_lines)
                    })
                    current_chunk_lines = header_lines.copy()
                    current_size = sum(len(line) + 1 for line in current_chunk_lines)
            
            current_chunk_lines.append(line)
            current_size += line_size
            
            # 크기 초과시 강제 분할
            if current_size > max_chunk_size:
                chunks.append({
                    'type': change_type,
                    'path': path,
                    'diff': '\n'.join(current_chunk_lines)
                })
                current_chunk_lines = header_lines.copy()
                current_size = sum(len(line) + 1 for line in current_chunk_lines)
        
        # 마지막 청크
        if len(current_chunk_lines) > len(header_lines):
            chunks.append({
                'type': change_type,
                'path': path,
                'diff': '\n'.join(current_chunk_lines)
            })
            
        return chunks

    def _split_by_size(self, chunks: list, header_lines: List[str], content_lines: List[str],
                      change_type: str, path: str, max_chunk_size: int):
        """크기 기준으로 분할"""
        current_chunk_lines = header_lines.copy()
        current_size = sum(len(line) + 1 for line in current_chunk_lines)
        
        for line in content_lines:
            line_size = len(line) + 1
            if current_size + line_size > max_chunk_size and len(current_chunk_lines) > len(header_lines):
                chunks.append({
                    'type': change_type,
                    'path': path,
                    'diff': '\n'.join(current_chunk_lines)
                })
                current_chunk_lines = header_lines.copy()
                current_size = sum(len(line) + 1 for line in current_chunk_lines)
            
            current_chunk_lines.append(line)
            current_size += line_size

        if len(current_chunk_lines) > len(header_lines):
            chunks.append({
                'type': change_type,
                'path': path,
                'diff': '\n'.join(current_chunk_lines)
            })

    def _get_change_type(self, d: diff.Diff) -> str:
        if d.new_file: return 'added'
        if d.deleted_file: return 'deleted'
        if d.renamed: return 'renamed'
        return 'modified'
            
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
            return "커밋 없음"
            
    def get_file_content_stream(self, file_path: str) -> Iterator[str]:
        """파일 내용을 스트림으로 반환 (메모리 효율적, 보안 강화)"""
        # 파일 경로 보안 검증
        if not Config.validate_file_path(file_path, str(self.repo_path)):
            return
            
        full_path = self.repo_path / file_path
        
        if not full_path.exists() or not full_path.is_file():
            return
            
        try:
            with full_path.open('r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    if line_num > 10000:  # DOS 방지
                        break
                    yield line
        except (OSError, IOError, PermissionError):
            return  # 파일 읽기 오류시 빈 이터레이터 반환 