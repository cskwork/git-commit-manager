"""커밋 메시지 생성 및 코드 리뷰 모듈"""

from typing import List, Dict, Optional
from .llm_providers import LLMProvider
from .git_analyzer import GitAnalyzer


class CommitAnalyzer:
    """AI를 사용한 커밋 분석 클래스"""
    
    def __init__(self, llm_provider: LLMProvider, git_analyzer: GitAnalyzer):
        self.llm = llm_provider
        self.git = git_analyzer
        
    def generate_commit_message(self, chunks: Optional[List[Dict[str, str]]] = None) -> str:
        """변경사항을 기반으로 커밋 메시지 생성"""
        if chunks is None:
            chunks = self.git.get_diff_chunks()
            
        if not chunks:
            return "No changes detected"
            
        # 시스템 프롬프트
        system_prompt = """You are a helpful assistant that generates clear, concise git commit messages.
        Follow conventional commit format: <type>(<scope>): <subject>
        
        Types: feat, fix, docs, style, refactor, test, chore
        
        Rules:
        - Subject line should be max 50 characters
        - Use imperative mood ("Add" not "Added")
        - Don't end with period
        - Include body if needed for complex changes"""
        
        # 변경사항 요약
        changes_summary = self._summarize_changes(chunks)
        
        prompt = f"""Based on these code changes, generate a git commit message:

{changes_summary}

Generate a conventional commit message with:
1. A clear subject line (max 50 chars)
2. An optional body explaining what and why (if needed)
3. Focus on the main purpose of the changes"""

        return self.llm.generate(prompt, system_prompt)
        
    def review_code_changes(self, chunks: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
        """변경사항에 대한 코드 리뷰 수행"""
        if chunks is None:
            chunks = self.git.get_diff_chunks()
            
        if not chunks:
            return [{"file": "N/A", "review": "No changes to review"}]
            
        reviews = []
        
        system_prompt = """You are an experienced code reviewer. 
        Provide constructive feedback focusing on:
        - Code quality and best practices
        - Potential bugs or issues
        - Performance concerns
        - Security vulnerabilities
        - Suggestions for improvement
        
        Be concise and actionable."""
        
        for chunk in chunks:
            if chunk['type'] in ['added', 'modified', 'untracked']:
                prompt = f"""Review this code change:

File: {chunk['path']}
Change Type: {chunk['type']}

{chunk['diff']}

Provide a brief code review with:
1. Any critical issues (if any)
2. Suggestions for improvement
3. Positive aspects (if notable)

Keep it concise and constructive."""

                review = self.llm.generate(prompt, system_prompt)
                reviews.append({
                    'file': chunk['path'],
                    'type': chunk['type'],
                    'review': review
                })
                
        return reviews
        
    def _summarize_changes(self, chunks: List[Dict[str, str]]) -> str:
        """변경사항을 요약하여 문자열로 반환"""
        summary_parts = []
        
        # 파일별로 그룹화
        file_changes = {}
        for chunk in chunks:
            path = chunk.get('path', chunk.get('old_path', 'unknown'))
            if path not in file_changes:
                file_changes[path] = []
            file_changes[path].append(chunk)
            
        for file_path, changes in file_changes.items():
            summary_parts.append(f"\nFile: {file_path}")
            for change in changes:
                if change['type'] == 'renamed':
                    summary_parts.append(f"- Renamed from {change['old_path']} to {change['new_path']}")
                else:
                    summary_parts.append(f"- {change['type'].capitalize()}")
                    if 'diff' in change and change['diff']:
                        # diff의 처음 몇 줄만 포함
                        diff_lines = change['diff'].split('\n')[:10]
                        summary_parts.append("```")
                        summary_parts.extend(diff_lines)
                        if len(change['diff'].split('\n')) > 10:
                            summary_parts.append("... (truncated)")
                        summary_parts.append("```")
                        
        return '\n'.join(summary_parts) 