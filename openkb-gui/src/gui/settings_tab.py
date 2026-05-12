"""
Settings Tab - Вкладка настроек приложения с улучшенным UI для выбора LLM провайдеров.

Особенности:
- Выбор провайдера из списка LiteLLM-совместимых провайдеров
- Выбор модели для каждого провайдера
- Тестирование подключения к модели
- Сохранение API ключей
- Подстановка из буфера обмена во все поля (правый клик -> Paste)
"""

import customtkinter as ctk
from tkinter import Menu, Tk
import logging
import threading
from pathlib import Path
from typing import Optional, Callable

from services.provider_service import (
    ProviderService,
    ProviderInfo,
    ModelInfo,
    ConnectionTestResult,
    ConnectionStatus,
)
from services.config_service import ConfigService

logger = logging.getLogger(__name__)


class ClipboardEntry(ctk.CTkEntry):
    """Entry с поддержкой вставки из буфера обмена через правый клик."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._setup_context_menu()

    def _setup_context_menu(self):
        """Создание контекстного меню."""
        self.context_menu = Menu(self, tearoff=0)
        self.context_menu.add_command(label="📋 Вставить (Paste)", command=self._paste_from_clipboard)
        self.context_menu.add_command(label="✂️ Вырезать (Cut)", command=self._cut_text)
        self.context_menu.add_command(label="📄 Копировать (Copy)", command=self._copy_text)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ Очистить (Clear)", command=self._clear_text)

        # Привязываем правый клик
        self.bind("<Button-3>", self._show_context_menu)

        # Также поддерживаем Ctrl+V
        self.bind("<Control-v>", lambda e: self._paste_from_clipboard())

    def _show_context_menu(self, event):
        """Показ контекстного меню."""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def _paste_from_clipboard(self):
        """Вставка из буфера обмена."""
        try:
            # Пробуем получить текст из буфера обмена
            clipboard_text = self.clipboard_get()
            # Вставляем в текущую позицию курсора
            self.insert("insert", clipboard_text)
        except Exception as e:
            logger.debug(f"Clipboard paste failed: {e}")

    def _cut_text(self):
        """Вырезать текст."""
        try:
            selected = self.selection_get()
            self.clipboard_clear()
            self.clipboard_append(selected)
            self.delete("sel.first", "sel.last")
        except Exception:
            pass

    def _copy_text(self):
        """Копировать текст."""
        try:
            selected = self.selection_get()
            self.clipboard_clear()
            self.clipboard_append(selected)
        except Exception:
            pass

    def _clear_text(self):
        """Очистить поле."""
        self.delete(0, "end")


class ProviderSelectorFrame(ctk.CTkFrame):
    """Фрейм для выбора провайдера и модели."""

    def __init__(self, master, on_provider_change: Optional[Callable] = None, **kwargs):
        super().__init__(master, **kwargs)

        self.provider_service = ProviderService.get_instance()
        self.config_service = ConfigService.get_instance()
        self.on_provider_change = on_provider_change

        self._current_provider_id: Optional[str] = None
        self._test_result: Optional[ConnectionTestResult] = None

        self._create_ui()
        self._load_initial_state()

    def _create_ui(self):
        """Создание UI элементов."""
        self.grid_columnconfigure(1, weight=1)

        row = 0

        # === Заголовок ===
        header_label = ctk.CTkLabel(
            self,
            text="🤖 LLM Provider Configuration",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        header_label.grid(row=row, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 5))
        row += 1

        help_text = "Выберите провайдера LiteLLM, модель и настройте API ключ"
        ctk.CTkLabel(self, text=help_text, text_color="gray").grid(
            row=row, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 10)
        )
        row += 1

        # === Выбор провайдера ===
        ctk.CTkLabel(self, text="Provider:").grid(row=row, column=0, sticky="w", padx=10, pady=5)

        providers = self.provider_service.get_providers()
        provider_names = [p.name for p in providers.values()]

        self.provider_dropdown = ctk.CTkOptionMenu(
            self,
            values=provider_names,
            width=300,
            command=self._on_provider_selected
        )
        self.provider_dropdown.grid(row=row, column=1, sticky="w", padx=10, pady=5)

        # Кнопка информации о провайдере
        self.info_btn = ctk.CTkButton(
            self, text="ℹ️", width=40, command=self._show_provider_info
        )
        self.info_btn.grid(row=row, column=2, padx=5, pady=5)
        row += 1

        # === Выбор модели ===
        ctk.CTkLabel(self, text="Model:").grid(row=row, column=0, sticky="w", padx=10, pady=5)

        self.model_dropdown = ctk.CTkOptionMenu(
            self,
            values=["Select provider first"],
            width=300,
            command=self._on_model_selected
        )
        self.model_dropdown.grid(row=row, column=1, sticky="w", padx=10, pady=5)

        # Информация о модели
        self.model_info_label = ctk.CTkLabel(self, text="", text_color="gray", width=200)
        self.model_info_label.grid(row=row, column=2, padx=5, pady=5, sticky="w")
        row += 1

        # === API Key ===
        ctk.CTkLabel(self, text="API Key:").grid(row=row, column=0, sticky="w", padx=10, pady=5)

        api_frame = ctk.CTkFrame(self, fg_color="transparent")
        api_frame.grid(row=row, column=1, columnspan=2, sticky="w", padx=10, pady=5)

        self.api_key_entry = ClipboardEntry(api_frame, width=350, show="*")
        self.api_key_entry.grid(row=0, column=0, padx=(0, 5))

        self.show_key_var = ctk.BooleanVar(value=False)
        self.show_key_cb = ctk.CTkCheckBox(
            api_frame, text="Show", variable=self.show_key_var,
            width=60, command=self._toggle_key_visibility
        )
        self.show_key_cb.grid(row=0, column=1)
        row += 1

        # === API Base URL (для custom провайдеров) ===
        ctk.CTkLabel(self, text="API Base URL:").grid(row=row, column=0, sticky="w", padx=10, pady=5)

        self.base_url_entry = ClipboardEntry(self, width=300)
        self.base_url_entry.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        self.base_url_entry.configure(state="disabled")
        row += 1

        # === Кнопки действий ===
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=row, column=0, columnspan=3, pady=15)

        self.test_btn = ctk.CTkButton(
            btn_frame, text="🔍 Test Connection", width=140,
            command=self._test_connection
        )
        self.test_btn.grid(row=0, column=0, padx=5)

        self.save_key_btn = ctk.CTkButton(
            btn_frame, text="💾 Save API Key", width=140,
            command=self._save_api_key
        )
        self.save_key_btn.grid(row=0, column=1, padx=5)

        self.fetch_models_btn = ctk.CTkButton(
            btn_frame, text="🔄 Fetch Models", width=140,
            command=self._fetch_models_from_api
        )
        self.fetch_models_btn.grid(row=0, column=2, padx=5)
        row += 1

        # === Статус подключения ===
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.status_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=10, pady=5)

        self.status_icon = ctk.CTkLabel(self.status_frame, text="", font=ctk.CTkFont(size=16))
        self.status_icon.grid(row=0, column=0, padx=5)

        self.status_label = ctk.CTkLabel(self.status_frame, text="", wraplength=500)
        self.status_label.grid(row=0, column=1, sticky="w")
        row += 1

        # === Разделитель ===
        ctk.CTkFrame(self, height=2).grid(row=row, column=0, columnspan=3, sticky="ew", padx=10, pady=15)

    def _load_initial_state(self):
        """Загрузка начального состояния из конфигурации."""
        config = self.config_service.config
        current_model = config.llm_model or "zai/glm-4.5-flash"

        # Определяем провайдера по модели
        provider_id = None
        model_id = None

        for pid, provider in self.provider_service.get_providers().items():
            if current_model.startswith(provider.prefix):
                provider_id = pid
                model_id = current_model.replace(provider.prefix, "")
                break

        if not provider_id:
            provider_id = "zai"
            model_id = "glm-4.5-flash"

        # Устанавливаем провайдера
        self._set_provider(provider_id)

        # Устанавливаем модель
        if model_id:
            self._set_model(model_id)

        # Загружаем API ключ
        api_key = self.provider_service.get_api_key(provider_id)
        if api_key:
            self.api_key_entry.delete(0, "end")
            self.api_key_entry.insert(0, api_key)

        # Загружаем base URL если есть
        if config.llm_api_base:
            self.base_url_entry.configure(state="normal")
            self.base_url_entry.delete(0, "end")
            self.base_url_entry.insert(0, config.llm_api_base)

    def _set_provider(self, provider_id: str):
        """Установка провайдера программно."""
        provider = self.provider_service.get_provider(provider_id)
        if not provider:
            return

        self._current_provider_id = provider_id

        # Обновляем dropdown провайдеров
        providers = self.provider_service.get_providers()
        provider_names = list(p.name for p in providers.values())
        self.provider_dropdown.configure(values=provider_names)
        self.provider_dropdown.set(provider.name)

        # Обновляем список моделей
        model_names = [m.name for m in provider.models]
        self.model_dropdown.configure(values=model_names if model_names else ["No models available"])

        # Загружаем API ключ
        api_key = self.provider_service.get_api_key(provider_id)
        self.api_key_entry.delete(0, "end")
        if api_key:
            self.api_key_entry.insert(0, api_key)

        # Базовый URL
        if provider_id == "custom":
            self.base_url_entry.configure(state="normal")
        else:
            self.base_url_entry.configure(state="disabled")
            self.base_url_entry.delete(0, "end")
            if provider.api_base:
                self.base_url_entry.insert(0, provider.api_base)

    def _set_model(self, model_id: str):
        """Установка модели программно."""
        if not self._current_provider_id:
            return

        provider = self.provider_service.get_provider(self._current_provider_id)
        if not provider:
            return

        # Ищем модель по ID
        for model in provider.models:
            if model.id == model_id:
                self.model_dropdown.set(model.name)
                self._update_model_info(model)
                break

    def _on_provider_selected(self, provider_name: str):
        """Обработчик выбора провайдера."""
        # Находим ID провайдера по имени
        for pid, provider in self.provider_service.get_providers().items():
            if provider.name == provider_name:
                self._current_provider_id = pid

                # Обновляем модели
                model_names = [m.name for m in provider.models]
                self.model_dropdown.configure(values=model_names if model_names else ["No models available"])

                if provider.models:
                    self.model_dropdown.set(provider.models[0].name)
                    self._update_model_info(provider.models[0])

                # Загружаем API ключ
                api_key = self.provider_service.get_api_key(pid)
                self.api_key_entry.delete(0, "end")
                if api_key:
                    self.api_key_entry.insert(0, api_key)

                # Управляем базовым URL
                if pid == "custom":
                    self.base_url_entry.configure(state="normal")
                else:
                    self.base_url_entry.configure(state="disabled")
                    self.base_url_entry.delete(0, "end")
                    if provider.api_base:
                        self.base_url_entry.insert(0, provider.api_base)

                # Callback
                if self.on_provider_change:
                    self.on_provider_change(pid)

                break

    def _on_model_selected(self, model_name: str):
        """Обработчик выбора модели."""
        if not self._current_provider_id:
            return

        provider = self.provider_service.get_provider(self._current_provider_id)
        if not provider:
            return

        # Находим модель по имени
        for model in provider.models:
            if model.name == model_name:
                self._update_model_info(model)
                break

    def _update_model_info(self, model: ModelInfo):
        """Обновление информации о модели."""
        info_parts = []

        if model.is_free:
            info_parts.append("🆓 Free")
        elif model.price_input:
            info_parts.append(f"💰 {model.price_input}")

        if model.context_window:
            ctx = model.context_window
            if ctx >= 1000000:
                info_parts.append(f"📚 {ctx // 1000}K ctx")
            else:
                info_parts.append(f"📚 {ctx // 1024}K ctx")

        if model.supports_vision:
            info_parts.append("👁️ Vision")

        self.model_info_label.configure(text=" | ".join(info_parts))

    def _toggle_key_visibility(self):
        """Переключение видимости API ключа."""
        if self.show_key_var.get():
            self.api_key_entry.configure(show="")
        else:
            self.api_key_entry.configure(show="*")

    def _show_provider_info(self):
        """Показ информации о провайдере."""
        if not self._current_provider_id:
            return

        provider = self.provider_service.get_provider(self._current_provider_id)
        if not provider:
            return

        # Создаём диалог с информацией
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Provider Info: {provider.name}")
        dialog.geometry("500x400")
        dialog.transient(self.winfo_toplevel())

        frame = ctk.CTkScrollableFrame(dialog)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Информация
        info_text = f"""
