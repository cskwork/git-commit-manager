"""커밋 메시지 생성 및 코드 리뷰 모듈"""

from typing import List, Dict, Optional, Tuple
from .llm_providers import LLMProvider
from .git_analyzer import GitAnalyzer
from .config import Config


class PromptTemplates:
    """프롬프트 템플릿 관리 클래스"""
    
    # 커밋 메시지 생성용 시스템 프롬프트
    COMMIT_SYSTEM_PROMPTS = {
        "korean": """당신은 명확하고 간결한 Git 커밋 메시지를 생성하는 도우미입니다.
Conventional Commit 형식을 따라주세요: <타입>(<범위>): <제목>

타입: feat, fix, docs, style, refactor, test, chore

규칙:
- 제목은 최대 50자
- 명령형 어조 사용 ("추가"가 아닌 "추가")
- 마침표로 끝나지 않음
- 복잡한 변경사항에는 본문 포함 가능

모든 응답은 반드시 한국어로 작성해주세요.""",
        
        "english": """You are a helpful assistant that generates clear, concise git commit messages.
Follow conventional commit format: <type>(<scope>): <subject>

Types: feat, fix, docs, style, refactor, test, chore

Rules:
- Subject line should be max 50 characters
- Use imperative mood ("Add" not "Added")
- Don't end with period
- Include body if needed for complex changes"""
    }
    
    # 커밋 메시지 생성용 사용자 프롬프트
    COMMIT_USER_PROMPTS = {
        "korean": """다음 코드 변경사항을 바탕으로 Git 커밋 메시지를 생성해주세요:

{changes_summary}

다음 조건을 만족하는 커밋 메시지를 생성해주세요:
1. 명확한 제목 (최대 50자)
2. 필요시 변경 이유를 설명하는 본문
3. 변경사항의 주요 목적에 집중""",
        
        "english": """Based on these code changes, generate a git commit message:

{changes_summary}

Generate a conventional commit message with:
1. A clear subject line (max 50 chars)
2. An optional body explaining what and why (if needed)
3. Focus on the main purpose of the changes"""
    }
    
    # 코드 리뷰용 시스템 프롬프트
    REVIEW_SYSTEM_PROMPTS = {
        "korean": """당신은 경험이 풍부한 코드 리뷰어입니다.
다음 사항에 중점을 두어 건설적인 피드백을 제공해주세요:
- 코드 품질 및 모범 사례
- 잠재적 버그나 문제점
- 성능 관련 사항
- 보안 취약점
- 개선 제안사항

간결하고 실행 가능한 조언을 제공해주세요.
모든 응답은 반드시 한국어로 작성해주세요.""",
        
        "english": """You are an experienced code reviewer. 
Provide constructive feedback focusing on:
- Code quality and best practices
- Potential bugs or issues  
- Performance concerns
- Security vulnerabilities
- Suggestions for improvement

Be concise and actionable."""
    }
    
    # 코드 리뷰용 사용자 프롬프트
    REVIEW_USER_PROMPTS = {
        "korean": """다음 코드 변경사항을 리뷰해주세요:

파일: {file_path}
변경 유형: {change_type}

{diff_content}

다음 내용을 포함한 간단한 코드 리뷰를 제공해주세요:
1. 중요한 문제점 (있다면)
2. 개선 제안사항
3. 긍정적인 측면 (주목할 만한 것이 있다면)

간결하고 건설적으로 작성해주세요.""",
        
        "english": """Review this code change:

File: {file_path}
Change Type: {change_type}

{diff_content}

Provide a brief code review with:
1. Any critical issues (if any)
2. Suggestions for improvement  
3. Positive aspects (if notable)

Keep it concise and constructive."""
    }


