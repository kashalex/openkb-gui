"""
Main Window - Главное окно приложения с вкладками
Интеграция со всеми сервисами
"""

import customtkinter as ctk
from typing import Optional
from pathlib import Path
import logging
import threading
import queue

from services.config_service import ConfigService
from services.build_service import BuildService, BuildState
from services.watch_service import WatchService
from services.wiki_service import WikiService
from services.chat_service import ChatService
from services.lint_service import LintService
from services.session_service import SessionService

logger = logging.getLogger(__name__)


class MainWindow(ctk.CTk):
    """Главное окно приложения OpenKB GUI"""
    
    def __init__(self):
        super().__init__()
        
        # Конфигурация окна
        self.title("OpenKB GUI - Система управления знаниями")
        self.geometry("1400x900")
        self.minsize(1200, 700)
        
        # Настройка сетки
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Переменные состояния
        self.current_state = "idle"
        
        # Очередь для thread-safe вывода
        self._output_queue = queue.Queue()
        self._poll_output_queue()
        
        # Загружаем конфигурацию
        self.config_service = ConfigService.get_instance()
        self.config = self.config_service.load_config()
        
        # Инициализируем сервисы (пока None, создадим при необходимости)
        self._build_service: Optional[BuildService] = None
        self._watch_service: Optional[WatchService] = None
        self._wiki_service: Optional[WikiService] = None
        self._chat_service: Optional[ChatService] = None
        self._lint_service: Optional[LintService] = None
        self._session_service: Optional[SessionService] = None
        
        # Создаём UI
        self._create_menu_bar()
        self._create_main_container()
        
        # Загружаем настройки в UI
        self._load_settings_to_ui()
        
        # Обработчик закрытия окна
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        logger.info("MainWindow инициализирован")
    
    def _get_build_service(self) -> BuildService:
        """Получение/создание BuildService"""
        if self._build_service is None:
            workspace = self.config_service.get_workspace_path()
            self._build_service = BuildService(str(workspace))
            # Добавляем callback для вывода
            self._build_service.add_output_callback(self._on_build_output)
        return self._build_service
    
    def _get_watch_service(self) -> WatchService:
        """Получение/создание WatchService"""
        if self._watch_service is None:
            workspace = self.config_service.get_workspace_path()
            self._watch_service = WatchService(
                str(workspace),
                on_change=self._on_watch_change
            )
        return self._watch_service
    
    def _get_wiki_service(self) -> WikiService:
        """Получение/создание WikiService"""
        if self._wiki_service is None:
            workspace = self.config_service.get_workspace_path()
            self._wiki_service = WikiService(str(workspace / "wiki"))
        return self._wiki_service
    
    def _get_lint_service(self) -> LintService:
        """Получение/создание LintService"""
        if self._lint_service is None:
            workspace = self.config_service.get_workspace_path()
            self._lint_service = LintService(str(workspace))
        return self._lint_service
    
    def _get_session_service(self) -> SessionService:
        """Получение/создание SessionService"""
        if self._session_service is None:
            workspace = self.config_service.get_workspace_path()
            self._session_service = SessionService(str(workspace / "sessions"))
        return self._session_service
    
    def _create_menu_bar(self):
        """Создание меню бара"""
        self.header_frame = ctk.CTkFrame(self, height=50)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        self.header_frame.grid_columnconfigure(1, weight=1)
        
        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="OpenKB GUI",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.status_var = ctk.StringVar(value="Готов к работе")
        self.status_label = ctk.CTkLabel(
            self.header_frame,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.status_label.grid(row=0, column=1, padx=10, pady=10, sticky="e")
        
        self.state_indicator = ctk.CTkLabel(
            self.header_frame,
            text="●",
            font=ctk.CTkFont(size=16),
            text_color="green"
        )
        self.state_indicator.grid(row=0, column=2, padx=10, pady=10)
    
    def _create_main_container(self):
        """Создание основного контейнера с вкладками"""
        self.main_container = ctk.CTkFrame(self)
        self.main_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)
        
        self.tabview = ctk.CTkTabview(self.main_container, width=1380, height=850)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        self._create_settings_tab()
        self._create_build_tab()
        self._create_wiki_tab()
        self._create_concepts_tab()
        self._create_chat_tab()
        self._create_health_tab()
        self._create_agents_tab()
    
    def _create_settings_tab(self):
        """Создание вкладки Settings"""
        self.tab_settings = self.tabview.add("Settings")
        self.tab_settings.grid_columnconfigure(0, weight=1)
        self.tab_settings.grid_rowconfigure(0, weight=1)
        
        settings_frame = ctk.CTkScrollableFrame(self.tab_settings)
        settings_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        settings_frame.grid_columnconfigure(1, weight=1)
        
        row = 0
        
        # === LLM Settings ===
        ctk.CTkLabel(settings_frame, text="LLM Configuration", 
                     font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))
        row += 1
        
        ctk.CTkLabel(settings_frame, text="API Key:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        self.api_key_entry = ctk.CTkEntry(settings_frame, width=400, show="*")
        self.api_key_entry.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        row += 1
        
        ctk.CTkLabel(settings_frame, text="API Base URL:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        self.base_url_entry = ctk.CTkEntry(settings_frame, width=400)
        self.base_url_entry.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        row += 1
        
        ctk.CTkLabel(settings_frame, text="Model:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        self.model_entry = ctk.CTkEntry(settings_frame, width=400)
        self.model_entry.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        row += 1
        
        ctk.CTkFrame(settings_frame, height=2).grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=15)
        row += 1
        
        # === Workspace Settings ===
        ctk.CTkLabel(settings_frame, text="Workspace Configuration",
                     font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))
        row += 1
        
        ctk.CTkLabel(settings_frame, text="Workspace Path:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        ws_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        ws_frame.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        
        self.workspace_entry = ctk.CTkEntry(ws_frame, width=350)
        self.workspace_entry.grid(row=0, column=0, padx=(0, 5))
        ctk.CTkButton(ws_frame, text="Browse", width=80, command=self._browse_workspace).grid(row=0, column=1)
        row += 1
        
        ctk.CTkFrame(settings_frame, height=2).grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=15)
        row += 1
        
        # === PageIndex Settings ===
        ctk.CTkLabel(settings_frame, text="PageIndex OCR (Optional)",
                     font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))
        row += 1
        
        ctk.CTkLabel(settings_frame, text="PageIndex API Key:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        self.pageindex_entry = ctk.CTkEntry(settings_frame, width=400, show="*")
        self.pageindex_entry.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        row += 1
        
        ctk.CTkFrame(settings_frame, height=2).grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=15)
        row += 1
        
        # === Watch Mode Settings ===
        ctk.CTkLabel(settings_frame, text="Watch Mode Settings",
                     font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))
        row += 1
        
        self.watch_enabled_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(settings_frame, text="Enable Watch Mode",
                        variable=self.watch_enabled_var).grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        row += 1
        
        ctk.CTkLabel(settings_frame, text="Debounce (seconds):").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        self.debounce_entry = ctk.CTkEntry(settings_frame, width=100)
        self.debounce_entry.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        row += 1
        
        ctk.CTkFrame(settings_frame, height=2).grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=15)
        row += 1
        
        ctk.CTkButton(settings_frame, text="Save Settings", width=150,
                      command=self._save_settings).grid(row=row, column=0, columnspan=2, pady=20)
    
    def _create_build_tab(self):
        """Создание вкладки Build"""
        self.tab_build = self.tabview.add("Build")
        self.tab_build.grid_columnconfigure(0, weight=1)
        self.tab_build.grid_rowconfigure(1, weight=1)
        
        control_frame = ctk.CTkFrame(self.tab_build, height=60)
        control_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        control_frame.grid_columnconfigure(3, weight=1)
        
        self.build_btn = ctk.CTkButton(control_frame, text="Build", width=100, command=self._start_build)
        self.build_btn.grid(row=0, column=0, padx=10, pady=10)
        
        self.watch_btn = ctk.CTkButton(control_frame, text="Watch", width=100, command=self._toggle_watch)
        self.watch_btn.grid(row=0, column=1, padx=10, pady=10)
        
        self.stop_btn = ctk.CTkButton(control_frame, text="Stop", width=100, 
                                        state="disabled", command=self._stop_process)
        self.stop_btn.grid(row=0, column=2, padx=10, pady=10)
        
        self.progress_label = ctk.CTkLabel(control_frame, text="Status: Idle", font=ctk.CTkFont(size=12))
        self.progress_label.grid(row=0, column=3, padx=10, pady=10, sticky="e")
        
        log_frame = ctk.CTkFrame(self.tab_build)
        log_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)
        
        self.build_log = ctk.CTkTextbox(log_frame, height=600)
        self.build_log.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.build_log.insert("0.0", "OpenKB Build Log\n")
        self.build_log.insert("end", "="*50 + "\n\n")
        self.build_log.insert("end", "Welcome to OpenKB GUI!\n\n")
        self.build_log.insert("end", "Instructions:\n")
        self.build_log.insert("end", "  1. Add documents to workspace/raw/ folder\n")
        self.build_log.insert("end", "  2. Click 'Build' to compile knowledge base\n")
        self.build_log.insert("end", "  3. Use Chat tab to query your knowledge\n\n")
        self.build_log.insert("end", "Supported formats: .pdf, .docx, .txt, .md\n\n")
    
    def _create_wiki_tab(self):
        """Создание вкладки Wiki Browser"""
        self.tab_wiki = self.tabview.add("Wiki Browser")
        self.tab_wiki.grid_columnconfigure(1, weight=1)
        self.tab_wiki.grid_rowconfigure(0, weight=1)
        
        tree_frame = ctk.CTkFrame(self.tab_wiki, width=300)
        tree_frame.grid(row=0, column=0, sticky="ns", padx=10, pady=10)
        tree_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(tree_frame, text="Wiki Files", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=10, pady=10)
        
        self.wiki_tree = ctk.CTkTextbox(tree_frame, width=280)
        self.wiki_tree.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        preview_frame = ctk.CTkFrame(self.tab_wiki)
        preview_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(preview_frame, text="Markdown Preview", 
                     font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.wiki_preview = ctk.CTkTextbox(preview_frame)
        self.wiki_preview.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
    
    def _create_concepts_tab(self):
        """Создание вкладки Concepts"""
        self.tab_concepts = self.tabview.add("Concepts")
        self.tab_concepts.grid_columnconfigure(0, weight=1)
        self.tab_concepts.grid_rowconfigure(0, weight=1)
        
        concepts_frame = ctk.CTkScrollableFrame(self.tab_concepts)
        concepts_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(concepts_frame, text="Concepts Management",
                     font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, pady=20)
        
        self.concepts_list = ctk.CTkTextbox(concepts_frame, height=600)
        self.concepts_list.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
    
    def _create_chat_tab(self):
        """Создание вкладки Chat"""
        self.tab_chat = self.tabview.add("Chat")
        self.tab_chat.grid_columnconfigure(1, weight=1)
        self.tab_chat.grid_rowconfigure(0, weight=1)
        
        sessions_frame = ctk.CTkFrame(self.tab_chat, width=250)
        sessions_frame.grid(row=0, column=0, sticky="ns", padx=10, pady=10)
        sessions_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(sessions_frame, text="Sessions", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=10, pady=10)
        
        self.session_list = ctk.CTkTextbox(sessions_frame, width=230, height=700)
        self.session_list.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        chat_frame = ctk.CTkFrame(self.tab_chat)
        chat_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        chat_frame.grid_columnconfigure(0, weight=1)
        chat_frame.grid_rowconfigure(0, weight=1)
        
        self.chat_history = ctk.CTkTextbox(chat_frame, height=700)
        self.chat_history.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        input_frame = ctk.CTkFrame(chat_frame)
        input_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        input_frame.grid_columnconfigure(0, weight=1)
        
        self.chat_input = ctk.CTkEntry(input_frame, placeholder_text="Type your question...")
        self.chat_input.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        self.chat_input.bind("<Return>", self._send_chat_message)
        
        ctk.CTkButton(input_frame, text="Send", width=80, 
                      command=self._send_chat_message).grid(row=0, column=1, padx=5, pady=5)
        
        ctk.CTkLabel(chat_frame, text="Sources:", 
                     font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, sticky="w", padx=5, pady=(10, 5))
        
        self.sources_display = ctk.CTkTextbox(chat_frame, height=100)
        self.sources_display.grid(row=3, column=0, sticky="ew", padx=5, pady=5)
    
    def _create_health_tab(self):
        """Создание вкладки Health"""
        self.tab_health = self.tabview.add("Health")
        self.tab_health.grid_columnconfigure(0, weight=1)
        self.tab_health.grid_rowconfigure(1, weight=1)
        
        control_frame = ctk.CTkFrame(self.tab_health, height=60)
        control_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        ctk.CTkButton(control_frame, text="Run Lint", width=100,
                      command=self._run_lint).grid(row=0, column=0, padx=10, pady=10)
        
        ctk.CTkButton(control_frame, text="Refresh", width=100,
                      command=self._refresh_health).grid(row=0, column=1, padx=10, pady=10)
        
        results_frame = ctk.CTkFrame(self.tab_health)
        results_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        results_frame.grid_columnconfigure(0, weight=1)
        results_frame.grid_rowconfigure(0, weight=1)
        
        self.health_results = ctk.CTkTextbox(results_frame)
        self.health_results.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
    
    def _create_agents_tab(self):
        """Создание вкладки AGENTS.md Editor"""
        self.tab_agents = self.tabview.add("AGENTS.md")
        self.tab_agents.grid_columnconfigure(0, weight=1)
        self.tab_agents.grid_rowconfigure(0, weight=1)
        
        editor_frame = ctk.CTkFrame(self.tab_agents)
        editor_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        editor_frame.grid_columnconfigure(0, weight=1)
        editor_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(editor_frame, text="AGENTS.md - Knowledge Behavior Configuration",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.agents_editor = ctk.CTkTextbox(editor_frame)
        self.agents_editor.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        btn_frame = ctk.CTkFrame(editor_frame)
        btn_frame.grid(row=2, column=0, sticky="e", padx=10, pady=10)
        
        ctk.CTkButton(btn_frame, text="Save", width=80,
                      command=self._save_agents).grid(row=0, column=0, padx=5)
        ctk.CTkButton(btn_frame, text="Reload", width=80,
                      command=self._reload_agents).grid(row=0, column=1, padx=5)
    
    # === UI Helpers ===
    
    def _load_settings_to_ui(self):
        """Загрузка настроек в UI"""
        self.api_key_entry.insert(0, self.config.openai_api_key or "")
        self.base_url_entry.insert(0, self.config.openai_api_base)
        self.model_entry.insert(0, self.config.openai_model)
        self.workspace_entry.delete(0, "end")
        self.workspace_entry.insert(0, self.config.workspace_path)
        self.pageindex_entry.insert(0, self.config.pageindex_api_key or "")
        self.debounce_entry.insert(0, str(self.config.watch_debounce_seconds))
        self.watch_enabled_var.set(self.config.watch_enabled)
    
    def _browse_workspace(self):
        """Выбор директории workspace"""
        import tkinter.filedialog as fd
        path = fd.askdirectory(title="Select Workspace Directory")
        if path:
            self.workspace_entry.delete(0, "end")
            self.workspace_entry.insert(0, path)
    
    # === Callbacks ===
    
    def _save_settings(self):
        """Сохранение настроек"""
        self.config_service.update_config(
            openai_api_key=self.api_key_entry.get(),
            openai_api_base=self.base_url_entry.get(),
            openai_model=self.model_entry.get(),
            workspace_path=self.workspace_entry.get(),
            pageindex_api_key=self.pageindex_entry.get(),
            watch_enabled=self.watch_enabled_var.get(),
            watch_debounce_seconds=int(self.debounce_entry.get() or "2"),
        )
        
        if self.config_service.save_config():
            self.status_var.set("Settings saved successfully")
            self._log_build("Settings saved.\n")
            
            # Пересоздаём сервисы с новыми путями
            self._build_service = None
            self._watch_service = None
            self._wiki_service = None
            self._lint_service = None
            
            # Создаём структуру workspace
            self.config_service.ensure_workspace()
        else:
            self.status_var.set("Failed to save settings")
    
    def _log_build(self, message: str):
        """Безопасное добавление сообщения в лог"""
        try:
            self.build_log.insert("end", message)
            self.build_log.see("end")
        except Exception as e:
            logger.error(f"Ошибка записи в лог: {e}")
    
    def _poll_output_queue(self):
        """Периодический опрос очереди вывода (main thread)"""
        try:
            while True:
                line = self._output_queue.get_nowait()
                self._log_build(line + "\n")
        except queue.Empty:
            pass
        # Продолжаем опрос каждые 50ms
        self.after(50, self._poll_output_queue)
    
    def _on_build_output(self, line: str):
        """Callback для вывода build процесса (вызывается из другого потока)"""
        # Добавляем в очередь - main thread прочитает через poll
        self._output_queue.put(line)
    
    def _on_build_complete(self, result):
        """Callback при завершении build (вызывается из build потока)"""
        # Используем очередь для thread-safe обновления
        self._output_queue.put("")
        if result.success:
            self._output_queue.put(f"Build completed successfully in {result.duration_seconds:.1f}s")
        else:
            self._output_queue.put(f"Build failed (exit code: {result.exit_code})")
            if result.error:
                self._output_queue.put(f"Error: {result.error}")
        
        # Планируем обновление UI в main thread
        self.after(100, lambda: self._update_build_complete_ui(result))
    
    def _update_build_complete_ui(self, result):
        """Обновление UI после завершения build (main thread)"""
        if result.success:
            self.set_state("idle")
            self.status_var.set("Build completed successfully")
        else:
            self.set_state("idle")
            self.status_var.set("Build failed")
    
    def _start_build(self):
        """Запуск build процесса"""
        build_service = self._get_build_service()
        
        # Проверяем состояние
        if build_service.is_building():
            self._log_build("Build already in progress.\n")
            return
        
        # Проверяем workspace
        workspace = self.config_service.get_workspace_path()
        if not workspace.exists():
            self._log_build(f"Creating workspace: {workspace}\n")
            self.config_service.ensure_workspace()
        
        # Проверяем raw директорию
        raw_path = workspace / "raw"
        doc_count = build_service.count_documents()
        
        self._log_build(f"\n{'='*50}\n")
        self._log_build(f"Starting build process...\n")
        self._log_build(f"Workspace: {workspace}\n")
        self._log_build(f"Documents in raw/: {doc_count}\n")
        self._log_build(f"{'='*50}\n\n")
        
        # Запускаем build
        self.set_state("building")
        self.status_var.set("Building knowledge base...")
        
        success = build_service.build(on_complete=self._on_build_complete)
        
        if not success:
            self.set_state("idle")
            self._log_build("Failed to start build process.\n")
            self._log_build("Make sure OpenKB is installed: pip install openkb\n")
    
    def _on_watch_change(self, event):
        """Callback при изменении файлов в watch mode"""
        msg = f"File {event.event_type}: {event.src_path}\n"
        self.after(0, lambda: self._log_build(msg))
    
    def _toggle_watch(self):
        """Переключение watch mode"""
        watch_service = self._get_watch_service()
        
        if watch_service.is_running():
            watch_service.stop()
            self.set_state("idle")
            self.watch_btn.configure(text="Watch")
            self.status_var.set("Watch mode stopped")
            self._log_build("\nWatch mode stopped.\n")
        else:
            if watch_service.start():
                self.set_state("watching")
                self.watch_btn.configure(text="Stop Watch")
                self.status_var.set("Watching for changes...")
                self._log_build(f"\nWatch mode started on: {watch_service.raw_path}\n")
            else:
                self._log_build("Failed to start watch mode.\n")
    
    def _stop_process(self):
        """Остановка текущего процесса"""
        if self.current_state == "building" and self._build_service:
            self._build_service.stop()
            self._log_build("\nBuild process stopped by user.\n")
        
        if self.current_state == "watching" and self._watch_service:
            self._watch_service.stop()
            self.watch_btn.configure(text="Watch")
        
        self.set_state("idle")
        self.status_var.set("Process stopped")
    
    def _run_lint(self):
        """Запуск lint проверки"""
        lint_service = self._get_lint_service()
        
        self.health_results.delete("0.0", "end")
        self.health_results.insert("0.0", "Running lint check...\n\n")
        
        report = lint_service.run_lint()
        
        result_text = f"Lint Report\n{'='*50}\n\n"
        result_text += f"Total issues: {report.total_issues}\n"
        result_text += f"Errors: {report.errors}\n"
        result_text += f"Warnings: {report.warnings}\n"
        result_text += f"Info: {report.info}\n\n"
        
        if report.issues:
            result_text += "Issues:\n" + "-"*50 + "\n"
            for issue in report.issues:
                result_text += f"{issue}\n"
        
        self.health_results.delete("0.0", "end")
        self.health_results.insert("0.0", result_text)
    
    def _refresh_health(self):
        """Обновление health статистики"""
        lint_service = self._get_lint_service()
        stats = lint_service.check_health()
        
        result_text = f"Health Statistics\n{'='*50}\n\n"
        result_text += f"Wiki exists: {stats['wiki_exists']}\n"
        result_text += f"Total pages: {stats['total_pages']}\n"
        result_text += f"Concepts: {stats['concepts_count']}\n"
        result_text += f"Summaries: {stats['summaries_count']}\n"
        result_text += f"Explorations: {stats['explorations_count']}\n"
        result_text += f"AGENTS.md: {'✓' if stats['agents_exists'] else '✗'}\n\n"
        
        if stats['issues']:
            result_text += "Issues:\n"
            for issue in stats['issues']:
                result_text += f"  • {issue}\n"
        
        self.health_results.delete("0.0", "end")
        self.health_results.insert("0.0", result_text)
    
    def _send_chat_message(self, event=None):
        """Отправка сообщения в чат"""
        message = self.chat_input.get().strip()
        if not message:
            return
        
        self.chat_input.delete(0, "end")
        
        # Добавляем сообщение пользователя
        self.chat_history.insert("end", f"\n[You]: {message}\n")
        
        # Проверяем API ключ
        if not self.config.is_valid():
            self.chat_history.insert("end", "\n[System]: Please configure API key in Settings.\n")
            return
        
        # Показываем что обрабатываем
        self.chat_history.insert("end", "\n[Assistant]: Thinking...\n")
        self.chat_history.see("end")
        
        # TODO: Реализовать асинхронный вызов chat_service
        self.chat_history.insert("end", "\n[Assistant]: Chat functionality requires valid API key and compiled wiki.\n")
        self.chat_history.insert("end", "1. Configure API key in Settings\n")
        self.chat_history.insert("end", "2. Add documents to raw/ folder\n")
        self.chat_history.insert("end", "3. Run Build to compile wiki\n\n")
    
    def _save_agents(self):
        """Сохранение AGENTS.md"""
        wiki_service = self._get_wiki_service()
        content = self.agents_editor.get("0.0", "end")
        
        if wiki_service.save_agents_content(content):
            self.status_var.set("AGENTS.md saved")
        else:
            self.status_var.set("Failed to save AGENTS.md")
    
    def _reload_agents(self):
        """Перезагрузка AGENTS.md"""
        wiki_service = self._get_wiki_service()
        content = wiki_service.get_agents_content()
        
        if content:
            self.agents_editor.delete("0.0", "end")
            self.agents_editor.insert("0.0", content)
            self.status_var.set("AGENTS.md reloaded")
        else:
            self.status_var.set("AGENTS.md not found")
    
    def set_state(self, state: str):
        """Установка состояния приложения"""
        self.current_state = state
        
        state_colors = {
            "idle": "green",
            "building": "orange",
            "watching": "blue",
            "linting": "yellow",
            "chatting": "purple",
        }
        self.state_indicator.configure(text_color=state_colors.get(state, "gray"))
        
        if state in ("building", "watching", "linting"):
            self.build_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
        else:
            self.build_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
        
        self.progress_label.configure(text=f"Status: {state.capitalize()}")
    
    def _on_close(self):
        """Обработчик закрытия окна"""
        logger.info("Закрытие приложения")
        
        # Останавливаем watch если запущен
        if self._watch_service and self._watch_service.is_running():
            self._watch_service.stop()
        
        # Останавливаем build если запущен
        if self._build_service and self._build_service.is_building():
            self._build_service.stop()
        
        self.destroy()
