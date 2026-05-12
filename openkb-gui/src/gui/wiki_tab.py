"""
Wiki Tab - Вкладка Wiki Browser с tree view и навигацией по wikilinks
Полноценный просмотр wiki с поиском и навигацией
"""

import customtkinter as ctk
from tkinter import ttk
from typing import Optional, Callable
from pathlib import Path
import logging
import re
import threading

logger = logging.getLogger(__name__)


class WikiTab(ctk.CTkFrame):
    """Вкладка Wiki Browser с tree view, поиском и wikilinks навигацией"""
    
    def __init__(self, master, wiki_service_getter: Callable, on_open_file: Optional[Callable] = None):
        """
        Инициализация Wiki Tab
        
        Args:
            master: Родительский виджет
            wiki_service_getter: Функция для получения WikiService
            on_open_file: Callback при открытии файла (опционально)
        """
        super().__init__(master)
        
        self._get_wiki_service = wiki_service_getter
        self._on_open_file = on_open_file
        self._current_page = None
        self._history = []  # История навигации
        self._history_index = -1
        
        # Настройка grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Создаём UI
        self._create_tree_panel()
        self._create_preview_panel()
        
        logger.info("WikiTab инициализирован")
    
    def _create_tree_panel(self):
        """Создание панели с деревом файлов"""
        self.tree_frame = ctk.CTkFrame(self, width=320)
        self.tree_frame.grid(row=0, column=0, sticky="ns", padx=(10, 5), pady=10)
        self.tree_frame.grid_propagate(False)
        self.tree_frame.grid_rowconfigure(2, weight=1)
        
        # Заголовок
        title_label = ctk.CTkLabel(
            self.tree_frame, 
            text="📁 Wiki Files", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        # Поиск
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._on_search_change)
        
        self.search_entry = ctk.CTkEntry(
            self.tree_frame,
            placeholder_text="🔍 Search wiki...",
            textvariable=self.search_var,
            height=32
        )
        self.search_entry.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        # Tree view с использованием ttk.Treeview (CustomTkinter не имеет своего)
        tree_container = ctk.CTkFrame(self.tree_frame)
        tree_container.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
        tree_container.grid_columnconfigure(0, weight=1)
        tree_container.grid_rowconfigure(0, weight=1)
        
        # Стилизация treeview
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            "Wiki.Treeview",
            background="#2b2b2b",
            foreground="white",
            fieldbackground="#2b2b2b",
            rowheight=28,
            font=('Segoe UI', 10)
        )
        style.configure(
            "Wiki.Treeview.Heading",
            background="#3b3b3b",
            foreground="white",
            font=('Segoe UI', 10, 'bold')
        )
        style.map("Wiki.Treeview", background=[('selected', '#1f6aa5')])
        
        self.tree = ttk.Treeview(
            tree_container,
            style="Wiki.Treeview",
            show="tree",
            selectmode="browse"
        )
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Привязка событий
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Button-3>", self._show_context_menu)
        
        # Кнопки навигации
        nav_frame = ctk.CTkFrame(self.tree_frame)
        nav_frame.grid(row=3, column=0, padx=5, pady=5, sticky="ew")
        
        self.back_btn = ctk.CTkButton(
            nav_frame, text="◀", width=40, 
            command=self._go_back, state="disabled"
        )
        self.back_btn.grid(row=0, column=0, padx=2, pady=2)
        
        self.forward_btn = ctk.CTkButton(
            nav_frame, text="▶", width=40,
            command=self._go_forward, state="disabled"
        )
        self.forward_btn.grid(row=0, column=1, padx=2, pady=2)
        
        self.refresh_btn = ctk.CTkButton(
            nav_frame, text="🔄", width=40,
            command=self.refresh_tree
        )
        self.refresh_btn.grid(row=0, column=2, padx=2, pady=2)
        
        # Статистика
        self.stats_label = ctk.CTkLabel(
            self.tree_frame,
            text="0 pages",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.stats_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
    
    def _create_preview_panel(self):
        """Создание панели предпросмотра"""
        self.preview_frame = ctk.CTkFrame(self)
        self.preview_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.preview_frame.grid_columnconfigure(0, weight=1)
        self.preview_frame.grid_rowconfigure(2, weight=1)
        
        # Заголовок с breadcrumbs
        header_frame = ctk.CTkFrame(self.preview_frame, height=50)
        header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        header_frame.grid_columnconfigure(1, weight=1)
        
        self.page_title = ctk.CTkLabel(
            header_frame,
            text="Select a file to preview",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.page_title.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        # Метаданные
        self.metadata_label = ctk.CTkLabel(
            header_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.metadata_label.grid(row=0, column=1, padx=10, pady=10, sticky="e")
        
        # Breadcrumbs
        self.breadcrumbs = ctk.CTkLabel(
            self.preview_frame,
            text="",
            font=ctk.CTkFont(size=10),
            text_color="#888888"
        )
        self.breadcrumbs.grid(row=1, column=0, padx=15, pady=(0, 5), sticky="w")
        
        # Preview с подсветкой markdown
        preview_container = ctk.CTkFrame(self.preview_frame)
        preview_container.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        preview_container.grid_columnconfigure(0, weight=1)
        preview_container.grid_rowconfigure(0, weight=1)
        
        self.preview_text = ctk.CTkTextbox(
            preview_container,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word"
        )
        self.preview_text.grid(row=0, column=0, sticky="nsew")
        
        # Привязка кликов по wikilinks
        self.preview_text.bind("<Button-1>", self._on_preview_click)
        self.preview_text.bind("<Motion>", self._on_preview_motion)
        
        # Панель с wikilinks
        links_frame = ctk.CTkFrame(self.preview_frame)
        links_frame.grid(row=3, column=0, sticky="ew", padx=5, pady=5)
        links_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            links_frame,
            text="Links:",
            font=ctk.CTkFont(size=11, weight="bold")
        ).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.links_display = ctk.CTkLabel(
            links_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#4a9eff",
            wraplength=800
        )
        self.links_display.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        # Backlinks
        backlinks_frame = ctk.CTkFrame(self.preview_frame)
        backlinks_frame.grid(row=4, column=0, sticky="ew", padx=5, pady=5)
        backlinks_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            backlinks_frame,
            text="Backlinks:",
            font=ctk.CTkFont(size=11, weight="bold")
        ).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.backlinks_display = ctk.CTkLabel(
            backlinks_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#4a9eff",
            wraplength=800
        )
        self.backlinks_display.grid(row=0, column=1, padx=10, pady=5, sticky="w")
    
    def refresh_tree(self):
        """Обновление дерева файлов"""
        # Очищаем дерево
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        wiki_service = self._get_wiki_service()
        if not wiki_service:
            return
        
        tree_data = wiki_service.get_tree()
        self._populate_tree("", tree_data.get("children", []))
        
        # Обновляем статистику
        stats = wiki_service.get_statistics()
        self.stats_label.configure(
            text=f"{stats['total_pages']} pages • {stats['total_words']} words"
        )
        
        logger.info("Wiki tree refreshed")
    
    def _populate_tree(self, parent: str, children: list):
        """Заполнение дерева данными"""
        # Иконки для разных типов
        icons = {
            "concepts": "💡",
            "summaries": "📄",
            "explorations": "🔍",
            "reports": "📊",
            "sources": "📑",
            "directory": "📁",
            "file": "📝"
        }
        
        for child in children:
            child_type = child.get("type", "file")
            child_name = child.get("name", "Unknown")
            child_path = child.get("path", "")
            
            if child_type == "directory":
                # Определяем иконку для папки
                icon = icons.get(child_name.lower(), icons["directory"])
                display_name = f"{icon} {child_name}"
                
                item_id = self.tree.insert(
                    parent, "end",
                    text=display_name,
                    values=("", child_name),
                    open=False
                )
                
                # Рекурсивно добавляем детей
                if "children" in child:
                    self._populate_tree(item_id, child["children"])
            else:
                # Файл
                icon = icons.get("file")
                display_name = f"{icon} {child_name}"
                
                self.tree.insert(
                    parent, "end",
                    text=display_name,
                    values=(child_path, child_name),
                    open=False
                )
    
    def _on_tree_select(self, event):
        """Обработка выбора элемента в дереве"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.tree.item(item, "values")
        
        if len(values) >= 2 and values[0]:
            # Это файл
            file_path = values[0]
            self._load_page(file_path)
    
    def _on_tree_double_click(self, event):
        """Обработка двойного клика"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.tree.item(item, "values")
        
        if len(values) >= 2 and values[0]:
            # Добавляем в историю
            self._add_to_history(values[0])
    
    def _load_page(self, relative_path: str):
        """Загрузка страницы wiki"""
        wiki_service = self._get_wiki_service()
        if not wiki_service:
            return
        
        page = wiki_service.get_page(relative_path)
        if not page:
            self._show_error(f"Could not load: {relative_path}")
            return
        
        self._current_page = page
        
        # Обновляем UI
        self.page_title.configure(text=page.title)
        self.breadcrumbs.configure(text=f"📁 {relative_path}")
        
        # Метаданные
        modified = page.modified_time.strftime("%Y-%m-%d %H:%M")
        self.metadata_label.configure(
            text=f"Modified: {modified} • {page.word_count} words"
        )
        
        # Контент с базовой подсветкой
        self._display_content(page.content)
        
        # Wikilinks
        if page.wikilinks:
            links_text = "  •  ".join(f"[[{link}]]" for link in page.wikilinks[:10])
            if len(page.wikilinks) > 10:
                links_text += f"  •  +{len(page.wikilinks) - 10} more"
            self.links_display.configure(text=links_text)
        else:
            self.links_display.configure(text="None")
        
        # Backlinks
        if page.backlinks:
            backlinks_text = "  •  ".join(page.backlinks[:5])
            if len(page.backlinks) > 5:
                backlinks_text += f"  •  +{len(page.backlinks) - 5} more"
            self.backlinks_display.configure(text=backlinks_text)
        else:
            self.backlinks_display.configure(text="None")
        
        logger.debug(f"Loaded page: {relative_path}")
    
    def _display_content(self, content: str):
        """Отображение контента с базовой подсветкой markdown"""
        self.preview_text.configure(state="normal")
        self.preview_text.delete("0.0", "end")
        
        # Добавляем контент
        self.preview_text.insert("0.0", content)
        
        # Применяем теги для подсветки (базовая реализация)
        self._apply_highlighting(content)
        
        self.preview_text.configure(state="disabled")
    
    def _apply_highlighting(self, content: str):
        """Применение подсветки синтаксиса markdown"""
        # Настраиваем теги
        self.preview_text.tag_configure(
            "heading",
            foreground="#569cd6",  # Голубой
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold")
        )
        self.preview_text.tag_configure(
            "bold",
            foreground="#ce9178",  # Оранжевый
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold")
        )
        self.preview_text.tag_configure(
            "link",
            foreground="#4ec9b0",  # Бирюзовый
            underline=True
        )
        self.preview_text.tag_configure(
            "code",
            foreground="#dcdcaa",  # Жёлтый
            background="#3c3c3c"
        )
        
        lines = content.split('\n')
        offset = 0
        
        for i, line in enumerate(lines):
            # Заголовки
            if line.startswith('# '):
                start = f"{i+1}.0"
                end = f"{i+1}.end"
                self.preview_text.tag_add("heading", start, end)
            elif line.startswith('## '):
                start = f"{i+1}.0"
                end = f"{i+1}.end"
                self.preview_text.tag_add("heading", start, end)
            elif line.startswith('### '):
                start = f"{i+1}.0"
                end = f"{i+1}.end"
                self.preview_text.tag_add("heading", start, end)
            
            # Wikilinks [[...]]
            for match in re.finditer(r'\[\[([^\]]+)\]\]', line):
                start_idx = match.start()
                end_idx = match.end()
                start = f"{i+1}.{start_idx}"
                end = f"{i+1}.{end_idx}"
                self.preview_text.tag_add("link", start, end)
            
            # Bold **...**
            for match in re.finditer(r'\*\*([^*]+)\*\*', line):
                start_idx = match.start()
                end_idx = match.end()
                start = f"{i+1}.{start_idx}"
                end = f"{i+1}.{end_idx}"
                self.preview_text.tag_add("bold", start, end)
            
            # Inline code `...`
            for match in re.finditer(r'`([^`]+)`', line):
                start_idx = match.start()
                end_idx = match.end()
                start = f"{i+1}.{start_idx}"
                end = f"{i+1}.{end_idx}"
                self.preview_text.tag_add("code", start, end)
    
    def _on_preview_click(self, event):
        """Обработка клика по preview"""
        # Получаем позицию клика
        index = self.preview_text.index(f"@{event.x},{event.y}")
        
        # Получаем теги в позиции
        tags = self.preview_text.tag_names(index)
        
        if "link" in tags:
            # Клик по wikilink - находим текст ссылки
            range_start = self.preview_text.tag_prevrange("link", index)
            if range_start:
                link_text = self.preview_text.get(range_start[0], range_start[1])
                # Извлекаем имя из [[...]]
                match = re.match(r'\[\[([^\]]+)\]\]', link_text)
                if match:
                    self._navigate_to_wikilink(match.group(1))
    
    def _on_preview_motion(self, event):
        """Обработка движения мыши над preview"""
        index = self.preview_text.index(f"@{event.x},{event.y}")
        tags = self.preview_text.tag_names(index)
        
        if "link" in tags:
            self.preview_text.configure(cursor="hand2")
        else:
            self.preview_text.configure(cursor="arrow")
    
    def _navigate_to_wikilink(self, link_name: str):
        """Навигация по wikilink"""
        wiki_service = self._get_wiki_service()
        if not wiki_service:
            return
        
        # Ищем файл с таким именем
        wiki_path = wiki_service.wiki_path
        
        # Пробуем разные варианты
        possible_paths = [
            f"concepts/{link_name}.md",
            f"summaries/{link_name}.md",
            f"explorations/{link_name}.md",
            f"sources/{link_name}.md",
            f"{link_name}.md",
        ]
        
        for rel_path in possible_paths:
            full_path = wiki_path / rel_path
            if full_path.exists():
                self._add_to_history(rel_path)
                self._load_page(rel_path)
                return
        
        # Файл не найден
        logger.warning(f"Wikilink target not found: {link_name}")
    
    def _add_to_history(self, path: str):
        """Добавление в историю навигации"""
        # Удаляем всё после текущей позиции
        if self._history_index < len(self._history) - 1:
            self._history = self._history[:self._history_index + 1]
        
        # Добавляем новый путь
        self._history.append(path)
        self._history_index = len(self._history) - 1
        
        self._update_nav_buttons()
    
    def _go_back(self):
        """Переход назад по истории"""
        if self._history_index > 0:
            self._history_index -= 1
            path = self._history[self._history_index]
            self._load_page(path)
            self._update_nav_buttons()
    
    def _go_forward(self):
        """Переход вперёд по истории"""
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            path = self._history[self._history_index]
            self._load_page(path)
            self._update_nav_buttons()
    
    def _update_nav_buttons(self):
        """Обновление состояния кнопок навигации"""
        self.back_btn.configure(
            state="normal" if self._history_index > 0 else "disabled"
        )
        self.forward_btn.configure(
            state="normal" if self._history_index < len(self._history) - 1 else "disabled"
        )
    
    def _on_search_change(self, *args):
        """Обработка изменения поискового запроса"""
        query = self.search_var.get().strip().lower()
        
        if not query:
            # Показываем все элементы
            self._show_all_items()
            return
        
        # Фильтруем дерево
        self._filter_tree(query)
    
    def _show_all_items(self):
        """Показать все элементы дерева"""
        def show_item(item):
            self.tree.item(item, open=True)
            for child in self.tree.get_children(item):
                show_item(child)
        
        for item in self.tree.get_children():
            show_item(item)
    
    def _filter_tree(self, query: str):
        """Фильтрация дерева по запросу"""
        wiki_service = self._get_wiki_service()
        if not wiki_service:
            return
        
        # Ищем в wiki
        results = wiki_service.search(query)
        
        # Собираем пути найденных файлов
        found_paths = set(r["path"] for r in results)
        
        # Показываем/скрываем элементы
        self._filter_items("", found_paths)
    
    def _filter_items(self, parent: str, found_paths: set):
        """Рекурсивная фильтрация элементов"""
        for item in self.tree.get_children(parent):
            values = self.tree.item(item, "values")
            
            if len(values) >= 2 and values[0]:
                # Это файл
                path = values[0]
                if path in found_paths:
                    self.tree.move(item, parent, 0)  # Перемещаем в начало
                    self.tree.item(item, open=True)
                else:
                    # Скрываем (перемещаем в конец)
                    pass
            
            # Рекурсивно обрабатываем детей
            self._filter_items(item, found_paths)
    
    def _show_context_menu(self, event):
        """Показ контекстного меню"""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        
        self.tree.selection_set(item)
        values = self.tree.item(item, "values")
        
        if len(values) < 2 or not values[0]:
            return
        
        file_path = values[0]
        
        # Создаём контекстное меню
        menu = ctk.CTkContextMenu(self)
        menu.add_command(label="Open", command=lambda: self._load_page(file_path))
        menu.add_command(label="Copy Path", command=lambda: self._copy_path(file_path))
        menu.tk_popup(event.x_root, event.y_root)
    
    def _copy_path(self, path: str):
        """Копирование пути в буфер обмена"""
        self.clipboard_clear()
        self.clipboard_append(path)
    
    def _show_error(self, message: str):
        """Показ сообщения об ошибке"""
        self.preview_text.configure(state="normal")
        self.preview_text.delete("0.0", "end")
        self.preview_text.insert("0.0", f"❌ {message}")
        self.preview_text.configure(state="disabled")
    
    def get_current_page(self):
        """Получение текущей страницы"""
        return self._current_page
