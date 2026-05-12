"""
Build Service - Управление компиляцией базы знаний через OpenKB
Запуск openkb build через subprocess с timeout
Поддержка всех провайдеров через ConfigService
Валидация путей и обработка ошибок
"""

import subprocess
import threading
import queue
import os
import sys
import json
import logging
import re
import importlib.metadata
import importlib.util
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


# Timeout для subprocess вызовов (секунды)
BUILD_TIMEOUT = 600  # 10 минут максимум


class BuildState(Enum):
    """Состояния build процесса"""
    IDLE = "idle"
    BUILDING = "building"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class BuildResult:
    """Результат build процесса"""
    success: bool
    exit_code: int
    output: str
    error: str
    duration_seconds: float
    timeout: bool = False


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
        
        # Инициализируем ConfigService для получения актуальных настроек
        from services.config_service import ConfigService
        self._config_service = ConfigService.get_instance()
        
        # Проверяем наличие openkb
        self._openkb_available = self._check_openkb()
        
        logger.info(f"BuildService инициализирован для: {self.workspace_path}")
    
    def _get_openkb_installed_version(self) -> str:
        """Best-effort package version for module-only OpenKB installs."""
        try:
            return importlib.metadata.version("openkb")
        except importlib.metadata.PackageNotFoundError:
            return "installed (version unknown)"

    def _check_openkb(self) -> bool:
        """Проверка наличия OpenKB теми же способами, что и startup check."""
        self._openkb_version = None
        self._use_python_m = False

        # Способ 1: module in the current interpreter. This must be first for
        # Windows venvs where `openkb`/`python -m openkb --version` can hang or
        # fail while the package is importable and runnable for normal commands.
        module_spec = importlib.util.find_spec("openkb")
        if module_spec is not None:
            self._openkb_version = self._get_openkb_installed_version()
            if importlib.util.find_spec("openkb.__main__") is not None:
                self._use_python_m = True
                logger.info(
                    "OpenKB найден (module): %s; build will use %s",
                    self._openkb_version,
                    f'"{sys.executable}" -m openkb'
                )
                return True
            logger.debug("OpenKB module found, but openkb.__main__ is missing; trying CLI next")

        # Способ 2: Прямой вызов openkb. Может быть доступен даже если модуль
        # не установлен в текущий Python, например через отдельный CLI install.
        try:
            result = subprocess.run(
                ["openkb", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip() or result.stderr.strip()
                logger.info(f"OpenKB найден (CLI): {version}")
                self._openkb_version = version
                return True
            logger.debug("OpenKB CLI --version failed: %s", result.stderr.strip() or result.stdout.strip())
        except FileNotFoundError:
            logger.debug("OpenKB CLI executable not found in PATH")
        except subprocess.TimeoutExpired:
            logger.warning("Таймаут проверки OpenKB (CLI)")
        except Exception as e:
            logger.debug(f"OpenKB CLI check failed: {e}")

        # Способ 3: python -m openkb --version as a final explicit command
        # probe. If this succeeds, build can safely use python -m openkb add.
        try:
            result = subprocess.run(
                [sys.executable, "-m", "openkb", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip() or result.stderr.strip()
                logger.info(f"OpenKB найден (python -m): {version}")
                self._openkb_version = version
                self._use_python_m = True
                return True
            logger.debug("python -m openkb --version failed: %s", result.stderr.strip() or result.stdout.strip())
        except FileNotFoundError:
            pass
        except subprocess.TimeoutExpired:
            logger.warning("Таймаут проверки OpenKB (python -m)")
        except Exception as e:
            logger.debug(f"OpenKB python -m check failed: {e}")

        if module_spec is not None:
            logger.warning(
                "OpenKB module is installed for this interpreter, but neither `openkb` CLI "
                "nor `python -m openkb` is runnable. Reinstall with: %s -m pip install --force-reinstall openkb",
                sys.executable
            )
        else:
            logger.warning("OpenKB не найден. Установите: %s -m pip install openkb", sys.executable)
        return False

    @property
    def openkb_available(self) -> bool:
        """Проверка доступности OpenKB"""
        return self._openkb_available
    
    @property
    def openkb_version(self) -> Optional[str]:
        """Получение версии OpenKB"""
        return self._openkb_version
    
    def is_initialized(self) -> bool:
        """Проверка, инициализирована ли база знаний"""
        openkb_config = self.workspace_path / ".openkb" / "config.yaml"
        wiki_path = self.get_wiki_path()
        return openkb_config.exists() or wiki_path.exists()
    
    def _validate_workspace_path(self) -> tuple:
        """
        Валидация пути к workspace
        
        Returns:
            tuple: (валиден, сообщение)
        """
        path_str = str(self.workspace_path)
        
        # Проверка на опасные символы
        dangerous_chars = ['<', '>', '|', '*', '?', '"']
        for char in dangerous_chars:
            if char in path_str:
                return False, f"Путь содержит недопустимый символ: {char}"
        
        # Проверка длины пути (Windows ограничение ~260 символов)
        if len(path_str) > 250:
            return False, "Путь слишком длинный (максимум 250 символов)"
        
        return True, "OK"
    
    def _setup_api(self) -> bool:
        """Настройка API для LLM вызовов (все провайдеры)"""
        config = self._config_service.config
        
        # Получаем текущую модель и провайдера
        model = config.llm_model
        provider = config.get_current_provider()
        api_key = config.get_api_key_for_provider(provider)
        
        if not api_key:
            logger.warning(f"API ключ не настроен для провайдера: {provider}")
            return False
        
        # Устанавливаем переменные окружения для LiteLLM
        if provider == "zai":
            os.environ["ZAI_API_KEY"] = api_key
        elif provider == "openrouter":
            os.environ["OPENROUTER_API_KEY"] = api_key
            os.environ["OPENROUTER_API_BASE"] = "https://openrouter.ai/api/v1"
        
        # Также устанавливаем общий LLM_API_KEY для совместимости
        os.environ["LLM_API_KEY"] = api_key
        os.environ["LLM_MODEL"] = model
        
        logger.info(f"API настроен: провайдер={provider}, модель={model}")
        self._emit_output(f"Provider: {provider}, Model: {model}")
        return True
    
    def _get_current_model(self) -> str:
        """Получение текущей модели из ConfigService"""
        config = self._config_service.config
        return config.llm_model or "zai/glm-4.5-flash"
    
    def _update_model_config(self) -> bool:
        """
        Обновление конфигурации модели в .openkb/config.yaml
        
        Returns:
            bool: True если успешно
        """
        try:
            current_model = self._get_current_model()
            config_path = self.workspace_path / ".openkb" / "config.yaml"
            
            if config_path.exists():
                # Читаем существующий конфиг
                with open(config_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Заменяем модель
                new_content = re.sub(
                    r'^model:.*$',
                    f'model: {current_model}',
                    content,
                    flags=re.MULTILINE
                )
                
                # Если модель не найдена, добавляем её
                if new_content == content and 'model:' not in content:
                    new_content = f'model: {current_model}\n' + content
                
                config_path.write_text(new_content, encoding='utf-8')
                self._emit_output(f"Configured model: {current_model}")
            else:
                # Создаём новый конфиг
                config_path.parent.mkdir(parents=True, exist_ok=True)
                config_content = f"""model: {current_model}
language: ru
pageindex_threshold: 20
"""
                config_path.write_text(config_content, encoding="utf-8")
                self._emit_output(f"Created config with model: {current_model}")
            
            logger.info(f"Обновлена модель в конфиге: {current_model}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обновления конфига модели: {e}")
            return False
    
    def init_knowledge_base(self) -> bool:
        """
        Инициализация базы знаний (openkb init)
        
        Returns:
            bool: True если успешно
        """
        if not self._openkb_available:
            logger.error("OpenKB недоступен")
            return False
        
        try:
            # Создаём структуру директорий
            self._ensure_structure()
            
            # Используем модель из ConfigService (поддержка всех провайдеров)
            current_model = self._get_current_model()
            
            # Создаём или обновляем конфигурационный файл
            config_path = self.workspace_path / ".openkb" / "config.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            config_content = f"""model: {current_model}
language: ru
pageindex_threshold: 20
"""
            config_path.write_text(config_content, encoding="utf-8")
            self._emit_output(f"Configured model: {current_model}")
            
            # Создаём hashes.json
            hashes_path = self.workspace_path / ".openkb" / "hashes.json"
            if not hashes_path.exists():
                hashes_path.write_text("{}", encoding="utf-8")
            
            logger.info(f"База знаний инициализирована с моделью: {current_model}")
            return True
                
        except Exception as e:
            self._emit_output(f"Init error: {e}")
            logger.error(f"Ошибка инициализации: {e}")
            return False
    
    def _ensure_structure(self):
        """Создание структуры директорий workspace"""
        dirs = [
            self.workspace_path / "raw",
            self.workspace_path / "wiki" / "concepts",
            self.workspace_path / "wiki" / "summaries",
            self.workspace_path / "wiki" / "sources",
            self.workspace_path / "wiki" / "reports",
            self.workspace_path / "sessions",
            self.workspace_path / "logs",
            self.workspace_path / ".openkb",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
    
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
        """Чтение stdout процесса в отдельном потоке"""
        try:
            for line in iter(process.stdout.readline, ''):
                if line:
                    self.output_queue.put(('stdout', line))
                    self._emit_output(line.rstrip('\n'))
        except Exception as e:
            logger.error(f"Ошибка чтения stdout: {e}")
    
    def _read_stderr(self, process: subprocess.Popen):
        """Чтение stderr процесса в отдельном потоке"""
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
        Запуск build процесса через subprocess с timeout
        
        Args:
            on_complete: Callback при завершении
            incremental: Инкрементальная сборка
        
        Returns:
            bool: True если процесс запущен успешно
        """
        if self.state == BuildState.BUILDING:
            logger.warning("Build уже выполняется")
            return False
        
        # Валидация пути
        is_valid, msg = self._validate_workspace_path()
        if not is_valid:
            self._emit_output(f"ERROR: {msg}")
            return False
        
        if not self._openkb_available:
            logger.error("OpenKB недоступен. Установите: pip install openkb")
            self._emit_output("ERROR: OpenKB is not installed. Real build cannot run.")
            self._emit_output("Install with: pip install openkb")
            self.state = BuildState.FAILED
            if on_complete:
                on_complete(BuildResult(
                    success=False,
                    exit_code=-2,
                    output="",
                    error="OpenKB is not installed; mock builds are disabled for production checks",
                    duration_seconds=0
                ))
            return False
        
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
        
        # Проверяем и создаём структуру
        self._ensure_structure()

        doc_count = self.count_documents()
        if doc_count == 0:
            message = "No supported documents found in raw/ (including nested folders)."
            self._emit_output(f"ERROR: {message}")
            self.state = BuildState.FAILED
            if on_complete:
                on_complete(BuildResult(
                    success=False,
                    exit_code=-3,
                    output="",
                    error=message,
                    duration_seconds=0
                ))
            return False
        self._emit_output(f"Found {doc_count} supported document(s) in raw/.")
        
        # Всегда обновляем конфигурацию модели (для поддержки смены провайдера)
        self._update_model_config()
        
        # Проверяем инициализацию базы знаний
        if not self.is_initialized():
            self._emit_output("Knowledge base not initialized.")
            self._emit_output("Creating configuration...")
            
            if not self.init_knowledge_base():
                self._emit_output("ERROR: Failed to initialize knowledge base")
                if on_complete:
                    on_complete(BuildResult(
                        success=False,
                        exit_code=-1,
                        output="",
                        error="Knowledge base initialization failed",
                        duration_seconds=0
                    ))
                return True
        
        # Настраиваем API для текущего провайдера
        current_model = self._get_current_model()
        config = self._config_service.config
        provider = config.get_current_provider()
        
        self._emit_output(f"Configuring API for {provider}...")
        if self._setup_api():
            self._emit_output(f"API configured: {current_model}")
        else:
            self._emit_output(f"Warning: Could not configure API for {provider}")
        
        self.state = BuildState.BUILDING
        
        # Всегда используем subprocess для изоляции
        return self._run_build_subprocess(on_complete, incremental)
    
    def _run_mock_build(self, on_complete: Optional[Callable]) -> bool:
        """Запуск mock build когда OpenKB не установлен"""
        def run_mock():
            import time
            start_time = time.time()
            
            self._emit_output("=" * 50)
            self._emit_output("MOCK BUILD MODE (OpenKB not installed)")
            self._emit_output("=" * 50)
            self._emit_output("")
            self._emit_output("To install OpenKB, run:")
            self._emit_output("  pip install openkb")
            self._emit_output("")
            self._emit_output("Simulating build process...")
            
            doc_count = self.count_documents()
            self._emit_output(f"Found {doc_count} documents in raw/")
            
            if doc_count > 0:
                for i in range(1, doc_count + 1):
                    time.sleep(0.3)
                    self._emit_output(f"  Would process document {i}/{doc_count}...")
            else:
                self._emit_output("  No documents found in raw/")
                self._emit_output("  Add .pdf, .docx, .txt or .md files to raw/")
            
            duration = time.time() - start_time
            
            self._emit_output("")
            self._emit_output("=" * 50)
            self._emit_output("MOCK BUILD STOPPED: this is not a successful production build")
            self._emit_output(f"Duration: {duration:.1f}s")
            self._emit_output("=" * 50)
            
            self.state = BuildState.FAILED
            
            if on_complete:
                on_complete(BuildResult(
                    success=False,
                    exit_code=-2,
                    output="Mock build did not create a knowledge base",
                    error="OpenKB is not installed; install OpenKB to run a real build",
                    duration_seconds=duration
                ))
        
        self.build_thread = threading.Thread(target=run_mock, daemon=True)
        self.build_thread.start()
        return True
    
    def _run_build_subprocess(self, on_complete: Optional[Callable], incremental: bool) -> bool:
        """Запуск build через subprocess с timeout"""
        raw_path = self.get_raw_path()
        if self._use_python_m:
            cmd = [sys.executable, "-m", "openkb", "add", str(raw_path)]
        else:
            cmd = ["openkb", "add", str(raw_path)]
        
        if incremental:
            cmd.append("--incremental")
        
        logger.info(f"Запуск build: {' '.join(cmd)}")
        
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
                
                # Ожидание завершения с timeout
                try:
                    self.process.wait(timeout=BUILD_TIMEOUT)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self._emit_output(f"ERROR: Build timeout after {BUILD_TIMEOUT}s")
                    self.state = BuildState.TIMEOUT
                    
                    if on_complete:
                        on_complete(BuildResult(
                            success=False,
                            exit_code=-1,
                            output="",
                            error=f"Timeout after {BUILD_TIMEOUT}s",
                            duration_seconds=BUILD_TIMEOUT,
                            timeout=True
                        ))
                    return
                
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

                if result.success and self.count_generated_wiki_pages() == 0:
                    result.success = False
                    result.exit_code = -4
                    result.error = (result.error + "\n" if result.error else "") + (
                        "Build finished with exit code 0 but no generated wiki pages were found"
                    )
                    self._emit_output("ERROR: Build produced no generated wiki pages")
                
                if result.success:
                    self.state = BuildState.SUCCESS
                    page_count = self.count_generated_wiki_pages()
                    self._emit_output(f"Build completed successfully in {duration:.1f}s")
                    self._emit_output(f"Generated wiki pages: {page_count}")
                    logger.info(f"Build завершён успешно за {duration:.1f}с; pages={page_count}")
                else:
                    self.state = BuildState.FAILED
                    self._emit_output(f"Build failed with exit code {result.exit_code}")
                    logger.error(f"Build failed с кодом {result.exit_code}: {result.error}")
                
                if on_complete:
                    on_complete(result)
                
            except Exception as e:
                self.state = BuildState.FAILED
                logger.error(f"Ошибка build: {e}")
                self._emit_output(f"ERROR: {e}")
                
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
        
        extensions = {'.pdf', '.docx', '.txt', '.md', '.markdown'}
        count = 0
        for f in raw_path.rglob("*"):
            if f.is_file() and f.suffix.lower() in extensions:
                count += 1
        return count

    def count_generated_wiki_pages(self) -> int:
        """Подсчёт сгенерированных страниц wiki, исключая служебный AGENTS.md."""
        wiki_path = self.get_wiki_path()
        if not wiki_path.exists():
            return 0
        count = 0
        for f in wiki_path.rglob("*.md"):
            if f.is_file() and f.name != "AGENTS.md":
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
