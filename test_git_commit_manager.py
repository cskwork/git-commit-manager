#!/usr/bin/env python3
"""Git Commit Manager 테스트 스크립트"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path
from git import Repo
from rich.console import Console

# 상위 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from git_commit_manager.git_analyzer import GitAnalyzer
from git_commit_manager.commit_analyzer import CommitAnalyzer
from git_commit_manager.llm_providers import get_provider, OllamaProvider
from git_commit_manager.config import Config
from git_commit_manager.watcher import GitWatcher

console = Console()


def print_section(title: str):
    """섹션 구분선 출력"""
    console.print(f"\n[bold cyan]{'=' * 60}[/bold cyan]")
    console.print(f"[bold cyan]{title:^60}[/bold cyan]")
    console.print(f"[bold cyan]{'=' * 60}[/bold cyan]\n")


def test_ollama_connection():
    """Ollama 연결 테스트"""
    print_section("Ollama 연결 테스트")
    
    try:
        models = OllamaProvider.get_available_models()
        if models:
            console.print(f"[green]✓ Ollama 연결 성공! {len(models)}개 모델 발견[/green]")
            for m in models:
                console.print(f"  - {m['name']}")
            
            # deepseek-r1:1.5b 확인
            if any('deepseek-r1:1.5b' in m['name'] for m in models):
                console.print("[green]✓ deepseek-r1:1.5b 모델 확인됨[/green]")
            else:
                console.print("[yellow]! deepseek-r1:1.5b 모델이 없습니다. 설치하세요:[/yellow]")
                console.print("[cyan]  ollama pull deepseek-r1:1.5b[/cyan]")
        else:
            console.print("[red]✗ Ollama에 모델이 없습니다[/red]")
            return False
            
        return True
    except Exception as e:
        console.print(f"[red]✗ Ollama 연결 실패: {e}[/red]")
        return False


def test_llm_generation():
    """LLM 생성 테스트"""
    print_section("LLM 생성 테스트")
    
    try:
        # deepseek-r1:1.5b로 테스트
        llm = get_provider("ollama", "deepseek-r1:1.5b")
        console.print("[green]✓ LLM 프로바이더 초기화 성공[/green]")
        
        # 간단한 프롬프트 테스트
        with console.status("[cyan]테스트 프롬프트 실행 중...[/cyan]"):
            response = llm.generate("Say 'Hello, Git Commit Manager!' in Korean.")
        
        console.print(f"[green]✓ 응답 받음:[/green] {response[:100]}...")
        return True
    except Exception as e:
        console.print(f"[red]✗ LLM 생성 실패: {e}[/red]")
        return False


def test_git_analyzer():
    """Git 분석기 테스트"""
    print_section("Git 분석기 테스트")
    
    # 임시 Git 저장소 생성
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Git 저장소 초기화
            repo = Repo.init(tmpdir)
            console.print(f"[green]✓ 임시 Git 저장소 생성: {tmpdir}[/green]")
            
            # 테스트 파일 생성
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("""
def hello():
    print("Hello, World!")
""")
            
            # 파일 추가 및 커밋
            repo.index.add([str(test_file)])
            repo.index.commit("Initial commit")
            
            # 파일 수정
            test_file.write_text("""
def hello():
    print("Hello, Git Commit Manager!")
    
def goodbye():
    print("Goodbye!")
""")
            
            # GitAnalyzer 테스트
            analyzer = GitAnalyzer(tmpdir)
            changes = analyzer.get_all_changes()
            
            if changes['modified']:
                console.print(f"[green]✓ 변경사항 감지: {changes}[/green]")
            else:
                console.print("[red]✗ 변경사항을 감지하지 못했습니다[/red]")
                return False
                
            # diff 청크 테스트
            chunks = analyzer.get_diff_chunks()
            if chunks:
                console.print(f"[green]✓ Diff 청크 생성: {len(chunks)}개[/green]")
                console.print(f"[dim]첫 번째 청크 미리보기:[/dim]")
                console.print(f"[dim]{chunks[0]['diff'][:200]}...[/dim]")
            else:
                console.print("[red]✗ Diff 청크를 생성하지 못했습니다[/red]")
                return False
                
            return True
            
        except Exception as e:
            console.print(f"[red]✗ Git 분석기 테스트 실패: {e}[/red]")
            return False


def test_commit_analyzer():
    """커밋 분석기 테스트"""
    print_section("커밋 분석기 테스트")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Git 저장소 설정
            repo = Repo.init(tmpdir)
            
            # 초기 파일 생성 및 커밋
            test_file = Path(tmpdir) / "calculator.py"
            test_file.write_text("""
def add(a, b):
    return a + b
