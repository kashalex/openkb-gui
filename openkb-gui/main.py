#!/usr/bin/env python3
"""
OpenKB GUI - Main Entry Point
Локальная система управления знаниями на базе OpenKB и GLM-4.7-Flash
"""

import sys
import os
import logging
from pathlib import Path
from types import ModuleType

# Добавляем src в path
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from services.config_service import ConfigService


def _format_python_command(*args: str) -> str:
    """Return a command pinned to the interpreter that is running the app."""
    executable = sys.executable or "python"
    return " ".join([f'"{executable}"', *args])


def _missing_dependency_message(package: str, import_name: str) -> str:
    """Build an actionable dependency error for venv/interpreter mismatches."""
    return (
        f"ERROR: Python package '{package}' is not installed for this interpreter.\n\n"
        f"Interpreter running OpenKB GUI:\n  {sys.executable}\n\n"
        "Install dependencies with the same interpreter, not a different global pip:\n"
        f"  {_format_python_command('-m', 'pip', 'install', '-r', 'requirements.txt')}\n"
        f"  {_format_python_command('-m', 'pip', 'install', package)}\n\n"
        "Verify that python and pip point to the same environment:\n"
        f"  {_format_python_command('-c', '"import sys; print(sys.executable)"')}\n"
        f"  {_format_python_command('-m', 'pip', '--version')}\n\n"
        f"If `pip install {package}` says 'Requirement already satisfied' but "
        f"`import {import_name}` still fails, your `pip` command is installing into another Python. "
        "Use `python -m pip ...` from the activated venv."
    )


def import_customtkinter_or_exit() -> ModuleType:
    """Import CustomTkinter with a clear message when the active venv is wrong."""
    try:
        import customtkinter as ctk
        return ctk
    except ModuleNotFoundError as exc:
        if exc.name != "customtkinter":
            raise
        print(_missing_dependency_message("customtkinter", "customtkinter"), file=sys.stderr)
        raise SystemExit(1) from exc


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
    
    # Проверяем OpenKB - пробуем разные способы
    openkb_found = False
    
    # Способ 1: Прямой вызов CLI
    try:
        import subprocess
        result = subprocess.run(["openkb", "--version"], capture_output=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.decode().strip() or result.stderr.decode().strip()
            logger.info(f"OpenKB (CLI): {version}")
            openkb_found = True
    except FileNotFoundError:
        pass
    except Exception:
        pass
    
    # Способ 2: python -m openkb
    if not openkb_found:
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, "-m", "openkb", "--version"],
                capture_output=True, timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.decode().strip() or result.stderr.decode().strip()
                logger.info(f"OpenKB (python -m): {version}")
                openkb_found = True
        except Exception:
            pass
    
    # Способ 3: Проверка импорта модуля
    if not openkb_found:
        try:
            import importlib.util
            spec = importlib.util.find_spec("openkb")
            if spec is not None:
                logger.info("OpenKB: installed (module)")
                openkb_found = True
        except Exception:
            pass
    
    if not openkb_found:
        missing.append("openkb")
        logger.warning("OpenKB not found. Install with: %s", _format_python_command("-m", "pip", "install", "openkb"))
    
    # Проверяем watchdog
    try:
        import watchdog
        logger.info("Watchdog: installed")
    except ImportError:
        missing.append("watchdog")
        logger.warning("Watchdog not found. Install with: %s", _format_python_command("-m", "pip", "install", "watchdog"))
    
    # Проверяем litellm
    try:
        import litellm
        logger.info("LiteLLM: installed")
    except ImportError:
        missing.append("litellm")
        logger.warning("LiteLLM not found. Install with: %s", _format_python_command("-m", "pip", "install", "litellm"))
    
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
    
    # Настройка CustomTkinter. Import happens here so missing GUI deps show
    # an actionable venv/pip diagnostic instead of a raw traceback.
    ctk = import_customtkinter_or_exit()
    from gui.main_window import MainWindow

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    # Создаём главное окно
    app = MainWindow()
    
    # Показываем предупреждения в build log
    if missing:
        def show_missing_warning():
            app._log_build("\n" + "="*50 + "\n")
            app._log_build("⚠ WARNING: Missing Dependencies\n")
            app._log_build("="*50 + "\n\n")
            app._log_build(f"Missing: {', '.join(missing)}\n")
            app._log_build(
                f"Install with: {_format_python_command('-m', 'pip', 'install', *missing)}\n\n"
            )
            if 'openkb' in missing:
                app._log_build("OpenKB is required for build functionality.\n")
                app._log_build("Without it, the Build tab cannot run a production build.\n\n")
            app._log_build("="*50 + "\n\n")
        app.after(100, show_missing_warning)
    
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
