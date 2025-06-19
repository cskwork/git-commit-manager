"""Git Commit Manager CLI 인터페이스"""

import click
import sys
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from .git_analyzer import GitAnalyzer
from .commit_analyzer import CommitAnalyzer
from .llm_providers import get_provider, OllamaProvider
from .watcher import GitWatcher
from .config import Config


console = Console()


@click.group()
def cli():
    """Git Commit Manager - AI 기반 커밋 메시지 생성 및 코드 리뷰 도구"""
    pass


def _check_and_suggest_ollama_model(model: Optional[str] = None) -> str:
    """Ollama 모델 확인 및 추천"""
    if model:
        return model
        
    # 사용 가능한 모델 확인
    available_models = OllamaProvider.get_available_models()
    
    if not available_models:
        console.print("[yellow]경고: Ollama에 설치된 모델이 없습니다.[/yellow]")
        console.print("[dim]모델을 설치하려면: ollama pull gemma3:1b[/dim]")
        console.print("[dim]또는 다른 프로바이더를 사용하세요: -p openrouter 또는 -p gemini[/dim]")
        sys.exit(1)
    
    # 모델 목록 표시
    console.print("\n[cyan]설치된 Ollama 모델:[/cyan]")
    for m in available_models:
        size_gb = m.size / (1024**3)
        console.print(f"  - {m.model} ({size_gb:.1f}GB)")
    
    # 추천 모델 가져오기
    suggested = OllamaProvider.suggest_model()
    
    if suggested:
        console.print(f"\n[green]추천 모델: {suggested}[/green]")
        return suggested
    else:
        # 추천할 모델이 없으면 첫 번째 모델 사용
        first_model = available_models[0].model
        console.print(f"\n[yellow]기본 모델 사용: {first_model}[/yellow]")
        return first_model


@cli.command()
@click.option('--provider', '-p', type=click.Choice(['ollama', 'openrouter', 'gemini']), 
              help='사용할 LLM 프로바이더 (기본값: .env의 DEFAULT_PROVIDER)')
@click.option('--model', '-m', help='사용할 모델 이름 (기본값: .env의 DEFAULT_MODEL)')
@click.option('--repo', '-r', default='.', help='Git 저장소 경로')
def watch(provider, model, repo):
    """Git 저장소 변경사항을 실시간으로 감시합니다."""
    try:
        # 설정에서 기본값 가져오기
        if provider is None:
            provider = Config.get_default_provider()
        if model is None:
            model = Config.get_default_model()
            
        # Git 분석기 초기화
        git_analyzer = GitAnalyzer(repo)
        
        # Ollama 사용 시 모델 확인
        if provider == 'ollama':
            model = _check_and_suggest_ollama_model(model)
            console.print(f"[dim]사용 모델: {model}[/dim]\n")
        
        # LLM 프로바이더 초기화
        console.print(f"[cyan]{provider} 프로바이더 초기화 중...[/cyan]")
        llm = get_provider(provider, model)
        
        # 커밋 분석기 초기화
        commit_analyzer = CommitAnalyzer(llm, git_analyzer)
        
        # 감시자 시작
        watcher = GitWatcher(repo, git_analyzer, commit_analyzer)
        watcher.start()
        
    except ValueError as e:
        console.print(f"[red]오류:[/red] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]감시가 중단되었습니다.[/yellow]")
        sys.exit(0)


@cli.command()
@click.option('--provider', '-p', type=click.Choice(['ollama', 'openrouter', 'gemini']), 
              help='사용할 LLM 프로바이더 (기본값: .env의 DEFAULT_PROVIDER)')
