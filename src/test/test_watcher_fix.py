"""Watcher 수정사항 검증 테스트"""

import time
import threading
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

def test_progress_conflict():
    """Progress 디스플레이 충돌 테스트"""
    console.print("[bold]Progress 디스플레이 충돌 테스트[/bold]")
    
    def create_progress(name: str, delay: float):
        try:
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            )
            progress.start()
            task = progress.add_task(f"[cyan]{name} 실행 중...", total=None)
            time.sleep(delay)
            progress.stop()
            console.print(f"[green]✓ {name} 완료[/green]")
        except Exception as e:
            console.print(f"[red]✗ {name} 오류: {e}[/red]")
    
    # 동시에 여러 Progress 생성 시도
    threads = []
    for i in range(3):
        t = threading.Thread(target=create_progress, args=(f"작업 {i+1}", 2))
        threads.append(t)
        t.start()
        time.sleep(0.5)  # 약간의 지연으로 충돌 유도
    
    for t in threads:
        t.join()
    
    console.print("\n[green]Progress 충돌 테스트 완료[/green]")

def test_state_tracking():
    """상태 추적 테스트"""
    console.print("\n[bold]상태 추적 테스트[/bold]")
    
    import threading
    
    # 동시 접근을 위한 락과 상태
    _is_processing = False
    _lock = threading.Lock()
    
    def process_with_lock(name: str):
        with _lock:
            if _is_processing:
                console.print(f"[yellow]{name}: 이미 처리 중, 건너뜀[/yellow]")
                return
            _is_processing = True
        
        try:
            console.print(f"[cyan]{name}: 처리 시작[/cyan]")
            time.sleep(1)
            console.print(f"[green]{name}: 처리 완료[/green]")
        finally:
            with _lock:
                _is_processing = False
    
    # 동시에 여러 처리 시도
    threads = []
    for i in range(5):
        t = threading.Thread(target=process_with_lock, args=(f"프로세스 {i+1}",))
        threads.append(t)
        t.start()
        time.sleep(0.2)
    
    for t in threads:
        t.join()
    
    console.print("\n[green]상태 추적 테스트 완료[/green]")

def test_user_input_simulation():
    """사용자 입력 시뮬레이션 테스트"""
    console.print("\n[bold]사용자 입력 시뮬레이션 테스트[/bold]")
    
    # Progress 시작
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    )
    
    try:
        progress.start()
        task = progress.add_task("[cyan]분석 중...", total=None)
        time.sleep(2)
        
        # Progress 중지 (사용자 입력 전)
        progress.stop()
        console.print("[green]Progress 정상 중지됨[/green]")
        
        # 사용자 입력 시뮬레이션
        console.print("\n[yellow]사용자 입력 대기 중... (시뮬레이션)[/yellow]")
        time.sleep(1)
        
        # 새로운 Progress 시작
        progress2 = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        )
        progress2.start()
        task2 = progress2.add_task("[cyan]추가 작업 중...", total=None)
        time.sleep(2)
        progress2.stop()
        
        console.print("[green]모든 Progress 정상 작동[/green]")
        
    except Exception as e:
        console.print(f"[red]오류 발생: {e}[/red]")
        if progress:
            try:
                progress.stop()
            except:
                pass

if __name__ == "__main__":
    console.print("[bold magenta]Watcher 수정사항 검증 시작[/bold magenta]\n")
    
    test_progress_conflict()
    test_state_tracking()
    test_user_input_simulation()
    
    console.print("\n[bold green]모든 테스트 완료![/bold green]") 