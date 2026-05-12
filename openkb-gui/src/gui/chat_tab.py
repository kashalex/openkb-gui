"""
Chat Tab - Вкладка чата с управлением сессиями
Полноценный чат с историей, сессиями, экспортом/импортом
"""

import customtkinter as ctk
from tkinter import filedialog
from typing import Callable, Optional
from pathlib import Path
import logging
import json
import threading
from datetime import datetime

logger = logging.getLogger(__name__)


class ChatTab(ctk.CTkFrame):
    """Вкладка чата с управлением сессиями"""
    
    def __init__(
        self,
        master,
        chat_service_getter: Callable,
        session_service_getter: Callable,
        config_getter: Callable
    ):
        """
        Инициализация Chat Tab
        
        Args:
            master: Родительский виджет
            chat_service_getter: Функция для получения ChatService
            session_service_getter: Функция для получения SessionService
            config_getter: Функция для получения конфигурации
        """
        super().__init__(master)
        
        self._get_chat_service = chat_service_getter
        self._get_session_service = session_service_getter
        self._get_config = config_getter
        
        self._current_session = None
        self._is_generating = False
        
        # Настройка grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Создаём UI
        self._create_sessions_panel()
        self._create_chat_panel()
        
        logger.info("ChatTab инициализирован")
    
    def _create_sessions_panel(self):
        """Создание панели управления сессиями"""
        self.sessions_frame = ctk.CTkFrame(self, width=280)
        self.sessions_frame.grid(row=0, column=0, sticky="ns", padx=(10, 5), pady=10)
        self.sessions_frame.grid_propagate(False)
        self.sessions_frame.grid_rowconfigure(1, weight=1)
        
        # Заголовок
        title_label = ctk.CTkLabel(
            self.sessions_frame,
            text="💬 Chat Sessions",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        # Список сессий
        sessions_container = ctk.CTkFrame(self.sessions_frame)
        sessions_container.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        sessions_container.grid_columnconfigure(0, weight=1)
        sessions_container.grid_rowconfigure(0, weight=1)
        
        self.sessions_list = ctk.CTkScrollableFrame(sessions_container)
        self.sessions_list.grid(row=0, column=0, sticky="nsew")
        
        # Кнопки управления
        buttons_frame = ctk.CTkFrame(self.sessions_frame)
        buttons_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        buttons_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.new_session_btn = ctk.CTkButton(
            buttons_frame,
            text="➕ New",
            height=32,
            command=self._create_new_session
        )
        self.new_session_btn.grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        
        self.export_btn = ctk.CTkButton(
            buttons_frame,
            text="📤 Export",
            height=32,
            command=self._export_current_session,
            state="disabled"
        )
        self.export_btn.grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        
        # Дополнительные кнопки
        buttons_frame2 = ctk.CTkFrame(self.sessions_frame)
        buttons_frame2.grid(row=3, column=0, padx=5, pady=5, sticky="ew")
        buttons_frame2.grid_columnconfigure((0, 1), weight=1)
        
        self.import_btn = ctk.CTkButton(
            buttons_frame2,
            text="📥 Import",
            height=32,
            command=self._import_session
        )
        self.import_btn.grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        
        self.clear_btn = ctk.CTkButton(
            buttons_frame2,
            text="🗑️ Clear",
            height=32,
            command=self._clear_current_session,
            state="disabled",
            fg_color="#c42b1c",
            hover_color="#a12318"
        )
        self.clear_btn.grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        
        # Статистика
        self.stats_label = ctk.CTkLabel(
            self.sessions_frame,
            text="0 sessions",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.stats_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
    
    def _create_chat_panel(self):
        """Создание панели чата"""
        self.chat_frame = ctk.CTkFrame(self)
        self.chat_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.chat_frame.grid_columnconfigure(0, weight=1)
        self.chat_frame.grid_rowconfigure(1, weight=1)
        
        # Заголовок с информацией о сессии
        header_frame = ctk.CTkFrame(self.chat_frame, height=50)
        header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        header_frame.grid_columnconfigure(1, weight=1)
        
        self.session_title_label = ctk.CTkLabel(
            header_frame,
            text="No session selected",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.session_title_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.session_info_label = ctk.CTkLabel(
            header_frame,
            text="Create or select a session to start",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.session_info_label.grid(row=0, column=1, padx=10, pady=10, sticky="e")
        
        # История чата
        chat_container = ctk.CTkFrame(self.chat_frame)
        chat_container.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        chat_container.grid_columnconfigure(0, weight=1)
        chat_container.grid_rowconfigure(0, weight=1)
        
        self.chat_history = ctk.CTkTextbox(
            chat_container,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            wrap="word"
        )
        self.chat_history.grid(row=0, column=0, sticky="nsew")

        # Получаем доступ к внутреннему Text widget для настройки тегов
        # CTkTextbox оборачивает tkinter.Text, доступ через ._textbox
        self._text_widget = self.chat_history._textbox

        # Настройка тегов для стилизации сообщений
        self._text_widget.tag_configure(
            "user",
            foreground="#4ec9b0",
            font=("Segoe UI", 12, "bold")
        )
        self._text_widget.tag_configure(
            "assistant",
            foreground="#569cd6",
            font=("Segoe UI", 12, "bold")
        )
        self._text_widget.tag_configure(
            "system",
            foreground="#888888",
            font=("Segoe UI", 11, "italic")
        )
        self._text_widget.tag_configure(
            "timestamp",
            foreground="#666666",
            font=("Segoe UI", 10)
        )
        
        # Показываем приветственное сообщение
        self._show_welcome_message()
        
        # Поле ввода
        input_frame = ctk.CTkFrame(self.chat_frame)
        input_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        input_frame.grid_columnconfigure(0, weight=1)
        
        self.chat_input = ctk.CTkEntry(
            input_frame,
            placeholder_text="Type your question... (Enter to send)",
            height=40,
            font=ctk.CTkFont(size=12)
        )
        self.chat_input.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.chat_input.bind("<Return>", self._send_message)
        self.chat_input.bind("<Shift-Return>", lambda e: "break")  # Разрешить перенос строки
        
        self.send_btn = ctk.CTkButton(
            input_frame,
            text="Send",
            width=80,
            height=40,
            command=self._send_message
        )
        self.send_btn.grid(row=0, column=1, padx=5, pady=5)
        
        # Панель источников
        sources_frame = ctk.CTkFrame(self.chat_frame)
        sources_frame.grid(row=3, column=0, sticky="ew", padx=5, pady=5)
        sources_frame.grid_columnconfigure(0, weight=1)
        
        sources_header = ctk.CTkLabel(
            sources_frame,
            text="📎 Sources:",
            font=ctk.CTkFont(size=11, weight="bold")
        )
        sources_header.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.sources_display = ctk.CTkLabel(
            sources_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#4a9eff",
            wraplength=800,
            justify="left"
        )
        self.sources_display.grid(row=1, column=0, padx=10, pady=5, sticky="w")
    
    def _show_welcome_message(self):
        """Показ приветственного сообщения"""
        self.chat_history.configure(state="normal")
        self.chat_history.delete("0.0", "end")
        
        welcome = """Welcome to OpenKB Chat! 🎉

This chat uses your compiled knowledge base to answer questions.

To get started:
1. Create a new session with "➕ New" button
2. Type your question in the input field
3. Press Enter or click "Send"

The assistant will search through your wiki and provide grounded answers with source citations.

Tips:
• Use specific questions for better results
• Check the Sources section to see where answers come from
• Export sessions to save important conversations
"""
        self.chat_history.insert("0.0", welcome)
        self.chat_history.configure(state="disabled")
    
    def refresh_sessions(self):
        """Обновление списка сессий"""
        # Очищаем список
        for widget in self.sessions_list.winfo_children():
            widget.destroy()
        
        session_service = self._get_session_service()
        if not session_service:
            return
        
        sessions = session_service.list_sessions()
        
        for session in sessions:
            self._create_session_item(session)
        
        # Обновляем статистику
        self.stats_label.configure(text=f"{len(sessions)} sessions")
        
        logger.info(f"Sessions refreshed: {len(sessions)} items")
    
    def _create_session_item(self, session):
        """Создание элемента сессии в списке"""
        item_frame = ctk.CTkFrame(self.sessions_list, height=60)
        item_frame.grid(sticky="ew", padx=2, pady=2)
        item_frame.grid_columnconfigure(0, weight=1)
        
        # Название сессии
        title_label = ctk.CTkLabel(
            item_frame,
            text=session.title,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        )
        title_label.grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")
        
        # Метаданные
        msg_count = len(session.messages)
        date_str = session.updated_at.strftime("%m/%d %H:%M")
        
        meta_label = ctk.CTkLabel(
            item_frame,
            text=f"{msg_count} messages • {date_str}",
            font=ctk.CTkFont(size=10),
            text_color="gray",
            anchor="w"
        )
        meta_label.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="w")
        
        # Кнопка удаления
        delete_btn = ctk.CTkButton(
            item_frame,
            text="🗑️",
            width=30,
            height=30,
            fg_color="transparent",
            text_color="#c42b1c",
            hover_color="#3c3c3c",
            command=lambda s=session: self._delete_session(s.id)
        )
        delete_btn.grid(row=0, column=1, rowspan=2, padx=5, pady=5)
        
        # Привязываем клик для выбора сессии
        def on_click(event, s=session):
            self._select_session(s)
        
        item_frame.bind("<Button-1>", on_click)
        title_label.bind("<Button-1>", on_click)
        meta_label.bind("<Button-1>", on_click)
        
        # Подсветка текущей сессии
        if self._current_session and self._current_session.id == session.id:
            item_frame.configure(fg_color="#1f6aa5")
    
    def _create_new_session(self):
        """Создание новой сессии"""
        session_service = self._get_session_service()
        if not session_service:
            return
        
        session = session_service.create_session()
        self._current_session = session
        
        # Обновляем UI
        self.refresh_sessions()
        self._update_session_header()
        self._clear_chat()
        self._enable_chat()
        
        logger.info(f"Created new session: {session.id}")
    
    def _select_session(self, session):
        """Выбор сессии"""
        self._current_session = session
        
        # Обновляем UI
        self.refresh_sessions()
        self._update_session_header()
        self._load_session_messages()
        self._enable_chat()
        
        logger.info(f"Selected session: {session.id}")
    
    def _delete_session(self, session_id: str):
        """Удаление сессии"""
        session_service = self._get_session_service()
        if not session_service:
            return
        
        session_service.delete_session(session_id)
        
        # Если удалили текущую сессию
        if self._current_session and self._current_session.id == session_id:
            self._current_session = None
            self._disable_chat()
            self._show_welcome_message()
        
        self.refresh_sessions()
        
        logger.info(f"Deleted session: {session_id}")
    
    def _update_session_header(self):
        """Обновление заголовка сессии"""
        if self._current_session:
            self.session_title_label.configure(text=self._current_session.title)
            msg_count = len(self._current_session.messages)
            created = self._current_session.created_at.strftime("%Y-%m-%d %H:%M")
            self.session_info_label.configure(text=f"{msg_count} messages • Created: {created}")
        else:
            self.session_title_label.configure(text="No session selected")
            self.session_info_label.configure(text="Create or select a session to start")
    
    def _load_session_messages(self):
        """Загрузка сообщений сессии"""
        if not self._current_session:
            return
        
        self.chat_history.configure(state="normal")
        self.chat_history.delete("0.0", "end")
        
        for msg in self._current_session.messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")
            sources = msg.get("sources", [])
            
            # Форматируем сообщение
            self._append_message(role, content, timestamp, sources)
        
        self.chat_history.configure(state="disabled")
        self.chat_history.see("end")
    
    def _append_message(self, role: str, content: str, timestamp: str = "", sources: list = None):
        """Добавление сообщения в чат"""
        self.chat_history.configure(state="normal")
        
        # Временная метка
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime("%H:%M:%S")
            except:
                time_str = timestamp
            self.chat_history.insert("end", f"[{time_str}] ", "timestamp")
        
        # Роль
        role_display = {
            "user": "👤 You",
            "assistant": "🤖 Assistant",
            "system": "⚙️ System"
        }.get(role, role)
        
        self.chat_history.insert("end", f"{role_display}\n", role)
        
        # Контент
        self.chat_history.insert("end", f"{content}\n\n")
        
        # Источники
        if sources:
            sources_text = "📎 Sources: " + ", ".join(sources[:5])
            if len(sources) > 5:
                sources_text += f" (+{len(sources) - 5} more)"
            self.chat_history.insert("end", f"{sources_text}\n\n", "system")
        
        self.chat_history.configure(state="disabled")
        self.chat_history.see("end")
    
    def _clear_chat(self):
        """Очистка чата"""
        self.chat_history.configure(state="normal")
        self.chat_history.delete("0.0", "end")
        self.chat_history.configure(state="disabled")
        self.sources_display.configure(text="")
    
    def _enable_chat(self):
        """Активация чата"""
        self.chat_input.configure(state="normal")
        self.send_btn.configure(state="normal")
        self.export_btn.configure(state="normal")
        self.clear_btn.configure(state="normal")
    
    def _disable_chat(self):
        """Деактивация чата"""
        self.chat_input.configure(state="disabled")
        self.send_btn.configure(state="disabled")
        self.export_btn.configure(state="disabled")
        self.clear_btn.configure(state="disabled")
    
    def _send_message(self, event=None):
        """Отправка сообщения"""
        message = self.chat_input.get().strip()
        if not message or self._is_generating:
            return
        
        if not self._current_session:
            self._create_new_session()
        
        # Очищаем ввод
        self.chat_input.delete(0, "end")
        
        # Показываем сообщение пользователя
        self._append_message("user", message)
        
        # Сохраняем в сессию
        session_service = self._get_session_service()
        if session_service:
            session_service.add_message(
                self._current_session.id,
                "user",
                message
            )
        
        # Блокируем ввод
        self._is_generating = True
        self.send_btn.configure(state="disabled")
        self.chat_input.configure(placeholder_text="Generating response...")
        
        # Запускаем генерацию в отдельном потоке
        def generate():
            try:
                chat_service = self._get_chat_service()
                if not chat_service:
                    raise ValueError("Chat service not available")
                
                response = chat_service.send_message(message)
                
                # Обновляем UI в main thread
                self.after(0, lambda: self._handle_response(response))
                
            except Exception as e:
                logger.error(f"Error generating response: {e}")
                self.after(0, lambda: self._handle_error(str(e)))
        
        threading.Thread(target=generate, daemon=True).start()
    
    def _handle_response(self, response):
        """Обработка ответа от ChatService"""
        # Показываем ответ
        self._append_message("assistant", response.content, sources=response.sources)
        
        # Обновляем источники
        if response.sources:
            sources_text = " • ".join(response.sources[:5])
            if len(response.sources) > 5:
                sources_text += f" • +{len(response.sources) - 5} more"
            self.sources_display.configure(text=sources_text)
        else:
            self.sources_display.configure(text="No sources")
        
        # Сохраняем в сессию
        session_service = self._get_session_service()
        if session_service and self._current_session:
            session_service.add_message(
                self._current_session.id,
                "assistant",
                response.content,
                response.sources
            )
            # Обновляем список сессий
            self.refresh_sessions()
        
        # Разблокируем ввод
        self._is_generating = False
        self.send_btn.configure(state="normal")
        self.chat_input.configure(placeholder_text="Type your question... (Enter to send)")
    
    def _handle_error(self, error: str):
        """Обработка ошибки"""
        self._append_message("system", f"❌ Error: {error}")
        
        # Разблокируем ввод
        self._is_generating = False
        self.send_btn.configure(state="normal")
        self.chat_input.configure(placeholder_text="Type your question... (Enter to send)")
    
    def _export_current_session(self):
        """Экспорт текущей сессии"""
        if not self._current_session:
            return
        
        # Выбор файла
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[
                ("JSON files", "*.json"),
                ("Markdown files", "*.md"),
                ("Text files", "*.txt")
            ],
            title="Export Session"
        )
        
        if not file_path:
            return
        
        session_service = self._get_session_service()
        if not session_service:
            return
        
        # Определяем формат
        ext = Path(file_path).suffix.lower()
        format_map = {".json": "json", ".md": "markdown", ".txt": "txt"}
        format_type = format_map.get(ext, "json")
        
        # Экспортируем
        content = session_service.export_session(self._current_session.id, format_type)
        
        if content:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"Session exported to: {file_path}")
            except Exception as e:
                logger.error(f"Error exporting session: {e}")
    
    def _import_session(self):
        """Импорт сессии из файла"""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")],
            title="Import Session"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            session_service = self._get_session_service()
            if session_service:
                session = session_service.import_session(content, "json")
                if session:
                    self._current_session = session
                    self.refresh_sessions()
                    self._update_session_header()
                    self._load_session_messages()
                    self._enable_chat()
                    logger.info(f"Session imported: {session.id}")
        except Exception as e:
            logger.error(f"Error importing session: {e}")
    
    def _clear_current_session(self):
        """Очистка текущей сессии"""
        if not self._current_session:
            return
        
        # Очищаем сообщения в сессии
        self._current_session.messages = []
        
        session_service = self._get_session_service()
        if session_service:
            session_service.update_session(self._current_session)
        
        self._clear_chat()
        self.refresh_sessions()
        
        logger.info(f"Session cleared: {self._current_session.id}")
    
    def get_current_session(self):
        """Получение текущей сессии"""
        return self._current_session
