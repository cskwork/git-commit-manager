"""파일 시스템 변경사항 감시 모듈"""

import time
import hashlib
from pathlib import Path
from typing import Callable, Optional, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from .git_analyzer import GitAnalyzer
from .commit_analyzer import CommitAnalyzer
from .config import Config


console = Console()


class GitChangeHandler(FileSystemEventHandler):
    """Git 저장소 변경사항 처리 핸들러"""
    
    def __init__(self, git_analyzer: GitAnalyzer, commit_analyzer: CommitAnalyzer, 
                 on_change_callback: Optional[Callable] = None):
        self.git = git_analyzer
        self.commit_analyzer = commit_analyzer
        self.on_change_callback = on_change_callback
        self.last_check_time = time.time()
        self.debounce_seconds = Config.get_debounce_delay()  # 설정에서 디바운스 시간 가져오기
        self.pending_check = False
        self.last_processed_hash = None  # 마지막 처리된 변경사항의 해시값
        self._ignored_patterns = {'.git/', '__pycache__/', '.pyc', '.pyo', '.DS_Store'}
        
    def should_ignore(self, path: str) -> bool:
        """무시해야 할 파일/디렉토리인지 확인"""
        path_str = str(path)
        for pattern in self._ignored_patterns:
            if pattern in path_str:
                return True
        return False
    
    def _get_changes_hash(self) -> str:
        """현재 변경사항의 해시값 생성"""
        try:
            changes = self.git.get_all_changes()
            # 변경사항을 문자열로 변환하여 해시 생성
            changes_str = str(sorted(changes.items()))
            return hashlib.md5(changes_str.encode()).hexdigest()
        except Exception:
            # Git 상태를 읽을 수 없는 경우 현재 시간 기반 해시 반환
            return hashlib.md5(str(time.time()).encode()).hexdigest()
        
    def on_any_event(self, event: FileSystemEvent):
        """모든 파일 시스템 이벤트 처리"""
        if self.should_ignore(event.src_path):
            return
            
        # 디바운싱: 짧은 시간 내 여러 변경사항을 하나로 처리
        current_time = time.time()
        if current_time - self.last_check_time < self.debounce_seconds:
            self.pending_check = True
            return
            
        # 변경사항 해시 확인하여 중복 처리 방지
        current_hash = self._get_changes_hash()
        if current_hash == self.last_processed_hash:
            return
            
        self.last_check_time = current_time
        self.pending_check = False
        self.last_processed_hash = current_hash
        
        if self.on_change_callback:
            self.on_change_callback()


class GitWatcher:
    """Git 저장소 감시자"""
    
    def __init__(self, repo_path: str, git_analyzer: GitAnalyzer, 
                 commit_analyzer: CommitAnalyzer):
        self.repo_path = Path(repo_path).resolve()
        self.git = git_analyzer
        self.commit_analyzer = commit_analyzer
        self.observer = Observer()
        self.handler = GitChangeHandler(git_analyzer, commit_analyzer, 
                                      self.on_changes_detected)
        self.watching = False
        
    def on_changes_detected(self):
        """변경사항이 감지되었을 때 실행"""
        console.print("\n[yellow]변경사항 감지됨![/yellow]")
        
        # 변경사항 분석
        changes = self.git.get_all_changes()
        if not any(changes.values()):
            console.print("[dim]변경사항이 없습니다.[/dim]")
            return
            
        # 변경사항 표시
        self._display_changes(changes)
        
        # 커밋 메시지 생성
        console.print("\n[cyan]커밋 메시지 생성 중...[/cyan]")
        chunks = self.git.get_diff_chunks()
        commit_message = self.commit_analyzer.generate_commit_message(chunks)
        
        console.print(Panel(
            commit_message,
            title="[bold green]추천 커밋 메시지[/bold green]",
            border_style="green"
        ))
        
        # 설정에 따라 자동 코드 리뷰 수행
        if Config.is_auto_review_enabled():
            console.print("\n[cyan]코드 리뷰 수행 중...[/cyan]")
            reviews = self.commit_analyzer.review_code_changes(chunks)
            
            for review in reviews:
                console.print(Panel(
                    f"[yellow]파일:[/yellow] {review['file']}\n"
                    f"[yellow]타입:[/yellow] {review['type']}\n\n"
                    f"{review['review']}",
                    title="[bold blue]코드 리뷰[/bold blue]",
                    border_style="blue"
                ))
        else:
            console.print("\n[dim]자동 코드 리뷰가 비활성화되어 있습니다. (AUTO_CODE_REVIEW=false)[/dim]")
            
    def _display_changes(self, changes: dict):
        """변경사항을 보기 좋게 표시"""
        change_text = []
        
        if changes.get('added'):
            change_text.append("[green]추가된 파일:[/green]")
            for f in changes['added']:
                change_text.append(f"  + {f}")
                
        if changes.get('modified'):
            change_text.append("[yellow]수정된 파일:[/yellow]")
            for f in changes['modified']:
                change_text.append(f"  M {f}")
                
        if changes.get('deleted'):
            change_text.append("[red]삭제된 파일:[/red]")
            for f in changes['deleted']:
                change_text.append(f"  - {f}")
                
        if changes.get('renamed'):
            change_text.append("[blue]이름 변경된 파일:[/blue]")
            for old, new in changes['renamed']:
                change_text.append(f"  R {old} -> {new}")
                
        if changes.get('untracked'):
            change_text.append("[dim]추적되지 않은 파일:[/dim]")
            for f in changes['untracked']:
                change_text.append(f"  ? {f}")
                
        console.print(Panel(
            "\n".join(change_text),
            title="[bold]감지된 변경사항[/bold]",
            border_style="white"
        ))
        
    def start(self):
        """감시 시작"""
        if self.watching:
            console.print("[yellow]이미 감시 중입니다.[/yellow]")
            return
            
        self.observer.schedule(self.handler, str(self.repo_path), recursive=True)
        self.observer.start()
        self.watching = True
        
        console.print(f"[green]Git 저장소 감시 시작:[/green] {self.repo_path}")
        console.print("[dim]변경사항을 감지하면 자동으로 분석합니다. Ctrl+C로 종료하세요.[/dim]")
        
        try:
            while True:
                time.sleep(1)
                # 디바운싱된 체크 수행
                if self.handler.pending_check and \
                   time.time() - self.handler.last_check_time >= self.handler.debounce_seconds:
                    # 변경사항 해시 확인하여 중복 처리 방지
                    current_hash = self.handler._get_changes_hash()
                    if current_hash != self.handler.last_processed_hash:
                        self.handler.pending_check = False
                        self.handler.last_check_time = time.time()
                        self.handler.last_processed_hash = current_hash
                        self.on_changes_detected()
                    else:
                        self.handler.pending_check = False
        except KeyboardInterrupt:
            self.stop()
            
    def stop(self):
        """감시 중지"""
        if not self.watching:
            return
            
        self.observer.stop()
        self.observer.join()
        self.watching = False
        console.print("\n[red]감시 중지됨[/red]") 