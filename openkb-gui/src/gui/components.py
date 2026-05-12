"""
UI Components - Общие компоненты интерфейса
Виджеты, используемые в разных вкладках
"""

import customtkinter as ctk
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class StatusBar(ctk.CTkFrame):
    """Статус-бар для отображения информации о приложении"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, height=30, **kwargs)
        
        self.grid_columnconfigure(1, weight=1)
        
        # Workspace info
        self.workspace_label = ctk.CTkLabel(
            self,
            text="📁 Workspace: -",
            font=ctk.CTkFont(size=11)
        )
        self.workspace_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # Статистика
        self.stats_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.stats_label.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        # API статус
        self.api_status = ctk.CTkLabel(
            self,
            text="🔴 API: Not configured",
            font=ctk.CTkFont(size=11)
        )
        self.api_status.grid(row=0, column=2, padx=10, pady=5, sticky="e")
    
    def set_workspace(self, path: str):
        """Установка пути к workspace"""
        self.workspace_label.configure(text=f"📁 Workspace: {path}")
    
    def set_stats(self, pages: int, concepts: int, words: int):
        """Установка статистики"""
        self.stats_label.configure(
            text=f"📊 {pages} pages • {concepts} concepts • {words:,} words"
        )
    
    def set_api_status(self, configured: bool, provider: str = ""):
        """Установка статуса API"""
        if configured:
            self.api_status.configure(
                text=f"🟢 API: {provider}",
                text_color="#4ec9b0"
            )
        else:
            self.api_status.configure(
                text="🔴 API: Not configured",
                text_color="#c42b1c"
            )


class ThemeSwitcher(ctk.CTkFrame):
    """Переключатель темы"""
    
    def __init__(self, master, on_change: Optional[Callable] = None, **kwargs):
        super().__init__(master, **kwargs)
        
        self._on_change = on_change
        
        label = ctk.CTkLabel(self, text="🎨 Theme:", font=ctk.CTkFont(size=11))
        label.grid(row=0, column=0, padx=5, pady=5)
        
        self.theme_var = ctk.StringVar(value="dark")
        
        self.dark_btn = ctk.CTkRadioButton(
            self,
            text="Dark",
            variable=self.theme_var,
            value="dark",
            command=self._on_theme_change
        )
        self.dark_btn.grid(row=0, column=1, padx=5, pady=5)
        
        self.light_btn = ctk.CTkRadioButton(
            self,
            text="Light",
            variable=self.theme_var,
            value="light",
            command=self._on_theme_change
        )
        self.light_btn.grid(row=0, column=2, padx=5, pady=5)
        
        self.system_btn = ctk.CTkRadioButton(
            self,
            text="System",
            variable=self.theme_var,
            value="system",
            command=self._on_theme_change
        )
        self.system_btn.grid(row=0, column=3, padx=5, pady=5)
    
    def _on_theme_change(self):
        """Обработка смены темы"""
        theme = self.theme_var.get()
        
        if theme == "dark":
            ctk.set_appearance_mode("dark")
        elif theme == "light":
            ctk.set_appearance_mode("light")
        else:
            ctk.set_appearance_mode("system")
        
        if self._on_change:
            self._on_change(theme)
        
        logger.info(f"Theme changed to: {theme}")
    
    def get_theme(self) -> str:
        """Получение текущей темы"""
        return self.theme_var.get()


class ProgressIndicator(ctk.CTkFrame):
    """Индикатор прогресса с текстом"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.grid_columnconfigure(0, weight=1)
        
        self.progress_bar = ctk.CTkProgressBar(self, height=10)
        self.progress_bar.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        self.progress_bar.set(0)
        
        self.progress_label = ctk.CTkLabel(
            self,
            text="Ready",
            font=ctk.CTkFont(size=11)
        )
        self.progress_label.grid(row=1, column=0, padx=10, pady=2, sticky="w")
    
    def set_progress(self, value: float, text: str = ""):
        """Установка прогресса"""
        self.progress_bar.set(value)
        if text:
            self.progress_label.configure(text=text)
    
    def set_indeterminate(self, text: str = "Processing..."):
        """Установка неопределённого прогресса"""
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()
        self.progress_label.configure(text=text)
    
    def stop(self, text: str = "Ready"):
        """Остановка прогресса"""
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(1)
        self.progress_label.configure(text=text)
    
    def reset(self):
        """Сброс прогресса"""
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
        self.progress_label.configure(text="Ready")


