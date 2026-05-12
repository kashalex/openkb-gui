"""
Config Service - Управление конфигурацией приложения
Загрузка и сохранение настроек из .env файла и .z-ai-config
Поддержка нескольких провайдеров: Z.ai и OpenRouter
Интеграция с ProviderService для гибкого управления провайдерами
Валидация ввода и безопасность
"""

import os
import re
import json
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from dotenv import load_dotenv, set_key, find_dotenv
import logging

logger = logging.getLogger(__name__)

PLACEHOLDER_API_KEYS = {"", "your_api_key_here", "your-zai-api-key"}

def clean_api_key(value: str) -> str:
    """Удаление placeholder-значений API ключей из конфигурации."""
    value = (value or "").strip()
    return "" if value in PLACEHOLDER_API_KEYS else value


# Оптимальные модели по цене/качеству (legacy compatibility)
PROVIDER_MODELS = {
    "zai": {
        "name": "Z.ai (智谱)",
        "prefix": "zai/",
        "api_key_env": "ZAI_API_KEY",
        "base_url": "https://api.z.ai/api/paas/v4/",
        "models": [
            {"id": "glm-4.5-flash", "name": "GLM-4.5 Flash (рекомендуется)", "price": "низкая"},
            {"id": "glm-4-plus", "name": "GLM-4 Plus (лучшее качество)", "price": "средняя"},
            {"id": "glm-4", "name": "GLM-4", "price": "средняя"},
            {"id": "glm-4-flash", "name": "GLM-4 Flash", "price": "низкая"},
        ]
    },
    "openrouter": {
        "name": "OpenRouter",
        "prefix": "openrouter/",
        "api_key_env": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "models": [
            # Бесплатные модели
            {"id": "deepseek/deepseek-chat", "name": "DeepSeek Chat (бесплатно)", "price": "бесплатно"},
            {"id": "meta-llama/llama-3.1-8b-instruct", "name": "Llama 3.1 8B (бесплатно)", "price": "бесплатно"},
            {"id": "meta-llama/llama-3.2-3b-instruct", "name": "Llama 3.2 3B (бесплатно)", "price": "бесплатно"},
            {"id": "qwen/qwen-2.5-7b-instruct", "name": "Qwen 2.5 7B (бесплатно)", "price": "бесплатно"},
            {"id": "google/gemma-2-9b-it", "name": "Gemma 2 9B (бесплатно)", "price": "бесплатно"},
            {"id": "mistralai/mistral-7b-instruct", "name": "Mistral 7B (бесплатно)", "price": "бесплатно"},
            {"id": "microsoft/phi-3-mini-128k-instruct", "name": "Phi-3 Mini (бесплатно)", "price": "бесплатно"},
            # Платные модели (оптимальные)
            {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "price": "$3/M"},
            {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "price": "$0.15/M"},
            {"id": "google/gemini-flash-1.5", "name": "Gemini 1.5 Flash", "price": "$0.075/M"},
            {"id": "deepseek/deepseek-chat-v3-0324", "name": "DeepSeek V3", "price": "$0.27/M"},
        ]
    }
}

# Fallback порядок провайдеров при ошибках
PROVIDER_FALLBACK_ORDER = ["openrouter", "zai"]


