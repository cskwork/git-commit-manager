"""Git Commit Manager CLI 인터페이스"""

import click
import sys
import os
from functools import wraps
from pathlib import Path
from typing import Optional, Callable, List
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel
from .git_analyzer import GitAnalyzer
from .commit_analyzer import CommitAnalyzer
from .llm_providers import get_provider, OllamaProvider, LLMProviderError
from .watcher import GitWatcher
from .config import Config


console = Console()


def handle_errors(f: Callable) -> Callable:
    """에러 처리 데코레이터"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except LLMProviderError as e:
            console.print(f"[red]LLM 프로바이더 오류: {e}[/red]")
            console.print("[yellow]팁: API 키나 모델 설정을 확인해주세요.[/yellow]")
            sys.exit(1)
        except ValueError as e:
            console.print(f"[red]오류: {e}[/red]")
            sys.exit(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]작업이 취소되었습니다.[/yellow]")
            sys.exit(0)
        except Exception as e:
            console.print(f"[red]예상치 못한 오류: {e}[/red]")
            if "--debug" in sys.argv:
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
            sys.exit(1)
    return wrapper


def _initialize_analysis(ctx: click.Context, provider: Optional[str], model: Optional[str], repo: str):
    """Helper to initialize GitAnalyzer, LLM provider, and CommitAnalyzer."""
    try:
        if provider is None:
            provider = Config.DEFAULT_PROVIDER
        if model is None:
            model = Config.DEFAULT_MODEL

        git_analyzer = GitAnalyzer(repo)

        if provider == 'ollama':
            model = _check_and_suggest_ollama_model(model)
            console.print(f"[dim]사용 모델: {model}[/dim]\n")

        console.print(f"[cyan]{provider} 프로바이더 초기화 중...[/cyan]")
        llm = get_provider(provider, model)
        
        commit_analyzer = CommitAnalyzer(llm, git_analyzer)

        ctx.obj = {
            'git_analyzer': git_analyzer,
            'commit_analyzer': commit_analyzer,
            'provider': provider,
            'model': model
        }
    except ValueError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"초기화 오류: {e}")


def analysis_options(f: Callable) -> Callable:
    """Decorator for common analysis command options."""
    @click.option('--provider', '-p', type=click.Choice(['ollama', 'openrouter', 'gemini']), 
                  help='사용할 LLM 프로바이더 (기본값: .env의 DEFAULT_PROVIDER)')
    @click.option('--model', '-m', help='사용할 모델 이름 (기본값: .env의 DEFAULT_MODEL)')
    @click.option('--repo', '-r', default='.', help='Git 저장소 경로')
    @click.option('--no-cache', is_flag=True, help='캐시 사용 안함')
    @wraps(f)
    def wrapper(provider: Optional[str], model: Optional[str], repo: str, no_cache: bool, *args, **kwargs):
        if no_cache:
            Config.ENABLE_CACHE = False
        ctx = click.get_current_context()
        _initialize_analysis(ctx, provider, model, repo)
        return f(*args, **kwargs)
    return wrapper


@click.group()
@click.option('--debug', is_flag=True, help='디버그 모드 활성화')
def cli(debug: bool):
    """Git Commit Manager - AI 기반 커밋 메시지 생성 및 코드 리뷰 도구"""
    if debug:
        console.print("[dim]디버그 모드 활성화됨[/dim]")


def _check_and_suggest_ollama_model(model: Optional[str] = None) -> str:
    """Ollama 모델 확인 및 추천"""
    if model:
        return model
        
    # 사용 가능한 모델 확인
    available_models = OllamaProvider.get_available_models()
    
    if not available_models:
        console.print(Panel(
            "[yellow]Ollama에 설치된 모델이 없습니다.[/yellow]\n\n"
            "다음 명령어로 모델을 설치하세요:\n"
            "[cyan]ollama pull deepseek-r1:1.5b[/cyan] (추천)\n"
            "[cyan]ollama pull qwen2.5-coder:1.5b[/cyan]\n"
            "[cyan]ollama pull gemma3:1b[/cyan]\n\n"
            "또는 다른 프로바이더를 사용하세요:\n"
            "[dim]-p openrouter 또는 -p gemini[/dim]",
            title="[bold red]모델 없음[/bold red]",
            border_style="red"
        ))
        raise click.ClickException("Ollama 모델이 없습니다.")
    
    # 모델 목록 표시
    table = Table(title="설치된 Ollama 모델", show_header=True, header_style="bold cyan")
    table.add_column("모델명", style="green")
    table.add_column("크기", style="yellow", justify="right")
    table.add_column("추천", style="cyan", justify="center")
    
    suggested = OllamaProvider.suggest_model()
    
    for m in available_models:
        size_gb = m.get('size', 0) / (1024**3)
        is_recommended = m['name'] == suggested or (suggested and suggested in m['name'])
        table.add_row(
            m['name'], 
            f"{size_gb:.1f}GB",
            "✓" if is_recommended else ""
        )
    
    console.print(table)
    
    if suggested:
        console.print(f"\n[green]추천 모델: {suggested}[/green]")
        return suggested
    else:
        # 추천할 모델이 없으면 첫 번째 모델 사용
        first_model = available_models[0]['name']
        console.print(f"\n[yellow]기본 모델 사용: {first_model}[/yellow]")
        return first_model


@cli.command()
@analysis_options
@handle_errors
def watch():
    """Git 저장소 변경사항을 실시간으로 감시합니다."""
    ctx = click.get_current_context()
    git_analyzer = ctx.obj['git_analyzer']
    commit_analyzer = ctx.obj['commit_analyzer']
    
    watcher = GitWatcher(git_analyzer.repo_path, git_analyzer, commit_analyzer)
    watcher.start()


@cli.command()
@analysis_options
@handle_errors
def analyze():
    """현재 변경사항을 분석하고 커밋 메시지를 생성합니다."""
    ctx = click.get_current_context()
    git_analyzer = ctx.obj['git_analyzer']
    commit_analyzer = ctx.obj['commit_analyzer']

    changes = git_analyzer.get_all_changes()
    if not any(changes.values()):
        console.print("[yellow]변경사항이 없습니다.[/yellow]")
        return
            
    _display_changes_table(changes)
    
    with console.status("[cyan]커밋 메시지 생성 중...[/cyan]"):
        chunks = git_analyzer.get_diff_chunks()
        commit_message = commit_analyzer.generate_commit_message(chunks)
    
    console.print(Panel(
        commit_message,
        title="[bold green]추천 커밋 메시지[/bold green]",
        border_style="green",
        padding=(1, 2)
    ))
    
    if Confirm.ask("\n이 커밋 메시지를 사용하시겠습니까?"):
        # Git 명령어 생성
        first_line = commit_message.split("\n")[0]
        remaining_lines = commit_message.split("\n")[1:]
        
        console.print("\n[dim]다음 명령어를 실행하세요:[/dim]")
        
        if remaining_lines and any(line.strip() for line in remaining_lines):
            # 여러 줄 커밋 메시지
            console.print(f'[cyan]git commit -m "{first_line}" -m "{" ".join(remaining_lines).strip()}"[/cyan]')
        else:
            # 단일 줄 커밋 메시지
            console.print(f'[cyan]git commit -m "{first_line}"[/cyan]')
            
        # 클립보드에 복사 옵션
        if Confirm.ask("\n커밋 메시지를 클립보드에 복사하시겠습니까?", default=False):
            try:
                import pyperclip
                pyperclip.copy(commit_message)
                console.print("[green]✓ 클립보드에 복사되었습니다.[/green]")
            except ImportError:
                console.print("[yellow]pyperclip이 설치되지 않아 복사할 수 없습니다.[/yellow]")
                console.print("[dim]설치: pip install pyperclip[/dim]")


@cli.command()
@click.option('--file', '-f', help='특정 파일만 리뷰')
@click.option('--type', '-t', type=click.Choice(['all', 'added', 'modified', 'deleted']), 
              default='all', help='리뷰할 변경 타입')
@analysis_options
@handle_errors
def review(file: Optional[str], type: str):
    """변경된 코드에 대한 리뷰를 수행합니다."""
    ctx = click.get_current_context()
    git_analyzer = ctx.obj['git_analyzer']
    commit_analyzer = ctx.obj['commit_analyzer']

    changes = git_analyzer.get_all_changes()
    if not any(changes.values()):
        console.print("[yellow]변경사항이 없습니다.[/yellow]")
        return
    
    with console.status("[cyan]코드 리뷰 중...[/cyan]"):
        chunks = git_analyzer.get_diff_chunks()
        
        # 필터링
        if file:
            chunks = [c for c in chunks if c.get('path') == file]
            if not chunks:
                console.print(f"[yellow]{file} 파일에 변경사항이 없습니다.[/yellow]")
                return
        
        if type != 'all':
            chunks = [c for c in chunks if c.get('type') == type]
            if not chunks:
                console.print(f"[yellow]{type} 타입의 변경사항이 없습니다.[/yellow]")
                return
                
        reviews = commit_analyzer.review_code_changes(chunks)
    
    if not reviews:
        console.print("[green]✓ 코드가 완벽합니다! 리뷰할 내용이 없습니다.[/green]")
        return

    console.print(f"\n[bold]코드 리뷰 결과 ({len(reviews)}개 파일)[/bold]\n")
    
    for i, review_item in enumerate(reviews, 1):
        severity = _get_review_severity(review_item['review'])
        border_color = {
            'critical': 'red',
            'warning': 'yellow',
            'info': 'blue'
        }.get(severity, 'blue')
        
        console.print(Panel(
            f"[yellow]파일:[/yellow] {review_item['file']}\n"
            f"[yellow]변경:[/yellow] {review_item['type']}\n"
            f"[yellow]심각도:[/yellow] {severity}\n\n"
            f"{review_item['review']}",
            title=f"[bold]리뷰 {i}/{len(reviews)}[/bold]",
            border_style=border_color,
            padding=(1, 2)
        ))


def _get_review_severity(review_text: str) -> str:
    """리뷰 내용에서 심각도 추출"""
    review_lower = review_text.lower()
    if any(word in review_lower for word in ['오류', '버그', 'error', 'bug', '취약', 'vulnerability']):
        return 'critical'
    elif any(word in review_lower for word in ['주의', '개선', 'warning', 'improve', '성능']):
        return 'warning'
    return 'info'


@cli.command()
@handle_errors
def cache():
    """캐시 관리 명령어"""
    cache_dir = Config.get_cache_dir()
    cache_files = list(cache_dir.glob("*.json"))
    
    if not cache_files:
        console.print("[yellow]캐시가 비어있습니다.[/yellow]")
        return
    
    # 캐시 통계
    total_size = sum(f.stat().st_size for f in cache_files)
    size_mb = total_size / (1024 * 1024)
    
    console.print(Panel(
        f"캐시 디렉토리: {cache_dir}\n"
        f"캐시 파일 수: {len(cache_files)}개\n"
        f"총 크기: {size_mb:.2f}MB\n"
        f"캐시 TTL: {Config.CACHE_TTL_SECONDS}초",
        title="[bold]캐시 정보[/bold]",
        border_style="cyan"
    ))
    
    if Confirm.ask("\n캐시를 삭제하시겠습니까?", default=False):
        for f in cache_files:
            f.unlink()
        console.print("[green]✓ 캐시가 삭제되었습니다.[/green]")


@cli.command()
@handle_errors
def models():
    """사용 가능한 모델 목록을 표시합니다."""
    console.print("[bold]사용 가능한 모델[/bold]\n")
    
    # Ollama 모델
    console.print("[yellow]Ollama (로컬):[/yellow]")
    ollama_models = OllamaProvider.get_available_models()
    if ollama_models:
        for m in ollama_models:
            size_gb = m.get('size', 0) / (1024**3)
            console.print(f"  - {m['name']} ({size_gb:.1f}GB)")
    else:
        console.print("  [dim]설치된 모델 없음[/dim]")
        console.print("  [dim]설치: ollama pull deepseek-r1:1.5b[/dim]")
    
    # OpenRouter 모델
    console.print("\n[yellow]OpenRouter (API):[/yellow]")
    openrouter_models = [
        "openai/gpt-3.5-turbo",
        "openai/gpt-4",
        "anthropic/claude-2",
        "meta-llama/llama-2-70b-chat"
    ]
    for m in openrouter_models:
        console.print(f"  - {m}")
    console.print("  [dim]더 많은 모델: https://openrouter.ai/models[/dim]")
    
    # Gemini 모델
    console.print("\n[yellow]Google Gemini (API):[/yellow]")
    gemini_models = ["gemini-pro", "gemini-pro-vision"]
    for m in gemini_models:
        console.print(f"  - {m}")


@cli.command()
@handle_errors
def config():
    """설정 가이드를 표시합니다."""
    console.print(Panel(
        "[bold]Git Commit Manager 설정 가이드[/bold]\n\n"
        "1. [yellow]빠른 시작:[/yellow]\n"
        "   gcm watch  # deepseek-r1:1.5b 모델로 자동 시작\n\n"
        "2. [yellow]Ollama 설정 (추천):[/yellow]\n"
        "   - 설치: https://ollama.ai\n"
        "   - 모델 설치: ollama pull deepseek-r1:1.5b\n"
        "   - 다른 추천: qwen2.5-coder:1.5b, gemma3:1b\n\n"
        "3. [yellow]환경 설정 (.env):[/yellow]\n"
        "   DEFAULT_PROVIDER=ollama\n"
        "   DEFAULT_MODEL=deepseek-r1:1.5b\n"
        "   COMMIT_MESSAGE_LANGUAGE=korean\n"
        "   AUTO_CODE_REVIEW=true\n"
        "   ENABLE_CACHE=true\n\n"
        "4. [yellow]고급 설정:[/yellow]\n"
        "   - 캐시 관리: gcm cache\n"
        "   - 모델 목록: gcm models\n"
        "   - 통계 확인: watch 모드에서 자동 표시",
        title="[bold cyan]설정 가이드[/bold cyan]",
        border_style="cyan",
        padding=(1, 2)
    ))
    
    # 현재 설정 표시
    console.print("\n[bold]현재 설정:[/bold]")
    settings_table = Table(show_header=False)
    settings_table.add_column("항목", style="cyan")
    settings_table.add_column("값", style="green")
    
    settings = [
        ("기본 프로바이더", Config.DEFAULT_PROVIDER),
        ("기본 모델", Config.DEFAULT_MODEL),
        ("언어", Config.COMMIT_MESSAGE_LANGUAGE),
        ("자동 리뷰", "활성화" if Config.AUTO_CODE_REVIEW else "비활성화"),
        ("캐싱", "활성화" if Config.ENABLE_CACHE else "비활성화"),
        ("디바운스 시간", f"{Config.DEBOUNCE_DELAY}초")
    ]
    
    for key, value in settings:
        settings_table.add_row(key, str(value))
    
    console.print(settings_table)


def _display_changes_table(changes: dict):
    """변경사항을 테이블로 표시"""
    table = Table(title="감지된 변경사항", show_header=True, header_style="bold")
    table.add_column("상태", style="cyan", width=10)
    table.add_column("파일", style="magenta")
    
    total_files = 0
    
    for change_type, files in changes.items():
        if change_type == 'added' and files:
            for f in files[:10]:  # 최대 10개만 표시
                table.add_row("추가됨", f)
                total_files += 1
            if len(files) > 10:
                table.add_row("[dim]...[/dim]", f"[dim]외 {len(files) - 10}개[/dim]")
        elif change_type == 'modified' and files:
            for f in files[:10]:
                table.add_row("수정됨", f)
                total_files += 1
            if len(files) > 10:
                table.add_row("[dim]...[/dim]", f"[dim]외 {len(files) - 10}개[/dim]")
        elif change_type == 'deleted' and files:
            for f in files[:10]:
                table.add_row("삭제됨", f)
                total_files += 1
            if len(files) > 10:
                table.add_row("[dim]...[/dim]", f"[dim]외 {len(files) - 10}개[/dim]")
        elif change_type == 'renamed' and files:
            for old, new in files[:5]:
                table.add_row("이름변경", f"{old} → {new}")
                total_files += 1
            if len(files) > 5:
                table.add_row("[dim]...[/dim]", f"[dim]외 {len(files) - 5}개[/dim]")
        elif change_type == 'untracked' and files:
            for f in files[:10]:
                table.add_row("추적안됨", f)
                total_files += 1
            if len(files) > 10:
                table.add_row("[dim]...[/dim]", f"[dim]외 {len(files) - 10}개[/dim]")
    
    console.print(table)
    console.print(f"\n[bold]총 {sum(len(f) if not isinstance(f, list) else len(f) for f in changes.values())}개 파일[/bold]")


def main():
    """메인 진입점"""
    cli()


if __name__ == '__main__':
    main() 