class CommitAnalyzer:
    """AI를 사용한 커밋 분석 클래스"""
    
    # 상수 정의
    MAX_DIFF_LINES = 10
    NO_CHANGES_MESSAGE = "No changes detected"
    NO_REVIEW_MESSAGE = "No changes to review"
    
    def __init__(self, llm_provider: LLMProvider, git_analyzer: GitAnalyzer):
        self.llm = llm_provider
        self.git = git_analyzer
        
    def generate_commit_message(self, chunks: Optional[List[Dict[str, str]]] = None) -> str:
        """변경사항을 기반으로 커밋 메시지 생성"""
        if chunks is None:
            chunks = self.git.get_diff_chunks()
            
        if not chunks:
            return self.NO_CHANGES_MESSAGE
            
        # 프롬프트 생성
        system_prompt = self._build_commit_system_prompt()
        user_prompt = self._build_commit_user_prompt(chunks)
        
        return self.llm.generate(user_prompt, system_prompt)
        
    def review_code_changes(self, chunks: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
        """변경사항에 대한 코드 리뷰 수행"""
        if chunks is None:
            chunks = self.git.get_diff_chunks()
            
        if not chunks:
            return [{"file": "N/A", "review": self.NO_REVIEW_MESSAGE}]
            
        reviews = []
        system_prompt = self._build_review_system_prompt()
        
        for chunk in chunks:
            if self._should_review_chunk(chunk):
                review = self._review_single_chunk(chunk, system_prompt)
                reviews.append(review)
                
        return reviews
    
    def _build_commit_system_prompt(self) -> str:
        """커밋 메시지 생성용 시스템 프롬프트 구성"""
        language = self._get_language_key()
        language_instruction = Config.get_language_instruction()
        
        base_prompt = PromptTemplates.COMMIT_SYSTEM_PROMPTS.get(
            language, 
            PromptTemplates.COMMIT_SYSTEM_PROMPTS["english"]
        )
        
        return f"{language_instruction}\n\n{base_prompt}"
    
    def _build_commit_user_prompt(self, chunks: List[Dict[str, str]]) -> str:
        """커밋 메시지 생성용 사용자 프롬프트 구성"""
        language = self._get_language_key()
        changes_summary = self._summarize_changes(chunks)
        
        prompt_template = PromptTemplates.COMMIT_USER_PROMPTS.get(
            language,
            PromptTemplates.COMMIT_USER_PROMPTS["english"]
        )
        
        return prompt_template.format(changes_summary=changes_summary)
    
    def _build_review_system_prompt(self) -> str:
        """코드 리뷰용 시스템 프롬프트 구성"""
        language = self._get_language_key()
        language_instruction = Config.get_language_instruction()
        
        base_prompt = PromptTemplates.REVIEW_SYSTEM_PROMPTS.get(
            language,
            PromptTemplates.REVIEW_SYSTEM_PROMPTS["english"]
        )
        
        return f"{language_instruction}\n\n{base_prompt}"
    
    def _review_single_chunk(self, chunk: Dict[str, str], system_prompt: str) -> Dict[str, str]:
        """개별 청크에 대한 코드 리뷰 수행"""
        language = self._get_language_key()
        
        prompt_template = PromptTemplates.REVIEW_USER_PROMPTS.get(
            language,
            PromptTemplates.REVIEW_USER_PROMPTS["english"]
        )
        
        user_prompt = prompt_template.format(
            file_path=chunk['path'],
            change_type=chunk['type'],
            diff_content=chunk['diff']
        )
        
        review = self.llm.generate(user_prompt, system_prompt)
        
        return {
            'file': chunk['path'],
            'type': chunk['type'],
            'review': review
        }
    
    def _should_review_chunk(self, chunk: Dict[str, str]) -> bool:
        """청크가 리뷰 대상인지 확인"""
        return chunk['type'] in ['added', 'modified', 'untracked']
    
    def _get_language_key(self) -> str:
        """설정된 언어 키 반환"""
        return "korean" if Config.get_commit_language().lower() == "korean" else "english"
    
    def _summarize_changes(self, chunks: List[Dict[str, str]]) -> str:
        """변경사항을 요약하여 문자열로 반환"""
        summary_parts = []
        
        # 파일별로 그룹화
        file_changes: Dict[str, List[Dict[str, str]]] = {}
        for chunk in chunks:
            path = chunk.get('path', chunk.get('old_path', 'unknown'))
            if path not in file_changes:
                file_changes[path] = []
            file_changes[path].append(chunk)
            
        # 파일별 변경사항 요약 생성
        for file_path, changes in file_changes.items():
            summary_parts.extend(self._summarize_file_changes(file_path, changes))
                        
        return '\n'.join(summary_parts)
    
    def _summarize_file_changes(self, file_path: str, changes: List[Dict[str, str]]) -> List[str]:
        """개별 파일의 변경사항 요약"""
        summary_parts = [f"\nFile: {file_path}"]
        
        for change in changes:
            if change['type'] == 'renamed':
                summary_parts.append(f"- Renamed from {change['old_path']} to {change['new_path']}")
            else:
                summary_parts.append(f"- {change['type'].capitalize()}")
                
                if 'diff' in change and change['diff']:
                    summary_parts.extend(self._format_diff_preview(change['diff']))
                    
        return summary_parts
    
    def _format_diff_preview(self, diff: str) -> List[str]:
        """diff 미리보기 형식화"""
        diff_lines = diff.split('\n')[:self.MAX_DIFF_LINES]
        
        preview_lines = ["```"]
        preview_lines.extend(diff_lines)
        
        if len(diff.split('\n')) > self.MAX_DIFF_LINES:
            preview_lines.append("... (truncated)")
            
        preview_lines.append("```")
        return preview_lines 