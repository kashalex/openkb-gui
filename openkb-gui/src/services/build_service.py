"""
Build Service - Управление компиляцией базы знаний через OpenKB
Запуск openkb build через subprocess с thread-safe логированием
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


class BuildState(Enum):
    """Состояния build процесса"""
    IDLE = "idle"
    BUILDING = "building"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class BuildResult:
    """Результат build процесса"""
    success: bool
    exit_code: int
    output: str
    error: str
    duration_seconds: float


class BuildService:
    """Сервис управления build процессом OpenKB"""
    
    def __init__(self, workspace_path: str):
        """
        Инициализация build сервиса
        
        Args:
            workspace_path: Путь к workspace директории
        """
        self.workspace_path = Path(workspace_path).resolve()
        self.state = BuildState.IDLE
        self.process: Optional[subprocess.Popen] = None
        self.output_queue: queue.Queue = queue.Queue()
        self.build_thread: Optional[threading.Thread] = None
        self._callbacks: list[Callable] = []
        
        # Проверяем наличие openkb
        self._openkb_available = self._check_openkb()
        
        logger.info(f"BuildService инициализирован для: {self.workspace_path}")
    
    def _check_openkb(self) -> bool:
        """Проверка наличия OpenKB"""
        try:
            result = subprocess.run(
                ["openkb", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                logger.info(f"OpenKB найден: {version}")
                self._openkb_version = version
                return True
        except FileNotFoundError:
            logger.warning("OpenKB не найден. Установите: pip install openkb")
            self._openkb_version = None
            return False
        except subprocess.TimeoutExpired:
            logger.warning("Таймаут проверки OpenKB")
            self._openkb_version = None
            return False
        except Exception as e:
            logger.error(f"Ошибка проверки OpenKB: {e}")
            self._openkb_version = None
            return False
        self._openkb_version = None
        return False
    
    @property
    def openkb_available(self) -> bool:
        """Проверка доступности OpenKB"""
        return self._openkb_available
    
    @property
    def openkb_version(self) -> Optional[str]:
        """Получение версии OpenKB"""
        return self._openkb_version
    
    def add_output_callback(self, callback: Callable[[str], None]):
        """
        Добавление callback для вывода
        
        Args:
            callback: Функция, вызываемая при появлении вывода
        """
        self._callbacks.append(callback)
    
    def _emit_output(self, line: str):
        """Отправка вывода всем callback'ам"""
        for callback in self._callbacks:
            try:
                callback(line)
            except Exception as e:
                logger.error(f"Ошибка в callback: {e}")
    
    def _read_stdout(self, process: subprocess.Popen):
        """
        Чтение stdout процесса в отдельном потоке
        
        Args:
            process: Процесс для чтения
        """
        try:
            for line in iter(process.stdout.readline, ''):
                if line:
                    self.output_queue.put(('stdout', line))
                    self._emit_output(line.rstrip('\n'))
        except Exception as e:
            logger.error(f"Ошибка чтения stdout: {e}")
    
    def _read_stderr(self, process: subprocess.Popen):
        """
        Чтение stderr процесса в отдельном потоке
        
        Args:
            process: Процесс для чтения
        """
        try:
            for line in iter(process.stderr.readline, ''):
                if line:
                    self.output_queue.put(('stderr', line))
                    self._emit_output(f"[ERROR] {line.rstrip('\n')}")
        except Exception as e:
            logger.error(f"Ошибка чтения stderr: {e}")
    
    def build(self, 
              on_complete: Optional[Callable[[BuildResult], None]] = None,
              incremental: bool = False) -> bool:
        """
        Запуск build процесса
        
        Args:
            on_complete: Callback при завершении
            incremental: Инкрементальная сборка (только изменённые файлы)
        
        Returns:
            bool: True если процесс запущен успешно
        """
        if self.state == BuildState.BUILDING:
            logger.warning("Build уже выполняется")
            return False
        
        if not self._openkb_available:
            logger.error("OpenKB недоступен. Установите: pip install openkb")
            self.state = BuildState.BUILDING
            
            # Запускаем в отдельном потоке для имитации процесса
            def run_mock_build():
                import time
                start_time = time.time()
                
                self._emit_output("="*50)
                self._emit_output("MOCK BUILD MODE (OpenKB not installed)")
                self._emit_output("="*50)
                self._emit_output("")
                self._emit_output("To install OpenKB, run:")
                self._emit_output("  pip install openkb")
                self._emit_output("")
                self._emit_output("Simulating build process for demonstration...")
                self._emit_output("")
                
                # Имитация обработки документов
                doc_count = self.count_documents()
                self._emit_output(f"Found {doc_count} documents in raw/")
                
                if doc_count > 0:
                    for i in range(1, doc_count + 1):
                        time.sleep(0.3)  # Имитация обработки
                        self._emit_output(f"  Processing document {i}/{doc_count}...")
                else:
                    self._emit_output("  No documents found in raw/ directory")
                    self._emit_output("  Add .pdf, .docx, .txt or .md files to raw/ folder")
                
                self._emit_output("")
                self._emit_output("Compiling wiki pages...")
                time.sleep(0.5)
                self._emit_output("  Generating concepts...")
                time.sleep(0.3)
                self._emit_output("  Creating summaries...")
                time.sleep(0.3)
                self._emit_output("  Building wikilinks...")
                time.sleep(0.2)
                
                duration = time.time() - start_time
                
                self._emit_output("")
                self._emit_output("="*50)
                self._emit_output("MOCK BUILD COMPLETE")
                self._emit_output(f"Duration: {duration:.1f}s")
                self._emit_output("="*50)
                self._emit_output("")
                self._emit_output("NOTE: This was a simulation.")
                self._emit_output("Install openkb package for real functionality:")
                self._emit_output("  pip install openkb")
                
                self.state = BuildState.SUCCESS
                
                if on_complete:
                    on_complete(BuildResult(
                        success=True,
                        exit_code=0,
                        output="Mock build completed (OpenKB not installed)",
                        error="",
                        duration_seconds=duration
                    ))
            
            self.build_thread = threading.Thread(target=run_mock_build, daemon=True)
            self.build_thread.start()
            return True
        
        if not self.workspace_path.exists():
            logger.error(f"Workspace не существует: {self.workspace_path}")
            self._emit_output(f"ERROR: Workspace not found: {self.workspace_path}")
            if on_complete:
                on_complete(BuildResult(
                    success=False,
                    exit_code=-1,
                    output="",
                    error=f"Workspace not found: {self.workspace_path}",
                    duration_seconds=0
                ))
            return True
        
        # Подготовка команды
        cmd = ["openkb", "build", str(self.workspace_path)]
        
        if incremental:
            cmd.append("--incremental")
        
        logger.info(f"Запуск build: {' '.join(cmd)}")
        self.state = BuildState.BUILDING
        
        # Запуск в отдельном потоке
        def run_build():
            import time
            start_time = time.time()
            output_lines = []
            error_lines = []
            
            try:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,  # Line buffered
                    cwd=str(self.workspace_path),
                    env={**os.environ, "PYTHONUNBUFFERED": "1"}
                )
                
                # Потоки для чтения stdout/stderr
                stdout_thread = threading.Thread(
                    target=self._read_stdout, 
                    args=(self.process,),
                    daemon=True
                )
                stderr_thread = threading.Thread(
                    target=self._read_stderr, 
                    args=(self.process,),
                    daemon=True
                )
                stdout_thread.start()
                stderr_thread.start()
                
                # Ожидание завершения
                self.process.wait()
                stdout_thread.join(timeout=5)
                stderr_thread.join(timeout=5)
                
                # Сбор вывода из очереди
                while not self.output_queue.empty():
                    stream, line = self.output_queue.get_nowait()
                    if stream == 'stdout':
                        output_lines.append(line)
                    else:
                        error_lines.append(line)
                
                duration = time.time() - start_time
                
                result = BuildResult(
                    success=self.process.returncode == 0,
                    exit_code=self.process.returncode,
                    output=''.join(output_lines),
                    error=''.join(error_lines),
                    duration_seconds=duration
                )
                
                if result.success:
                    self.state = BuildState.SUCCESS
                    logger.info(f"Build завершён успешно за {duration:.1f}с")
                else:
                    self.state = BuildState.FAILED
                    logger.error(f"Build failed с кодом {result.exit_code}")
                
                if on_complete:
                    on_complete(result)
                
            except Exception as e:
                self.state = BuildState.FAILED
                logger.error(f"Ошибка build: {e}")
                
                if on_complete:
                    on_complete(BuildResult(
                        success=False,
                        exit_code=-1,
                        output='',
                        error=str(e),
                        duration_seconds=time.time() - start_time
                    ))
            finally:
                self.process = None
        
        self.build_thread = threading.Thread(target=run_build, daemon=True)
        self.build_thread.start()
        
        return True
    
    def stop(self) -> bool:
        """
        Остановка build процесса
        
        Returns:
            bool: True если процесс остановлен
        """
        if self.process and self.state == BuildState.BUILDING:
            logger.info("Остановка build процесса")
            try:
                self.process.terminate()
                # Ждём graceful shutdown
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    logger.warning("Process killed (timeout)")
                
                self.state = BuildState.IDLE
                return True
            except Exception as e:
                logger.error(f"Ошибка остановки процесса: {e}")
                return False
        
        return False
    
    def get_state(self) -> BuildState:
        """Получение текущего состояния"""
        return self.state
    
    def is_building(self) -> bool:
        """Проверка, выполняется ли build"""
        return self.state == BuildState.BUILDING
    
    def get_output_queue(self) -> queue.Queue:
        """Получение очереди вывода"""
        return self.output_queue
    
    def get_wiki_path(self) -> Path:
        """Получение пути к wiki директории"""
        return self.workspace_path / "wiki"
    
    def get_raw_path(self) -> Path:
        """Получение пути к raw директории"""
        return self.workspace_path / "raw"
    
    def get_concepts_path(self) -> Path:
        """Получение пути к concepts директории"""
        return self.get_wiki_path() / "concepts"
    
    def get_summaries_path(self) -> Path:
        """Получение пути к summaries директории"""
        return self.get_wiki_path() / "summaries"
    
    def get_agents_path(self) -> Path:
        """Получение пути к AGENTS.md"""
        return self.get_wiki_path() / "AGENTS.md"
    
    def count_documents(self) -> int:
        """Подсчёт документов в raw/"""
        raw_path = self.get_raw_path()
        if not raw_path.exists():
            return 0
        
        extensions = {'.pdf', '.docx', '.txt', '.md'}
        count = 0
        for f in raw_path.iterdir():
            if f.is_file() and f.suffix.lower() in extensions:
                count += 1
        return count
    
    def count_wiki_pages(self) -> int:
        """Подсчёт wiki страниц"""
        wiki_path = self.get_wiki_path()
        if not wiki_path.exists():
            return 0
        
        count = 0
        for f in wiki_path.rglob("*.md"):
            if f.is_file():
                count += 1
        return count