@dataclass
class AppConfig:
    """Конфигурация приложения"""
    # Текущий провайдер и модель
    llm_model: str = "zai/glm-4.5-flash"
    llm_api_key: str = ""
    llm_api_base: str = ""
    
    # Z.ai Settings
    zai_api_key: str = ""
    zai_model: str = "glm-4.5-flash"
    
    # OpenRouter Settings
    openrouter_api_key: str = ""
    openrouter_model: str = "deepseek/deepseek-chat"
    
    # PageIndex OCR
    pageindex_api_key: str = ""
    
    # Workspace
    workspace_path: str = "./workspace"
    
    # Watch Mode
    watch_enabled: bool = True
    watch_debounce_seconds: int = 2
    
    # Logging
    log_level: str = "INFO"
    
    # Runtime state
    config_loaded: bool = field(default=False, repr=False)
    config_path: Optional[Path] = field(default=None, repr=False)
    
    def is_valid(self) -> bool:
        """Проверка валидности конфигурации"""
        has_key = bool(
            (self.zai_api_key and self.zai_api_key not in ["your-zai-api-key", "your_api_key_here", ""]) or
            (self.openrouter_api_key and self.openrouter_api_key not in ["your_api_key_here", ""]) or
            (self.llm_api_key and self.llm_api_key not in ["your_api_key_here", ""])
        )
        return has_key
    
    def has_pageindex(self) -> bool:
        """Проверка наличия PageIndex API ключа"""
        return bool(self.pageindex_api_key)
    
    def get_litellm_model(self) -> str:
        """Получение модели для LiteLLM с правильным префиксом"""
        if self.llm_model:
            return self.llm_model
        # Fallback
        if self.zai_api_key:
            return f"zai/{self.zai_model}"
        return "zai/glm-4.5-flash"
    
    def get_current_provider(self) -> str:
        """Определение текущего провайдера по модели."""
        if self.llm_model.startswith(("zai/", "zhipu/")):
            return "zai"
        if self.llm_model.startswith("openrouter/"):
            return "openrouter"
        return "custom"
    
    def get_api_key_for_provider(self, provider: str) -> str:
        """Получение API ключа для провайдера с fallback на общий ключ."""
        if provider == "zai":
            return self.zai_api_key or self.llm_api_key
        if provider == "openrouter":
            return self.openrouter_api_key or self.llm_api_key
        return self.llm_api_key


