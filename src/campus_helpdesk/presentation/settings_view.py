"""CustomTkinter Settings View Component.

Features grouped settings sections, CTkOptionMenu dropdowns, CTkSlider brevity scale,
CTkSwitch hallucination verification toggle, and save confirmation toast.
"""

from typing import Any, Callable, Dict
import customtkinter as ctk

from campus_helpdesk.presentation.theme import ThemeEngine


class SettingsView(ctk.CTkFrame):
    """CustomTkinter Settings View Component."""

    def __init__(
        self,
        master: any,
        theme_engine: ThemeEngine,
        save_callback: Callable[[Dict[str, Any]], None],
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.theme_engine = theme_engine
        self.save_callback = save_callback

        self._build_ui()

    def _build_ui(self) -> None:
        """Construct Settings layout."""
        c = self.theme_engine.colors

        self.grid_columnconfigure(0, weight=1)

        # Header Title Banner
        header = ctk.CTkFrame(self, fg_color=c.panel_bg, corner_radius=14)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text="⚙️ System & AI Model Settings", font=ThemeEngine.font_card_title(), text_color=c.text_main).grid(row=0, column=0, sticky="w", padx=16, pady=12)

        # Settings Form Card Container
        form = ctk.CTkFrame(self, fg_color=c.panel_bg, corner_radius=14)
        form.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))
        form.grid_columnconfigure(1, weight=1)

        # 1. Model Selection (CTkOptionMenu)
        ctk.CTkLabel(form, text="Ollama LLM Model:", font=ThemeEngine.font_body(), text_color=c.text_main).grid(row=0, column=0, sticky="w", padx=20, pady=14)
        self.model_option = ctk.CTkOptionMenu(
            form,
            values=["llama3.1:8b", "llama3.2", "mistral:7b"],
            fg_color=c.accent_brand,
            button_color="#C2410C",
            font=ThemeEngine.font_body(),
        )
        self.model_option.grid(row=0, column=1, sticky="w", padx=20, pady=14)

        # 2. Target Response Length (CTkSlider)
        ctk.CTkLabel(form, text="Max Sentences (Brevity):", font=ThemeEngine.font_body(), text_color=c.text_main).grid(row=1, column=0, sticky="w", padx=20, pady=14)
        self.length_slider = ctk.CTkSlider(form, from_=2, to=8, number_of_steps=6, progress_color=c.accent_brand)
        self.length_slider.set(4)
        self.length_slider.grid(row=1, column=1, sticky="ew", padx=20, pady=14)

        # 3. System Prompt Version (CTkOptionMenu)
        ctk.CTkLabel(form, text="System Prompt Version:", font=ThemeEngine.font_body(), text_color=c.text_main).grid(row=2, column=0, sticky="w", padx=20, pady=14)
        self.prompt_ver_option = ctk.CTkOptionMenu(
            form,
            values=["v2_grounded_concise", "v1_baseline"],
            fg_color=c.accent_primary,
            button_color=c.accent_hover,
            font=ThemeEngine.font_body(),
        )
        self.prompt_ver_option.grid(row=2, column=1, sticky="w", padx=20, pady=14)

        # 4. Hallucination Verification (CTkSwitch)
        ctk.CTkLabel(form, text="Self-Check Hallucinations:", font=ThemeEngine.font_body(), text_color=c.text_main).grid(row=3, column=0, sticky="w", padx=20, pady=14)
        self.verify_switch = ctk.CTkSwitch(form, text="Enable Post-Generation Verification", progress_color=c.accent_success)
        self.verify_switch.select()
        self.verify_switch.grid(row=3, column=1, sticky="w", padx=20, pady=14)

        # Save Button & Confirmation Toast
        btn_bar = ctk.CTkFrame(self, fg_color=c.panel_bg, corner_radius=14)
        btn_bar.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))
        btn_bar.grid_columnconfigure(0, weight=1)

        save_btn = ctk.CTkButton(
            btn_bar,
            text="💾 Save Settings",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=44,
            corner_radius=10,
            fg_color=c.accent_brand,
            hover_color="#C2410C",
            command=self._save_settings,
        )
        save_btn.grid(row=0, column=0, sticky="w", padx=16, pady=12)

        self.toast_lbl = ctk.CTkLabel(btn_bar, text="", font=ThemeEngine.font_caption(), text_color=c.accent_success)
        self.toast_lbl.grid(row=0, column=1, sticky="e", padx=16, pady=12)

    def _save_settings(self) -> None:
        """Save settings and trigger toast."""
        settings = {
            "model": self.model_option.get(),
            "max_sentences": int(self.length_slider.get()),
            "prompt_version": self.prompt_ver_option.get(),
            "verify_hallucinations": bool(self.verify_switch.get()),
        }
        self.save_callback(settings)
        self.toast_lbl.configure(text="✓ Settings saved & applied successfully!")
        self.after(4000, lambda: self.toast_lbl.configure(text=""))
