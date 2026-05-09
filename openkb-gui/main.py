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
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    # Создаём директорию для логов
    log_dir = Path(__file__).parent / "workspace" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Файловый обработчик
    log_file = log_dir / "openkb_gui.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(log_format))
    logging.root.addHandler(file_handler)


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
    
    # Проверяем конфигурацию
    if not config.is_valid():
        logger.warning("API ключ не настроен. Откройте Settings для настройки.")
    
    # Создаём структуру workspace
    config_service.ensure_workspace()
    
    # Настройка CustomTkinter
    ctk.set_appearance_mode("dark")  # dark, light, system
    ctk.set_default_color_theme("blue")  # blue, dark-blue, green
    
    # Создаём главное окно
    app = MainWindow()
    
    # Запускаем главный цикл
    logger.info("Запуск главного цикла приложения")
    app.mainloop()
    
    logger.info("Приложение завершено")


if __name__ == "__main__":
    main()
