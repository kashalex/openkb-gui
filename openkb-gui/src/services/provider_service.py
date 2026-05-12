"""
Provider Service - Управление LLM провайдерами для LiteLLM.

Обеспечивает:
- Список поддерживаемых LiteLLM провайдеров
- Получение моделей для каждого провайдера
- Тестирование подключения к модели
- Сохранение API ключей
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Lazy import для litellm
_litellm = None


def get_litellm():
    """Ленивый импорт litellm."""
    global _litellm
    if _litellm is None:
        import litellm
        _litellm = litellm
    return _litellm


class ConnectionStatus(Enum):
    """Статус подключения."""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    NO_API_KEY = "no_api_key"
    INVALID_KEY = "invalid_key"


@dataclass
class ModelInfo:
    """Информация о модели."""
    id: str
    name: str
    description: str = ""
    context_window: int = 4096
    max_output: int = 2048
    supports_vision: bool = False
    supports_streaming: bool = True
    supports_function_calling: bool = True
    price_input: str = ""
    price_output: str = ""
    is_free: bool = False
    is_popular: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "context_window": self.context_window,
            "max_output": self.max_output,
            "supports_vision": self.supports_vision,
            "supports_streaming": self.supports_streaming,
            "supports_function_calling": self.supports_function_calling,
            "price_input": self.price_input,
            "price_output": self.price_output,
            "is_free": self.is_free,
            "is_popular": self.is_popular,
        }


@dataclass
class ProviderInfo:
    """Информация о провайдере."""
    id: str
    name: str
    prefix: str
    api_key_env: str
    api_base: str = ""
    description: str = ""
    website: str = ""
    docs_url: str = ""
    supports_model_listing: bool = False
    models: list[ModelInfo] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "prefix": self.prefix,
            "api_key_env": self.api_key_env,
            "api_base": self.api_base,
            "description": self.description,
            "website": self.website,
            "docs_url": self.docs_url,
            "supports_model_listing": self.supports_model_listing,
            "models": [m.to_dict() for m in self.models],
        }


@dataclass
class ConnectionTestResult:
    """Результат тестирования подключения."""
    success: bool
    status: ConnectionStatus
    message: str
    model: str = ""
    response_time_ms: float = 0
    error_details: str = ""


# ============================================================================
# LITELLM SUPPORTED PROVIDERS
# ============================================================================

# Провайдеры LiteLLM с их моделями
LITELLM_PROVIDERS: dict[str, ProviderInfo] = {
    "openai": ProviderInfo(
        id="openai",
        name="OpenAI",
        prefix="openai/",
        api_key_env="OPENAI_API_KEY",
        api_base="https://api.openai.com/v1",
        description="OpenAI GPT models including GPT-4 and GPT-3.5",
        website="https://openai.com",
        docs_url="https://platform.openai.com/docs",
        supports_model_listing=True,
        models=[
            ModelInfo(id="gpt-4o", name="GPT-4o", context_window=128000, max_output=4096,
                     supports_vision=True, price_input="$5/1M", price_output="$15/1M", is_popular=True),
            ModelInfo(id="gpt-4o-mini", name="GPT-4o Mini", context_window=128000, max_output=16384,
                     supports_vision=True, price_input="$0.15/1M", price_output="$0.6/1M", is_popular=True),
            ModelInfo(id="gpt-4-turbo", name="GPT-4 Turbo", context_window=128000, max_output=4096,
                     supports_vision=True, price_input="$10/1M", price_output="$30/1M"),
            ModelInfo(id="gpt-4", name="GPT-4", context_window=8192, max_output=4096,
                     price_input="$30/1M", price_output="$60/1M"),
            ModelInfo(id="gpt-3.5-turbo", name="GPT-3.5 Turbo", context_window=16385, max_output=4096,
                     price_input="$0.5/1M", price_output="$1.5/1M"),
            ModelInfo(id="o1-preview", name="o1 Preview", context_window=128000, max_output=32768,
                     price_input="$15/1M", price_output="$60/1M"),
            ModelInfo(id="o1-mini", name="o1 Mini", context_window=128000, max_output=65536,
                     price_input="$3/1M", price_output="$12/1M"),
        ],
    ),

    "anthropic": ProviderInfo(
        id="anthropic",
        name="Anthropic (Claude)",
        prefix="anthropic/",
        api_key_env="ANTHROPIC_API_KEY",
        api_base="https://api.anthropic.com/v1",
        description="Claude models by Anthropic",
        website="https://anthropic.com",
        docs_url="https://docs.anthropic.com",
        models=[
            ModelInfo(id="claude-sonnet-4-20250514", name="Claude Sonnet 4", context_window=200000, max_output=16000,
                     supports_vision=True, price_input="$3/1M", price_output="$15/1M", is_popular=True),
            ModelInfo(id="claude-3-5-sonnet-20241022", name="Claude 3.5 Sonnet", context_window=200000, max_output=8192,
                     supports_vision=True, price_input="$3/1M", price_output="$15/1M", is_popular=True),
            ModelInfo(id="claude-3-5-haiku-20241022", name="Claude 3.5 Haiku", context_window=200000, max_output=8192,
                     supports_vision=True, price_input="$1/1M", price_output="$5/1M", is_popular=True),
            ModelInfo(id="claude-3-opus-20240229", name="Claude 3 Opus", context_window=200000, max_output=4096,
                     supports_vision=True, price_input="$15/1M", price_output="$75/1M"),
            ModelInfo(id="claude-3-sonnet-20240229", name="Claude 3 Sonnet", context_window=200000, max_output=4096,
                     supports_vision=True, price_input="$3/1M", price_output="$15/1M"),
            ModelInfo(id="claude-3-haiku-20240307", name="Claude 3 Haiku", context_window=200000, max_output=4096,
                     supports_vision=True, price_input="$0.25/1M", price_output="$1.25/1M"),
        ],
    ),

    "openrouter": ProviderInfo(
        id="openrouter",
        name="OpenRouter",
        prefix="openrouter/",
        api_key_env="OPENROUTER_API_KEY",
        api_base="https://openrouter.ai/api/v1",
        description="Unified API for 200+ LLMs from multiple providers",
        website="https://openrouter.ai",
        docs_url="https://openrouter.ai/docs",
        supports_model_listing=True,
        models=[
            # Бесплатные модели
            ModelInfo(id="deepseek/deepseek-chat", name="DeepSeek Chat (Free)", context_window=128000,
                     price_input="Free", price_output="Free", is_free=True, is_popular=True),
            ModelInfo(id="deepseek/deepseek-r1", name="DeepSeek R1 (Free)", context_window=128000,
                     price_input="Free", price_output="Free", is_free=True, is_popular=True),
            ModelInfo(id="meta-llama/llama-3.1-8b-instruct", name="Llama 3.1 8B (Free)", context_window=128000,
                     price_input="Free", price_output="Free", is_free=True),
            ModelInfo(id="meta-llama/llama-3.2-3b-instruct", name="Llama 3.2 3B (Free)", context_window=128000,
                     price_input="Free", price_output="Free", is_free=True),
            ModelInfo(id="qwen/qwen-2.5-7b-instruct", name="Qwen 2.5 7B (Free)", context_window=128000,
                     price_input="Free", price_output="Free", is_free=True),
            ModelInfo(id="google/gemma-2-9b-it", name="Gemma 2 9B (Free)", context_window=8192,
                     price_input="Free", price_output="Free", is_free=True),
            ModelInfo(id="mistralai/mistral-7b-instruct", name="Mistral 7B (Free)", context_window=32768,
                     price_input="Free", price_output="Free", is_free=True),
            ModelInfo(id="microsoft/phi-3-mini-128k-instruct", name="Phi-3 Mini (Free)", context_window=128000,
                     price_input="Free", price_output="Free", is_free=True),
            # Платные модели
            ModelInfo(id="anthropic/claude-3.5-sonnet", name="Claude 3.5 Sonnet", context_window=200000,
                     price_input="$3/1M", price_output="$15/1M", is_popular=True),
            ModelInfo(id="openai/gpt-4o", name="GPT-4o", context_window=128000,
                     price_input="$5/1M", price_output="$15/1M", is_popular=True),
            ModelInfo(id="openai/gpt-4o-mini", name="GPT-4o Mini", context_window=128000,
                     price_input="$0.15/1M", price_output="$0.6/1M"),
            ModelInfo(id="google/gemini-flash-1.5", name="Gemini 1.5 Flash", context_window=1000000,
                     price_input="$0.075/1M", price_output="$0.3/1M"),
            ModelInfo(id="google/gemini-pro-1.5", name="Gemini 1.5 Pro", context_window=2000000,
                     price_input="$3.5/1M", price_output="$10.5/1M"),
            ModelInfo(id="meta-llama/llama-3.1-405b-instruct", name="Llama 3.1 405B", context_window=128000,
                     price_input="$3/1M", price_output="$3/1M"),
            ModelInfo(id="deepseek/deepseek-chat-v3-0324", name="DeepSeek V3", context_window=128000,
                     price_input="$0.27/1M", price_output="$1.1/1M"),
            ModelInfo(id="qwen/qwen-2.5-72b-instruct", name="Qwen 2.5 72B", context_window=128000,
                     price_input="$0.9/1M", price_output="$0.9/1M"),
        ],
    ),

    "zai": ProviderInfo(
        id="zai",
        name="Zhipu AI (Z.ai)",
        prefix="zai/",
        api_key_env="ZAI_API_KEY",
        api_base="https://api.z.ai/api/paas/v4/",
        description="Chinese GLM models by Zhipu AI",
        website="https://zhipuai.cn",
        docs_url="https://open.bigmodel.cn/dev/api",
        models=[
            ModelInfo(id="glm-4.5-flash", name="GLM-4.5 Flash (Recommended)", context_window=128000, max_output=4096,
                     price_input="Low", price_output="Low", is_popular=True),
            ModelInfo(id="glm-4-plus", name="GLM-4 Plus", context_window=128000, max_output=4096,
                     price_input="Medium", price_output="Medium", is_popular=True),
            ModelInfo(id="glm-4", name="GLM-4", context_window=128000, max_output=4096,
                     price_input="Medium", price_output="Medium"),
            ModelInfo(id="glm-4-flash", name="GLM-4 Flash", context_window=128000, max_output=4096,
                     price_input="Low", price_output="Low"),
            ModelInfo(id="glm-4-air", name="GLM-4 Air", context_window=128000, max_output=4096,
                     price_input="Low", price_output="Low"),
            ModelInfo(id="glm-4v-flash", name="GLM-4V Flash (Vision)", context_window=8192, max_output=4096,
                     supports_vision=True, price_input="Free", price_output="Free", is_free=True),
        ],
    ),

    "deepseek": ProviderInfo(
        id="deepseek",
        name="DeepSeek",
        prefix="deepseek/",
        api_key_env="DEEPSEEK_API_KEY",
        api_base="https://api.deepseek.com/v1",
        description="DeepSeek models with excellent reasoning",
        website="https://deepseek.com",
        docs_url="https://platform.deepseek.com/docs",
        models=[
            ModelInfo(id="deepseek-chat", name="DeepSeek Chat", context_window=64000, max_output=4096,
                     price_input="$0.27/1M", price_output="$1.1/1M", is_popular=True),
            ModelInfo(id="deepseek-reasoner", name="DeepSeek Reasoner (R1)", context_window=64000, max_output=8192,
                     price_input="$0.55/1M", price_output="$2.19/1M", is_popular=True),
        ],
    ),

    "google": ProviderInfo(
        id="google",
        name="Google AI (Gemini)",
        prefix="gemini/",
        api_key_env="GEMINI_API_KEY",
        api_base="https://generativelanguage.googleapis.com/v1beta",
        description="Google Gemini models",
        website="https://ai.google.dev",
        docs_url="https://ai.google.dev/docs",
        supports_model_listing=True,
        models=[
            ModelInfo(id="gemini-2.0-flash", name="Gemini 2.0 Flash", context_window=1000000, max_output=8192,
                     supports_vision=True, price_input="Free tier", price_output="Free tier", is_popular=True),
            ModelInfo(id="gemini-1.5-flash", name="Gemini 1.5 Flash", context_window=1000000, max_output=8192,
                     supports_vision=True, price_input="$0.075/1M", price_output="$0.3/1M", is_popular=True),
            ModelInfo(id="gemini-1.5-pro", name="Gemini 1.5 Pro", context_window=2000000, max_output=8192,
                     supports_vision=True, price_input="$3.5/1M", price_output="$10.5/1M"),
            ModelInfo(id="gemini-1.5-flash-8b", name="Gemini 1.5 Flash 8B", context_window=1000000, max_output=8192,
                     supports_vision=True, price_input="Free tier", price_output="Free tier", is_free=True),
        ],
    ),

    "groq": ProviderInfo(
        id="groq",
        name="Groq",
        prefix="groq/",
        api_key_env="GROQ_API_KEY",
        api_base="https://api.groq.com/openai/v1",
        description="Ultra-fast inference with LPU technology",
        website="https://groq.com",
        docs_url="https://console.groq.com/docs",
        supports_model_listing=True,
        models=[
            ModelInfo(id="llama-3.3-70b-versatile", name="Llama 3.3 70B", context_window=128000, max_output=8192,
                     price_input="Free tier", price_output="Free tier", is_popular=True),
            ModelInfo(id="llama-3.1-8b-instant", name="Llama 3.1 8B Instant", context_window=128000, max_output=8192,
                     price_input="Free tier", price_output="Free tier", is_free=True),
            ModelInfo(id="llama-3.2-1b-preview", name="Llama 3.2 1B Preview", context_window=8192, max_output=8192,
                     price_input="Free tier", price_output="Free tier", is_free=True),
            ModelInfo(id="llama-3.2-3b-preview", name="Llama 3.2 3B Preview", context_window=8192, max_output=8192,
                     price_input="Free tier", price_output="Free tier", is_free=True),
            ModelInfo(id="mixtral-8x7b-32768", name="Mixtral 8x7B", context_window=32768, max_output=32768,
                     price_input="Free tier", price_output="Free tier", is_free=True),
            ModelInfo(id="gemma2-9b-it", name="Gemma 2 9B", context_window=8192, max_output=8192,
                     price_input="Free tier", price_output="Free tier", is_free=True),
        ],
    ),

    "together_ai": ProviderInfo(
        id="together_ai",
        name="Together AI",
        prefix="together_ai/",
        api_key_env="TOGETHER_API_KEY",
        api_base="https://api.together.xyz/v1",
        description="Open-source models with fast inference",
        website="https://together.ai",
        docs_url="https://docs.together.ai",
        models=[
            ModelInfo(id="meta-llama/Llama-3.3-70B-Instruct-Turbo", name="Llama 3.3 70B Turbo", context_window=128000,
                     price_input="$0.88/1M", price_output="$0.88/1M", is_popular=True),
            ModelInfo(id="meta-llama/Llama-3.2-3B-Instruct-Turbo", name="Llama 3.2 3B Turbo", context_window=128000,
                     price_input="$0.06/1M", price_output="$0.06/1M"),
            ModelInfo(id="mistralai/Mixtral-8x7B-Instruct-v0.1", name="Mixtral 8x7B", context_window=32768,
                     price_input="$0.6/1M", price_output="$0.6/1M"),
            ModelInfo(id="Qwen/Qwen2.5-72B-Instruct-Turbo", name="Qwen 2.5 72B Turbo", context_window=32768,
                     price_input="$0.88/1M", price_output="$0.88/1M"),
        ],
    ),

    "mistral": ProviderInfo(
        id="mistral",
        name="Mistral AI",
        prefix="mistral/",
        api_key_env="MISTRAL_API_KEY",
        api_base="https://api.mistral.ai/v1",
        description="European AI company with efficient models",
        website="https://mistral.ai",
        docs_url="https://docs.mistral.ai",
        models=[
            ModelInfo(id="mistral-large-latest", name="Mistral Large", context_window=128000, max_output=8192,
                     price_input="$2/1M", price_output="$6/1M"),
            ModelInfo(id="mistral-medium-latest", name="Mistral Medium", context_window=128000, max_output=8192,
                     price_input="$0.7/1M", price_output="$2.1/1M"),
            ModelInfo(id="mistral-small-latest", name="Mistral Small", context_window=128000, max_output=8192,
                     price_input="$0.2/1M", price_output="$0.6/1M", is_popular=True),
            ModelInfo(id="codestral-latest", name="Codestral (Code)", context_window=32768, max_output=8192,
                     price_input="$0.3/1M", price_output="$0.9/1M"),
            ModelInfo(id="pixtral-12b-2409", name="Pixtral 12B (Vision)", context_window=128000, max_output=8192,
                     supports_vision=True, price_input="$0.15/1M", price_output="$0.15/1M"),
        ],
    ),

    "cohere": ProviderInfo(
        id="cohere",
        name="Cohere",
        prefix="cohere/",
        api_key_env="COHERE_API_KEY",
        api_base="https://api.cohere.ai/v1",
        description="Enterprise-focused AI models",
        website="https://cohere.ai",
        docs_url="https://docs.cohere.com",
        models=[
            ModelInfo(id="command-r-plus", name="Command R+", context_window=128000, max_output=4096,
                     price_input="$2.5/1M", price_output="$10/1M", is_popular=True),
            ModelInfo(id="command-r", name="Command R", context_window=128000, max_output=4096,
                     price_input="$0.5/1M", price_output="$1.5/1M"),
            ModelInfo(id="command", name="Command", context_window=4096, max_output=4096,
                     price_input="$1/1M", price_output="$2/1M"),
            ModelInfo(id="command-light", name="Command Light", context_window=4096, max_output=4096,
                     price_input="$0.38/1M", price_output="$0.38/1M"),
        ],
    ),

    "perplexity": ProviderInfo(
        id="perplexity",
        name="Perplexity AI",
        prefix="perplexity/",
        api_key_env="PERPLEXITY_API_KEY",
        api_base="https://api.perplexity.ai",
        description="AI-powered search with citations",
        website="https://perplexity.ai",
        docs_url="https://docs.perplexity.ai",
        models=[
            ModelInfo(id="llama-3.1-sonar-large-128k-online", name="Sonar Large Online", context_window=127072,
                     price_input="$1/1M", price_output="$1/1M", is_popular=True),
            ModelInfo(id="llama-3.1-sonar-small-128k-online", name="Sonar Small Online", context_window=127072,
                     price_input="$0.2/1M", price_output="$0.2/1M"),
            ModelInfo(id="llama-3.1-sonar-large-128k-chat", name="Sonar Large Chat", context_window=127072,
                     price_input="$1/1M", price_output="$1/1M"),
            ModelInfo(id="llama-3.1-sonar-small-128k-chat", name="Sonar Small Chat", context_window=127072,
                     price_input="$0.2/1M", price_output="$0.2/1M"),
        ],
    ),

    "xai": ProviderInfo(
        id="xai",
        name="xAI (Grok)",
        prefix="xai/",
        api_key_env="XAI_API_KEY",
        api_base="https://api.x.ai/v1",
        description="Elon Musk's AI company - Grok models",
        website="https://x.ai",
        docs_url="https://docs.x.ai",
        models=[
            ModelInfo(id="grok-beta", name="Grok Beta", context_window=131072, max_output=8192,
                     price_input="$5/1M", price_output="$15/1M", is_popular=True),
            ModelInfo(id="grok-2-1212", name="Grok 2", context_window=131072, max_output=8192,
                     price_input="$2/1M", price_output="$10/1M"),
            ModelInfo(id="grok-2-vision-1212", name="Grok 2 Vision", context_window=32768, max_output=8192,
                     supports_vision=True, price_input="$2/1M", price_output="$10/1M"),
        ],
    ),

    "azure": ProviderInfo(
        id="azure",
        name="Azure OpenAI",
        prefix="azure/",
        api_key_env="AZURE_API_KEY",
        api_base="",  # Configured per deployment
        description="OpenAI models on Microsoft Azure",
        website="https://azure.microsoft.com/en-us/products/ai-services/openai-service",
        docs_url="https://learn.microsoft.com/en-us/azure/ai-services/openai/",
        models=[
            ModelInfo(id="gpt-4o", name="GPT-4o", context_window=128000, max_output=4096,
                     supports_vision=True, is_popular=True),
            ModelInfo(id="gpt-4o-mini", name="GPT-4o Mini", context_window=128000, max_output=16384,
                     supports_vision=True),
            ModelInfo(id="gpt-4-turbo", name="GPT-4 Turbo", context_window=128000, max_output=4096,
                     supports_vision=True),
            ModelInfo(id="gpt-4", name="GPT-4", context_window=8192, max_output=4096),
            ModelInfo(id="gpt-35-turbo", name="GPT-3.5 Turbo", context_window=16385, max_output=4096),
        ],
    ),

    "custom": ProviderInfo(
        id="custom",
        name="Custom (OpenAI-compatible)",
        prefix="openai/",
        api_key_env="LLM_API_KEY",
        api_base="",  # User-defined
        description="Any OpenAI-compatible API endpoint",
        website="",
        docs_url="",
        models=[
            ModelInfo(id="custom-model", name="Custom Model", context_window=8192, max_output=4096),
        ],
    ),
}


class ProviderService:
    """Сервис управления LLM провайдерами."""

    _instance: Optional['ProviderService'] = None
    _providers: dict[str, ProviderInfo] = {}
    _api_keys: dict[str, str] = {}

    def __new__(cls) -> 'ProviderService':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._providers:
            self._providers = LITELLM_PROVIDERS.copy()
            self._load_api_keys_from_env()

    @classmethod
    def get_instance(cls) -> 'ProviderService':
        """Получение singleton экземпляра."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_api_keys_from_env(self):
        """Загрузка API ключей из переменных окружения."""
        for provider_id, provider in self._providers.items():
            key = os.getenv(provider.api_key_env, "")
            if key:
                self._api_keys[provider_id] = key

    def get_providers(self) -> dict[str, ProviderInfo]:
        """Получение всех провайдеров."""
        return self._providers.copy()

    def get_provider(self, provider_id: str) -> Optional[ProviderInfo]:
        """Получение провайдера по ID."""
        return self._providers.get(provider_id)

    def get_provider_models(self, provider_id: str) -> list[ModelInfo]:
        """Получение моделей провайдера."""
        provider = self.get_provider(provider_id)
        return provider.models if provider else []

    def get_api_key(self, provider_id: str) -> str:
        """Получение API ключа для провайдера."""
        return self._api_keys.get(provider_id, "")

    def set_api_key(self, provider_id: str, api_key: str) -> bool:
        """Установка API ключа для провайдера."""
        if provider_id not in self._providers:
            logger.error(f"Unknown provider: {provider_id}")
            return False

        self._api_keys[provider_id] = api_key

        # Сохраняем в переменные окружения
        provider = self._providers[provider_id]
        os.environ[provider.api_key_env] = api_key

        logger.info(f"API key set for provider: {provider_id}")
        return True

    def set_api_key_to_env(self, provider_id: str, api_key: str) -> bool:
        """Сохранение API ключа в переменные окружения."""
        if provider_id not in self._providers:
            return False

        provider = self._providers[provider_id]
        os.environ[provider.api_key_env] = api_key
        self._api_keys[provider_id] = api_key
        return True

    def save_api_key_to_file(self, provider_id: str, api_key: str, env_path: Optional[Path] = None) -> bool:
        """Сохранение API ключа в .env файл."""
        if provider_id not in self._providers:
            return False

        provider = self._providers[provider_id]

        try:
            from dotenv import set_key

            if env_path is None:
                env_path = Path.cwd() / ".env"

            if not env_path.exists():
                env_path.touch()

            set_key(str(env_path), provider.api_key_env, api_key)
            self._api_keys[provider_id] = api_key
            os.environ[provider.api_key_env] = api_key

            logger.info(f"API key saved for {provider_id} to {env_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save API key: {e}")
            return False

    def has_api_key(self, provider_id: str) -> bool:
        """Проверка наличия API ключа."""
        key = self._api_keys.get(provider_id, "")
        return bool(key and key not in ["", "your_api_key_here", "your-zai-api-key"])

    def test_connection(self, provider_id: str, model_id: Optional[str] = None) -> ConnectionTestResult:
        """Тестирование подключения к провайдеру."""
        provider = self.get_provider(provider_id)
        if not provider:
            return ConnectionTestResult(
                success=False,
                status=ConnectionStatus.FAILED,
                message=f"Unknown provider: {provider_id}",
            )

        api_key = self.get_api_key(provider_id)
        if not api_key:
            return ConnectionTestResult(
                success=False,
                status=ConnectionStatus.NO_API_KEY,
                message=f"No API key configured for {provider.name}",
            )

        # Если модель не указана, используем первую из списка
        if not model_id and provider.models:
            model_id = provider.models[0].id

        if not model_id:
            return ConnectionTestResult(
                success=False,
                status=ConnectionStatus.FAILED,
                message="No model specified and no models available",
            )

        return self._test_model_connection(provider, model_id, api_key)

    def test_model(self, provider_id: str, model_id: str) -> ConnectionTestResult:
        """Тестирование конкретной модели."""
        provider = self.get_provider(provider_id)
        if not provider:
            return ConnectionTestResult(
                success=False,
                status=ConnectionStatus.FAILED,
                message=f"Unknown provider: {provider_id}",
            )

        api_key = self.get_api_key(provider_id)
        if not api_key:
            return ConnectionTestResult(
                success=False,
                status=ConnectionStatus.NO_API_KEY,
                message=f"No API key configured for {provider.name}",
            )

        return self._test_model_connection(provider, model_id, api_key)

    def _test_model_connection(self, provider: ProviderInfo, model_id: str, api_key: str) -> ConnectionTestResult:
        """Тестирование подключения к конкретной модели."""
        import time

        litellm = get_litellm()
        full_model = f"{provider.prefix}{model_id}"

        start_time = time.time()

        try:
            # Формируем параметры запроса
            kwargs = {
                "model": full_model,
                "messages": [{"role": "user", "content": "Say 'OK' if you can read this."}],
                "max_tokens": 10,
                "timeout": 30,
            }

            # Устанавливаем API ключ
            if provider.api_base:
                kwargs["api_base"] = provider.api_base

            # Специфичные настройки для провайдеров
            if provider.id == "anthropic":
                os.environ["ANTHROPIC_API_KEY"] = api_key
            elif provider.id == "zai":
                os.environ["ZAI_API_KEY"] = api_key
            elif provider.id == "openrouter":
                os.environ["OPENROUTER_API_KEY"] = api_key
            elif provider.id == "deepseek":
                os.environ["DEEPSEEK_API_KEY"] = api_key
            elif provider.id == "google":
                os.environ["GEMINI_API_KEY"] = api_key
            elif provider.id == "groq":
                os.environ["GROQ_API_KEY"] = api_key
            elif provider.id == "mistral":
                os.environ["MISTRAL_API_KEY"] = api_key
            else:
                kwargs["api_key"] = api_key

            response = litellm.completion(**kwargs)

            elapsed_ms = (time.time() - start_time) * 1000

            if response and response.choices:
                return ConnectionTestResult(
                    success=True,
                    status=ConnectionStatus.SUCCESS,
                    message=f"Successfully connected to {provider.name}",
                    model=full_model,
                    response_time_ms=round(elapsed_ms, 2),
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    status=ConnectionStatus.FAILED,
                    message="Empty response from API",
                    model=full_model,
                    response_time_ms=round(elapsed_ms, 2),
                )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            error_msg = str(e)

            # Определяем тип ошибки
            if "api_key" in error_msg.lower() or "unauthorized" in error_msg.lower() or "401" in error_msg:
                status = ConnectionStatus.INVALID_KEY
            elif "timeout" in error_msg.lower():
                status = ConnectionStatus.TIMEOUT
            else:
                status = ConnectionStatus.FAILED

            return ConnectionTestResult(
                success=False,
                status=status,
                message=f"Connection failed: {error_msg[:100]}",
                model=full_model,
                response_time_ms=round(elapsed_ms, 2),
                error_details=error_msg,
            )

    def fetch_models_from_api(self, provider_id: str) -> list[dict]:
        """Получение списка моделей через API провайдера (если поддерживается)."""
        provider = self.get_provider(provider_id)
        if not provider or not provider.supports_model_listing:
            return []

        api_key = self.get_api_key(provider_id)
        if not api_key:
            return []

        try:
            import requests

            headers = {"Authorization": f"Bearer {api_key}"}

            if provider_id == "openai":
                response = requests.get("https://api.openai.com/v1/models", headers=headers, timeout=10)
            elif provider_id == "openrouter":
                response = requests.get("https://openrouter.ai/api/v1/models", headers=headers, timeout=10)
            elif provider_id == "groq":
                response = requests.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=10)
            else:
                return []

            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])

        except Exception as e:
            logger.warning(f"Failed to fetch models from {provider_id}: {e}")

        return []

    def get_litellm_config(self, provider_id: str, model_id: str) -> dict:
        """Получение конфигурации для LiteLLM."""
        provider = self.get_provider(provider_id)
        if not provider:
            return {}

        api_key = self.get_api_key(provider_id)
        full_model = f"{provider.prefix}{model_id}"

        config = {
            "model": full_model,
            "api_key": api_key,
        }

        if provider.api_base and provider.id != "openai":
            config["api_base"] = provider.api_base

        return config

    def get_popular_models(self) -> list[tuple[str, str, ModelInfo]]:
        """Получение списка популярных моделей (provider_id, model_id, ModelInfo)."""
        popular = []
        for provider_id, provider in self._providers.items():
            for model in provider.models:
                if model.is_popular:
                    popular.append((provider_id, model.id, model))
        return popular

    def get_free_models(self) -> list[tuple[str, str, ModelInfo]]:
        """Получение списка бесплатных моделей."""
        free = []
        for provider_id, provider in self._providers.items():
            for model in provider.models:
                if model.is_free:
                    free.append((provider_id, model.id, model))
        return free

    def search_models(self, query: str) -> list[tuple[str, str, ModelInfo]]:
        """Поиск моделей по названию или описанию."""
        query_lower = query.lower()
        results = []

        for provider_id, provider in self._providers.items():
            for model in provider.models:
                if (query_lower in model.name.lower() or
                    query_lower in model.id.lower() or
                    query_lower in provider.name.lower()):
                    results.append((provider_id, model.id, model))

        return results
