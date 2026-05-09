"""
Main Window - Главное окно приложения с вкладками
"""

import customtkinter as ctk
from typing import Optional
import logging

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
        self.current_state = "idle"  # idle, building, watching, linting, chatting
        
        # Создаём UI
        self._create_menu_bar()
        self._create_main_container()
        
        # Обработчик закрытия окна
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        logger.info("MainWindow инициализирован")
    
    def _create_menu_bar(self):
        """Создание меню бара"""
        # Верхняя панель с заголовком и статусом
        self.header_frame = ctk.CTkFrame(self, height=50)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        self.header_frame.grid_columnconfigure(1, weight=1)
        
        # Заголовок
        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="OpenKB GUI",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        # Статус
        self.status_var = ctk.StringVar(value="Готов к работе")
        self.status_label = ctk.CTkLabel(
            self.header_frame,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.status_label.grid(row=0, column=1, padx=10, pady=10, sticky="e")
        
        # Индикатор состояния
        self.state_indicator = ctk.CTkLabel(
            self.header_frame,
            text="●",
            font=ctk.CTkFont(size=16),
            text_color="green"
        )
        self.state_indicator.grid(row=0, column=2, padx=10, pady=10)
    
    def _create_main_container(self):
        """Создание основного контейнера с вкладками"""
        # Главный контейнер
        self.main_container = ctk.CTkFrame(self)
        self.main_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)
        
        # Tabview с вкладками
        self.tabview = ctk.CTkTabview(
            self.main_container,
            width=1380,
            height=850
        )
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Создаём вкладки согласно ТЗ (7 вкладок)
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
        
        # Контейнер настроек
        settings_frame = ctk.CTkScrollableFrame(self.tab_settings)
        settings_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        settings_frame.grid_columnconfigure(1, weight=1)
        
        row = 0
        
        # === LLM Settings ===
        llm_label = ctk.CTkLabel(
            settings_frame,
            text="LLM Configuration",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        llm_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))
        row += 1
        
        # API Key
        api_key_label = ctk.CTkLabel(settings_frame, text="API Key:")
        api_key_label.grid(row=row, column=0, sticky="w", padx=10, pady=5)
        self.api_key_entry = ctk.CTkEntry(settings_frame, width=400, show="*")
        self.api_key_entry.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        row += 1
        
        # Base URL
        base_url_label = ctk.CTkLabel(settings_frame, text="API Base URL:")
        base_url_label.grid(row=row, column=0, sticky="w", padx=10, pady=5)
        self.base_url_entry = ctk.CTkEntry(settings_frame, width=400)
        self.base_url_entry.insert(0, "https://api.z.ai/api/paas/v4")
        self.base_url_entry.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        row += 1
        
        # Model
        model_label = ctk.CTkLabel(settings_frame, text="Model:")
        model_label.grid(row=row, column=0, sticky="w", padx=10, pady=5)
        self.model_entry = ctk.CTkEntry(settings_frame, width=400)
        self.model_entry.insert(0, "openai/glm-4.7-flash")
        self.model_entry.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        row += 1
        
        # Separator
        separator1 = ctk.CTkFrame(settings_frame, height=2)
        separator1.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=15)
        row += 1
        
        # === Workspace Settings ===
        workspace_label = ctk.CTkLabel(
            settings_frame,
            text="Workspace Configuration",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        workspace_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))
        row += 1
        
        # Workspace Path
        ws_path_label = ctk.CTkLabel(settings_frame, text="Workspace Path:")
        ws_path_label.grid(row=row, column=0, sticky="w", padx=10, pady=5)
        
        ws_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        ws_frame.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        ws_frame.grid_columnconfigure(0, weight=1)
        
        self.workspace_entry = ctk.CTkEntry(ws_frame, width=350)
        self.workspace_entry.insert(0, "./workspace")
        self.workspace_entry.grid(row=0, column=0, padx=(0, 5))
        
        self.browse_btn = ctk.CTkButton(ws_frame, text="Browse", width=80)
        self.browse_btn.grid(row=0, column=1)
        row += 1
        
        # Separator
        separator2 = ctk.CTkFrame(settings_frame, height=2)
        separator2.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=15)
        row += 1
        
        # === PageIndex Settings ===
        pageindex_label = ctk.CTkLabel(
            settings_frame,
            text="PageIndex OCR (Optional)",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        pageindex_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))
        row += 1
        
        # PageIndex API Key
        pi_key_label = ctk.CTkLabel(settings_frame, text="PageIndex API Key:")
        pi_key_label.grid(row=row, column=0, sticky="w", padx=10, pady=5)
        self.pageindex_entry = ctk.CTkEntry(settings_frame, width=400, show="*")
        self.pageindex_entry.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        row += 1
        
        # Separator
        separator3 = ctk.CTkFrame(settings_frame, height=2)
        separator3.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=15)
        row += 1
        
        # === Watch Mode Settings ===
        watch_label = ctk.CTkLabel(
            settings_frame,
            text="Watch Mode Settings",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        watch_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))
        row += 1
        
        # Watch Enabled
        self.watch_enabled_var = ctk.BooleanVar(value=True)
        watch_check = ctk.CTkCheckBox(
            settings_frame,
            text="Enable Watch Mode",
            variable=self.watch_enabled_var
        )
        watch_check.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        row += 1
        
        # Debounce
        debounce_label = ctk.CTkLabel(settings_frame, text="Debounce (seconds):")
        debounce_label.grid(row=row, column=0, sticky="w", padx=10, pady=5)
        self.debounce_entry = ctk.CTkEntry(settings_frame, width=100)
        self.debounce_entry.insert(0, "2")
        self.debounce_entry.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        row += 1
        
        # Separator
        separator4 = ctk.CTkFrame(settings_frame, height=2)
        separator4.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=15)
        row += 1
        
        # === Save Button ===
        self.save_settings_btn = ctk.CTkButton(
            settings_frame,
            text="Save Settings",
            width=150,
            command=self._save_settings
        )
        self.save_settings_btn.grid(row=row, column=0, columnspan=2, pady=20)
    
    def _create_build_tab(self):
        """Создание вкладки Build"""
        self.tab_build = self.tabview.add("Build")
        self.tab_build.grid_columnconfigure(0, weight=1)
        self.tab_build.grid_rowconfigure(1, weight=1)
        
        # Верхняя панель с кнопками
        control_frame = ctk.CTkFrame(self.tab_build, height=60)
        control_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        control_frame.grid_columnconfigure(3, weight=1)
        
        # Build Button
        self.build_btn = ctk.CTkButton(
            control_frame,
            text="Build",
            width=100,
            command=self._start_build
        )
        self.build_btn.grid(row=0, column=0, padx=10, pady=10)
        
        # Watch Button
        self.watch_btn = ctk.CTkButton(
            control_frame,
            text="Watch",
            width=100,
            command=self._toggle_watch
        )
        self.watch_btn.grid(row=0, column=1, padx=10, pady=10)
        
        # Stop Button
        self.stop_btn = ctk.CTkButton(
            control_frame,
            text="Stop",
            width=100,
            state="disabled",
            command=self._stop_process
        )
        self.stop_btn.grid(row=0, column=2, padx=10, pady=10)
        
        # Progress indicator
        self.progress_label = ctk.CTkLabel(
            control_frame,
            text="Status: Idle",
            font=ctk.CTkFont(size=12)
        )
        self.progress_label.grid(row=0, column=3, padx=10, pady=10, sticky="e")
        
        # Log area
        log_frame = ctk.CTkFrame(self.tab_build)
        log_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)
        
        self.build_log = ctk.CTkTextbox(log_frame, height=600)
        self.build_log.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.build_log.insert("0.0", "Build logs will appear here...\n")
    
    def _create_wiki_tab(self):
        """Создание вкладки Wiki Browser"""
        self.tab_wiki = self.tabview.add("Wiki Browser")
        self.tab_wiki.grid_columnconfigure(1, weight=1)
        self.tab_wiki.grid_rowconfigure(0, weight=1)
        
        # Левая панель - дерево файлов
        tree_frame = ctk.CTkFrame(self.tab_wiki, width=300)
        tree_frame.grid(row=0, column=0, sticky="ns", padx=10, pady=10)
        tree_frame.grid_rowconfigure(1, weight=1)
        
        tree_label = ctk.CTkLabel(tree_frame, text="Wiki Files", font=ctk.CTkFont(weight="bold"))
        tree_label.grid(row=0, column=0, padx=10, pady=10)
        
        # Placeholder для дерева
        self.wiki_tree = ctk.CTkTextbox(tree_frame, width=280)
        self.wiki_tree.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.wiki_tree.insert("0.0", "wiki/\n├── concepts/\n├── summaries/\n├── explorations/\n├── reports/\n├── sources/\n└── AGENTS.md\n")
        
        # Правая панель - просмотр markdown
        preview_frame = ctk.CTkFrame(self.tab_wiki)
        preview_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_rowconfigure(1, weight=1)
        
        preview_label = ctk.CTkLabel(preview_frame, text="Markdown Preview", font=ctk.CTkFont(weight="bold"))
        preview_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.wiki_preview = ctk.CTkTextbox(preview_frame)
        self.wiki_preview.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.wiki_preview.insert("0.0", "Select a wiki file to preview...\n\nWiki preview will be rendered here with:\n- Markdown rendering\n- Wikilinks navigation\n- Concept references\n")
    
    def _create_concepts_tab(self):
        """Создание вкладки Concepts"""
        self.tab_concepts = self.tabview.add("Concepts")
        self.tab_concepts.grid_columnconfigure(0, weight=1)
        self.tab_concepts.grid_rowconfigure(0, weight=1)
        
        # Основной контейнер
        concepts_frame = ctk.CTkScrollableFrame(self.tab_concepts)
        concepts_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        concepts_frame.grid_columnconfigure(0, weight=1)
        
        # Placeholder
        placeholder = ctk.CTkLabel(
            concepts_frame,
            text="Concepts Management",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        placeholder.grid(row=0, column=0, pady=20)
        
        info_label = ctk.CTkLabel(
            concepts_frame,
            text="This tab will display:\n• List of concepts\n• Related documents\n• Backlinks\n• Timestamps\n• Summaries",
            justify="left"
        )
        info_label.grid(row=1, column=0, pady=10)
    
    def _create_chat_tab(self):
        """Создание вкладки Chat"""
        self.tab_chat = self.tabview.add("Chat")
        self.tab_chat.grid_columnconfigure(1, weight=1)
        self.tab_chat.grid_rowconfigure(0, weight=1)
        
        # Левая панель - sessions
        sessions_frame = ctk.CTkFrame(self.tab_chat, width=250)
        sessions_frame.grid(row=0, column=0, sticky="ns", padx=10, pady=10)
        sessions_frame.grid_rowconfigure(1, weight=1)
        
        sessions_label = ctk.CTkLabel(sessions_frame, text="Sessions", font=ctk.CTkFont(weight="bold"))
        sessions_label.grid(row=0, column=0, padx=10, pady=10)
        
        # Session list placeholder
        self.session_list = ctk.CTkTextbox(sessions_frame, width=230, height=700)
        self.session_list.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.session_list.insert("0.0", "Session 1 - Today\nSession 2 - Yesterday\n\n[+ New Session]\n")
        
        # Правая панель - чат
        chat_frame = ctk.CTkFrame(self.tab_chat)
        chat_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        chat_frame.grid_columnconfigure(0, weight=1)
        chat_frame.grid_rowconfigure(0, weight=1)
        
        # История сообщений
        self.chat_history = ctk.CTkTextbox(chat_frame, height=700)
        self.chat_history.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.chat_history.insert("0.0", "Chat with your knowledge base...\n\nThe chat uses compiled wiki (not vector RAG).\nAnswers are based on:\n• Concepts pages\n• Summaries\n• Wiki links\n• Knowledge graph\n")
        
        # Поле ввода
        input_frame = ctk.CTkFrame(chat_frame)
        input_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        input_frame.grid_columnconfigure(0, weight=1)
        
        self.chat_input = ctk.CTkEntry(input_frame, placeholder_text="Type your question...")
        self.chat_input.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        send_btn = ctk.CTkButton(input_frame, text="Send", width=80)
        send_btn.grid(row=0, column=1, padx=5, pady=5)
        
        # Sources panel
        sources_label = ctk.CTkLabel(chat_frame, text="Sources:", font=ctk.CTkFont(weight="bold"))
        sources_label.grid(row=2, column=0, sticky="w", padx=5, pady=(10, 5))
        
        self.sources_display = ctk.CTkTextbox(chat_frame, height=100)
        self.sources_display.grid(row=3, column=0, sticky="ew", padx=5, pady=5)
        self.sources_display.insert("0.0", "Sources will appear here...\n")
    
    def _create_health_tab(self):
        """Создание вкладки Health"""
        self.tab_health = self.tabview.add("Health")
        self.tab_health.grid_columnconfigure(0, weight=1)
        self.tab_health.grid_rowconfigure(1, weight=1)
        
        # Верхняя панель
        control_frame = ctk.CTkFrame(self.tab_health, height=60)
        control_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        lint_btn = ctk.CTkButton(control_frame, text="Run Lint", width=100)
        lint_btn.grid(row=0, column=0, padx=10, pady=10)
        
        refresh_btn = ctk.CTkButton(control_frame, text="Refresh", width=100)
        refresh_btn.grid(row=0, column=1, padx=10, pady=10)
        
        # Results area
        results_frame = ctk.CTkFrame(self.tab_health)
        results_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        results_frame.grid_columnconfigure(0, weight=1)
        results_frame.grid_rowconfigure(0, weight=1)
        
        self.health_results = ctk.CTkTextbox(results_frame)
        self.health_results.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.health_results.insert("0.0", "Health & Lint Results\n" + "=" * 50 + "\n\nThis tab will display:\n• Orphan concepts\n• Stale pages\n• Contradictions\n• Broken links\n• Compilation warnings\n")
    
    def _create_agents_tab(self):
        """Создание вкладки AGENTS.md Editor"""
        self.tab_agents = self.tabview.add("AGENTS.md")
        self.tab_agents.grid_columnconfigure(0, weight=1)
        self.tab_agents.grid_rowconfigure(0, weight=1)
        
        # Контейнер редактора
        editor_frame = ctk.CTkFrame(self.tab_agents)
        editor_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        editor_frame.grid_columnconfigure(0, weight=1)
        editor_frame.grid_rowconfigure(1, weight=1)
        
        # Заголовок
        header = ctk.CTkLabel(
            editor_frame,
            text="AGENTS.md - Knowledge Behavior Configuration",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        header.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        # Текстовый редактор
        self.agents_editor = ctk.CTkTextbox(editor_frame)
        self.agents_editor.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.agents_editor.insert("0.0", "# AGENTS.md\n\nThis file configures knowledge behavior for OpenKB.\n\nEdit this file to customize:\n• Concept extraction rules\n• Summary generation\n• Cross-linking behavior\n\n[Save] [Reload] buttons coming soon...\n")
        
        # Кнопки
        btn_frame = ctk.CTkFrame(editor_frame)
        btn_frame.grid(row=2, column=0, sticky="e", padx=10, pady=10)
        
        save_btn = ctk.CTkButton(btn_frame, text="Save", width=80)
        save_btn.grid(row=0, column=0, padx=5)
        
        reload_btn = ctk.CTkButton(btn_frame, text="Reload", width=80)
        reload_btn.grid(row=0, column=1, padx=5)
    
    # === Callbacks ===
    
    def _save_settings(self):
        """Сохранение настроек"""
        from services.config_service import ConfigService
        
        config_service = ConfigService.get_instance()
        config_service.update_config(
            openai_api_key=self.api_key_entry.get(),
            openai_api_base=self.base_url_entry.get(),
            openai_model=self.model_entry.get(),
            workspace_path=self.workspace_entry.get(),
            pageindex_api_key=self.pageindex_entry.get(),
            watch_enabled=self.watch_enabled_var.get(),
            watch_debounce_seconds=int(self.debounce_entry.get() or "2"),
        )
        
        if config_service.save_config():
            self.status_var.set("Settings saved successfully")
            logger.info("Настройки сохранены")
        else:
            self.status_var.set("Failed to save settings")
    
    def _start_build(self):
        """Запуск build процесса"""
        self.set_state("building")
        self.status_var.set("Building knowledge base...")
        self.build_log.insert("end", "\nStarting build process...\n")
        self.build_log.see("end")
        # TODO: Реализовать build_service
    
    def _toggle_watch(self):
        """Переключение watch mode"""
        if self.current_state == "watching":
            self.set_state("idle")
            self.watch_btn.configure(text="Watch")
            self.status_var.set("Watch mode stopped")
        else:
            self.set_state("watching")
            self.watch_btn.configure(text="Stop Watch")
            self.status_var.set("Watching for changes...")
        # TODO: Реализовать watch_service
    
    def _stop_process(self):
        """Остановка текущего процесса"""
        self.set_state("idle")
        self.status_var.set("Process stopped")
        self.build_log.insert("end", "\nProcess stopped by user.\n")
        self.build_log.see("end")
    
    def set_state(self, state: str):
        """Установка состояния приложения"""
        self.current_state = state
        
        # Обновляем индикатор
        state_colors = {
            "idle": "green",
            "building": "orange",
            "watching": "blue",
            "linting": "yellow",
            "chatting": "purple",
        }
        self.state_indicator.configure(text_color=state_colors.get(state, "gray"))
        
        # Управляем кнопками
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
        self.destroy()
