"""파일 시스템 변경사항 감시 모듈"""

import time
import hashlib
import threading
import queue
from pathlib import Path
from typing import Callable, Optional, Set, Dict
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from .git_analyzer import GitAnalyzer
from .commit_analyzer import CommitAnalyzer
from .config import Config


console = Console()


class PerformanceMonitor:
    """성능 모니터링 클래스"""
    
    def __init__(self):
        self.stats = {
            'total_analyses': 0,
            'total_time': 0.0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0
        }
        
    def record_analysis(self, duration: float, cache_hit: bool = False):
        """분석 기록"""
        self.stats['total_analyses'] += 1
        self.stats['total_time'] += duration
        if cache_hit:
            self.stats['cache_hits'] += 1
        else:
            self.stats['cache_misses'] += 1
    
    def record_error(self):
        """에러 기록"""
        self.stats['errors'] += 1
    
    def get_stats(self) -> Dict[str, any]:
        """통계 반환"""
        avg_time = self.stats['total_time'] / max(1, self.stats['total_analyses'])
        cache_rate = self.stats['cache_hits'] / max(1, self.stats['cache_hits'] + self.stats['cache_misses'])
        
        return {
            '총 분석 횟수': self.stats['total_analyses'],
            '평균 분석 시간': f"{avg_time:.2f}초",
            '캐시 적중률': f"{cache_rate * 100:.1f}%",
            '오류 발생 횟수': self.stats['errors']
        }


