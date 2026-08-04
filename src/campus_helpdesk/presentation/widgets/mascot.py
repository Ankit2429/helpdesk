"""Robot Mascot Canvas Badge Generator ("Sparky" Campus Assistant)."""

import customtkinter as ctk


class MascotAvatar(ctk.CTkCanvas):
    """Canvas-rendered Robot Mascot ("Sparky") avatar icon badge."""

    def __init__(
        self,
        master: any,
        size: int = 48,
        bg_color: str = "#1E293B",
        accent_color: str = "#3B82F6",
        eye_color: str = "#10B981",
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            width=size,
            height=size,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            **kwargs,
        )
        self.size = size
        self.accent_color = accent_color
        self.eye_color = eye_color

        self.draw_mascot()

    def draw_mascot(self) -> None:
        """Draw friendly robot mascot face."""
        s = self.size
        self.delete("all")

        # Outer Rounded Head Contour
        pad = s * 0.1
        self.create_rectangle(
            pad, pad, s - pad, s - pad,
            fill="#334155",
            outline=self.accent_color,
            width=2,
        )

        # Antenna
        self.create_line(s * 0.5, pad, s * 0.5, s * 0.05, fill=self.accent_color, width=2)
        self.create_oval(s * 0.45, s * 0.02, s * 0.55, s * 0.08, fill=self.eye_color, outline="")

        # Ears / Side Bolts
        self.create_rectangle(pad * 0.5, s * 0.4, pad, s * 0.6, fill=self.accent_color, outline="")
        self.create_rectangle(s - pad, s * 0.4, s - pad * 0.5, s * 0.6, fill=self.accent_color, outline="")

        # Visor Screen
        v_left, v_top, v_right, v_bottom = s * 0.2, s * 0.25, s * 0.8, s * 0.65
        self.create_rectangle(v_left, v_top, v_right, v_bottom, fill="#0F172A", outline="")

        # Animated Eye Dots (Emerald green glowing eyes)
        e_y = s * 0.45
        e_r = s * 0.08
        self.create_oval(s * 0.35 - e_r, e_y - e_r, s * 0.35 + e_r, e_y + e_r, fill=self.eye_color, outline="")
        self.create_oval(s * 0.65 - e_r, e_y - e_r, s * 0.65 + e_r, e_y + e_r, fill=self.eye_color, outline="")

        # Friendly Curved Smile
        self.create_arc(
            s * 0.35, s * 0.45, s * 0.65, s * 0.6,
            start=200, extent=140, style="arc",
            outline="#F8FAFC", width=2,
        )
