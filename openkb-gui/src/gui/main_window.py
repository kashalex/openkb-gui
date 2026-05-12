"""
Main Window - Главное окно приложения с вкладками
Интеграция со всеми сервисами и улучшенными вкладками
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

# Импорт новых вкладок
from gui.wiki_tab import WikiTab
from gui.concepts_tab import ConceptsTab
from gui.chat_tab import ChatTab
from gui.settings_tab import LLMSettingsTab
from gui.components import StatusBar, ThemeSwitcher, ProgressIndicator, NotificationToast, KeyboardShortcuts

logger = logging.getLogger(__name__)


class MainWindow(ctk.CTk):
    """Главное окно приложения OpenKB GUI с улучшенным UI"""
    
    def __init__(self):
        super().__init__()
        
        # Конфигурация окна
        self.title("OpenKB GUI - Система управления знаниями")
        self.geometry("1500x950")
        self.minsize(1300, 800)
        
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
        self._create_status_bar()
        
        # Загружаем настройки в UI
        self._load_settings_to_ui()
        
        # Регистрируем горячие клавиши
        self._register_shortcuts()
        
        # Обработчик закрытия окна
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        logger.info("MainWindow инициализирован")
    
    # === Service Getters ===
    
    def _get_build_service(self) -> BuildService:
        """Получение/создание BuildService"""
        if self._build_service is None:
            workspace = self.config_service.get_workspace_path()
            self._build_service = BuildService(str(workspace))
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

    def _get_chat_service(self) -> ChatService:
        """Получение/создание ChatService с актуальной конфигурацией."""
        if self._chat_service is None:
            workspace = self.config_service.get_workspace_path()
            self._chat_service = ChatService.from_config(
                str(workspace / "wiki"),
                self.config_service.config,
            )
        return self._chat_service
    
    def _get_session_service(self) -> SessionService:
        """Получение/создание SessionService"""
        if self._session_service is None:
            workspace = self.config_service.get_workspace_path()
            self._session_service = SessionService(str(workspace / "sessions"))
        return self._session_service
    
    # === UI Creation ===
    
    def _create_menu_bar(self):
        """Создание меню бара"""
        self.header_frame = ctk.CTkFrame(self, height=60)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        self.header_frame.grid_columnconfigure(2, weight=1)
        
        # Логотип и название
        title_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_frame.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.title_label = ctk.CTkLabel(
            title_frame,
            text="📚 OpenKB GUI",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        self.title_label.grid(row=0, column=0, sticky="w")
        
        self.version_label = ctk.CTkLabel(
            title_frame,
            text="v1.1.0",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        self.version_label.grid(row=1, column=0, sticky="w")
        
        # Статус
        status_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        status_frame.grid(row=0, column=1, padx=20, pady=10)
        
        self.state_indicator = ctk.CTkLabel(
            status_frame,
            text="●",
            font=ctk.CTkFont(size=18),
            text_color="#4ec9b0"
        )
        self.state_indicator.grid(row=0, column=0, padx=5)
        
        self.status_var = ctk.StringVar(value="Ready")
        self.status_label = ctk.CTkLabel(
            status_frame,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=12)
        )
        self.status_label.grid(row=0, column=1)
        
        # Переключатель темы
        self.theme_switcher = ThemeSwitcher(
            self.header_frame,
            on_change=self._on_theme_change
        )
        self.theme_switcher.grid(row=0, column=2, padx=10, pady=10, sticky="e")
    
    def _create_main_container(self):
        """Создание основного контейнера с вкладками"""
        self.main_container = ctk.CTkFrame(self)
        self.main_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)
        
        # Создаём вкладки с иконками
        self.tabview = ctk.CTkTabview(self.main_container, width=1460, height=850)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Создаём все вкладки
        self._create_settings_tab()
        self._create_build_tab()
        self._create_wiki_tab()
        self._create_concepts_tab()
        self._create_chat_tab()
        self._create_health_tab()
        self._create_agents_tab()
    
    def _create_status_bar(self):
        """Создание статус-бара"""
        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 10))
        
        # Обновляем информацию
        workspace = self.config_service.get_workspace_path()
        self.status_bar.set_workspace(str(workspace))
        
        api_configured = self.config.is_valid()
        provider = self.config.get_current_provider()
        self.status_bar.set_api_status(api_configured, provider)
    
    # === Tab Creation ===
    
    def _create_settings_tab(self):
        """Создание вкладки Settings с улучшенным UI для выбора LLM провайдеров"""
        self.tab_settings = self.tabview.add("⚙️ Settings")
        self.tab_settings.grid_columnconfigure(0, weight=1)
        self.tab_settings.grid_rowconfigure(0, weight=1)

        # Используем новый компонент LLMSettingsTab
        self.settings_tab = LLMSettingsTab(self.tab_settings)
        self.settings_tab.grid(row=0, column=0, sticky="nsew")
    
    def _create_build_tab(self):
        """Создание вкладки Build"""
        self.tab_build = self.tabview.add("🔨 Build")
        self.tab_build.grid_columnconfigure(0, weight=1)
        self.tab_build.grid_rowconfigure(1, weight=1)
        
        control_frame = ctk.CTkFrame(self.tab_build, height=70)
        control_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        control_frame.grid_columnconfigure(3, weight=1)
        
        self.build_btn = ctk.CTkButton(control_frame, text="🔨 Build", width=100, 
                                        height=40, command=self._start_build)
        self.build_btn.grid(row=0, column=0, padx=10, pady=10)
        
        self.watch_btn = ctk.CTkButton(control_frame, text="👀 Watch", width=100,
                                         height=40, command=self._toggle_watch)
        self.watch_btn.grid(row=0, column=1, padx=10, pady=10)
        
        self.stop_btn = ctk.CTkButton(control_frame, text="⏹️ Stop", width=100, 
                                        height=40, state="disabled", command=self._stop_process)
        self.stop_btn.grid(row=0, column=2, padx=10, pady=10)
        
        # Прогресс
        self.progress_indicator = ProgressIndicator(control_frame)
        self.progress_indicator.grid(row=0, column=3, padx=10, pady=10, sticky="e")
        
        log_frame = ctk.CTkFrame(self.tab_build)
        log_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)
        
        self.build_log = ctk.CTkTextbox(log_frame, font=ctk.CTkFont(family="Consolas", size=11))
        self.build_log.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.build_log.insert("0.0", "OpenKB Build Log\n")
        self.build_log.insert("end", "="*50 + "\n\n")
        self.build_log.insert("end", "Welcome to OpenKB GUI! 🎉\n\n")
        self.build_log.insert("end", "Instructions:\n")
        self.build_log.insert("end", "  1. Configure API key in Settings\n")
        self.build_log.insert("end", "  2. Add documents to workspace/raw/ folder\n")
        self.build_log.insert("end", "  3. Click 'Build' to compile knowledge base\n")
        self.build_log.insert("end", "  4. Use Chat tab to query your knowledge\n\n")
        self.build_log.insert("end", "Supported formats: .pdf, .docx, .txt, .md\n\n")
    
    def _create_wiki_tab(self):
        """Создание вкладки Wiki Browser"""
        self.tab_wiki = self.tabview.add("📁 Wiki Browser")
        self.tab_wiki.grid_columnconfigure(0, weight=1)
        self.tab_wiki.grid_rowconfigure(0, weight=1)
        
        # Создаём улучшенную вкладку Wiki
        self.wiki_tab = WikiTab(
            self.tab_wiki,
            wiki_service_getter=self._get_wiki_service
        )
        self.wiki_tab.grid(row=0, column=0, sticky="nsew")
    
    def _create_concepts_tab(self):
        """Создание вкладки Concepts"""
        self.tab_concepts = self.tabview.add("💡 Concepts")
        self.tab_concepts.grid_columnconfigure(0, weight=1)
        self.tab_concepts.grid_rowconfigure(0, weight=1)
        
        # Создаём улучшенную вкладку Concepts
        self.concepts_tab = ConceptsTab(
            self.tab_concepts,
            wiki_service_getter=self._get_wiki_service
        )
        self.concepts_tab.grid(row=0, column=0, sticky="nsew")
    
    def _create_chat_tab(self):
        """Создание вкладки Chat"""
        self.tab_chat = self.tabview.add("💬 Chat")
        self.tab_chat.grid_columnconfigure(0, weight=1)
        self.tab_chat.grid_rowconfigure(0, weight=1)
        
        # Создаём улучшенную вкладку Chat
        self.chat_tab = ChatTab(
            self.tab_chat,
            chat_service_getter=self._get_chat_service,
            session_service_getter=self._get_session_service,
            config_getter=lambda: self.config
        )
        self.chat_tab.grid(row=0, column=0, sticky="nsew")
    
    def _create_health_tab(self):
        """Создание вкладки Health"""
        self.tab_health = self.tabview.add("🏥 Health")
        self.tab_health.grid_columnconfigure(0, weight=1)
        self.tab_health.grid_rowconfigure(1, weight=1)
        
        control_frame = ctk.CTkFrame(self.tab_health, height=60)
        control_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        ctk.CTkButton(control_frame, text="🔍 Run Lint", width=100, height=35,
                      command=self._run_lint).grid(row=0, column=0, padx=10, pady=10)
        
        ctk.CTkButton(control_frame, text="🔄 Refresh", width=100, height=35,
                      command=self._refresh_health).grid(row=0, column=1, padx=10, pady=10)
        
        results_frame = ctk.CTkFrame(self.tab_health)
        results_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        results_frame.grid_columnconfigure(0, weight=1)
        results_frame.grid_rowconfigure(0, weight=1)
        
        self.health_results = ctk.CTkTextbox(results_frame, font=ctk.CTkFont(family="Consolas", size=11))
        self.health_results.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
    
    def _create_agents_tab(self):
        """Создание вкладки AGENTS.md Editor"""
        self.tab_agents = self.tabview.add("📝 AGENTS.md")
        self.tab_agents.grid_columnconfigure(0, weight=1)
        self.tab_agents.grid_rowconfigure(0, weight=1)
        
        editor_frame = ctk.CTkFrame(self.tab_agents)
        editor_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        editor_frame.grid_columnconfigure(0, weight=1)
        editor_frame.grid_rowconfigure(1, weight=1)
        
        header_frame = ctk.CTkFrame(editor_frame)
        header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        header_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(header_frame, text="📝 AGENTS.md - Knowledge Behavior Configuration",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        btn_frame = ctk.CTkFrame(header_frame)
        btn_frame.grid(row=0, column=1, padx=10, pady=10, sticky="e")
        
        ctk.CTkButton(btn_frame, text="💾 Save", width=80, height=32,
                      command=self._save_agents).grid(row=0, column=0, padx=5)
        ctk.CTkButton(btn_frame, text="🔄 Reload", width=80, height=32,
                      command=self._reload_agents).grid(row=0, column=1, padx=5)
        
        self.agents_editor = ctk.CTkTextbox(editor_frame, font=ctk.CTkFont(family="Consolas", size=12))
        self.agents_editor.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
    
    # === Keyboard Shortcuts ===
    
    def _register_shortcuts(self):
        """Регистрация горячих клавиш"""
        self.shortcuts = KeyboardShortcuts(self)
        
        # Ctrl+B - Build
        self.shortcuts.register("<Control-b>", self._start_build, "Build")
        
        # Ctrl+S - Save settings
        self.shortcuts.register("<Control-s>", self._save_settings, "Save Settings")
        
        # F5 - Refresh
        self.shortcuts.register("<F5>", self._refresh_all, "Refresh All")
        
        # Escape - Stop process
        self.shortcuts.register("<Escape>", self._stop_process, "Stop Process")
        
        # Ctrl+1-7 - Switch tabs
        for i in range(1, 8):
            self.shortcuts.register(
                f"<Control-Key-{i}>",
                lambda idx=i-1: self._switch_tab(idx),
                f"Switch to Tab {i}"
            )
    
    def _switch_tab(self, index: int):
        """Переключение вкладки"""
        try:
            tabs = list(self.tabview._tab_dict.keys())
            if 0 <= index < len(tabs):
                self.tabview.set(tabs[index])
        except Exception:
            pass
    
    def _refresh_all(self):
        """Обновление всех компонентов"""
        if hasattr(self, 'wiki_tab'):
            self.wiki_tab.refresh_tree()
        if hasattr(self, 'concepts_tab'):
            self.concepts_tab.refresh_concepts()
        if hasattr(self, 'chat_tab'):
            self.chat_tab.refresh_sessions()
        self._refresh_health()
    
    # === UI Helpers ===

    def _on_theme_change(self, theme: str):
        """Callback при смене темы"""
        self._log_build(f"Theme changed to: {theme}\n")

    def _save_settings(self):
        """Сохранение настроек через Ctrl+S"""
        if hasattr(self, 'settings_tab'):
            # Сохраняем настройки через LLMSettingsTab
            self.settings_tab._save_all_settings()
            self.status_var.set("Settings saved ✓")
            NotificationToast(self, "Settings saved! ✓", 2000)

    def _load_settings_to_ui(self):
        """Загрузка настроек в UI - настройки загружаются в LLMSettingsTab автоматически"""
        # LLMSettingsTab загружает настройки автоматически в _load_initial_state
        pass
    
    def _log_build(self, message: str):
        """Безопасное добавление сообщения в лог"""
        try:
            self.build_log.insert("end", message)
            self.build_log.see("end")
        except Exception as e:
            logger.error(f"Ошибка записи в лог: {e}")
    
    def _poll_output_queue(self):
        """Периодический опрос очереди вывода"""
        try:
            while True:
                line = self._output_queue.get_nowait()
                self._log_build(line + "\n")
        except queue.Empty:
            pass
        self.after(50, self._poll_output_queue)
    
    def _on_build_output(self, line: str):
        """Callback для вывода build процесса"""
        self._output_queue.put(line)
    
    def _on_build_complete(self, result):
        """Callback при завершении build"""
        self._output_queue.put("")
        if result.success:
            self._output_queue.put(f"✅ Build completed in {result.duration_seconds:.1f}s")
        else:
            self._output_queue.put(f"❌ Build failed (exit code: {result.exit_code})")
            if result.error:
                self._output_queue.put(f"Error: {result.error}")
        
        self.after(100, lambda: self._update_build_complete_ui(result))
    
    def _update_build_complete_ui(self, result):
        """Обновление UI после завершения build"""
        if result.success:
            self.set_state("idle")
            self.status_var.set("Build completed ✓")
            self.progress_indicator.stop("Build completed ✓")
            
            # Обновляем вкладки
            if hasattr(self, 'wiki_tab'):
                self.wiki_tab.refresh_tree()
            if hasattr(self, 'concepts_tab'):
                self.concepts_tab.refresh_concepts()
            
            # Обновляем статистику
            wiki_service = self._get_wiki_service()
            stats = wiki_service.get_statistics()
            self.status_bar.set_stats(
                stats['total_pages'],
                stats['concepts'],
                stats['total_words']
            )
            
            # Уведомление
            NotificationToast(self, "Build completed successfully! ✓", 3000)
        else:
            self.set_state("idle")
            self.status_var.set("Build failed")
            self.progress_indicator.stop("Build failed")
    
    def _start_build(self):
        """Запуск build процесса"""
        build_service = self._get_build_service()
        
        if build_service.is_building():
            self._log_build("Build already in progress.\n")
            return
        
        workspace = self.config_service.get_workspace_path()
        if not workspace.exists():
            self._log_build(f"Creating workspace: {workspace}\n")
            self.config_service.ensure_workspace()
        
        doc_count = build_service.count_documents()
        
        self._log_build(f"\n{'='*50}\n")
        self._log_build(f"🔨 Compiling knowledge base...\n")
        self._log_build(f"📁 Workspace: {workspace}\n")
        self._log_build(f"📄 Documents: {doc_count}\n")
        self._log_build(f"{'='*50}\n\n")
        
        self.set_state("building")
        self.status_var.set("Building...")
        self.progress_indicator.set_indeterminate("Building knowledge base...")
        
        success = build_service.build(on_complete=self._on_build_complete)
        
        if not success:
            self.set_state("idle")
            self._log_build("❌ Failed to start build.\n")
            self.progress_indicator.stop("Failed to start")
    
    def _on_watch_change(self, event):
        """Callback при изменении файлов в watch mode"""
        msg = f"📝 File {event.event_type}: {event.src_path}\n"
        self.after(0, lambda: self._log_build(msg))
    
    def _toggle_watch(self):
        """Переключение watch mode"""
        watch_service = self._get_watch_service()
        
        if watch_service.is_running():
            watch_service.stop()
            self.set_state("idle")
            self.watch_btn.configure(text="👀 Watch")
            self.status_var.set("Watch stopped")
            self._log_build("\n⏹️ Watch mode stopped.\n")
        else:
            if watch_service.start():
                self.set_state("watching")
                self.watch_btn.configure(text="⏹️ Stop Watch")
                self.status_var.set("Watching...")
                self._log_build(f"\n👀 Watch mode started on: {watch_service.raw_path}\n")
            else:
                self._log_build("❌ Failed to start watch mode.\n")
    
    def _stop_process(self):
        """Остановка текущего процесса"""
        if self.current_state == "building" and self._build_service:
            self._build_service.stop()
            self._log_build("\n⏹️ Build stopped by user.\n")
        
        if self.current_state == "watching" and self._watch_service:
            self._watch_service.stop()
            self.watch_btn.configure(text="👀 Watch")
        
        self.set_state("idle")
        self.status_var.set("Stopped")
        self.progress_indicator.stop("Stopped")
    
    def _run_lint(self):
        """Запуск lint проверки"""
        lint_service = self._get_lint_service()
        
        self.health_results.delete("0.0", "end")
        self.health_results.insert("0.0", "🔍 Running lint check...\n\n")
        
        report = lint_service.run_lint()
        
        result_text = f"🔍 Lint Report\n{'='*50}\n\n"
        result_text += f"Total issues: {report.total_issues}\n"
        result_text += f"❌ Errors: {report.errors}\n"
        result_text += f"⚠️ Warnings: {report.warnings}\n"
        result_text += f"ℹ️ Info: {report.info}\n\n"
        
        if report.issues:
            result_text += "Issues:\n" + "-"*50 + "\n"
            for issue in report.issues:
                result_text += f"  {issue}\n"
        
        self.health_results.delete("0.0", "end")
        self.health_results.insert("0.0", result_text)
    
    def _refresh_health(self):
        """Обновление health статистики"""
        lint_service = self._get_lint_service()
        stats = lint_service.check_health()
        
        result_text = f"📊 Health Statistics\n{'='*50}\n\n"
        result_text += f"Wiki exists: {'✓' if stats['wiki_exists'] else '✗'}\n"
        result_text += f"📄 Total pages: {stats['total_pages']}\n"
        result_text += f"💡 Concepts: {stats['concepts_count']}\n"
        result_text += f"📝 Summaries: {stats['summaries_count']}\n"
        result_text += f"🔍 Explorations: {stats['explorations_count']}\n"
        result_text += f"📋 AGENTS.md: {'✓' if stats['agents_exists'] else '✗'}\n\n"
        
        if stats['issues']:
            result_text += "⚠️ Issues:\n"
            for issue in stats['issues']:
                result_text += f"  • {issue}\n"
        
        self.health_results.delete("0.0", "end")
        self.health_results.insert("0.0", result_text)
    
    def _save_agents(self):
        """Сохранение AGENTS.md"""
        wiki_service = self._get_wiki_service()
        content = self.agents_editor.get("0.0", "end")
        
        if wiki_service.save_agents_content(content):
            self.status_var.set("AGENTS.md saved ✓")
            NotificationToast(self, "AGENTS.md saved! ✓", 2000)
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
            "idle": "#4ec9b0",
            "building": "#ffa500",
            "watching": "#569cd6",
            "linting": "#dcdcaa",
            "chatting": "#c586c0",
        }
        self.state_indicator.configure(text_color=state_colors.get(state, "gray"))
        
        if state in ("building", "watching", "linting"):
            self.build_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
        else:
            self.build_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
        
        self.progress_label_text = f"Status: {state.capitalize()}"
    
    def _on_close(self):
        """Обработчик закрытия окна"""
        logger.info("Закрытие приложения")
        
        if self._watch_service and self._watch_service.is_running():
            self._watch_service.stop()
        
        if self._build_service and self._build_service.is_building():
            self._build_service.stop()
        
        self.destroy()