class ConfigService:
    """Сервис управления конфигурацией"""
    
    _instance: Optional['ConfigService'] = None
    _config: Optional[AppConfig] = None
    
    def __new__(cls) -> 'ConfigService':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._config = AppConfig()
    
    @classmethod
    def get_instance(cls) -> 'ConfigService':
        """Получение singleton экземпляра"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """
        Сброс singleton экземпляра.
        Использовать при смене настроек для применения изменений.
        """
        cls._instance = None
        cls._config = None
        logger.info("ConfigService instance reset")
    
    def reload_config(self, config_path: Optional[str] = None) -> AppConfig:
        """
        Перезагрузка конфигурации из файла.
        Использовать после сохранения настроек.
        
        Args:
            config_path: Путь к .env файлу (опционально)
        
        Returns:
            AppConfig: Перезагруженная конфигурация
        """
        # Сбрасываем текущую конфигурацию
        self._config = AppConfig()
        return self.load_config(config_path)
    
    @property
    def config(self) -> AppConfig:
        """Получение текущей конфигурации"""
        return self._config
    
    def load_config(self, config_path: Optional[str] = None) -> AppConfig:
        """
        Загрузка конфигурации из .env и .z-ai-config файлов
        
        Args:
            config_path: Путь к .env файлу (опционально)
        
        Returns:
            AppConfig: Загруженная конфигурация
        """
        # Определяем путь к .env
        if config_path:
            env_path = Path(config_path)
        else:
            # Ищем .env в текущей директории и родительских
            env_path = Path(find_dotenv()) if find_dotenv() else Path.cwd() / ".env"
        
        self._config.config_path = env_path
        
        # Загружаем .env
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"Загружена конфигурация из: {env_path}")
        
        # Загружаем .z-ai-config (приоритет над .env для Z.ai ключа)
        self._load_zai_config()
        
        # Читаем значения из env. OPENAI_* оставлен как legacy fallback,
        # но каноничная конфигурация приложения — LLM_* + provider-specific keys.
        legacy_model = os.getenv("OPENAI_MODEL", "")
        legacy_key = os.getenv("OPENAI_API_KEY", "")
        legacy_base = os.getenv("OPENAI_API_BASE", "")
        self._config.llm_model = os.getenv("LLM_MODEL", legacy_model or self._config.llm_model)
        self._config.llm_api_key = clean_api_key(os.getenv("LLM_API_KEY", legacy_key))
        self._config.llm_api_base = os.getenv("LLM_API_BASE", legacy_base)
        
        # Provider-specific keys
        self._config.zai_api_key = clean_api_key(os.getenv("ZAI_API_KEY", self._config.zai_api_key)) or (
            self._config.llm_api_key if self._config.llm_model.startswith(("zai/", "zhipu/")) else ""
        )
        self._config.openrouter_api_key = clean_api_key(os.getenv("OPENROUTER_API_KEY", "")) or (
            self._config.llm_api_key if self._config.llm_model.startswith("openrouter/") else ""
        )
        
        # Other settings
        self._config.pageindex_api_key = os.getenv("PAGEINDEX_API_KEY", "")
        self._config.workspace_path = os.getenv("WORKSPACE_PATH", self._config.workspace_path)
        self._config.watch_enabled = os.getenv("WATCH_ENABLED", "true").lower() == "true"
        self._config.watch_debounce_seconds = int(os.getenv("WATCH_DEBOUNCE_SECONDS", "2"))
        self._config.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Устанавливаем переменные окружения для LiteLLM
        self._set_provider_env()
        
        self._config.config_loaded = True
        
        return self._config
    
    def _load_zai_config(self):
        """Загрузка конфигурации из .z-ai-config файла"""
        # Пути для поиска .z-ai-config
        config_paths = [
            Path.cwd() / ".z-ai-config",
            Path.cwd() / ".z-ai-config.json",
            Path.cwd() / "workspace" / ".z-ai-config",
            Path.cwd() / "workspace" / ".z-ai-config.json",
            Path.home() / ".z-ai-config",
        ]
        
        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        zai_config = json.load(f)
                    
                    # Загружаем Z.ai настройки
                    token = zai_config.get("token", zai_config.get("apiKey", ""))
                    model = zai_config.get("model", "glm-4.5-flash")
                    
                    token = clean_api_key(token)
                    if token:
                        self._config.zai_api_key = token
                        self._config.zai_model = model
                        
                        # Если модель не установлена, используем Z.ai
                        if not self._config.llm_model or self._config.llm_model == "zai/glm-4.5-flash":
                            self._config.llm_model = f"zai/{model}"
                            self._config.llm_api_key = token
                        
                        logger.info(f"Загружена конфигурация Z.ai из: {config_path}")
                        return
                        
                except Exception as e:
                    logger.warning(f"Ошибка чтения {config_path}: {e}")
                    continue
        
        logger.debug("Файл .z-ai-config не найден или пуст")
    
    def save_config(self) -> bool:
        """
        Сохранение текущей конфигурации в .env файл
        
        Returns:
            bool: True если сохранение успешно
        """
        if not self._config.config_path:
            self._config.config_path = Path.cwd() / ".env"
        
        env_path = self._config.config_path
        
        try:
            # Создаём файл если не существует
            if not env_path.exists():
                env_path.touch()
            
            # Сохраняем основные настройки
            set_key(str(env_path), "LLM_MODEL", self._config.llm_model)
            set_key(str(env_path), "LLM_API_KEY", self._config.llm_api_key)
            set_key(str(env_path), "LLM_API_BASE", self._config.llm_api_base or "")
            
            # Provider-specific keys
            set_key(str(env_path), "ZAI_API_KEY", self._config.zai_api_key)
            set_key(str(env_path), "OPENROUTER_API_KEY", self._config.openrouter_api_key)
            
            # Other settings
            set_key(str(env_path), "PAGEINDEX_API_KEY", self._config.pageindex_api_key)
            set_key(str(env_path), "WORKSPACE_PATH", self._config.workspace_path)
            set_key(str(env_path), "WATCH_ENABLED", str(self._config.watch_enabled).lower())
            set_key(str(env_path), "WATCH_DEBOUNCE_SECONDS", str(self._config.watch_debounce_seconds))
            set_key(str(env_path), "LOG_LEVEL", self._config.log_level)
            
            # Устанавливаем переменные окружения
            self._set_provider_env()
            
            logger.info(f"Конфигурация сохранена в: {env_path}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации: {e}")
            return False
    
    def update_config(self, **kwargs) -> None:
        """
        Обновление параметров конфигурации
        
        Args:
            **kwargs: Параметры для обновления
        """
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
                logger.debug(f"Обновлён параметр {key}")
            else:
                logger.warning(f"Неизвестный параметр конфигурации: {key}")
    
    def _set_provider_env(self) -> None:
        """Установка переменных окружения для провайдеров"""
        # Z.ai
        zai_key = self._config.zai_api_key or (
            self._config.llm_api_key if self._config.llm_model.startswith(("zai/", "zhipu/")) else ""
        )
        if zai_key:
            os.environ["ZAI_API_KEY"] = zai_key
        
        # OpenRouter
        openrouter_key = self._config.openrouter_api_key or (
            self._config.llm_api_key if self._config.llm_model.startswith("openrouter/") else ""
        )
        if openrouter_key:
            os.environ["OPENROUTER_API_KEY"] = openrouter_key
        
        # Общие для LLM
        if self._config.llm_api_key:
            os.environ["LLM_API_KEY"] = self._config.llm_api_key
        if self._config.llm_model:
            os.environ["LLM_MODEL"] = self._config.llm_model
        if self._config.llm_api_base:
            os.environ["LLM_API_BASE"] = self._config.llm_api_base
        
        logger.debug(f"Provider env set: model={self._config.llm_model}")
    
    def set_provider(self, provider: str, model_id: str) -> None:
        """
        Установка провайдера и модели
        
        Args:
            provider: ID провайдера (zai, openrouter)
            model_id: ID модели
        """
        if provider not in PROVIDER_MODELS:
            logger.error(f"Неизвестный провайдер: {provider}")
            return
        
        provider_info = PROVIDER_MODELS[provider]
        prefix = provider_info["prefix"]
        
        # Устанавливаем модель
        self._config.llm_model = f"{prefix}{model_id}"
        
        # Устанавливаем API ключ для провайдера
        api_key = self._config.get_api_key_for_provider(provider)
        if api_key:
            self._config.llm_api_key = api_key
        
        # Устанавливаем base URL для OpenRouter
        if provider == "openrouter":
            self._config.llm_api_base = provider_info["base_url"]
        else:
            self._config.llm_api_base = ""
        
        self._set_provider_env()
        logger.info(f"Установлен провайдер: {provider}, модель: {model_id}")
    
    # === Валидация ввода ===
    
    def validate_api_key(self, api_key: str) -> tuple:
        """
        Валидация API ключа
        
        Args:
            api_key: API ключ для проверки
        
        Returns:
            tuple: (валиден, сообщение)
        """
        if not api_key:
            return False, "API ключ не указан"
        
        if api_key in PLACEHOLDER_API_KEYS:
            return False, "Укажите реальный API ключ"
        
        if len(api_key) < 10:
            return False, "API ключ слишком короткий"
        
        return True, "API ключ валиден"
    
    def validate_path(self, path: str) -> tuple:
        """
        Валидация пути к файлу/директории
        
        Args:
            path: Путь для проверки
        
        Returns:
            tuple: (валиден, сообщение)
        """
        if not path:
            return False, "Путь не указан"
        
        # Проверка на опасные символы
        dangerous_chars = ['<', '>', '|', '*', '?', '"']
        for char in dangerous_chars:
            if char in path:
                return False, f"Путь содержит недопустимый символ: {char}"
        
        # Проверка на абсолютные пути вне домашней директории (опционально)
        try:
            p = Path(path)
            # Нормализуем путь
            normalized = p.resolve()
            return True, f"Путь валиден: {normalized}"
        except Exception as e:
            return False, f"Некорректный путь: {e}"
    
    def validate_filename(self, filename: str) -> tuple:
        """
        Валидация имени файла
        
        Args:
            filename: Имя файла для проверки
        
        Returns:
            tuple: (валиден, sanitized_name или сообщение об ошибке)
        """
        if not filename:
            return False, "Имя файла не указано"
        
        # Удаляем опасные символы
        dangerous_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        sanitized = filename
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Удаляем управляющие символы
        sanitized = ''.join(c for c in sanitized if ord(c) >= 32)
        
        # Ограничиваем длину
        if len(sanitized) > 255:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:250] + ext
        
        if sanitized != filename:
            logger.warning(f"Имя файла изменено: '{filename}' -> '{sanitized}'")
        
        return True, sanitized
    
    def sanitize_path(self, path: str) -> str:
        """
        Санитизация пути
        
        Args:
            path: Исходный путь
        
        Returns:
            str: Санитизированный путь
        """
        # Нормализуем разделители
        sanitized = path.replace('\\', '/')
        
        # Удаляем множественные слеши
        sanitized = re.sub(r'/+', '/', sanitized)
        
        # Удаляем trailing slash
        sanitized = sanitized.rstrip('/')
        
        return sanitized
    
    def get_workspace_path(self) -> Path:
        """Получение абсолютного пути к workspace"""
        sanitized = self.sanitize_path(self._config.workspace_path)
        return Path(sanitized).resolve()
    
    def ensure_workspace(self) -> bool:
        """
        Создание структуры workspace если не существует
        
        Returns:
            bool: True если структура создана или уже существует
        """
        try:
            workspace = self.get_workspace_path()
            
            # Основные директории
            dirs = [
                workspace / "raw",
                workspace / "wiki" / "concepts",
                workspace / "wiki" / "summaries",
                workspace / "wiki" / "explorations",
                workspace / "wiki" / "reports",
                workspace / "wiki" / "sources",
                workspace / "sessions",
                workspace / "logs",
            ]
            
            for d in dirs:
                d.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Workspace структура создана: {workspace}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка создания workspace: {e}")
            return False
    
    def get_llm_config(self) -> dict:
        """
        Получение конфигурации для LiteLLM
        
        Returns:
            dict: Конфигурация для LiteLLM
        """
        model = self._config.get_litellm_model()
        provider = self._config.get_current_provider()
        
        config = {
            "model": model,
            "api_key": self._config.get_api_key_for_provider(provider),
        }
        
        if provider == "openrouter":
            config["api_base"] = PROVIDER_MODELS["openrouter"]["base_url"]
        
        return config
    
    def get_available_models(self) -> Dict:
        """Получение списка доступных моделей"""
        return PROVIDER_MODELS
    
    # === Provider Service Integration ===
    
    def get_provider_service(self):
        """Get the ProviderService instance"""
        from services.provider_service import ProviderService
        return ProviderService.get_instance()
    
    def load_providers(self, config_path: Optional[str] = None) -> Dict:
        """
        Load providers from providers.json
        
        Args:
            config_path: Optional path to providers.json
        
        Returns:
            Dict of provider configurations
        """
        provider_service = self.get_provider_service()
        return provider_service.load_providers(config_path)
    
    def get_all_providers(self) -> Dict:
        """Get all provider configurations"""
        provider_service = self.get_provider_service()
        return provider_service.get_providers()
    
    def get_provider_config(self, provider_id: str):
        """Get a specific provider configuration"""
        provider_service = self.get_provider_service()
        return provider_service.get_provider(provider_id)
    
    def set_provider_model(self, provider_id: str, model_id: str) -> bool:
        """
        Set the current provider and model
        
        Args:
            provider_id: Provider ID
            model_id: Model ID
        
        Returns:
            True if successful
        """
        provider = self.get_provider_config(provider_id)
        if not provider:
            logger.error(f"Provider {provider_id} not found")
            return False
        
        provider_service = self.get_provider_service()
        
        # Set the full model name
        self._config.llm_model = f"{provider.prefix}{model_id}"
        
        # Get API key for this provider
        api_key = provider_service.get_api_key(provider_id)
        if api_key:
            self._config.llm_api_key = api_key
        
        # Set API base for non-Z.ai providers
        if provider_id != "zai":
            self._config.llm_api_base = provider.api_base
        else:
            self._config.llm_api_base = ""
        
        self._set_provider_env()
        logger.info(f"Set provider: {provider_id}, model: {model_id}")
        return True
    
    def fetch_models_for_provider(self, provider_id: str) -> List:
        """
        Fetch models from provider API
        
        Args:
            provider_id: Provider ID
        
        Returns:
            List of model configurations
        """
        provider_service = self.get_provider_service()
        return provider_service.fetch_models_from_api(provider_id)
    
    def test_provider_connection(self, provider_id: str, model_id: Optional[str] = None):
        """
        Test connection to a provider
        
        Args:
            provider_id: Provider ID
            model_id: Optional specific model to test
        
        Returns:
            ConnectionTestResult
        """
        provider_service = self.get_provider_service()
        return provider_service.test_connection(provider_id, model_id)
    
    def test_model(self, provider_id: str, model_id: str):
        """
        Test a specific model
        
        Args:
            provider_id: Provider ID
            model_id: Model ID
        
        Returns:
            ConnectionTestResult
        """
        provider_service = self.get_provider_service()
        return provider_service.test_model(provider_id, model_id)
    
    def add_provider(self, provider_config) -> bool:
        """
        Add a new provider
        
        Args:
            provider_config: ProviderConfig object
        
        Returns:
            True if successful
        """
        provider_service = self.get_provider_service()
        return provider_service.add_provider(provider_config)
    
    def update_provider(self, provider_id: str, updates: dict) -> bool:
        """
        Update an existing provider
        
        Args:
            provider_id: Provider ID
            updates: Fields to update
        
        Returns:
            True if successful
        """
        provider_service = self.get_provider_service()
        return provider_service.update_provider(provider_id, updates)
    
    def delete_provider(self, provider_id: str) -> bool:
        """
        Delete a provider
        
        Args:
            provider_id: Provider ID
        
        Returns:
            True if successful
        """
        provider_service = self.get_provider_service()
        return provider_service.delete_provider(provider_id)
    
    def add_model_to_provider(self, provider_id: str, model_config) -> bool:
        """
        Add a model to a provider
        
        Args:
            provider_id: Provider ID
            model_config: ModelConfig object
        
        Returns:
            True if successful
        """
        provider_service = self.get_provider_service()
        return provider_service.add_model_to_provider(provider_id, model_config)
    
    def remove_model_from_provider(self, provider_id: str, model_id: str) -> bool:
        """
        Remove a model from a provider
        
        Args:
            provider_id: Provider ID
            model_id: Model ID
        
        Returns:
            True if successful
        """
        provider_service = self.get_provider_service()
        return provider_service.remove_model_from_provider(provider_id, model_id)
    
    def set_provider_api_key(self, provider_id: str, api_key: str) -> bool:
        """
        Set API key for a provider
        
        Args:
            provider_id: Provider ID
            api_key: API key value
        
        Returns:
            True if successful
        """
        provider_service = self.get_provider_service()
        success = provider_service.set_api_key_to_env(provider_id, api_key)
        
        # Also update the config for known providers
        if provider_id == "zai":
            self._config.zai_api_key = api_key
        elif provider_id == "openrouter":
            self._config.openrouter_api_key = api_key
        
        return success
    
    def get_provider_api_key(self, provider_id: str) -> str:
        """
        Get API key for a provider
        
        Args:
            provider_id: Provider ID
        
        Returns:
            API key or empty string
        """
        provider_service = self.get_provider_service()
        return provider_service.get_api_key(provider_id)
    
    # === Fallback механизм ===
    
    def get_fallback_provider(self, current_provider: str) -> Optional[str]:
        """
        Получение fallback провайдера
        
        Args:
            current_provider: Текущий провайдер
        
        Returns:
            ID fallback провайдера или None
        """
        for provider_id in PROVIDER_FALLBACK_ORDER:
            if provider_id != current_provider:
                api_key = self._config.get_api_key_for_provider(provider_id)
                if api_key:
                    return provider_id
        return None
    
    def try_with_fallback(self, operation, *args, **kwargs):
        """
        Выполнить операцию с fallback на другой провайдер
        
        Args:
            operation: Функция для выполнения
            *args, **kwargs: Аргументы для функции
        
        Returns:
            Результат операции или None
        """
        current_provider = self._config.get_current_provider()
        
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Operation failed with {current_provider}: {e}")
            
            # Try fallback
            fallback = self.get_fallback_provider(current_provider)
            if fallback:
                logger.info(f"Trying fallback provider: {fallback}")
                # Переключаем на fallback
                old_model = self._config.llm_model
                fallback_key = self._config.get_api_key_for_provider(fallback)
                prefix = PROVIDER_MODELS[fallback]["prefix"]
                
                # Устанавливаем fallback модель (первую из списка)
                first_model = PROVIDER_MODELS[fallback]["models"][0]["id"]
                self._config.llm_model = f"{prefix}{first_model}"
                self._config.llm_api_key = fallback_key
                self._set_provider_env()
                
                try:
                    result = operation(*args, **kwargs)
                    logger.info(f"Fallback to {fallback} succeeded")
                    return result
                except Exception as e2:
                    logger.error(f"Fallback also failed: {e2}")
                    # Восстанавливаем оригинальную модель
                    self._config.llm_model = old_model
                    self._set_provider_env()
            
            return None


# Import for type hints (avoid circular import)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from services.provider_service import ProviderService
