"""커밋 메시지 생성 및 코드 리뷰 모듈"""

import hashlib
import json
import time
import re
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from .llm_providers import LLMProvider
from .git_analyzer import GitAnalyzer
from .config import Config


class CacheManager:
    """분석 결과 캐싱 관리자"""
    
    def __init__(self):
        self.cache_dir = Config.get_cache_dir()
        self.enabled = Config.ENABLE_CACHE
        self.ttl = Config.CACHE_TTL_SECONDS
    
    def _get_cache_key(self, prefix: str, content: str) -> str:
        """캐시 키 생성 (SHA-256 사용)"""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        return f"{prefix}_{content_hash}"
    
    def get(self, prefix: str, content: str) -> Optional[str]:
        """캐시에서 값 가져오기"""
        if not self.enabled:
            return None
            
        cache_key = self._get_cache_key(prefix, content)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
            
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                
            # TTL 확인
            if time.time() - cache_data['timestamp'] > self.ttl:
                cache_file.unlink()  # 만료된 캐시 삭제
                return None
                
            return cache_data['value']
        except Exception:
            return None
    
    def set(self, prefix: str, content: str, value: str):
        """캐시에 값 저장"""
        if not self.enabled:
            return
            
        cache_key = self._get_cache_key(prefix, content)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': time.time(),
                    'value': value
                }, f, ensure_ascii=False)
        except Exception:
            pass  # 캐시 저장 실패는 무시
    
    def clear(self):
        """모든 캐시 삭제"""
        if self.cache_dir.exists():
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()


