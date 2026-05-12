"""
Provider Dialog - Диалоги для управления провайдерами и моделями
"""

import customtkinter as ctk
from typing import Optional, Callable, Dict, List
import logging

from models.models import ProviderConfig, ModelConfig, ModelPricing

logger = logging.getLogger(__name__)


def _paste_to_entry(dialog, entry_widget):
    """Вставка текста из буфера обмена в поле ввода"""
    try:
        clipboard_text = dialog.clipboard_get()
        entry_widget.delete(0, "end")
        entry_widget.insert(0, clipboard_text)
    except Exception as e:
        logger.warning(f"Failed to paste from clipboard: {e}")


class ProviderDialog(ctk.CTkToplevel):
    """Dialog for adding/editing providers"""
    
    def __init__(
        self,
        master,
        provider: Optional[ProviderConfig] = None,
        on_save: Optional[Callable] = None
    ):
        """
        Initialize the dialog
        
        Args:
            master: Parent window
            provider: Existing provider to edit (None for new)
            on_save: Callback when save is clicked
        """
        super().__init__(master)
        
        self.provider = provider
        self.on_save = on_save
        self.result = None
        
        # Configure window
        self.title("Add Provider" if provider is None else "Edit Provider")
        self.geometry("600x520")
        self.resizable(False, False)
        
        # Make modal
        self.transient(master)
        self.grab_set()
        
        # Create UI
        self._create_ui()
        
        # Load existing data if editing
        if provider:
            self._load_provider_data()
        
        # Center the dialog
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_y() + (master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        
        # Focus on first entry
        self.id_entry.focus_set()
    
    def _create_ui(self):
        """Create dialog UI"""
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title = "Add New Provider" if self.provider is None else f"Edit Provider: {self.provider.name}"
        ctk.CTkLabel(
            main_frame,
            text=title,
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(0, 15))
        
        # Form frame
        form_frame = ctk.CTkFrame(main_frame)
        form_frame.pack(fill="x", pady=5)
        form_frame.grid_columnconfigure(1, weight=1)
        
        row = 0
        
        # Provider ID
        ctk.CTkLabel(form_frame, text="Provider ID:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        id_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        id_frame.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        self.id_entry = ctk.CTkEntry(id_frame, width=320, placeholder_text="e.g., openai, anthropic")
        self.id_entry.grid(row=0, column=0, padx=(0, 5))
        ctk.CTkButton(id_frame, text="📋", width=30, command=lambda: _paste_to_entry(self, self.id_entry)).grid(row=0, column=1)
        row += 1
        
        # Display Name
        ctk.CTkLabel(form_frame, text="Display Name:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        name_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        name_frame.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        self.name_entry = ctk.CTkEntry(name_frame, width=320, placeholder_text="e.g., OpenAI, Anthropic")
        self.name_entry.grid(row=0, column=0, padx=(0, 5))
        ctk.CTkButton(name_frame, text="📋", width=30, command=lambda: _paste_to_entry(self, self.name_entry)).grid(row=0, column=1)
        row += 1
        
        # API Base URL
        ctk.CTkLabel(form_frame, text="API Base URL:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        api_base_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        api_base_frame.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        self.api_base_entry = ctk.CTkEntry(api_base_frame, width=320, placeholder_text="https://api.example.com/v1")
        self.api_base_entry.grid(row=0, column=0, padx=(0, 5))
        ctk.CTkButton(api_base_frame, text="📋", width=30, command=lambda: _paste_to_entry(self, self.api_base_entry)).grid(row=0, column=1)
        row += 1
        
        # API Key Env Variable
        ctk.CTkLabel(form_frame, text="API Key Env Var:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        env_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        env_frame.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        self.api_key_env_entry = ctk.CTkEntry(env_frame, width=320, placeholder_text="e.g., OPENAI_API_KEY")
        self.api_key_env_entry.grid(row=0, column=0, padx=(0, 5))
        ctk.CTkButton(env_frame, text="📋", width=30, command=lambda: _paste_to_entry(self, self.api_key_env_entry)).grid(row=0, column=1)
        row += 1
        
        # Prefix
        ctk.CTkLabel(form_frame, text="Model Prefix:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        prefix_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        prefix_frame.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        self.prefix_entry = ctk.CTkEntry(prefix_frame, width=320, placeholder_text="e.g., openai/, anthropic/")
        self.prefix_entry.grid(row=0, column=0, padx=(0, 5))
        ctk.CTkButton(prefix_frame, text="📋", width=30, command=lambda: _paste_to_entry(self, self.prefix_entry)).grid(row=0, column=1)
        row += 1
        
        # Description
        ctk.CTkLabel(form_frame, text="Description:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        desc_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        desc_frame.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        self.description_entry = ctk.CTkEntry(desc_frame, width=320, placeholder_text="Optional description")
        self.description_entry.grid(row=0, column=0, padx=(0, 5))
        ctk.CTkButton(desc_frame, text="📋", width=30, command=lambda: _paste_to_entry(self, self.description_entry)).grid(row=0, column=1)
        row += 1
        
        # Model fetch support
        self.supports_fetch_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            form_frame,
            text="Supports model list API",
            variable=self.supports_fetch_var,
            command=self._on_fetch_support_change
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        row += 1
        
        # Models API Endpoint
        ctk.CTkLabel(form_frame, text="Models Endpoint:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        endpoint_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        endpoint_frame.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        self.models_endpoint_entry = ctk.CTkEntry(endpoint_frame, width=320, placeholder_text="/models")
        self.models_endpoint_entry.grid(row=0, column=0, padx=(0, 5))
        ctk.CTkButton(endpoint_frame, text="📋", width=30, command=lambda: _paste_to_entry(self, self.models_endpoint_entry)).grid(row=0, column=1)
        self.models_endpoint_entry.configure(state="disabled")
        row += 1
        
        # Enabled
        self.enabled_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(form_frame, text="Enabled", variable=self.enabled_var).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=(15, 0))
        
        ctk.CTkButton(
            button_frame,
            text="Cancel",
            width=100,
            fg_color="gray",
            command=self._on_cancel
        ).pack(side="right", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="Save",
            width=100,
            command=self._on_save
        ).pack(side="right", padx=5)
    
    def _on_fetch_support_change(self):
        """Handle fetch support checkbox change"""
        if self.supports_fetch_var.get():
            self.models_endpoint_entry.configure(state="normal")
        else:
            self.models_endpoint_entry.configure(state="disabled")
    
    def _load_provider_data(self):
        """Load existing provider data into form"""
        if not self.provider:
            return
        
        self.id_entry.insert(0, self.provider.id)
        self.id_entry.configure(state="disabled")  # Can't change ID
        self.name_entry.insert(0, self.provider.name)
        self.api_base_entry.insert(0, self.provider.api_base)
        self.api_key_env_entry.insert(0, self.provider.api_key_env)
        self.prefix_entry.insert(0, self.provider.prefix)
        self.description_entry.insert(0, self.provider.description)
        self.supports_fetch_var.set(self.provider.supports_model_fetch)
        self.models_endpoint_entry.insert(0, self.provider.models_api_endpoint)
        self.enabled_var.set(self.provider.enabled)
        
        self._on_fetch_support_change()
    
    def _on_save(self):
        """Handle save button"""
        # Validate
        provider_id = self.id_entry.get().strip()
        if not provider_id:
            self._show_error("Provider ID is required")
            return
        
        name = self.name_entry.get().strip()
        if not name:
            self._show_error("Display Name is required")
            return
        
        api_base = self.api_base_entry.get().strip()
        if not api_base:
            self._show_error("API Base URL is required")
            return
        
        # Create/update provider
        provider = ProviderConfig(
            id=provider_id,
            name=name,
            api_base=api_base,
            api_key_env=self.api_key_env_entry.get().strip() or f"{provider_id.upper()}_API_KEY",
            prefix=self.prefix_entry.get().strip() or f"{provider_id}/",
            description=self.description_entry.get().strip(),
            supports_model_fetch=self.supports_fetch_var.get(),
            models_api_endpoint=self.models_endpoint_entry.get().strip(),
            enabled=self.enabled_var.get(),
            models=self.provider.models if self.provider else []
        )
        
        self.result = provider
        
        if self.on_save:
            self.on_save(provider)
        
        self.destroy()
    
    def _on_cancel(self):
        """Handle cancel button"""
        self.result = None
        self.destroy()
    
    def _show_error(self, message: str):
        """Show error message"""
        # Simple error dialog
        error_dialog = ctk.CTkToplevel(self)
        error_dialog.title("Error")
        error_dialog.geometry("300x100")
        error_dialog.transient(self)
        error_dialog.grab_set()
        
        ctk.CTkLabel(error_dialog, text=message, text_color="red").pack(pady=20)
        ctk.CTkButton(error_dialog, text="OK", width=80, command=error_dialog.destroy).pack()


class ModelDialog(ctk.CTkToplevel):
    """Dialog for adding/editing models"""
    
    def __init__(
        self,
        master,
        model: Optional[ModelConfig] = None,
        on_save: Optional[Callable] = None
    ):
        """
        Initialize the dialog
        
        Args:
            master: Parent window
            model: Existing model to edit (None for new)
            on_save: Callback when save is clicked
        """
        super().__init__(master)
        
        self.model = model
        self.on_save = on_save
        self.result = None
        
        # Configure window
        self.title("Add Model" if model is None else "Edit Model")
        self.geometry("560x580")
        self.resizable(False, False)
        
        # Make modal
        self.transient(master)
        self.grab_set()
        
        # Create UI
        self._create_ui()
        
        # Load existing data if editing
        if model:
            self._load_model_data()
        
        # Center the dialog
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_y() + (master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        
        # Focus on first entry
        self.id_entry.focus_set()
    
    def _create_ui(self):
        """Create dialog UI"""
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title = "Add New Model" if self.model is None else f"Edit Model: {self.model.name}"
        ctk.CTkLabel(
            main_frame,
            text=title,
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(0, 15))
        
        # Form frame
        form_frame = ctk.CTkFrame(main_frame)
        form_frame.pack(fill="x", pady=5)
        form_frame.grid_columnconfigure(1, weight=1)
        
        row = 0
        
        # Model ID
        ctk.CTkLabel(form_frame, text="Model ID:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        id_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        id_frame.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        self.id_entry = ctk.CTkEntry(id_frame, width=320, placeholder_text="e.g., gpt-4, claude-3-opus")
        self.id_entry.grid(row=0, column=0, padx=(0, 5))
        ctk.CTkButton(id_frame, text="📋", width=30, command=lambda: _paste_to_entry(self, self.id_entry)).grid(row=0, column=1)
        row += 1
        
        # Display Name
        ctk.CTkLabel(form_frame, text="Display Name:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        name_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        name_frame.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        self.name_entry = ctk.CTkEntry(name_frame, width=320, placeholder_text="e.g., GPT-4, Claude 3 Opus")
        self.name_entry.grid(row=0, column=0, padx=(0, 5))
        ctk.CTkButton(name_frame, text="📋", width=30, command=lambda: _paste_to_entry(self, self.name_entry)).grid(row=0, column=1)
        row += 1
        
        # Context Length
        ctk.CTkLabel(form_frame, text="Context Length:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        ctx_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        ctx_frame.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        self.context_entry = ctk.CTkEntry(ctx_frame, width=320, placeholder_text="e.g., 8192, 128000")
        self.context_entry.grid(row=0, column=0, padx=(0, 5))
        ctk.CTkButton(ctx_frame, text="📋", width=30, command=lambda: _paste_to_entry(self, self.context_entry)).grid(row=0, column=1)
        row += 1
        
        # Description
        ctk.CTkLabel(form_frame, text="Description:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        desc_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        desc_frame.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        self.description_entry = ctk.CTkEntry(desc_frame, width=320, placeholder_text="Optional description")
        self.description_entry.grid(row=0, column=0, padx=(0, 5))
        ctk.CTkButton(desc_frame, text="📋", width=30, command=lambda: _paste_to_entry(self, self.description_entry)).grid(row=0, column=1)
        row += 1
        
        # Pricing section
        ctk.CTkLabel(
            form_frame,
            text="Pricing (per 1M tokens):",
            font=ctk.CTkFont(weight="bold")
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(15, 5))
        row += 1
        
        # Prompt Price
        ctk.CTkLabel(form_frame, text="Input Price:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        prompt_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        prompt_frame.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        self.prompt_price_entry = ctk.CTkEntry(prompt_frame, width=320, placeholder_text="$ per 1M tokens (e.g., 0.15)")
        self.prompt_price_entry.grid(row=0, column=0, padx=(0, 5))
        ctk.CTkButton(prompt_frame, text="📋", width=30, command=lambda: _paste_to_entry(self, self.prompt_price_entry)).grid(row=0, column=1)
        row += 1
        
        # Completion Price
        ctk.CTkLabel(form_frame, text="Output Price:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        comp_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        comp_frame.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        self.completion_price_entry = ctk.CTkEntry(comp_frame, width=320, placeholder_text="$ per 1M tokens (e.g., 0.60)")
        self.completion_price_entry.grid(row=0, column=0, padx=(0, 5))
        ctk.CTkButton(comp_frame, text="📋", width=30, command=lambda: _paste_to_entry(self, self.completion_price_entry)).grid(row=0, column=1)
        row += 1
        
        # Features section
        ctk.CTkLabel(
            form_frame,
            text="Features:",
            font=ctk.CTkFont(weight="bold")
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=(15, 5))
        row += 1
        
        # Enabled
        self.enabled_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(form_frame, text="Enabled", variable=self.enabled_var).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        row += 1
        
        # Vision support
        self.vision_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(form_frame, text="Supports Vision/Images", variable=self.vision_var).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        row += 1
        
        # Function calling
        self.function_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(form_frame, text="Supports Function Calling", variable=self.function_var).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=(15, 0))
        
        ctk.CTkButton(
            button_frame,
            text="Cancel",
            width=100,
            fg_color="gray",
            command=self._on_cancel
        ).pack(side="right", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="Save",
            width=100,
            command=self._on_save
        ).pack(side="right", padx=5)
    
    def _load_model_data(self):
        """Load existing model data into form"""
        if not self.model:
            return
        
        self.id_entry.insert(0, self.model.id)
        self.name_entry.insert(0, self.model.name)
        self.context_entry.insert(0, str(self.model.context_length))
        self.description_entry.insert(0, self.model.description)
        self.prompt_price_entry.insert(0, str(self.model.pricing.prompt))
        self.completion_price_entry.insert(0, str(self.model.pricing.completion))
        self.enabled_var.set(self.model.enabled)
        self.vision_var.set(self.model.supports_vision)
        self.function_var.set(self.model.supports_function_calling)
    
    def _on_save(self):
        """Handle save button"""
        # Validate
        model_id = self.id_entry.get().strip()
        if not model_id:
            self._show_error("Model ID is required")
            return
        
        name = self.name_entry.get().strip() or model_id
        
        # Parse context length
        try:
            context_length = int(self.context_entry.get().strip() or "4096")
        except ValueError:
            context_length = 4096
        
        # Parse pricing
        try:
            prompt_price = float(self.prompt_price_entry.get().strip() or "0")
        except ValueError:
            prompt_price = 0.0
        
        try:
            completion_price = float(self.completion_price_entry.get().strip() or "0")
        except ValueError:
            completion_price = 0.0
        
        # Create model
        model = ModelConfig(
            id=model_id,
            name=name,
            context_length=context_length,
            pricing=ModelPricing(prompt=prompt_price, completion=completion_price),
            description=self.description_entry.get().strip(),
            enabled=self.enabled_var.get(),
            supports_vision=self.vision_var.get(),
            supports_function_calling=self.function_var.get()
        )
        
        self.result = model
        
        if self.on_save:
            self.on_save(model)
        
        self.destroy()
    
    def _on_cancel(self):
        """Handle cancel button"""
        self.result = None
        self.destroy()
    
    def _show_error(self, message: str):
        """Show error message"""
        error_dialog = ctk.CTkToplevel(self)
        error_dialog.title("Error")
        error_dialog.geometry("300x100")
        error_dialog.transient(self)
        error_dialog.grab_set()
        
        ctk.CTkLabel(error_dialog, text=message, text_color="red").pack(pady=20)
        ctk.CTkButton(error_dialog, text="OK", width=80, command=error_dialog.destroy).pack()


class TestResultDialog(ctk.CTkToplevel):
    """Dialog showing test results"""
    
    def __init__(
        self,
        master,
        title: str,
        result
    ):
        """
        Initialize the dialog
        
        Args:
            master: Parent window
            title: Dialog title
            result: ConnectionTestResult object
        """
        super().__init__(master)
        
        self.result = result
        
        # Configure window
        self.title(title)
        self.geometry("450x300")
        self.resizable(False, False)
        
        # Make modal
        self.transient(master)
        self.grab_set()
        
        # Create UI
        self._create_ui()
        
        # Center the dialog
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_y() + (master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
    
    def _create_ui(self):
        """Create dialog UI"""
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Status icon and text
        if self.result.success:
            status_text = "✓ Success"
            status_color = "green"
        else:
            status_text = "✗ Failed"
            status_color = "red"
        
        ctk.CTkLabel(
            main_frame,
            text=status_text,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=status_color
        ).pack(pady=(0, 15))
        
        # Details frame
        details_frame = ctk.CTkFrame(main_frame)
        details_frame.pack(fill="x", pady=5)
        
        # Message
        ctk.CTkLabel(
            details_frame,
            text="Message:",
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 0))
        ctk.CTkLabel(
            details_frame,
            text=self.result.message,
            wraplength=400
        ).pack(anchor="w", padx=10)
        
        # Response time
        if self.result.response_time_ms > 0:
            ctk.CTkLabel(
                details_frame,
                text=f"\nResponse time: {self.result.response_time_ms:.0f}ms"
            ).pack(anchor="w", padx=10)
        
        # Model availability
        if hasattr(self.result, 'model_available'):
            availability = "Available" if self.result.model_available else "Not Available"
            ctk.CTkLabel(
                details_frame,
                text=f"Model status: {availability}"
            ).pack(anchor="w", padx=10, pady=(5, 0))
        
        # Error details
        if self.result.error_details:
            ctk.CTkLabel(
                details_frame,
                text="\nError details:",
                font=ctk.CTkFont(weight="bold")
            ).pack(anchor="w", padx=10, pady=(10, 0))
            
            error_text = ctk.CTkTextbox(details_frame, height=80)
            error_text.pack(fill="x", padx=10, pady=(0, 10))
            error_text.insert("0.0", self.result.error_details)
            error_text.configure(state="disabled")
        
        # Close button
        ctk.CTkButton(
            main_frame,
            text="Close",
            width=100,
            command=self.destroy
        ).pack(pady=(15, 0))
