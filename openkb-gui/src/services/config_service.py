"""
Config Service - Управление конфигурацией приложения
Загрузка и сохранение настроек из .env файла
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv, set_key, find_dotenv
import logging

logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """Конфигурация приложения"""
    # LLM Settings (для GUI)
    openai_model: str = "zhipu/glm-4-flash"
    openai_api_base: str = ""
    openai_api_key: str = ""
    
    # OpenKB Settings (для CLI)
    llm_model: str = "zhipu/glm-4-flash"
    llm_api_key: str = ""
    llm_api_base: str = ""
    
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
        return bool(self.llm_api_key and self.llm_api_key not in ["your_api_key_here", ""])
    
    def has_pageindex(self) -> bool:
        """Проверка наличия PageIndex API ключа"""
        return bool(self.pageindex_api_key)


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
    
    @property
    def config(self) -> AppConfig:
        """Получение текущей конфигурации"""
        return self._config
    
    def load_config(self, config_path: Optional[str] = None) -> AppConfig:
        """
        Загрузка конфигурации из .env файла
        
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
        else:
            logger.warning(f"Файл конфигурации не найден: {env_path}")
            return self._config
        
        # Читаем значения
        # GUI settings
        self._config.openai_model = os.getenv("OPENAI_MODEL", self._config.openai_model)
        self._config.openai_api_base = os.getenv("OPENAI_API_BASE", self._config.openai_api_base)
        self._config.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        
        # OpenKB/LLM settings (these are what OpenKB CLI uses)
        self._config.llm_model = os.getenv("LLM_MODEL", os.getenv("OPENAI_MODEL", self._config.llm_model))
        self._config.llm_api_key = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        self._config.llm_api_base = os.getenv("LLM_API_BASE", os.getenv("OPENAI_API_BASE", ""))
        
        # Other settings
        self._config.pageindex_api_key = os.getenv("PAGEINDEX_API_KEY", "")
        self._config.workspace_path = os.getenv("WORKSPACE_PATH", self._config.workspace_path)
        self._config.watch_enabled = os.getenv("WATCH_ENABLED", "true").lower() == "true"
        self._config.watch_debounce_seconds = int(os.getenv("WATCH_DEBOUNCE_SECONDS", "2"))
        self._config.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Устанавливаем переменные окружения для OpenKB
        self._set_openkb_env()
        
        self._config.config_loaded = True
        
        return self._config
    
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
            
            # Сохраняем значения - как GUI так и OpenKB settings
            set_key(str(env_path), "LLM_MODEL", self._config.llm_model)
            set_key(str(env_path), "LLM_API_KEY", self._config.llm_api_key)
            set_key(str(env_path), "LLM_API_BASE", self._config.llm_api_base)
            set_key(str(env_path), "OPENAI_MODEL", self._config.openai_model)
            set_key(str(env_path), "OPENAI_API_BASE", self._config.openai_api_base)
            set_key(str(env_path), "OPENAI_API_KEY", self._config.openai_api_key)
            set_key(str(env_path), "PAGEINDEX_API_KEY", self._config.pageindex_api_key)
            set_key(str(env_path), "WORKSPACE_PATH", self._config.workspace_path)
            set_key(str(env_path), "WATCH_ENABLED", str(self._config.watch_enabled).lower())
            set_key(str(env_path), "WATCH_DEBOUNCE_SECONDS", str(self._config.watch_debounce_seconds))
            set_key(str(env_path), "LOG_LEVEL", self._config.log_level)
            
            # Устанавливаем переменные окружения для OpenKB
            self._set_openkb_env()
            
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
                logger.debug(f"Обновлён параметр {key} = {value}")
            else:
                logger.warning(f"Неизвестный параметр конфигурации: {key}")
    
    def _set_openkb_env(self) -> None:
        """Установка переменных окружения для OpenKB CLI"""
        # OpenKB использует эти переменные окружения
        if self._config.llm_api_key:
            os.environ["LLM_API_KEY"] = self._config.llm_api_key
        if self._config.llm_model:
            os.environ["LLM_MODEL"] = self._config.llm_model
        if self._config.llm_api_base:
            os.environ["LLM_API_BASE"] = self._config.llm_api_base
        
        # Также устанавливаем переменные для LiteLLM (используются некоторыми провайдерами)
        if self._config.llm_api_key:
            os.environ["OPENAI_API_KEY"] = self._config.llm_api_key
        
        logger.debug(f"OpenKB env set: LLM_MODEL={self._config.llm_model}")
    
    def validate_api_key(self, api_key: str) -> tuple[bool, str]:
        """
        Валидация API ключа
        
        Args:
            api_key: API ключ для проверки
        
        Returns:
            tuple[bool, str]: (валиден, сообщение)
        """
        if not api_key:
            return False, "API ключ не указан"
        
        if api_key == "your_api_key_here":
            return False, "Укажите реальный API ключ"
        
        if len(api_key) < 10:
            return False, "API ключ слишком короткий"
        
        # Базовая проверка формата
        if not any(c.isalnum() for c in api_key):
            return False, "API ключ должен содержать буквенно-цифровые символы"
        
        return True, "API ключ валиден"
    
    def get_workspace_path(self) -> Path:
        """Получение абсолютного пути к workspace"""
        return Path(self._config.workspace_path).resolve()
    
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
        return {
            "model": self._config.openai_model,
            "api_base": self._config.openai_api_base,
            "api_key": self._config.openai_api_key,
        }