class PromptTemplates:
    """프롬프트 템플릿 관리 클래스"""
    
    # 최적화된 커밋 메시지 생성용 시스템 프롬프트
    DEFAULT_COMMIT_SYSTEM_PROMPTS = {
        "korean": """당신은 지시된 형식에 따라 Git 커밋 메시지를 생성하는 자동화된 도구입니다. 당신의 유일한 임무는 제공된 변경사항 요약을 바탕으로 Conventional Commit 형식의 커밋 메시지 텍스트를 생성하는 것입니다.

응답은 항상 다음 형식으로 시작해야 합니다: `feat(<범위>): <제목>` 또는 `fix(<범위>): <제목>` 등. 다른 텍스트를 포함하지 마세요.

### 출력 예시 ###
feat(api): 사용자 인증 엔드포인트 추가

- JWT 기반의 사용자 로그인 및 회원가입 API를 구현했습니다.
- `/auth/login`, `/auth/register` 엔드포인트를 포함합니다.""",
        
        "english": """You are an automated tool that generates Git commit messages according to a specified format. Your sole task is to generate the text for a Conventional Commit message based on the provided summary of changes.

Your response must always start with the format: `feat(<scope>): <subject>` or `fix(<scope>): <subject>`, etc. Do not include any other text.

### Example Output ###
feat(api): add user authentication endpoint

- Implemented JWT-based user login and registration API.
- Includes `/auth/login` and `/auth/register` endpoints."""
    }
    
    # 최적화된 커밋 메시지 생성용 사용자 프롬프트
    DEFAULT_COMMIT_USER_PROMPTS = {
        "korean": """### 변경사항 요약 ###
{changes_summary}

### 지시사항 ###
위 변경사항에 대한 Conventional Commit 형식의 커밋 메시지를 생성하세요.""",
        
        "english": """### Change Summary ###
{changes_summary}

### Instructions ###
Generate a Conventional Commit message for the changes above."""
    }
    
    # 최적화된 코드 리뷰용 시스템 프롬프트
    DEFAULT_REVIEW_SYSTEM_PROMPTS = {
        "korean": """당신은 코드 리뷰를 수행하는 자동화된 도구입니다. 당신의 유일한 임무는 제공된 코드 변경사항에 대해 지정된 형식으로 리뷰를 생성하는 것입니다. 다른 텍스트를 포함하지 마세요.

### 리뷰 형식 ###
**💡 개선 제안:**
(더 나은 코드, 리팩토링 아이디어 등)

**🐛 잠재적 문제:**
(버그, 성능 저하, 보안 이슈 등)

**👍 좋은 점:**
(칭찬할 부분, 잘 구현된 패턴 등)

해당 사항이 없으면 섹션을 생략하세요.""",
        
        "english": """You are an automated tool that performs code reviews. Your sole task is to generate a review in the specified format for the provided code change. Do not include any other text.

### Review Format ###
**💡 Suggestions for Improvement:**
(Better code, refactoring ideas, etc.)

**🐛 Potential Issues:**
(Bugs, performance degradations, security concerns, etc.)

**👍 Positive Feedback:**
(Praise for good code, well-implemented patterns, etc.)

Omit sections if they are not applicable."""
    }
    
    # 최적화된 코드 리뷰용 사용자 프롬프트
    DEFAULT_REVIEW_USER_PROMPTS = {
        "korean": """### 코드 변경사항 ###
**파일:** `{file_path}`
**변경 종류:** `{change_type}`

```diff
{diff_content}
```

### 지시사항 ###
위 코드 변경사항에 대한 리뷰를 생성하세요.""",
        
        "english": """### Code Change ###
**File:** `{file_path}`
**Change Type:** `{change_type}`

```diff
{diff_content}
```

### Instructions ###
Generate a code review for the change above."""
    }

    @classmethod
    def get_commit_system_prompts(cls) -> Dict[str, str]:
        """환경변수 또는 기본값에서 커밋 시스템 프롬프트 가져오기"""
        return {
            "korean": Config.CUSTOM_COMMIT_SYSTEM_PROMPT_KOREAN or cls.DEFAULT_COMMIT_SYSTEM_PROMPTS["korean"],
            "english": Config.CUSTOM_COMMIT_SYSTEM_PROMPT_ENGLISH or cls.DEFAULT_COMMIT_SYSTEM_PROMPTS["english"]
        }
    
    @classmethod
    def get_commit_user_prompts(cls) -> Dict[str, str]:
        """환경변수 또는 기본값에서 커밋 사용자 프롬프트 가져오기"""
        return {
            "korean": Config.CUSTOM_COMMIT_USER_PROMPT_KOREAN or cls.DEFAULT_COMMIT_USER_PROMPTS["korean"],
            "english": Config.CUSTOM_COMMIT_USER_PROMPT_ENGLISH or cls.DEFAULT_COMMIT_USER_PROMPTS["english"]
        }
    
    @classmethod
    def get_review_system_prompts(cls) -> Dict[str, str]:
        """환경변수 또는 기본값에서 리뷰 시스템 프롬프트 가져오기"""
        return {
            "korean": Config.CUSTOM_REVIEW_SYSTEM_PROMPT_KOREAN or cls.DEFAULT_REVIEW_SYSTEM_PROMPTS["korean"],
            "english": Config.CUSTOM_REVIEW_SYSTEM_PROMPT_ENGLISH or cls.DEFAULT_REVIEW_SYSTEM_PROMPTS["english"]
        }
    
    @classmethod
    def get_review_user_prompts(cls) -> Dict[str, str]:
        """환경변수 또는 기본값에서 리뷰 사용자 프롬프트 가져오기"""
        return {
            "korean": Config.CUSTOM_REVIEW_USER_PROMPT_KOREAN or cls.DEFAULT_REVIEW_USER_PROMPTS["korean"],
            "english": Config.CUSTOM_REVIEW_USER_PROMPT_ENGLISH or cls.DEFAULT_REVIEW_USER_PROMPTS["english"]
        }

    @classmethod
    def get_supported_languages(cls) -> List[str]:
        """지원되는 언어 목록 반환"""
        return list(cls.DEFAULT_COMMIT_SYSTEM_PROMPTS.keys())


