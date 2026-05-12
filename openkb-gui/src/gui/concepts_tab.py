"""
Concepts Tab - Вкладка управления концептами
Список концептов с backlinks, metadata и preview
"""

import customtkinter as ctk
from tkinter import ttk
from typing import Callable, Optional
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ConceptsTab(ctk.CTkFrame):
    """Вкладка управления концептами с списком, preview и backlinks"""
    
    def __init__(self, master, wiki_service_getter: Callable):
        """
        Инициализация Concepts Tab
        
        Args:
            master: Родительский виджет
            wiki_service_getter: Функция для получения WikiService
        """
        super().__init__(master)
        
        self._get_wiki_service = wiki_service_getter
        self._current_concept = None
        self._concepts_data = []
        
        # Настройка grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Создаём UI
        self._create_list_panel()
        self._create_detail_panel()
        
        logger.info("ConceptsTab инициализирован")
    
    def _create_list_panel(self):
        """Создание панели со списком концептов"""
        self.list_frame = ctk.CTkFrame(self, width=350)
        self.list_frame.grid(row=0, column=0, sticky="ns", padx=(10, 5), pady=10)
        self.list_frame.grid_propagate(False)
        self.list_frame.grid_rowconfigure(2, weight=1)
        
        # Заголовок
        title_label = ctk.CTkLabel(
            self.list_frame,
            text="💡 Concepts",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        # Поиск
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._on_search_change)
        
        self.search_entry = ctk.CTkEntry(
            self.list_frame,
            placeholder_text="🔍 Filter concepts...",
            textvariable=self.search_var,
            height=32
        )
        self.search_entry.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        # Таблица концептов
        table_container = ctk.CTkFrame(self.list_frame)
        table_container.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
        table_container.grid_columnconfigure(0, weight=1)
        table_container.grid_rowconfigure(0, weight=1)
        
        # Стилизация
        style = ttk.Style()
        style.configure(
            "Concepts.Treeview",
            background="#2b2b2b",
            foreground="white",
            fieldbackground="#2b2b2b",
            rowheight=32,
            font=('Segoe UI', 10)
        )
        style.configure(
            "Concepts.Treeview.Heading",
            background="#3b3b3b",
            foreground="white",
            font=('Segoe UI', 10, 'bold')
        )
        style.map("Concepts.Treeview", background=[('selected', '#1f6aa5')])
        
        # Treeview с колонками
        columns = ("name", "backlinks", "words")
        self.concepts_tree = ttk.Treeview(
            table_container,
            style="Concepts.Treeview",
            columns=columns,
            show="headings",
            selectmode="browse"
        )
        self.concepts_tree.grid(row=0, column=0, sticky="nsew")
        
        # Заголовки колонок
        self.concepts_tree.heading("name", text="Name")
        self.concepts_tree.heading("backlinks", text="Links")
        self.concepts_tree.heading("words", text="Words")
        
        self.concepts_tree.column("name", width=180, minwidth=100)
        self.concepts_tree.column("backlinks", width=60, minwidth=50, anchor="center")
        self.concepts_tree.column("words", width=60, minwidth=50, anchor="center")
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(
            table_container,
            orient="vertical",
            command=self.concepts_tree.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.concepts_tree.configure(yscrollcommand=scrollbar.set)
        
        # События
        self.concepts_tree.bind("<<TreeviewSelect>>", self._on_concept_select)
        self.concepts_tree.bind("<Double-1>", self._on_concept_double_click)
        
        # Панель действий
        actions_frame = ctk.CTkFrame(self.list_frame)
        actions_frame.grid(row=3, column=0, padx=5, pady=5, sticky="ew")
        
        self.refresh_btn = ctk.CTkButton(
            actions_frame,
            text="🔄 Refresh",
            width=100,
            command=self.refresh_concepts
        )
        self.refresh_btn.grid(row=0, column=0, padx=5, pady=5)
        
        self.delete_btn = ctk.CTkButton(
            actions_frame,
            text="🗑️ Delete",
            width=100,
            command=self._delete_selected_concept,
            state="disabled",
            fg_color="#c42b1c",
            hover_color="#a12318"
        )
        self.delete_btn.grid(row=0, column=1, padx=5, pady=5)
        
        # Статистика
        self.stats_label = ctk.CTkLabel(
            self.list_frame,
            text="0 concepts",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.stats_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
    
    def _create_detail_panel(self):
        """Создание панели детальной информации"""
        self.detail_frame = ctk.CTkFrame(self)
        self.detail_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.detail_frame.grid_columnconfigure(0, weight=1)
        self.detail_frame.grid_rowconfigure(2, weight=1)
        
        # Заголовок
        header_frame = ctk.CTkFrame(self.detail_frame, height=60)
        header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        header_frame.grid_columnconfigure(1, weight=1)
        
        self.concept_title = ctk.CTkLabel(
            header_frame,
            text="Select a concept to view details",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.concept_title.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.concept_path = ctk.CTkLabel(
            header_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.concept_path.grid(row=0, column=1, padx=10, pady=10, sticky="e")
        
        # Метаданные
        meta_frame = ctk.CTkFrame(self.detail_frame)
        meta_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        self.meta_created = ctk.CTkLabel(
            meta_frame,
            text="Created: -",
            font=ctk.CTkFont(size=11),
            text_color="#888888"
        )
        self.meta_created.grid(row=0, column=0, padx=15, pady=5, sticky="w")
        
        self.meta_modified = ctk.CTkLabel(
            meta_frame,
            text="Modified: -",
            font=ctk.CTkFont(size=11),
            text_color="#888888"
        )
        self.meta_modified.grid(row=0, column=1, padx=15, pady=5, sticky="w")
        
        self.meta_words = ctk.CTkLabel(
            meta_frame,
            text="Words: -",
            font=ctk.CTkFont(size=11),
            text_color="#888888"
        )
        self.meta_words.grid(row=0, column=2, padx=15, pady=5, sticky="w")
        
        self.meta_links = ctk.CTkLabel(
            meta_frame,
            text="Backlinks: -",
            font=ctk.CTkFont(size=11),
            text_color="#888888"
        )
        self.meta_links.grid(row=0, column=3, padx=15, pady=5, sticky="w")
        
        # Preview
        preview_container = ctk.CTkFrame(self.detail_frame)
        preview_container.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        preview_container.grid_columnconfigure(0, weight=1)
        preview_container.grid_rowconfigure(0, weight=1)
        
        self.preview_text = ctk.CTkTextbox(
            preview_container,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word"
        )
        self.preview_text.grid(row=0, column=0, sticky="nsew")
        
        # Backlinks секция
        backlinks_frame = ctk.CTkFrame(self.detail_frame)
        backlinks_frame.grid(row=3, column=0, sticky="ew", padx=5, pady=5)
        backlinks_frame.grid_columnconfigure(0, weight=1)
        
        backlinks_header = ctk.CTkLabel(
            backlinks_frame,
            text="📎 Backlinks (pages that link to this concept)",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        backlinks_header.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        self.backlinks_list = ctk.CTkScrollableFrame(
            backlinks_frame,
            height=120
        )
        self.backlinks_list.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        
        # Placeholder для backlinks
        self.backlinks_placeholder = ctk.CTkLabel(
            self.backlinks_list,
            text="No backlinks found",
            text_color="gray"
        )
        self.backlinks_placeholder.grid(row=0, column=0, padx=10, pady=5, sticky="w")
    
    def refresh_concepts(self):
        """Обновление списка концептов"""
        # Очищаем таблицу
        for item in self.concepts_tree.get_children():
            self.concepts_tree.delete(item)
        
        wiki_service = self._get_wiki_service()
        if not wiki_service:
            return
        
        # Получаем список концептов
        self._concepts_data = wiki_service.list_concepts()
        
        # Заполняем таблицу
        for concept in self._concepts_data:
            self.concepts_tree.insert(
                "",
                "end",
                values=(
                    concept["name"],
                    concept["backlinks_count"],
                    concept["word_count"]
                ),
                iid=concept["path"]
            )
        
        # Обновляем статистику
        total_backlinks = sum(c["backlinks_count"] for c in self._concepts_data)
        total_words = sum(c["word_count"] for c in self._concepts_data)
        
        self.stats_label.configure(
            text=f"{len(self._concepts_data)} concepts • {total_backlinks} links • {total_words} words"
        )
        
        logger.info(f"Concepts refreshed: {len(self._concepts_data)} items")
    
    def _on_concept_select(self, event):
        """Обработка выбора концепта"""
        selection = self.concepts_tree.selection()
        if not selection:
            return
        
        path = selection[0]
        self._load_concept(path)
    
    def _on_concept_double_click(self, event):
        """Обработка двойного клика"""
        # Можно добавить действие (например, редактирование)
        pass
    
    def _load_concept(self, relative_path: str):
        """Загрузка информации о концепте"""
        wiki_service = self._get_wiki_service()
        if not wiki_service:
            return
        
        page = wiki_service.get_page(relative_path)
        if not page:
            self._show_error(f"Could not load: {relative_path}")
            return
        
        self._current_concept = page
        
        # Обновляем UI
        self.concept_title.configure(text=page.title)
        self.concept_path.configure(text=f"📁 {relative_path}")
        
        # Метаданные
        try:
            stat = page.path.stat()
            created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M")
            modified = page.modified_time.strftime("%Y-%m-%d %H:%M")
            
            self.meta_created.configure(text=f"Created: {created}")
            self.meta_modified.configure(text=f"Modified: {modified}")
        except Exception:
            self.meta_created.configure(text="Created: -")
            self.meta_modified.configure(text=f"Modified: {page.modified_time.strftime('%Y-%m-%d %H:%M')}")
        
        self.meta_words.configure(text=f"Words: {page.word_count}")
        self.meta_links.configure(text=f"Backlinks: {len(page.backlinks)}")
        
        # Preview
        self.preview_text.configure(state="normal")
        self.preview_text.delete("0.0", "end")
        self.preview_text.insert("0.0", page.content)
        self.preview_text.configure(state="disabled")
        
        # Backlinks
        self._display_backlinks(page.backlinks)
        
        # Активируем кнопку удаления
        self.delete_btn.configure(state="normal")
        
        logger.debug(f"Loaded concept: {relative_path}")
    
    def _display_backlinks(self, backlinks: list):
        """Отображение списка backlinks"""
        # Очищаем предыдущие backlinks
        for widget in self.backlinks_list.winfo_children():
            widget.destroy()
        
        if not backlinks:
            placeholder = ctk.CTkLabel(
                self.backlinks_list,
                text="No backlinks found",
                text_color="gray"
            )
            placeholder.grid(row=0, column=0, padx=10, pady=5, sticky="w")
            return
        
        # Показываем backlinks
        for i, link_path in enumerate(backlinks[:20]):  # Максимум 20
            link_label = ctk.CTkLabel(
                self.backlinks_list,
                text=f"📄 {link_path}",
                text_color="#4a9eff",
                cursor="hand2"
            )
            link_label.grid(row=i, column=0, padx=10, pady=2, sticky="w")
            
            # Привязываем клик
            link_label.bind(
                "<Button-1>",
                lambda e, p=link_path: self._on_backlink_click(p)
            )
        
        if len(backlinks) > 20:
            more_label = ctk.CTkLabel(
                self.backlinks_list,
                text=f"... and {len(backlinks) - 20} more",
                text_color="gray"
            )
            more_label.grid(row=20, column=0, padx=10, pady=2, sticky="w")
    
    def _on_backlink_click(self, path: str):
        """Обработка клика по backlink"""
        # Можно реализовать переход к файлу
        logger.info(f"Backlink clicked: {path}")
    
    def _on_search_change(self, *args):
        """Обработка изменения поискового запроса"""
        query = self.search_var.get().strip().lower()
        
        # Фильтруем концепты
        for item in self.concepts_tree.get_children():
            values = self.concepts_tree.item(item, "values")
            if values:
                name = values[0].lower()
                if query in name:
                    self.concepts_tree.item(item, open=True)
                    # Показываем элемент
                    self.concepts_tree.move(item, "", "end")
                else:
                    # Скрываем элемент (перемещаем в конец)
                    pass
    
    def _delete_selected_concept(self):
        """Удаление выбранного концепта"""
        selection = self.concepts_tree.selection()
        if not selection:
            return
        
        path = selection[0]
        
        # Подтверждение
        dialog = ctk.CTkInputDialog(
            text=f"Delete concept '{path}'?\nType 'DELETE' to confirm:",
            title="Confirm Delete"
        )
        
        confirmation = dialog.get_input()
        if confirmation != "DELETE":
            return
        
        wiki_service = self._get_wiki_service()
        if not wiki_service:
            return
        
        # Удаляем файл
        full_path = wiki_service.wiki_path / path
        if full_path.exists():
            try:
                full_path.unlink()
                logger.info(f"Deleted concept: {path}")
                self.refresh_concepts()
                self._clear_detail_panel()
            except Exception as e:
                logger.error(f"Error deleting concept: {e}")
    
    def _clear_detail_panel(self):
        """Очистка панели детальной информации"""
        self.concept_title.configure(text="Select a concept to view details")
        self.concept_path.configure(text="")
        self.meta_created.configure(text="Created: -")
        self.meta_modified.configure(text="Modified: -")
        self.meta_words.configure(text="Words: -")
        self.meta_links.configure(text="Backlinks: -")
        
        self.preview_text.configure(state="normal")
        self.preview_text.delete("0.0", "end")
        self.preview_text.configure(state="disabled")
        
        # Очищаем backlinks
        for widget in self.backlinks_list.winfo_children():
            widget.destroy()
        
        self.backlinks_placeholder = ctk.CTkLabel(
            self.backlinks_list,
            text="No backlinks found",
            text_color="gray"
        )
        self.backlinks_placeholder.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.delete_btn.configure(state="disabled")
    
    def _show_error(self, message: str):
        """Показ сообщения об ошибке"""
        self.concept_title.configure(text="Error")
        self.preview_text.configure(state="normal")
        self.preview_text.delete("0.0", "end")
        self.preview_text.insert("0.0", f"❌ {message}")
        self.preview_text.configure(state="disabled")
    
    def get_selected_concept(self):
        """Получение выбранного концепта"""
        return self._current_concept