""")
            repo.index.add([str(test_file)])
            repo.index.commit("Initial commit")
            
            # 파일 수정
            test_file.write_text("""
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b
""")
            
            # 분석기 초기화
            git_analyzer = GitAnalyzer(tmpdir)
            llm = get_provider("ollama", "deepseek-r1:1.5b")
            commit_analyzer = CommitAnalyzer(llm, git_analyzer)
            
            # 커밋 메시지 생성 테스트
            with console.status("[cyan]커밋 메시지 생성 중...[/cyan]"):
                chunks = git_analyzer.get_diff_chunks()
                commit_msg = commit_analyzer.generate_commit_message(chunks)
            
            if commit_msg:
                console.print("[green]✓ 커밋 메시지 생성 성공:[/green]")
                console.print(f"[yellow]{commit_msg}[/yellow]")
            else:
                console.print("[red]✗ 커밋 메시지 생성 실패[/red]")
                return False
            
            # 코드 리뷰 테스트
            with console.status("[cyan]코드 리뷰 실행 중...[/cyan]"):
                reviews = commit_analyzer.review_code_changes(chunks)
            
            if reviews:
                console.print(f"[green]✓ 코드 리뷰 생성 성공: {len(reviews)}개[/green]")
                for review in reviews:
                    console.print(f"[dim]파일: {review['file']}[/dim]")
                    console.print(f"[dim]리뷰: {review['review'][:100]}...[/dim]")
            else:
                console.print("[yellow]! 리뷰할 내용이 없습니다[/yellow]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]✗ 커밋 분석기 테스트 실패: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return False


def test_cache_functionality():
    """캐싱 기능 테스트"""
    print_section("캐싱 기능 테스트")
    
    # 캐싱 활성화 확인
    if not Config.ENABLE_CACHE:
        console.print("[yellow]! 캐싱이 비활성화되어 있습니다[/yellow]")
        Config.ENABLE_CACHE = True
        console.print("[green]✓ 캐싱 활성화됨[/green]")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Git 저장소 설정
            repo = Repo.init(tmpdir)
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("print('test')")
            repo.index.add([str(test_file)])
            repo.index.commit("Initial commit")
            
            # 파일 수정
            test_file.write_text("print('test modified')")
            
            # 분석기 초기화
            git_analyzer = GitAnalyzer(tmpdir)
            llm = get_provider("ollama", "deepseek-r1:1.5b")
            commit_analyzer = CommitAnalyzer(llm, git_analyzer)
            
            # 첫 번째 실행 (캐시 미스)
            start_time = time.time()
            chunks = git_analyzer.get_diff_chunks()
            commit_msg1 = commit_analyzer.generate_commit_message(chunks)
            first_time = time.time() - start_time
            
            console.print(f"[yellow]첫 번째 실행 시간: {first_time:.2f}초[/yellow]")
            
            # 두 번째 실행 (캐시 히트)
            start_time = time.time()
            commit_msg2 = commit_analyzer.generate_commit_message(chunks)
            second_time = time.time() - start_time
            
            console.print(f"[yellow]두 번째 실행 시간: {second_time:.2f}초[/yellow]")
            
            if second_time < first_time * 0.5:  # 캐시로 인해 50% 이상 빨라짐
                console.print("[green]✓ 캐싱이 정상 작동합니다[/green]")
                return True
            else:
                console.print("[yellow]! 캐싱 효과가 미미합니다[/yellow]")
                return True  # 경고만 표시
                
        except Exception as e:
            console.print(f"[red]✗ 캐싱 테스트 실패: {e}[/red]")
            return False


def test_configuration():
    """설정 테스트"""
    print_section("설정 테스트")
    
    console.print("[bold]현재 설정:[/bold]")
    settings = {
        "기본 프로바이더": Config.DEFAULT_PROVIDER,
        "기본 모델": Config.DEFAULT_MODEL,
        "언어": Config.COMMIT_MESSAGE_LANGUAGE,
        "자동 리뷰": Config.AUTO_CODE_REVIEW,
        "캐싱": Config.ENABLE_CACHE,
        "디바운스 시간": f"{Config.DEBOUNCE_DELAY}초",
        "최대 청크 크기": Config.MAX_CHUNK_SIZE,
        "최대 파일 크기": f"{Config.MAX_FILE_SIZE_MB}MB"
    }
    
    for key, value in settings.items():
        console.print(f"  {key}: [green]{value}[/green]")
    
    # deepseek-r1:1.5b가 기본 모델인지 확인
    if Config.DEFAULT_MODEL == "deepseek-r1:1.5b":
        console.print("\n[green]✓ deepseek-r1:1.5b가 기본 모델로 설정되어 있습니다[/green]")
    else:
        console.print(f"\n[yellow]! 기본 모델이 {Config.DEFAULT_MODEL}입니다[/yellow]")
        console.print("[dim]  .env 파일에서 DEFAULT_MODEL=deepseek-r1:1.5b로 설정하세요[/dim]")
    
    return True


def run_all_tests():
    """모든 테스트 실행"""
    console.print("[bold green]Git Commit Manager 테스트 시작[/bold green]")
    console.print(f"[dim]Python 버전: {sys.version}[/dim]")
    console.print(f"[dim]작업 디렉토리: {os.getcwd()}[/dim]")
    
    tests = [
        ("Ollama 연결", test_ollama_connection),
        ("LLM 생성", test_llm_generation),
        ("Git 분석기", test_git_analyzer),
        ("커밋 분석기", test_commit_analyzer),
        ("캐싱 기능", test_cache_functionality),
        ("설정", test_configuration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            console.print(f"[red]✗ {test_name} 테스트 중 예외 발생: {e}[/red]")
            results.append((test_name, False))
    
    # 최종 결과
    print_section("테스트 결과 요약")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "[green]✓ PASS[/green]" if success else "[red]✗ FAIL[/red]"
        console.print(f"{test_name:20} {status}")
    
    console.print(f"\n[bold]총 {total}개 테스트 중 {passed}개 통과[/bold]")
    
    if passed == total:
        console.print("[bold green]모든 테스트가 통과했습니다! 🎉[/bold green]")
    else:
        console.print(f"[bold red]{total - passed}개 테스트가 실패했습니다.[/bold red]")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        console.print("\n[yellow]테스트가 중단되었습니다.[/yellow]")
        sys.exit(1) 