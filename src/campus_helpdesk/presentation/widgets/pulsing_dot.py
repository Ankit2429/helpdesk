"""Animated Pulsing Status Dot Widget."""

import tkinter as tk
import customtkinter as ctk


class PulsingStatusDot(ctk.CTkFrame):
    """Status Indicator Dot with looping color pulse animation."""

    def __init__(
        self,
        master: any,
        name: str,
        state_text: str = "Online",
        base_color: str = "#10B981",
        pulse_color: str = "#6EE7B7",
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)

        self.name = name
        self.state_text = state_text
        self.base_color = base_color
        self.pulse_color = pulse_color
        self.is_pulsing = True
        self._pulse_state = False

        self.canvas = tk.Canvas(self, width=16, height=16, bg="#020617", bd=0, highlightthickness=0)
        self.canvas.pack(side="left", padx=(0, 6))

        self.label = ctk.CTkLabel(
            self,
            text=f"{self.name}: {self.state_text}",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#F8FAFC",
        )
        self.label.pack(side="left")

        self._dot_id = self.canvas.create_oval(3, 3, 13, 13, fill=self.base_color, outline="")
        self._animate_pulse()

    def _animate_pulse(self) -> None:
        """Loop pulse animation every 800ms."""
        if not self.winfo_exists():
            return

        next_color = self.pulse_color if self._pulse_state else self.base_color
        self.canvas.itemconfig(self._dot_id, fill=next_color)
        self._pulse_state = not self._pulse_state

        if self.is_pulsing:
            self.after(800, self._animate_pulse)

    def set_status(self, state_text: str, color: str) -> None:
        """Update dot status label and base color."""
        self.state_text = state_text
        self.base_color = color
        self.label.configure(text=f"{self.name}: {self.state_text}")
        self.canvas.itemconfig(self._dot_id, fill=color)