class NotificationToast(ctk.CTkToplevel):
    """Всплывающее уведомление"""
    
    def __init__(self, master, message: str, duration: int = 3000, **kwargs):
        super().__init__(master, **kwargs)
        
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        
        # Размеры
        self.geometry("300x50")
        
        # Контент
        frame = ctk.CTkFrame(self, corner_radius=10)
        frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        label = ctk.CTkLabel(
            frame,
            text=message,
            font=ctk.CTkFont(size=12)
        )
        label.pack(expand=True, padx=10, pady=10)
        
        # Позиционирование
        self.update_idletasks()
        x = master.winfo_x() + master.winfo_width() - 320
        y = master.winfo_y() + 60
        self.geometry(f"+{x}+{y}")
        
        # Автозакрытие
        self.after(duration, self.destroy)


class Tooltip:
    """Подсказка при наведении"""
    
    def __init__(self, widget, text: str, delay: int = 500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.after_id = None
        
        self.widget.bind("<Enter>", self._show_tooltip)
        self.widget.bind("<Leave>", self._hide_tooltip)
    
    def _show_tooltip(self, event=None):
        """Показ подсказки"""
        if self.after_id:
            return
        
        self.after_id = self.widget.after(self.delay, self._create_tooltip)
    
    def _create_tooltip(self):
        """Создание окна подсказки"""
        if self.tooltip_window:
            return
        
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        
        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.overrideredirect(True)
        self.tooltip_window.geometry(f"+{x}+{y}")
        
        label = ctk.CTkLabel(
            self.tooltip_window,
            text=self.text,
            font=ctk.CTkFont(size=11),
            corner_radius=5,
            fg_color="#3c3c3c"
        )
        label.pack(padx=5, pady=5)
    
    def _hide_tooltip(self, event=None):
        """Скрытие подсказки"""
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
        
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


class KeyboardShortcuts:
    """Менеджер горячих клавиш"""
    
    def __init__(self, master):
        self.master = master
        self.shortcuts = {}
    
    def register(self, key_sequence: str, callback: Callable, description: str = ""):
        """Регистрация горячей клавиши"""
        self.shortcuts[key_sequence] = {
            "callback": callback,
            "description": description
        }
        
        # Привязываем к master
        self.master.bind(key_sequence, lambda e: callback())
        
        logger.debug(f"Registered shortcut: {key_sequence} -> {description}")
    
    def unregister(self, key_sequence: str):
        """Отмена регистрации горячей клавиши"""
        if key_sequence in self.shortcuts:
            self.master.unbind(key_sequence)
            del self.shortcuts[key_sequence]
    
    def get_all(self) -> dict:
        """Получение всех горячих клавиш"""
        return self.shortcuts.copy()


class IconButton(ctk.CTkButton):
    """Кнопка с иконкой"""
    
    def __init__(self, master, icon: str, command: Optional[Callable] = None, **kwargs):
        # Устанавливаем defaults
        kwargs.setdefault("width", 40)
        kwargs.setdefault("height", 40)
        kwargs.setdefault("corner_radius", 8)
        
        super().__init__(master, text=icon, command=command, **kwargs)
        
        self.configure(font=ctk.CTkFont(size=16))


class CardFrame(ctk.CTkFrame):
    """Карточка с заголовком"""
    
    def __init__(self, master, title: str = "", **kwargs):
        super().__init__(master, **kwargs)
        
        self.grid_columnconfigure(0, weight=1)
        
        if title:
            title_label = ctk.CTkLabel(
                self,
                text=title,
                font=ctk.CTkFont(size=14, weight="bold")
            )
            title_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
    
    def add_content(self, widget, **grid_kwargs):
        """Добавление контента в карточку"""
        grid_kwargs.setdefault("row", 1)
        grid_kwargs.setdefault("column", 0)
        grid_kwargs.setdefault("padx", 10)
        grid_kwargs.setdefault("pady", 5)
        grid_kwargs.setdefault("sticky", "nsew")
        
        widget.grid(**grid_kwargs)