# {provider.name}

**ID:** {provider.id}
**Prefix:** {provider.prefix}
**API Key Env:** {provider.api_key_env}

## Description
{provider.description or 'No description available'}

## API Base
{provider.api_base or 'Not specified'}

## Links
- Website: {provider.website or 'N/A'}
- Docs: {provider.docs_url or 'N/A'}

## Available Models: {len(provider.models)}
"""

        textbox = ctk.CTkTextbox(frame, font=ctk.CTkFont(family="Consolas", size=12))
        textbox.pack(fill="both", expand=True)
        textbox.insert("0.0", info_text)
        textbox.configure(state="disabled")

    def _test_connection(self):
        """Тестирование подключения в отдельном потоке."""
        if not self._current_provider_id:
            self._update_status(False, "Select a provider first")
            return

        api_key = self.api_key_entry.get()
        if not api_key:
            self._update_status(False, "Enter API key first")
            return

        # Получаем выбранную модель
        model_name = self.model_dropdown.get()
        model_id = None

        provider = self.provider_service.get_provider(self._current_provider_id)
        if provider:
            for model in provider.models:
                if model.name == model_name:
                    model_id = model.id
                    break

        # Устанавливаем API ключ временно
        self.provider_service.set_api_key(self._current_provider_id, api_key)

        # Показываем прогресс
        self.test_btn.configure(state="disabled", text="Testing...")
        self._update_status(None, "Testing connection...")

        # Запускаем в отдельном потоке
        def test_thread():
            result = self.provider_service.test_model(self._current_provider_id, model_id)
            self.after(0, lambda: self._on_test_complete(result))

        threading.Thread(target=test_thread, daemon=True).start()

    def _on_test_complete(self, result: ConnectionTestResult):
        """Обработчик завершения тестирования."""
        self.test_btn.configure(state="normal", text="🔍 Test Connection")
        self._test_result = result
        self._update_status(result.success, result.message)

    def _update_status(self, success: Optional[bool], message: str):
        """Обновление статуса."""
        if success is None:
            # Прогресс
            self.status_icon.configure(text="⏳", text_color="#ffa500")
        elif success:
            self.status_icon.configure(text="✅", text_color="#4ec9b0")
        else:
            self.status_icon.configure(text="❌", text_color="#ff6b6b")

        self.status_label.configure(text=message)

    def _save_api_key(self):
        """Сохранение API ключа."""
        if not self._current_provider_id:
            self._update_status(False, "Select a provider first")
            return

        api_key = self.api_key_entry.get()
        if not api_key:
            self._update_status(False, "Enter API key first")
            return

        # Сохраняем ключ
        success = self.provider_service.set_api_key(self._current_provider_id, api_key)

        if success:
            # Также сохраняем в файл
            env_path = Path.cwd() / ".env"
            self.provider_service.save_api_key_to_file(self._current_provider_id, api_key, env_path)

            # Обновляем конфигурацию
            self.config_service.update_config(
                llm_api_key=api_key,
            )

            self._update_status(True, f"API key saved for {self._current_provider_id}")
        else:
            self._update_status(False, "Failed to save API key")

    def _fetch_models_from_api(self):
        """Получение моделей через API провайдера."""
        if not self._current_provider_id:
            return

        provider = self.provider_service.get_provider(self._current_provider_id)
        if not provider or not provider.supports_model_listing:
            self._update_status(False, "This provider doesn't support model listing via API")
            return

        api_key = self.api_key_entry.get()
        if not api_key:
            self._update_status(False, "Enter API key first")
            return

        # Устанавливаем ключ
        self.provider_service.set_api_key(self._current_provider_id, api_key)

        # Показываем прогресс
        self.fetch_models_btn.configure(state="disabled", text="Fetching...")
        self._update_status(None, "Fetching models from API...")

        def fetch_thread():
            models = self.provider_service.fetch_models_from_api(self._current_provider_id)
            self.after(0, lambda: self._on_models_fetched(models))

        threading.Thread(target=fetch_thread, daemon=True).start()

    def _on_models_fetched(self, models: list):
        """Обработчик получения моделей."""
        self.fetch_models_btn.configure(state="normal", text="🔄 Fetch Models")

        if models:
            # Получаем список ID моделей
            # Для разных провайдеров формат может отличаться:
            # - OpenRouter: id уже содержит префикс (например, "anthropic/claude-...")
            # - OpenAI, Groq: id без префикса (например, "gpt-4o"), нужно добавить префикс провайдера
            provider = self.provider_service.get_provider(self._current_provider_id)
            prefix = provider.prefix if provider else ""
            
            model_ids = []
            for m in models[:50]:  # Ограничиваем список
                model_id = m.get("id", m.get("name", "Unknown"))
                # Если ID не содержит префикс слэша и у провайдера есть префикс, добавляем его
                if "/" not in model_id and prefix and self._current_provider_id != "openrouter":
                    model_id = f"{prefix}{model_id}"
                model_ids.append(model_id)
            
            self._update_status(True, f"Fetched {len(models)} models (showing first 50)")

            # Показываем диалог со списком моделей
            dialog = ctk.CTkToplevel(self)
            dialog.title(f"Available Models - {self._current_provider_id}")
            dialog.geometry("600x500")
            dialog.transient(self.winfo_toplevel())

            frame = ctk.CTkScrollableFrame(dialog)
            frame.pack(fill="both", expand=True, padx=10, pady=10)

            for model_id in model_ids:
                btn = ctk.CTkButton(
                    frame,
                    text=model_id,
                    anchor="w",
                    command=lambda mid=model_id: self._select_fetched_model(mid)
                )
                btn.pack(fill="x", pady=2)
        else:
            self._update_status(False, "No models fetched or API not available")

    def _select_fetched_model(self, model_id: str):
        """Выбор модели из полученного списка."""
        # Для fetched моделей model_id уже может содержать префикс провайдера (например, "anthropic/claude-...")
        # Сохраняем его как есть для использования в full_model
        
        # Обновляем список моделей в dropdown с выбранной моделью
        current_values = list(self.model_dropdown.cget("values"))
        
        # Если модели еще нет в списке, добавляем её
        if model_id not in current_values:
            current_values.append(model_id)
            self.model_dropdown.configure(values=current_values)
        
        # Устанавливаем выбранную модель
        self.model_dropdown.set(model_id)
        
        # Обновляем информацию о модели (сбрасываем, так как это fetched модель)
        self.model_info_label.configure(text="🌐 Fetched from API")
        
        # Закрываем диалог со списком моделей
        for widget in self.winfo_children():
            if isinstance(widget, ctk.CTkToplevel):
                widget.destroy()
        
        self._update_status(True, f"Selected model: {model_id}")

    def get_current_config(self) -> dict:
        """Получение текущей конфигурации."""
        provider = self.provider_service.get_provider(self._current_provider_id) if self._current_provider_id else None

        model_name = self.model_dropdown.get()
        model_id = None
        full_model = ""
        
        # Проверяем, является ли модель fetched (уже содержит префикс провайдера)
        # Fetched модели имеют формат "provider/model-name" (например, "anthropic/claude-3-sonnet")
        is_fetched_model = "/" in model_name
        
        if is_fetched_model:
            # Это fetched модель - используем её как есть для full_model
            full_model = model_name
            model_id = model_name  # Сохраняем полный ID для использования
        else:
            # Это стандартная модель из списка провайдера
            # Сначала ищем модель в списке провайдера
            if provider:
                for model in provider.models:
                    if model.name == model_name:
                        model_id = model.id
                        break
            
            # Если не нашли (модель была получена через API), используем имя напрямую
            if not model_id and model_name and model_name != "Select provider first":
                model_id = model_name
            
            # Формируем full_model с префиксом провайдера
            if provider and model_id:
                full_model = f"{provider.prefix}{model_id}"
            elif model_name:
                full_model = model_name

        return {
            "provider_id": self._current_provider_id,
            "model_id": model_id,
            "api_key": self.api_key_entry.get(),
            "api_base": self.base_url_entry.get() if self._current_provider_id == "custom" else "",
            "full_model": full_model,
        }


class LLMSettingsTab(ctk.CTkFrame):
    """Полная вкладка настроек LLM."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Scrollable контейнер
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        # Селектор провайдера
        self.provider_selector = ProviderSelectorFrame(self.scroll_frame)
        self.provider_selector.grid(row=0, column=0, sticky="ew", pady=5)

        # Дополнительные настройки
        self._create_additional_settings()

    def _create_additional_settings(self):
        """Создание дополнительных настроек."""
        # Workspace Settings
        workspace_frame = ctk.CTkFrame(self.scroll_frame)
        workspace_frame.grid(row=1, column=0, sticky="ew", pady=10)
        workspace_frame.grid_columnconfigure(1, weight=1)

        row = 0
        ctk.CTkLabel(
            workspace_frame, text="📁 Workspace Configuration",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=row, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 5))
        row += 1

        ctk.CTkLabel(workspace_frame, text="Workspace Path:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )

        ws_frame = ctk.CTkFrame(workspace_frame, fg_color="transparent")
        ws_frame.grid(row=row, column=1, columnspan=2, sticky="w", padx=10, pady=5)

        self.workspace_entry = ClipboardEntry(ws_frame, width=350)
        self.workspace_entry.grid(row=0, column=0, padx=(0, 5))

        ctk.CTkButton(ws_frame, text="Browse", width=80, command=self._browse_workspace).grid(
            row=0, column=1
        )
        row += 1

        # Watch Mode
        ctk.CTkFrame(workspace_frame, height=2).grid(
            row=row, column=0, columnspan=3, sticky="ew", padx=10, pady=15
        )
        row += 1

        ctk.CTkLabel(
            workspace_frame, text="👀 Watch Mode Settings",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=row, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 5))
        row += 1

        self.watch_enabled_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            workspace_frame, text="Enable Watch Mode",
            variable=self.watch_enabled_var
        ).grid(row=row, column=0, columnspan=3, sticky="w", padx=10, pady=5)
        row += 1

        ctk.CTkLabel(workspace_frame, text="Debounce (seconds):").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.debounce_entry = ClipboardEntry(workspace_frame, width=100)
        self.debounce_entry.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        row += 1

        # PageIndex
        ctk.CTkFrame(workspace_frame, height=2).grid(
            row=row, column=0, columnspan=3, sticky="ew", padx=10, pady=15
        )
        row += 1

        ctk.CTkLabel(
            workspace_frame, text="📄 PageIndex OCR (Optional)",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=row, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 5))
        row += 1

        ctk.CTkLabel(workspace_frame, text="PageIndex API Key:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.pageindex_entry = ClipboardEntry(workspace_frame, width=350, show="*")
        self.pageindex_entry.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        row += 1

        # Кнопка сохранения
        ctk.CTkFrame(workspace_frame, height=2).grid(
            row=row, column=0, columnspan=3, sticky="ew", padx=10, pady=15
        )
        row += 1

        ctk.CTkButton(
            workspace_frame, text="💾 Save All Settings", width=200,
            command=self._save_all_settings
        ).grid(row=row, column=0, columnspan=3, pady=20)

        # Загружаем текущие настройки
        self._load_settings()

    def _load_settings(self):
        """Загрузка текущих настроек."""
        config = ConfigService.get_instance().config

        self.workspace_entry.delete(0, "end")
        self.workspace_entry.insert(0, config.workspace_path)

        self.debounce_entry.delete(0, "end")
        self.debounce_entry.insert(0, str(config.watch_debounce_seconds))

        self.watch_enabled_var.set(config.watch_enabled)

        if config.pageindex_api_key:
            self.pageindex_entry.delete(0, "end")
            self.pageindex_entry.insert(0, config.pageindex_api_key)

    def _browse_workspace(self):
        """Выбор директории workspace."""
        import tkinter.filedialog as fd
        path = fd.askdirectory(title="Select Workspace Directory")
        if path:
            self.workspace_entry.delete(0, "end")
            self.workspace_entry.insert(0, path)

    def _save_all_settings(self):
        """Сохранение всех настроек."""
        config_service = ConfigService.get_instance()

        # Получаем конфигурацию провайдера
        provider_config = self.provider_selector.get_current_config()

        # Обновляем конфигурацию
        config_service.update_config(
            llm_model=provider_config.get("full_model", ""),
            llm_api_key=provider_config.get("api_key", ""),
            llm_api_base=provider_config.get("api_base", ""),
            workspace_path=self.workspace_entry.get(),
            pageindex_api_key=self.pageindex_entry.get(),
            watch_enabled=self.watch_enabled_var.get(),
            watch_debounce_seconds=int(self.debounce_entry.get() or "2"),
        )

        if config_service.save_config():
            self.provider_selector._update_status(True, "All settings saved successfully!")
        else:
            self.provider_selector._update_status(False, "Failed to save settings")
