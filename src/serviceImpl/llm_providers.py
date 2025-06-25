"""LLM 프로바이더 추상화 - Ollama, OpenRouter, Gemini 지원"""

import os
import json
import time
import signal
import threading
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
import requests
    
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    
from dotenv import load_dotenv

load_dotenv()


class TimeoutError(Exception):
    """타임아웃 예외"""
    pass


def with_timeout(timeout_seconds: int):
    """타임아웃 데코레이터"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = [None]
            exception = [None]
            
            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e
            
            thread = threading.Thread(target=target, daemon=True)
            thread.start()
            thread.join(timeout=timeout_seconds)
            
            if thread.is_alive():
                # 스레드가 아직 실행 중이면 타임아웃
                raise TimeoutError(f"LLM 요청이 {timeout_seconds}초 후 타임아웃되었습니다")
            
            if exception[0]:
                raise exception[0]
            
            return result[0]
        return wrapper
    return decorator


class LLMProviderError(Exception):
    """LLM 프로바이더 관련 오류"""
    pass


class RetryableLLMError(LLMProviderError):
    """재시도 가능한 LLM 오류"""
    pass


class LLMProvider(ABC):
    """LLM 프로바이더 기본 클래스"""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    @abstractmethod
    def _generate_impl(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """프롬프트에 대한 응답 생성 구현"""
        pass
    
    @with_timeout(60)  # 60초 타임아웃
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """프롬프트에 대한 응답 생성 (재시도 로직 포함)"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return self._generate_impl(prompt, system_prompt)
            except RetryableLLMError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                continue
            except TimeoutError:
                raise LLMProviderError("LLM 요청이 타임아웃되었습니다. 네트워크 연결이나 모델 상태를 확인해주세요.")
            except LLMProviderError:
                raise
            except Exception as e:
                raise LLMProviderError(f"예상치 못한 오류: {e}") from e
        
        raise last_error or LLMProviderError("최대 재시도 횟수 초과")