class CommitAnalyzer:
    """AI를 사용한 커밋 분석 클래스"""
    
    # 상수 정의
    MAX_DIFF_LINES = 15  
    MAX_FILES_PER_CHUNK = 5  # 한 청크당 최대 파일 수
    
    def __init__(self, llm_provider: LLMProvider, git_analyzer: GitAnalyzer):
        self.llm = llm_provider
        self.git = git_analyzer
        self.cache = CacheManager()
        
    def _clean_llm_output(self, text: str) -> str:
        """LLM 응답에서 불필요한 태그와 공백 제거"""
        if not isinstance(text, str):
            return ""
        # <think>...</think> 블록을 포함한 모든 XML/HTML 태그 제거
        cleaned_text = re.sub(r'<[^>]+>', '', text, flags=re.DOTALL)
        return cleaned_text.strip()

    def generate_commit_message(self, chunks: Optional[List[Dict[str, str]]] = None) -> str:
        """변경사항을 기반으로 커밋 메시지 생성"""
        if chunks is None:
            chunks = self.git.get_diff_chunks(max_chunk_size=Config.MAX_CHUNK_SIZE)
            
        if not chunks:
            return ""
        
        # 캐시 확인
        chunks_str = json.dumps(chunks, sort_keys=True)
        cached_result = self.cache.get("commit", chunks_str)
        if cached_result:
            return cached_result
            
        # 프롬프트 생성
        system_prompt = self._build_commit_system_prompt()
        user_prompt = self._build_commit_user_prompt(chunks)
        
        # 토큰 제한을 고려한 프롬프트 최적화
        if len(user_prompt) > Config.MAX_CONTEXT_LENGTH:
            user_prompt = self._optimize_prompt(user_prompt, Config.MAX_CONTEXT_LENGTH)
        
        raw_result = self.llm.generate(user_prompt, system_prompt)
        result = self._clean_llm_output(raw_result)
        
        # 결과 캐싱
        self.cache.set("commit", chunks_str, result)
        
        return result
        
    def review_code_changes(self, chunks: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
        """변경사항에 대한 코드 리뷰 수행"""
        if chunks is None:
            chunks = self.git.get_diff_chunks(max_chunk_size=Config.MAX_CHUNK_SIZE)
            
        if not chunks:
            return []
            
        reviews = []
        system_prompt = self._build_review_system_prompt()
        
        # 청크를 배치로 처리하여 효율성 향상
        for chunk in chunks:
            if self._should_review_chunk(chunk):
                # 캐시 확인
                chunk_str = json.dumps(chunk, sort_keys=True)
                cached_review = self.cache.get("review", chunk_str)
                
                if cached_review:
                    reviews.append({
                        'file': chunk['path'],
                        'type': chunk['type'],
                        'review': cached_review
                    })
                else:
                    review_response = self._review_single_chunk(chunk, system_prompt)
                    # review_response가 딕셔너리이므로 'review' 키에서 텍스트를 가져와 클린징
                    cleaned_review = self._clean_llm_output(review_response.get('review', ''))
                    review_response['review'] = cleaned_review
                    
                    reviews.append(review_response)
                    # 리뷰 캐싱
                    self.cache.set("review", chunk_str, cleaned_review)
                
        return reviews
    
    def clear_cache(self):
        """캐시 초기화"""
        self.cache.clear()
    
    def _optimize_prompt(self, prompt: str, max_length: int) -> str:
        """프롬프트 길이 최적화"""
        if len(prompt) <= max_length:
            return prompt
            
        # 중요한 부분을 유지하면서 길이 축소
        lines = prompt.split('\n')
        optimized_lines = []
        current_length = 0
        
        # 파일 정보와 주요 변경사항 우선 포함
        for line in lines:
            if current_length + len(line) > max_length:
                if optimized_lines:
                    optimized_lines.append("... (일부 내용 생략)")
                break
            optimized_lines.append(line)
            current_length += len(line) + 1
            
        return '\n'.join(optimized_lines)
    
    def _get_prompt(self, prompt_dict: Dict[str, str]) -> str:
        """설정 언어에 맞는 프롬프트 반환"""
        language = Config.COMMIT_MESSAGE_LANGUAGE.lower()
        supported_languages = PromptTemplates.get_supported_languages()

        if language not in supported_languages:
            language = "english" # 기본값
            
        return prompt_dict[language]

    def _build_commit_system_prompt(self) -> str:
        """커밋 메시지 생성용 시스템 프롬프트 구성"""
        return self._get_prompt(PromptTemplates.get_commit_system_prompts())
    
    def _build_commit_user_prompt(self, chunks: List[Dict[str, str]]) -> str:
        """커밋 메시지 생성용 사용자 프롬프트 구성"""
        changes_summary = self._summarize_changes(chunks)
        prompt_template = self._get_prompt(PromptTemplates.get_commit_user_prompts())
        return prompt_template.format(changes_summary=changes_summary)
    
    def _build_review_system_prompt(self) -> str:
        """코드 리뷰용 시스템 프롬프트 구성"""
        return self._get_prompt(PromptTemplates.get_review_system_prompts())
    
    def _review_single_chunk(self, chunk: Dict[str, str], system_prompt: str) -> Dict[str, str]:
        """개별 청크에 대한 코드 리뷰 수행"""
        prompt_template = self._get_prompt(PromptTemplates.get_review_user_prompts())
        
        # diff 내용 최적화
        diff_content = chunk['diff']
        if len(diff_content) > Config.MAX_CHUNK_SIZE:
            diff_content = self._extract_important_diff(diff_content, Config.MAX_CHUNK_SIZE)
        
        user_prompt = prompt_template.format(
            file_path=chunk['path'],
            change_type=chunk['type'],
            diff_content=diff_content
        )
        
        raw_review = self.llm.generate(user_prompt, system_prompt)
        cleaned_review = self._clean_llm_output(raw_review)
        
        return {
            'file': chunk['path'],
            'type': chunk['type'],
            'review': cleaned_review
        }
    
    def _extract_important_diff(self, diff: str, max_size: int) -> str:
        """중요한 diff 부분만 추출 (보안 및 성능 개선)"""
        if not diff or max_size <= 0:
            return ""
            
        lines = diff.split('\n')
        important_lines = []
        current_size = 0
        
        # 추가/삭제된 라인 우선 포함 (보안 검사 포함)
        for line in lines:
            # 민감한 정보가 포함된 라인 필터링 (확장된 패턴)
            sensitive_patterns = [
                'password', 'passwd', 'pwd', 'api_key', 'apikey', 'token', 'secret', 
                'key', 'auth', 'credential', 'private', 'session', 'jwt', 'bearer',
                'access_token', 'refresh_token', 'client_secret', 'client_id'
            ]
            if any(sensitive in line.lower() for sensitive in sensitive_patterns):
                line = "... (민감한 정보가 포함된 라인 제외됨)"
            
            if line.startswith(('+', '-')) and not line.startswith(('+++', '---')):
                if current_size + len(line) > max_size:
                    break
                important_lines.append(line)
                current_size += len(line) + 1
                
                # 라인 수 제한 (DOS 방지)
                if len(important_lines) > 100:
                    important_lines.append("... (너무 많은 변경사항으로 일부 생략)")
                    break
        
        # 컨텍스트 라인 추가
        remaining_size = max_size - current_size
        if remaining_size > 0:
            context_lines = [l for l in lines if not l.startswith(('+', '-'))]
            
            for line in context_lines[:min(10, remaining_size // 50)]:  # 최대 10라인, 평균 라인 길이 50 가정
                important_lines.append(line)
            
        return '\n'.join(important_lines)
    
    def _should_review_chunk(self, chunk: Dict[str, str]) -> bool:
        """청크가 리뷰 대상인지 확인"""
        # 바이너리 파일이나 큰 파일은 제외
        if chunk.get('binary', False):
            return False
            
        # 특정 파일 타입만 리뷰
        reviewable_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs', '.rb', '.php'}
        file_path = chunk.get('path', '')
        
        if any(file_path.endswith(ext) for ext in reviewable_extensions):
            return chunk['type'] in ['added', 'modified', 'untracked']
            
        return False
    
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
            
        # 파일별 변경사항 요약 생성 (최대 파일 수 제한)
        for i, (file_path, changes) in enumerate(file_changes.items()):
            if i >= self.MAX_FILES_PER_CHUNK:
                summary_parts.append(f"\n... 외 {len(file_changes) - i}개 파일")
                break
            summary_parts.extend(self._summarize_file_changes(file_path, changes))
                        
        return '\n'.join(summary_parts)
    
    def _summarize_file_changes(self, file_path: str, changes: List[Dict[str, str]]) -> List[str]:
        """개별 파일의 변경사항 요약"""
        summary_parts = [f"\n파일: {file_path}"]
        
        for change in changes:
            if change['type'] == 'renamed':
                summary_parts.append(f"- 이름변경: {change['old_path']} → {change['new_path']}")
            else:
                summary_parts.append(f"- {change['type']}")
                
                if 'diff' in change and change['diff']:
                    summary_parts.extend(self._format_diff_preview(change['diff']))
                    
        return summary_parts
    
    def _format_diff_preview(self, diff: str) -> List[str]:
        """diff 미리보기 형식화"""
        diff_lines = diff.split('\n')[:self.MAX_DIFF_LINES]
        
        # 중요한 변경사항만 표시
        important_lines = []
        for line in diff_lines:
            if line.startswith(('+', '-')) and not line.startswith(('+++', '---')):
                important_lines.append(line)
                
        if not important_lines:
            important_lines = diff_lines[:5]
        
        preview_lines = ["```diff"]
        preview_lines.extend(important_lines[:10])  # 최대 10줄
        
        if len(diff.split('\n')) > self.MAX_DIFF_LINES:
            preview_lines.append("...")
            
        preview_lines.append("```")
        return preview_lines 