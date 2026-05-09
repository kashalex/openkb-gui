"""
Watch Service - Автоматическое отслеживание изменений в документах
Запуск openkb watch и обработка событий файловой системы
"""

import subprocess
import threading
import queue
import os
import logging
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Lazy import for watchdog
_watchdog_available = False


def _init_watchdog():
    """Lazy initialization of watchdog"""
    global _watchdog_available
    if _watchdog_available:
        return True
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler, FileSystemEvent
        _watchdog_available = True
        return True
    except ImportError:
        logger.warning("watchdog not installed. Watch functionality will be limited.")
        return False


class WatchState(Enum):
    """Состояния watch режима"""
    STOPPED = "stopped"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class WatchEvent:
    """Событие изменения файла"""
    event_type: str  # created, modified, deleted, moved
    src_path: str
    is_directory: bool


class _EventHandler:
    """Internal event handler for watchdog"""
    
    def __init__(self, callback: Callable[[str, str, bool], None]):
        self._callback = callback
    
    def on_created(self, event):
        if not event.is_directory:
            self._callback('created', event.src_path, event.is_directory)
    
    def on_modified(self, event):
        if not event.is_directory:
            self._callback('modified', event.src_path, event.is_directory)
    
    def on_deleted(self, event):
        if not event.is_directory:
            self._callback('deleted', event.src_path, event.is_directory)
    
    def on_moved(self, event):
        if not event.is_directory:
            self._callback('moved', event.src_path, event.is_directory)


class WatchService:
    """Сервис отслеживания изменений"""
    
    def __init__(self, 
                 workspace_path: str,
                 on_change: Optional[Callable[[WatchEvent], None]] = None,
                 debounce_seconds: float = 2.0):
        """
        Инициализация watch сервиса
        
        Args:
            workspace_path: Путь к workspace
            on_change: Callback при изменении файлов
            debounce_seconds: Задержка перед обработкой (анти-дребезг)
        """
        self.workspace_path = Path(workspace_path).resolve()
        self.raw_path = self.workspace_path / "raw"
        self.state = WatchState.STOPPED
        self.on_change = on_change
        self.debounce_seconds = debounce_seconds
        
        # Watchdog observer
        self.observer = None
        self._handler = None
        
        # Debounce timer
        self._debounce_timer: Optional[threading.Timer] = None
        self._pending_events: list[WatchEvent] = []
        
        # OpenKB watch process
        self._openkb_process: Optional[subprocess.Popen] = None
        self._output_queue: queue.Queue = queue.Queue()
        
        logger.info(f"WatchService инициализирован для: {self.workspace_path}")
    
    def start(self) -> bool:
        """
        Запуск отслеживания
        
        Returns:
            bool: True если успешно запущен
        """
        if self.state == WatchState.RUNNING:
            logger.warning("Watch уже запущен")
            return False
        
        if not self.raw_path.exists():
            logger.error(f"Raw директория не существует: {self.raw_path}")
            return False
        
        try:
            # Инициализируем watchdog
            if _init_watchdog():
                from watchdog.observers import Observer
                
                # Создаём handler
                self._handler = _EventHandler(self._handle_file_event)
                
                # Запуск watchdog observer
                self.observer = Observer()
                self.observer.schedule(self._handler, str(self.raw_path), recursive=True)
                self.observer.start()
            else:
                logger.warning("Watchdog недоступен, используется только openkb watch")
            
            # Запуск openkb watch в отдельном потоке
            self._start_openkb_watch()
            
            self.state = WatchState.RUNNING
            logger.info("Watch режим запущен")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка запуска watch: {e}")
            self.state = WatchState.ERROR
            return False
    
    def stop(self) -> bool:
        """
        Остановка отслеживания
        
        Returns:
            bool: True если успешно остановлен
        """
        if self.state != WatchState.RUNNING:
            return False
        
        try:
            # Остановка watchdog
            if self.observer:
                self.observer.stop()
                self.observer.join(timeout=5)
                self.observer = None
            
            # Остановка openkb watch
            self._stop_openkb_watch()
            
            # Отмена debounce timer
            if self._debounce_timer:
                self._debounce_timer.cancel()
                self._debounce_timer = None
            
            self.state = WatchState.STOPPED
            logger.info("Watch режим остановлен")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка остановки watch: {e}")
            return False
    
    def _start_openkb_watch(self):
        """Запуск openkb watch процесса"""
        try:
            cmd = ["openkb", "watch", str(self.workspace_path)]
            
            self._openkb_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=str(self.workspace_path),
                env={**os.environ, "PYTHONUNBUFFERED": "1"}
            )
            
            # Поток для чтения вывода
            def read_output():
                for line in iter(self._openkb_process.stdout.readline, ''):
                    if line:
                        self._output_queue.put(line)
                        logger.debug(f"OpenKB watch: {line.strip()}")
            
            thread = threading.Thread(target=read_output, daemon=True)
            thread.start()
            
            logger.info("OpenKB watch процесс запущен")
            
        except FileNotFoundError:
            logger.warning("OpenKB не найден, используется только watchdog")
        except Exception as e:
            logger.error(f"Ошибка запуска openkb watch: {e}")
    
    def _stop_openkb_watch(self):
        """Остановка openkb watch процесса"""
        if self._openkb_process:
            try:
                self._openkb_process.terminate()
                self._openkb_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._openkb_process.kill()
            except Exception as e:
                logger.error(f"Ошибка остановки openkb watch: {e}")
            finally:
                self._openkb_process = None
    
    def _handle_file_event(self, event_type: str, src_path: str, is_directory: bool):
        """Обработка события от watchdog"""
        # Фильтруем только поддерживаемые форматы
        extensions = {'.pdf', '.docx', '.txt', '.md'}
        path = Path(src_path)
        
        if not is_directory and path.suffix.lower() not in extensions:
            return
        
        self._add_event(event_type, src_path, is_directory)
    
    def _debounce_callback(self):
        """Callback для debounce - обработка накопленных событий"""
        if not self._pending_events:
            return
        
        # Берём все накопленные события
        events = self._pending_events.copy()
        self._pending_events.clear()
        
        logger.info(f"Обработка {len(events)} событий изменения")
        
        # Вызываем callback
        if self.on_change:
            for event in events:
                try:
                    self.on_change(event)
                except Exception as e:
                    logger.error(f"Ошибка в callback: {e}")
    
    def _add_event(self, event_type: str, src_path: str, is_directory: bool):
        """Добавление события с debounce"""
        # Добавляем событие
        self._pending_events.append(WatchEvent(
            event_type=event_type,
            src_path=src_path,
            is_directory=is_directory
        ))
        
        # Сбрасываем debounce timer
        if self._debounce_timer:
            self._debounce_timer.cancel()
        
        self._debounce_timer = threading.Timer(
            self.debounce_seconds,
            self._debounce_callback
        )
        self._debounce_timer.start()
    
    def is_running(self) -> bool:
        """Проверка, запущен ли watch"""
        return self.state == WatchState.RUNNING
    
    def get_state(self) -> WatchState:
        """Получение текущего состояния"""
        return self.state