class OllamaProvider(LLMProvider):
    """Ollama 로컬 모델 프로바이더 (requests API 사용)"""
    
    def __init__(self, model_name: str = "gemma3:1b", max_retries: int = 3):
        super().__init__(max_retries=max_retries)
        self.model_name = model_name
        self.base_url = "http://localhost:11434"
        
        # Ollama 서버 연결 확인
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if response.status_code != 200:
                raise LLMProviderError("Ollama 서버에 연결할 수 없습니다. Ollama가 실행 중인지 확인하세요.")
        except requests.ConnectionError:
            raise LLMProviderError("Ollama 서버에 연결할 수 없습니다. Ollama가 실행 중인지 확인하세요.")
        except requests.Timeout:
            raise LLMProviderError("Ollama 서버 응답 시간 초과")
        
    def _generate_impl(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Ollama API 직접 호출
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    'model': self.model_name,
                    'messages': messages,
                    'stream': False,
                    'options': {
                        'temperature': 0.7,
                        'num_predict': 500,
                    }
                },
                timeout=30
            )
            
            if response.status_code != 200:
                raise RetryableLLMError(f"Ollama API 오류: {response.status_code}")
            
            result = response.json()
            if 'message' not in result or 'content' not in result['message']:
                raise RetryableLLMError("올바르지 않은 응답 형식")
                
            return result['message']['content']
                
        except requests.ConnectionError:
            raise RetryableLLMError("Ollama 서버에 연결할 수 없습니다.")
        except requests.Timeout:
            raise RetryableLLMError("Ollama 요청 타임아웃")
        except Exception as e:
            if "connection" in str(e).lower():
                raise RetryableLLMError(f"Ollama 연결 오류: {e}") from e
            raise LLMProviderError(f"Ollama 오류: {e}") from e
    
    @staticmethod
    def get_available_models() -> List[Dict[str, Any]]:
        """설치된 Ollama 모델 목록 가져오기"""
        try:
            response = requests.get('http://localhost:11434/api/tags', timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('models', [])
            return []
        except Exception:
            return []
    
    @staticmethod
    def suggest_model() -> Optional[str]:
        """사용 가능한 모델 중 적합한 모델 추천"""
        models = OllamaProvider.get_available_models()
        if not models:
            return None
            
        model_names = [m['name'] for m in models]
        
        # 선호 모델 순서 (코드 분석에 적합한 모델들)
        preferred_models = [
            'gemma3:1b',
            'qwen2.5-coder:1.5b',
            'qwen2.5-coder:3b',
            'llama3.2:1b',
            'llama3.2:3b',
            'codellama:7b',
            'codellama',
            'llama3.1:8b',
            'llama2:7b',
            'llama2',
            'mistral',
            'phi3',
            'qwen2.5-coder:7b'
        ]
        
        # 선호 모델 중 사용 가능한 첫 번째 모델 반환
        for preferred in preferred_models:
            for model_name in model_names:
                if preferred in model_name or model_name.startswith(preferred):
                    return model_name
                    
        # 선호 모델이 없으면 첫 번째 모델 반환
        return model_names[0] if model_names else None


class OpenRouterProvider(LLMProvider):
    """OpenRouter API 프로바이더"""
    
    def __init__(self, model_name: str = "openai/gpt-3.5-turbo", max_retries: int = 3):
        super().__init__(max_retries=max_retries)
        from .config import Config
        self.api_key = Config.OPENROUTER_API_KEY
        if not self.api_key:
            raise LLMProviderError(
                "OpenRouter API 키가 설정되지 않았거나 유효하지 않습니다. "
                ".env 파일을 확인하고 OPENROUTER_API_KEY를 올바른 형식으로 설정해주세요."
            )
        self.model_name = model_name
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        
    def _generate_impl(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        # 입력 검증
        if not prompt or not isinstance(prompt, str):
            raise LLMProviderError("유효하지 않은 프롬프트")
            
        # 프롬프트 길이 제한
        max_prompt_length = 50000  # 약 50KB
        if len(prompt) > max_prompt_length:
            raise LLMProviderError(f"프롬프트가 너무 깁니다 ({len(prompt)} > {max_prompt_length})")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "GitCommitManager/1.0"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": 500,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(
                self.base_url, 
                headers=headers, 
                json=data,
                timeout=30,
                # 보안 옵션
                verify=True,  # SSL 인증서 검증
                allow_redirects=False  # 리다이렉트 방지
            )
            
            if response.status_code == 429:
                raise RetryableLLMError("API 속도 제한에 도달했습니다")
            elif response.status_code >= 500:
                raise RetryableLLMError(f"서버 오류: {response.status_code}")
                
            response.raise_for_status()
            result = response.json()
            
            if 'choices' not in result or not result['choices']:
                raise LLMProviderError("응답에 결과가 없습니다")
                
            return result['choices'][0]['message']['content']
        except requests.Timeout:
            raise RetryableLLMError("API 요청 타임아웃")
        except requests.ConnectionError:
            raise RetryableLLMError("API 연결 오류")
        except requests.RequestException as e:
            raise LLMProviderError(f"OpenRouter API 요청 오류: {e}") from e
        except (KeyError, IndexError) as e:
            raise LLMProviderError(f"OpenRouter API 응답 처리 오류: {e}") from e


class GeminiProvider(LLMProvider):
    """Google Gemini API 프로바이더"""
    
    def __init__(self, model_name: str = "gemini-pro", max_retries: int = 3):
        super().__init__(max_retries=max_retries)
        if not GEMINI_AVAILABLE:
            raise LLMProviderError("google-generativeai 패키지가 설치되지 않았습니다. pip install google-generativeai를 실행하세요.")
            
        from .config import Config
        self.api_key = Config.GEMINI_API_KEY
        if not self.api_key:
            raise LLMProviderError(
                "Gemini API 키가 설정되지 않았거나 유효하지 않습니다. "
                ".env 파일을 확인하고 GEMINI_API_KEY를 올바른 형식으로 설정해주세요."
            )

        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(
                model_name,
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 500,
                }
            )
        except Exception as e:
            raise LLMProviderError(f"Gemini SDK 초기화 오류: {e}") from e

    def _generate_impl(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        try:
            # 입력 검증
            if not prompt or not isinstance(prompt, str):
                raise LLMProviderError("유효하지 않은 프롬프트")
                
            # 프롬프트 길이 제한
            max_prompt_length = 30000  # Gemini의 상대적으로 작은 컨텍스트 창
            if len(prompt) > max_prompt_length:
                raise LLMProviderError(f"프롬프트가 너무 깁니다 ({len(prompt)} > {max_prompt_length})")
            
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
                
            response = self.model.generate_content(full_prompt)
            
            if not response or not response.text:
                raise RetryableLLMError("응답이 비어있습니다")
                
            return response.text
        except Exception as e:
            if "quota" in str(e).lower():
                raise RetryableLLMError("API 할당량 초과")
            if GEMINI_AVAILABLE and hasattr(genai, 'types') and hasattr(genai.types, 'BlockedPromptException'):
                if isinstance(e, genai.types.BlockedPromptException):
                    raise LLMProviderError("프롬프트가 차단되었습니다")
            raise LLMProviderError(f"Gemini API 오류: {e}") from e


def get_provider(provider_type: str, model_name: Optional[str] = None) -> LLMProvider:
    """지정된 타입의 LLM 프로바이더 반환"""
    providers = {
        "ollama": OllamaProvider,
        "openrouter": OpenRouterProvider,
        "gemini": GeminiProvider
    }
    
    if provider_type not in providers:
        raise ValueError(f"지원하지 않는 프로바이더: {provider_type}")
        
    # 기본 모델 설정
    default_models = {
        "ollama": "gemma3:1b",
        "openrouter": "openai/gpt-3.5-turbo",
        "gemini": "gemini-pro"
    }
    
    if model_name:
        return providers[provider_type](model_name)
    else:
        # 모델명이 없으면 기본 모델 사용
        return providers[provider_type](default_models.get(provider_type)) 