#!/usr/bin/env python3
"""
OpenKB GUI - Main Entry Point
Локальная система управления знаниями на базе OpenKB и GLM-4.7-Flash
"""

import sys
import os
import logging
from pathlib import Path

# Добавляем src в path
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import customtkinter as ctk

from gui.main_window import MainWindow
from services.config_service import ConfigService


def setup_logging(log_level: str = "INFO"):
    """Настройка логирования"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Создаём директорию для логов
    log_dir = Path(__file__).parent / "workspace" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    handlers = [
        logging.StreamHandler(sys.stdout),
    ]
    
    # Файловый обработчик
    try:
        log_file = log_dir / "openkb_gui.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(file_handler)
    except Exception as e:
        print(f"Warning: Could not create log file: {e}")
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format=log_format,
        handlers=handlers,
    )


def check_dependencies():
    """Проверка зависимостей"""
    logger = logging.getLogger(__name__)
    missing = []
    
    # Проверяем OpenKB
    try:
        import subprocess
        result = subprocess.run(["openkb", "--version"], capture_output=True, timeout=10)
        if result.returncode == 0:
            logger.info(f"OpenKB: {result.stdout.decode().strip()}")
        else:
            missing.append("openkb")
    except FileNotFoundError:
        missing.append("openkb")
        logger.warning("OpenKB not found. Install with: pip install openkb")
    except Exception as e:
        logger.warning(f"Could not check OpenKB: {e}")
    
    # Проверяем watchdog
    try:
        import watchdog
        logger.info("Watchdog: installed")
    except ImportError:
        missing.append("watchdog")
        logger.warning("Watchdog not found. Install with: pip install watchdog")
    
    # Проверяем litellm
    try:
        import litellm
        logger.info("LiteLLM: installed")
    except ImportError:
        missing.append("litellm")
        logger.warning("LiteLLM not found. Install with: pip install litellm")
    
    return missing


def main():
    """Главная функция приложения"""
    # Загружаем конфигурацию
    config_service = ConfigService.get_instance()
    config = config_service.load_config()
    
    # Настраиваем логирование
    setup_logging(config.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 50)
    logger.info("OpenKB GUI - Запуск приложения")
    logger.info(f"Версия: 0.1.0")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info("=" * 50)
    
    # Проверяем зависимости
    missing = check_dependencies()
    if missing:
        logger.warning(f"Missing dependencies: {', '.join(missing)}")
        logger.warning("Some functionality may be limited.")
    
    # Проверяем конфигурацию
    if not config.is_valid():
        logger.warning("API ключ не настроен. Откройте Settings для настройки.")
    
    # Создаём структуру workspace
    config_service.ensure_workspace()
    logger.info(f"Workspace: {config_service.get_workspace_path()}")
    
    # Настройка CustomTkinter
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    # Создаём главное окно
    app = MainWindow()
    
    # Показываем предупреждения
    if missing:
        app.after(100, lambda: app._log_build(
            f"\n⚠ Warning: Missing dependencies: {', '.join(missing)}\n"
            f"Install with: pip install {' '.join(missing)}\n\n"
        ))
    
    if not config.is_valid():
        app.after(200, lambda: app._log_build(
            "⚠ Warning: API key not configured.\n"
            "Open Settings tab to configure your API key.\n\n"
        ))
    
    # Запускаем главный цикл
    logger.info("Запуск главного цикла приложения")
    app.mainloop()
    
    logger.info("Приложение завершено")


if __name__ == "__main__":
    main()
