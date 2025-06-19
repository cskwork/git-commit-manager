"""LLM 프로바이더 추상화 - Ollama, OpenRouter, Gemini 지원"""

import os
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
import requests
import ollama
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()


class LLMProvider(ABC):
    """LLM 프로바이더 기본 클래스"""
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """프롬프트에 대한 응답 생성"""
        pass


class OllamaProvider(LLMProvider):
    """Ollama 로컬 모델 프로바이더"""
    
    def __init__(self, model_name: str = "gemma3:1b"):
        self.model_name = model_name
        
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = ollama.chat(
                model=self.model_name,
                messages=messages
            )
            return response['message']['content']
        except Exception as e:
            return f"Ollama 오류: {str(e)}"
    
    @staticmethod
    def get_available_models() -> List[Dict[str, Any]]:
        """설치된 Ollama 모델 목록 가져오기"""
        try:
            models = ollama.list()
            return models.get('models', [])
        except Exception:
            return []
    
    @staticmethod
    def suggest_model() -> Optional[str]:
        """사용 가능한 모델 중 적합한 모델 추천"""
        models = OllamaProvider.get_available_models()
        if not models:
            return None
            
        model_names = [m.model for m in models]
        
        # 선호 모델 순서 (코드 분석에 적합한 모델들)
        preferred_models = [
            'gemma3:1b',
            'gemma2:2b', 
            'gemma:2b',
            'llama3.2:1b',
            'llama3.2:3b',
            'llama3.1:8b',
            'codellama:7b',
            'codellama',
            'llama2:7b',
            'llama2',
            'mistral',
            'phi3',
            'qwen2.5-coder:1.5b',
            'qwen2.5-coder:3b',
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
    
    def __init__(self, model_name: str = "openai/gpt-3.5-turbo"):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model_name = model_name
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self.api_key:
            return "OpenRouter API 키가 설정되지 않았습니다."
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": self.model_name,
            "messages": messages
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            return f"OpenRouter 오류: {str(e)}"


class GeminiProvider(LLMProvider):
    """Google Gemini API 프로바이더"""
    
    def __init__(self, model_name: str = "gemini-pro"):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(model_name)
        else:
            self.model = None
            
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self.api_key:
            return "Gemini API 키가 설정되지 않았습니다."
            
        try:
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
                
            response = self.model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            return f"Gemini 오류: {str(e)}"


def get_provider(provider_type: str, model_name: Optional[str] = None) -> LLMProvider:
    """지정된 타입의 LLM 프로바이더 반환"""
    providers = {
        "ollama": OllamaProvider,
        "openrouter": OpenRouterProvider,
        "gemini": GeminiProvider
    }
    
    if provider_type not in providers:
        raise ValueError(f"지원하지 않는 프로바이더: {provider_type}")
        
    if model_name:
        return providers[provider_type](model_name)
    else:
        return providers[provider_type]() 