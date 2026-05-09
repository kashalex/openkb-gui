"""
Utils - Вспомогательные функции
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def format_file_size(size_bytes: int) -> str:
    """Форматирование размера файла"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def format_duration(seconds: float) -> str:
    """Форматирование длительности"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def format_datetime(dt: datetime) -> str:
    """Форматирование даты и времени"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def sanitize_filename(name: str) -> str:
    """Санитизация имени файла"""
    # Удаляем недопустимые символы
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # Заменяем пробелы на подчёркивания
    name = name.replace(' ', '_')
    # Ограничиваем длину
    if len(name) > 255:
        name = name[:255]
    return name


def extract_wikilinks(content: str) -> list[str]:
    """Извлечение wikilinks из markdown"""
    pattern = r'\[\[([^\]]+)\]\]'
    return list(set(re.findall(pattern, content)))


def extract_headings(content: str) -> list[tuple[int, str]]:
    """Извлечение заголовков из markdown"""
    headings = []
    for line in content.split('\n'):
        if line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            title = line.lstrip('#').strip()
            headings.append((level, title))
    return headings


def count_words(text: str) -> int:
    """Подсчёт слов в тексте"""
    # Для CJK символов считаем каждый символ как слово
    cjk_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    # Для остальных считаем слова
    words = len(re.findall(r'\b[a-zA-Z0-9]+\b', text))
    return cjk_chars + words


def is_text_pdf(path: Path) -> bool:
    """Проверка, является ли PDF текстовым (не сканом)"""
    try:
        import subprocess
        result = subprocess.run(
            ['pdftotext', str(path), '-'],
            capture_output=True,
            timeout=30
        )
        # Если извлечено достаточно текста, это не скан
        return len(result.stdout) > 500
    except Exception:
        return False


def get_file_info(path: Path) -> dict:
    """Получение информации о файле"""
    stat = path.stat()
    return {
        "name": path.name,
        "extension": path.suffix.lower(),
        "size": stat.st_size,
        "size_formatted": format_file_size(stat.st_size),
        "modified": datetime.fromtimestamp(stat.st_mtime),
        "modified_formatted": format_datetime(datetime.fromtimestamp(stat.st_mtime)),
        "is_text_pdf": path.suffix.lower() == '.pdf' and is_text_pdf(path) if path.suffix.lower() == '.pdf' else None,
    }


def ensure_dir(path: Path) -> bool:
    """Создание директории если не существует"""
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Ошибка создания директории {path}: {e}")
        return False


def copy_file(src: Path, dst: Path) -> bool:
    """Копирование файла"""
    try:
        import shutil
        shutil.copy2(src, dst)
        return True
    except Exception as e:
        logger.error(f"Ошибка копирования {src} -> {dst}: {e}")
        return False


def move_file(src: Path, dst: Path) -> bool:
    """Перемещение файла"""
    try:
        import shutil
        shutil.move(str(src), str(dst))
        return True
    except Exception as e:
        logger.error(f"Ошибка перемещения {src} -> {dst}: {e}")
        return False


def delete_file(path: Path) -> bool:
    """Удаление файла"""
    try:
        path.unlink()
        return True
    except Exception as e:
        logger.error(f"Ошибка удаления {path}: {e}")
        return False


def read_file_safe(path: Path, encoding: str = 'utf-8') -> Optional[str]:
    """Безопасное чтение файла"""
    try:
        return path.read_text(encoding=encoding)
    except UnicodeDecodeError:
        # Пробуем другие кодировки
        for enc in ['cp1251', 'latin-1', 'utf-16']:
            try:
                return path.read_text(encoding=enc)
            except Exception:
                continue
        logger.error(f"Не удалось прочитать файл {path}")
        return None
    except Exception as e:
        logger.error(f"Ошибка чтения файла {path}: {e}")
        return None


def write_file_safe(path: Path, content: str, encoding: str = 'utf-8') -> bool:
    """Безопасная запись файла"""
    try:
        path.write_text(content, encoding=encoding)
        return True
    except Exception as e:
        logger.error(f"Ошибка записи файла {path}: {e}")
        return False