@click.option('--model', '-m', help='사용할 모델 이름 (기본값: .env의 DEFAULT_MODEL)')
@click.option('--repo', '-r', default='.', help='Git 저장소 경로')
def analyze(provider, model, repo):
    """현재 변경사항을 분석하고 커밋 메시지를 생성합니다."""
    try:
        # 설정에서 기본값 가져오기
        if provider is None:
            provider = Config.get_default_provider()
        if model is None:
            model = Config.get_default_model()
            
        # Git 분석기 초기화
        git_analyzer = GitAnalyzer(repo)
        
        # 변경사항 확인
        changes = git_analyzer.get_all_changes()
        if not any(changes.values()):
            console.print("[yellow]변경사항이 없습니다.[/yellow]")
            return
            
        # 변경사항 표시
        _display_changes_table(changes)
        
        # Ollama 사용 시 모델 확인
        if provider == 'ollama':
            model = _check_and_suggest_ollama_model(model)
            console.print(f"[dim]사용 모델: {model}[/dim]")
        
        # LLM 프로바이더 초기화
        console.print(f"\n[cyan]{provider} 프로바이더를 사용하여 분석 중...[/cyan]")
        llm = get_provider(provider, model)
        
        # 커밋 분석기 초기화
        commit_analyzer = CommitAnalyzer(llm, git_analyzer)
        
        # 커밋 메시지 생성
        chunks = git_analyzer.get_diff_chunks()
        commit_message = commit_analyzer.generate_commit_message(chunks)
        
        console.print("\n[bold green]추천 커밋 메시지:[/bold green]")
        console.print(commit_message)
        
        # 사용자 확인
        if Confirm.ask("\n이 커밋 메시지를 사용하시겠습니까?"):
            # git commit 명령어 표시
            console.print("\n[dim]다음 명령어를 실행하세요:[/dim]")
            first_line = commit_message.split("\n")[0]
            console.print(f'[cyan]git commit -m "{first_line}"[/cyan]')
            
    except ValueError as e:
        console.print(f"[red]오류:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.option('--provider', '-p', type=click.Choice(['ollama', 'openrouter', 'gemini']), 
              help='사용할 LLM 프로바이더 (기본값: .env의 DEFAULT_PROVIDER)')
@click.option('--model', '-m', help='사용할 모델 이름 (기본값: .env의 DEFAULT_MODEL)')
@click.option('--repo', '-r', default='.', help='Git 저장소 경로')
@click.option('--file', '-f', help='특정 파일만 리뷰')
def review(provider, model, repo, file):
    """변경된 코드에 대한 리뷰를 수행합니다."""
    try:
        # 설정에서 기본값 가져오기
        if provider is None:
            provider = Config.get_default_provider()
        if model is None:
            model = Config.get_default_model()
            
        # Git 분석기 초기화
        git_analyzer = GitAnalyzer(repo)
        
        # 변경사항 확인
        changes = git_analyzer.get_all_changes()
        if not any(changes.values()):
            console.print("[yellow]변경사항이 없습니다.[/yellow]")
            return
            
        # Ollama 사용 시 모델 확인
        if provider == 'ollama':
            model = _check_and_suggest_ollama_model(model)
            console.print(f"[dim]사용 모델: {model}[/dim]")
            
        # LLM 프로바이더 초기화
        console.print(f"[cyan]{provider} 프로바이더를 사용하여 코드 리뷰 중...[/cyan]")
        llm = get_provider(provider, model)
        
        # 커밋 분석기 초기화
        commit_analyzer = CommitAnalyzer(llm, git_analyzer)
        
        # 코드 리뷰 수행
        chunks = git_analyzer.get_diff_chunks()
        
        # 특정 파일만 필터링
        if file:
            chunks = [c for c in chunks if c.get('path') == file]
            if not chunks:
                console.print(f"[yellow]{file} 파일에 변경사항이 없습니다.[/yellow]")
                return
                
        reviews = commit_analyzer.review_code_changes(chunks)
        
        # 리뷰 결과 표시
        for i, review in enumerate(reviews, 1):
            console.print(f"\n[bold]리뷰 {i}/{len(reviews)}[/bold]")
            console.print(f"[yellow]파일:[/yellow] {review['file']}")
            console.print(f"[yellow]타입:[/yellow] {review['type']}")
            console.print("\n[bold]리뷰 내용:[/bold]")
            console.print(review['review'])
            console.print("-" * 50)
            
    except ValueError as e:
        console.print(f"[red]오류:[/red] {e}")
        sys.exit(1)