class GitChangeHandler(FileSystemEventHandler):
    """Git 저장소 변경사항 처리 핸들러"""
    
    def __init__(self, git_analyzer: GitAnalyzer, commit_analyzer: CommitAnalyzer, 
                 on_change_callback: Optional[Callable] = None):
        self.git = git_analyzer
        self.commit_analyzer = commit_analyzer
        self.on_change_callback = on_change_callback
        self.last_check_time = time.time()
        self.debounce_seconds = Config.DEBOUNCE_DELAY
        self.pending_check = False
        self.last_processed_hash = None
        self._ignored_patterns = set(Config.IGNORE_PATTERNS)
        self.change_queue = queue.Queue()
        self.processing_thread = None
        self.running = False
        self.performance = PerformanceMonitor()
        
    def start_processing(self):
        """변경사항 처리 스레드 시작"""
        self.running = True
        self.processing_thread = threading.Thread(target=self._process_changes, daemon=True)
        self.processing_thread.start()
    
    def stop_processing(self):
        """변경사항 처리 스레드 중지"""
        self.running = False
        self.change_queue.put(None)  # 종료 신호
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
    
    def _process_changes(self):
        """변경사항 처리 (별도 스레드)"""
        while self.running:
            try:
                # 큐에서 변경사항 가져오기 (타임아웃 설정)
                item = self.change_queue.get(timeout=1)
                if item is None:  # 종료 신호
                    break
                    
                # 디바운싱
                time.sleep(self.debounce_seconds)
                
                # 큐에 있는 중복 항목 제거
                while not self.change_queue.empty():
                    try:
                        self.change_queue.get_nowait()
                    except queue.Empty:
                        break
                
                # 변경사항 처리
                if self.on_change_callback:
                    start_time = time.time()
                    try:
                        self.on_change_callback()
                        duration = time.time() - start_time
                        self.performance.record_analysis(duration)
                    except Exception as e:
                        console.print(f"[red]오류 발생: {e}[/red]")
                        self.performance.record_error()
                        
            except queue.Empty:
                continue
            except Exception as e:
                console.print(f"[red]처리 스레드 오류: {e}[/red]")
                self.performance.record_error()
        
    def should_ignore(self, path: str) -> bool:
        """무시해야 할 파일/디렉토리인지 확인"""
        path_str = str(path)
        return any(pattern in path_str for pattern in self._ignored_patterns)
    
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
        
        # 이벤트를 큐에 추가
        try:
            self.change_queue.put_nowait(event)
        except queue.Full:
            pass  # 큐가 가득 찬 경우 무시


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
        self.last_analysis_time = None
        self.analysis_count = 0
        
    def on_changes_detected(self):
        """변경사항이 감지되었을 때 실행"""
        self.analysis_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        console.print(f"\n[yellow]변경사항 감지됨! [{timestamp}][/yellow]")
        
        # 변경사항 해시 확인
        current_hash = self.handler._get_changes_hash()
        if current_hash == self.handler.last_processed_hash:
            console.print("[dim]이미 처리된 변경사항입니다.[/dim]")
            return
        
        try:
            # Progress spinner로 분석 상태 표시
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                # 변경사항 분석
                analyze_task = progress.add_task("[cyan]변경사항 분석 중...", total=None)
                
                changes = self.git.get_all_changes()
                if not any(changes.values()):
                    console.print("[dim]변경사항이 없습니다.[/dim]")
                    return
                
                # 변경사항 표시
                self._display_changes(changes)
                
                # 커밋 메시지 생성
                progress.update(analyze_task, description="[cyan]커밋 메시지 생성 중...")
                
                chunks = self.git.get_diff_chunks()
                if not chunks:
                    console.print("[yellow]분석할 변경사항이 없습니다.[/yellow]")
                    return
                    
                commit_message = self.commit_analyzer.generate_commit_message(chunks)
                
                # 결과 표시
                console.print(Panel(
                    commit_message,
                    title="[bold green]추천 커밋 메시지[/bold green]",
                    border_style="green",
                    padding=(1, 2)
                ))
                
                # 자동 코드 리뷰
                if Config.AUTO_CODE_REVIEW:
                    progress.update(analyze_task, description="[cyan]코드 리뷰 실행 중...")
                    
                    reviews = self.commit_analyzer.review_code_changes(chunks)
                    
                    if reviews:
                        console.print(f"\n[bold blue]코드 리뷰 결과 ({len(reviews)}개 파일)[/bold blue]")
                        for i, review in enumerate(reviews, 1):
                            console.print(Panel(
                                f"[yellow]파일:[/yellow] {review['file']}\n"
                                f"[yellow]변경:[/yellow] {review['type']}\n\n"
                                f"{review['review']}",
                                title=f"[bold blue]리뷰 {i}/{len(reviews)}[/bold blue]",
                                border_style="blue",
                                padding=(1, 2)
                            ))
                    else:
                        console.print("\n[green]✓ 코드가 깔끔합니다! 리뷰할 내용이 없습니다.[/green]")
                else:
                    console.print("\n[dim]자동 코드 리뷰가 비활성화되어 있습니다.[/dim]")
            
            # 성공적으로 처리된 해시 저장
            self.handler.last_processed_hash = current_hash
            self.last_analysis_time = datetime.now()
            
            # 통계 표시
            if self.analysis_count % 10 == 0:  # 10번마다 통계 표시
                self._display_statistics()
                
        except Exception as e:
            console.print(f"[red]분석 중 오류 발생: {e}[/red]")
            self.handler.performance.record_error()
            # 스택 트레이스 표시 (디버깅용)
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            
    def _display_changes(self, changes: dict):
        """변경사항을 보기 좋게 표시"""
        change_text = []
        total_changes = sum(len(files) for files in changes.values())
        
        if changes.get('added'):
            change_text.append(f"[green]추가: {len(changes['added'])}개[/green]")
            for f in changes['added'][:3]:  # 처음 3개만 표시
                change_text.append(f"  + {f}")
            if len(changes['added']) > 3:
                change_text.append(f"  ... 외 {len(changes['added']) - 3}개")
                
        if changes.get('modified'):
            change_text.append(f"[yellow]수정: {len(changes['modified'])}개[/yellow]")
            for f in changes['modified'][:3]:
                change_text.append(f"  M {f}")
            if len(changes['modified']) > 3:
                change_text.append(f"  ... 외 {len(changes['modified']) - 3}개")
                
        if changes.get('deleted'):
            change_text.append(f"[red]삭제: {len(changes['deleted'])}개[/red]")
            for f in changes['deleted'][:3]:
                change_text.append(f"  - {f}")
            if len(changes['deleted']) > 3:
                change_text.append(f"  ... 외 {len(changes['deleted']) - 3}개")
                
        if changes.get('renamed'):
            change_text.append(f"[blue]이름변경: {len(changes['renamed'])}개[/blue]")
            for old, new in changes['renamed'][:2]:
                change_text.append(f"  R {old} → {new}")
            if len(changes['renamed']) > 2:
                change_text.append(f"  ... 외 {len(changes['renamed']) - 2}개")
                
        if changes.get('untracked'):
            change_text.append(f"[dim]추적안됨: {len(changes['untracked'])}개[/dim]")
            for f in changes['untracked'][:3]:
                change_text.append(f"  ? {f}")
            if len(changes['untracked']) > 3:
                change_text.append(f"  ... 외 {len(changes['untracked']) - 3}개")
                
        console.print(Panel(
            "\n".join(change_text),
            title=f"[bold]감지된 변경사항 (총 {total_changes}개)[/bold]",
            border_style="white",
            padding=(1, 2)
        ))
        
    def _display_statistics(self):
        """통계 정보 표시"""
        stats = self.handler.performance.get_stats()
        stat_lines = [f"{k}: {v}" for k, v in stats.items()]
        
        console.print(Panel(
            "\n".join(stat_lines),
            title="[bold cyan]성능 통계[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        ))
        
    def start(self):
        """감시 시작"""
        if self.watching:
            console.print("[yellow]이미 감시 중입니다.[/yellow]")
            return
        
        # 처리 스레드 시작
        self.handler.start_processing()
        
        # 파일 시스템 감시 시작
        self.observer.schedule(self.handler, str(self.repo_path), recursive=True)
        self.observer.start()
        self.watching = True
        
        # 시작 메시지
        console.print(Panel(
            f"[green]Git 저장소 감시 시작[/green]\n\n"
            f"경로: {self.repo_path}\n"
            f"모델: {self.commit_analyzer.llm.model_name if hasattr(self.commit_analyzer.llm, 'model_name') else 'Unknown'}\n"
            f"언어: {Config.COMMIT_MESSAGE_LANGUAGE}\n"
            f"자동 리뷰: {'활성화' if Config.AUTO_CODE_REVIEW else '비활성화'}\n"
            f"캐싱: {'활성화' if Config.ENABLE_CACHE else '비활성화'}\n\n"
            f"[dim]변경사항을 감지하면 자동으로 분석합니다. Ctrl+C로 종료하세요.[/dim]",
            title="[bold]Git Commit Manager[/bold]",
            border_style="green",
            padding=(1, 2)
        ))
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
            
    def stop(self):
        """감시 중지"""
        if not self.watching:
            return
        
        console.print("\n[yellow]감시를 중지하는 중...[/yellow]")
        
        # 처리 스레드 중지
        self.handler.stop_processing()
        
        # 파일 시스템 감시 중지
        self.observer.stop()
        self.observer.join()
        self.watching = False
        
        # 최종 통계 표시
        self._display_statistics()
        
        console.print("[red]감시가 중지되었습니다.[/red]") 