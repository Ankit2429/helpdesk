"""Live Latency Sparkline Chart Widget."""

import customtkinter as ctk


class LatencySparkline(ctk.CTkCanvas):
    """Canvas-based sparkline chart displaying latency trends over time."""

    def __init__(
        self,
        master: any,
        width: int = 180,
        height: int = 40,
        line_color: str = "#3B82F6",
        fill_color: str = "#1E3A8A",
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            width=width,
            height=height,
            bg="#1E293B",
            bd=0,
            highlightthickness=0,
            **kwargs,
        )
        self.w = width
        self.h = height
        self.line_color = line_color
        self.data: list[float] = [45.0, 52.0, 48.0, 65.0, 55.0, 42.0, 58.0, 50.0, 57.6]

        self.draw_chart()

    def add_data_point(self, val: float) -> None:
        """Append new latency measurement and redraw sparkline."""
        self.data.append(val)
        if len(self.data) > 12:
            self.data.pop(0)
        self.draw_chart()

    def draw_chart(self) -> None:
        """Render sparkline curve."""
        self.delete("all")
        if not self.data or len(self.data) < 2:
            return

        min_v = min(self.data) * 0.8
        max_v = max(self.data) * 1.2
        span = max(1.0, max_v - min_v)

        step = self.w / (len(self.data) - 1)
        points = []

        for i, val in enumerate(self.data):
            x = i * step
            norm_y = (val - min_v) / span
            y = self.h - (norm_y * (self.h - 8) + 4)
            points.append((x, y))

        # Draw Sparkline Line
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            self.create_line(x1, y1, x2, y2, fill=self.line_color, width=2, smooth=True)

        # Draw End Point Dot
        last_x, last_y = points[-1]
        self.create_oval(last_x - 3, last_y - 3, last_x + 3, last_y + 3, fill="#10B981", outline="")