@cli.command()
def config():
    """설정 가이드를 표시합니다."""
    console.print("[bold]Git Commit Manager 설정 가이드[/bold]\n")
    
    console.print("1. [yellow]Ollama 설정:[/yellow]")
    console.print("   - Ollama 설치: https://ollama.ai")
    console.print("   - 추천 모델 설치: ollama pull gemma3:1b")
    console.print("   - 다른 추천 모델: qwen2.5-coder:1.5b, llama3.2:1b, codellama")
    console.print("   - 사용 예: gcm watch (모델 자동 선택)")
    console.print("   - 사용 예: gcm watch -p ollama -m gemma3:1b\n")
    
    console.print("2. [yellow]OpenRouter 설정:[/yellow]")
    console.print("   - API 키 발급: https://openrouter.ai")
    console.print("   - 환경변수 설정: export OPENROUTER_API_KEY='your-key'")
    console.print("   - 사용 예: gcm watch -p openrouter -m openai/gpt-3.5-turbo\n")
    
    console.print("3. [yellow]Gemini 설정:[/yellow]")
    console.print("   - API 키 발급: https://makersuite.google.com/app/apikey")
    console.print("   - 환경변수 설정: export GEMINI_API_KEY='your-key'")
    console.print("   - 사용 예: gcm watch -p gemini -m gemini-pro\n")
    
    console.print("4. [yellow].env 파일 생성 (선택사항):[/yellow]")
    console.print("   프로젝트 루트에 .env 파일을 생성하여 설정을 저장할 수 있습니다:")
    console.print("   ```")
    console.print("   # 기본 LLM 프로바이더 및 모델 설정")
    console.print("   DEFAULT_PROVIDER=ollama")
    console.print("   DEFAULT_MODEL=gemma3:1b")
    console.print("   ")
    console.print("   # API 키")
    console.print("   OPENROUTER_API_KEY=your-openrouter-key")
    console.print("   GEMINI_API_KEY=your-gemini-key")
    console.print("   ")
    console.print("   # 고급 설정")
    console.print("   DEBOUNCE_DELAY=3.0  # 파일 변경 후 대기 시간(초)")
    console.print("   COMMIT_MESSAGE_LANGUAGE=korean  # 커밋 메시지 언어")
    console.print("   AUTO_CODE_REVIEW=true  # 자동 코드 리뷰 활성화")
    console.print("   ```")
    console.print("\n   [dim].env.example 파일을 참고하여 설정하세요.[/dim]")
    
    # 현재 설치된 Ollama 모델 확인
    console.print("\n5. [yellow]현재 설치된 Ollama 모델:[/yellow]")
    models = OllamaProvider.get_available_models()
    if models:
        for m in models:
            size_gb = m.get('size', 0) / (1024**3)
            console.print(f"   - {m['name']} ({size_gb:.1f}GB)")
    else:
        console.print("   [dim]설치된 모델이 없습니다.[/dim]")


def _display_changes_table(changes: dict):
    """변경사항을 테이블로 표시"""
    table = Table(title="감지된 변경사항")
    table.add_column("상태", style="cyan")
    table.add_column("파일", style="magenta")
    
    for change_type, files in changes.items():
        if change_type == 'added' and files:
            for f in files:
                table.add_row("추가됨", f)
        elif change_type == 'modified' and files:
            for f in files:
                table.add_row("수정됨", f)
        elif change_type == 'deleted' and files:
            for f in files:
                table.add_row("삭제됨", f)
        elif change_type == 'renamed' and files:
            for old, new in files:
                table.add_row("이름변경", f"{old} → {new}")
        elif change_type == 'untracked' and files:
            for f in files:
                table.add_row("추적안됨", f)
                
    console.print(table)


def main():
    """메인 진입점"""
    cli()


if __name__ == '__main__':
    main() 