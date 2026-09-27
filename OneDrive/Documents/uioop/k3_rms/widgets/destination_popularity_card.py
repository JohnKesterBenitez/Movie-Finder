from __future__ import annotations

import textwrap

import customtkinter as ctk
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import MaxNLocator


class DestinationPopularityCard(ctk.CTkFrame):
    """Dashboard card for destination ranking analytics.

    The component accepts a simple ``dict[str, int]`` mapping destination names
    to booking counts, which keeps the UI easy to reconnect later to database
    aggregates or controller responses.
    """

    def __init__(
        self,
        master,
        palette: dict[str, str],
        title: str = "Most Picked Destinations",
        subtitle: str = "See which destinations guests choose most often.",
        subject_singular: str = "Destination",
        subject_plural: str = "Destinations",
        sample_data: dict[str, int] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            fg_color=palette["surface"],
            corner_radius=28,
            border_width=1,
            border_color="#E5DDD6",
            **kwargs,
        )
        self.palette = palette
        self.title = title
        self.subtitle = subtitle
        self.subject_singular = subject_singular
        self.subject_plural = subject_plural
        self.sample_data = sample_data or {
            "Sandbar Escape": 34,
            "Coral View": 29,
            "Mangrove Cove": 24,
            "Sunset Dock": 18,
            "Lagoon Trail": 15,
        }
        self.current_data: dict[str, int] = dict(self.sample_data)
        self.figure: Figure | None = None
        self.axis = None
        self.canvas: FigureCanvasTkAgg | None = None
        self.anim: FuncAnimation | None = None
        self._visibility_job = None
        self._resize_after_id = None
        self._animate_on_next_render = False
        self._summary_cards: list[dict] = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(
            self,
            text=self.title,
            text_color="#005F61",
            font=("Segoe UI", 22, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(22, 4))
        ctk.CTkLabel(
            self,
            text=self.subtitle,
            text_color="#8FA3A6",
            font=("Segoe UI", 13),
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 16))

        self.summary_row = ctk.CTkFrame(self, fg_color="transparent")
        self.summary_row.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))
        for index in range(3):
            self.summary_row.grid_columnconfigure(index, weight=1, uniform="summary_card")

        self.chart_host = ctk.CTkFrame(self, fg_color=self.palette["surface"])
        self.chart_host.grid(row=3, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.chart_host.grid_columnconfigure(0, weight=1)
        self.chart_host.grid_rowconfigure(0, weight=1)
        self.chart_host.configure(height=360)
        self.chart_host.bind("<Configure>", self._handle_resize)

        self._setup_summary_widgets()
        self.set_data(self.sample_data)

    def set_data(self, data: dict[str, int] | None, animate: bool | None = None) -> None:
        """Update the ranking data and redraw the card."""
        cleaned_data = {
            str(name).strip(): max(0, int(value))
            for name, value in (data or {}).items()
            if str(name).strip()
        }
        self.current_data = cleaned_data or dict(self.sample_data)
        if animate is not None:
            self._animate_on_next_render = animate
        self._render(animate=animate if animate is not None else self._animate_on_next_render)

    def _handle_resize(self, _event=None) -> None:
        if self._resize_after_id is not None:
            self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after(120, lambda: self._render(animate=self._animate_on_next_render))

    def _prepare_items(self) -> list[tuple[str, int]]:
        return sorted(
            self.current_data.items(),
            key=lambda item: (-item[1], item[0].lower()),
        )

    @staticmethod
    def _truncate_text(text: str, max_length: int) -> str:
        normalized = " ".join(str(text).split())
        if not normalized:
            return ""
        if len(normalized) <= max_length:
            return normalized
        return textwrap.shorten(normalized, width=max_length, placeholder="...")

    def _chart_label(self, text: str) -> str:
        shortened = self._truncate_text(text, 36)
        return textwrap.fill(shortened, width=18, break_long_words=False)

    def _setup_summary_widgets(self) -> None:
        """Create the summary card widgets once to prevent stacking glitches."""
        self._summary_cards = []
        for i in range(3):
            card = ctk.CTkFrame(
                self.summary_row,
                fg_color="#FCFEFD",
                corner_radius=20,
                border_width=1,
                border_color="#E5DDD6",
                height=108,
            )
            card.grid(row=0, column=i, sticky="ew", padx=8, pady=6)
            card.grid_columnconfigure(0, weight=1)
            
            title_label = ctk.CTkLabel(
                card,
                text="",
                text_color="#8FA3A6",
                font=("Segoe UI", 12, "bold"),
                anchor="w",
            )
            title_label.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 2))
            
            value_label = ctk.CTkLabel(
                card,
                text="",
                text_color="#005F61",
                font=("Segoe UI", 20, "bold"),
                anchor="w",
            )
            value_label.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 2))
            
            subtitle_label = ctk.CTkLabel(
                card,
                text="",
                text_color="#8FA3A6",
                font=("Segoe UI", 10),
                anchor="w",
            )
            subtitle_label.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))

            def make_sync(c=card, t=title_label, v=value_label, s=subtitle_label):
                def sync(_e=None):
                    if not c.winfo_exists(): return
                    try:
                        w = max(c.winfo_width() - 36, 140)
                        t.configure(wraplength=w)
                        v.configure(wraplength=w)
                        s.configure(wraplength=w)
                    except: pass
                return sync

            sync_func = make_sync()
            card.bind("<Configure>", sync_func)
            self._summary_cards.append({
                "frame": card,
                "title": title_label,
                "value": value_label,
                "subtitle": subtitle_label
            })

    def _render_summary(self, items: list[tuple[str, int]]) -> None:
        if not items or len(self._summary_cards) < 3:
            return

        total_bookings = sum(value for _, value in items)
        top_destination, top_value = items[0]
        active_destinations = sum(1 for _, value in items if value > 0)
        top_share = (top_value / total_bookings * 100) if total_bookings else 0

        # Update Top Destination Card
        self._summary_cards[0]["title"].configure(text=f"Top {self.subject_singular}")
        self._summary_cards[0]["value"].configure(text=top_destination)
        self._summary_cards[0]["subtitle"].configure(text=f"{top_value} bookings | {top_share:.0f}% share")
        self._summary_cards[0]["frame"].configure(fg_color="#FFF7F6")

        # Update Total Bookings Card
        self._summary_cards[1]["title"].configure(text=f"Total {self.subject_singular} Bookings")
        self._summary_cards[1]["value"].configure(text=str(total_bookings))
        self._summary_cards[1]["subtitle"].configure(text=f"Combined bookings across the ranked list.")
        self._summary_cards[1]["frame"].configure(fg_color="#FCFEFD")

        # Update Active Destinations Card
        self._summary_cards[2]["title"].configure(text=f"Active {self.subject_plural}")
        self._summary_cards[2]["value"].configure(text=str(active_destinations))
        self._summary_cards[2]["subtitle"].configure(text=f"{self.subject_plural} with recorded bookings.")
        self._summary_cards[2]["frame"].configure(fg_color="#F6FBF7")

    def _stop_render_jobs(self) -> None:
        if self._visibility_job is not None:
            try:
                self.after_cancel(self._visibility_job)
            except Exception:
                pass
            self._visibility_job = None
        if self.anim is not None:
            try:
                self.anim.event_source.stop()
            except Exception:
                pass
            self.anim = None

    def _destroy_canvas(self) -> None:
        self._stop_render_jobs()
        if self.canvas is not None:
            try:
                self.canvas.get_tk_widget().destroy()
            except Exception:
                pass
            self.canvas = None
        if self.figure is not None:
            self.figure.clear()
            self.figure = None
        self.axis = None

    def reset_animation(self) -> None:
        self._animate_on_next_render = False
        self._render(animate=False)

    def replay_animation_when_visible(self) -> None:
        self._animate_on_next_render = True
        self._render(animate=True)

    def _is_widget_visible_in_window(self, widget) -> bool:
        try:
            if widget is None or not widget.winfo_exists() or not widget.winfo_ismapped():
                return False
            widget_height = max(int(widget.winfo_height()), 1)
            widget_top = widget.winfo_rooty()
            widget_bottom = widget_top + widget_height
            root = self.winfo_toplevel()
            window_top = root.winfo_rooty()
            window_bottom = window_top + max(int(root.winfo_height()), 1)
            visible_height = min(widget_bottom, window_bottom) - max(widget_top, window_top)
            minimum_visible = min(max(widget_height * 0.25, 80), widget_height)
            return visible_height >= minimum_visible
        except Exception:
            return False

    def _start_animation_when_visible(self, widget, starter) -> None:
        if self._visibility_job is not None:
            try:
                self.after_cancel(self._visibility_job)
            except Exception:
                pass
            self._visibility_job = None

        def try_start() -> None:
            if widget is None or not widget.winfo_exists():
                self._visibility_job = None
                return
            if self._is_widget_visible_in_window(widget):
                self._visibility_job = None
                starter()
                return
            self._visibility_job = self.after(120, try_start)

        self._visibility_job = self.after(80, try_start)

    def _render_chart(self, items: list[tuple[str, int]], animate: bool = True) -> None:
        self._stop_render_jobs()

        width = max(self.chart_host.winfo_width(), 760)
        height = max(self.chart_host.winfo_height(), 340)
        if self.figure is None:
            self.figure = Figure(
                figsize=(width / 100, height / 100),
                dpi=100,
                facecolor=self.palette["surface"],
            )
        else:
            self.figure.clear()
            self.figure.set_size_inches(width / 100, height / 100, forward=True)

        if self.canvas is None:
            self.canvas = FigureCanvasTkAgg(self.figure, master=self.chart_host)
            self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        figure = self.figure
        axis = figure.add_subplot(111)
        self.axis = axis
        axis.set_facecolor(self.palette["surface"])

        ordered_items = list(items)[:5]
        labels = [self._chart_label(name) for name, _ in ordered_items]
        values = [value for _, value in ordered_items]
        total = max(sum(values), 1)
        max_value = max(max(values) if values else 0, 5)
        color_cycle = ["#E9A09A", "#7ED6D1", "#AFC7A3", "#D7BFA8", "#4AA8A4", "#B7D9D7"]
        bar_height = 0.62
        frame_count = 90

        axis.set_xlim(0, max_value * 1.28)
        axis.set_ylim(-0.6, max(len(labels), 1) - 0.4)

        patches: list[tuple[FancyBboxPatch, int, str]] = []
        value_labels = []
        for index, (label, value) in enumerate(ordered_items):
            color = color_cycle[index % len(color_cycle)]
            patch = FancyBboxPatch(
                (0, index - bar_height / 2),
                0,
                bar_height,
                boxstyle="round,pad=0.02,rounding_size=0.16",
                linewidth=0,
                facecolor=color,
                edgecolor=color,
                mutation_aspect=1,
                zorder=3,
            )
            axis.add_patch(patch)
            patches.append((patch, value, label))
            percentage = (value / total) * 100 if total else 0
            value_text = axis.text(
                max_value * 0.03,
                index,
                "0  |  0%",
                va="center",
                ha="left",
                fontsize=10,
                color="#005F61",
                fontweight="bold" if index == 0 else "normal",
                zorder=4,
            )
            value_labels.append((value_text, value, percentage))

        axis.set_yticks(range(len(labels)))
        axis.set_yticklabels(labels, color="#005F61", fontsize=11)
        axis.invert_yaxis()
        axis.tick_params(axis="y", length=0)
        axis.tick_params(axis="x", colors="#8FA3A6", labelsize=10)
        axis.xaxis.set_major_locator(MaxNLocator(integer=True))
        axis.set_xlabel("Bookings", color="#8FA3A6", fontsize=10, labelpad=10)
        axis.grid(axis="x", color="#E5DDD6", linewidth=0.8, alpha=0.65, zorder=1)
        axis.grid(axis="y", visible=False)

        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        axis.spines["left"].set_visible(False)
        axis.spines["bottom"].set_color("#E5DDD6")

        figure.tight_layout(pad=2.0)
        canvas_widget = self.canvas.get_tk_widget()
        self.canvas.draw()

        def update(frame_index: int):
            progress = frame_index / (frame_count - 1)
            eased_progress = 1 - ((1 - progress) ** 3)
            for bar_index, ((patch, final_value, _label), (value_text, _target_value, percentage)) in enumerate(
                zip(patches, value_labels)
            ):
                animated_value = final_value * eased_progress
                patch.set_bounds(0, bar_index - bar_height / 2, animated_value, bar_height)
                value_text.set_x(animated_value + max_value * 0.03)
                value_text.set_text(f"{int(round(animated_value))}  |  {percentage * eased_progress:.0f}%")
            return [pair[0] for pair in patches] + [pair[0] for pair in value_labels]

        if not animate:
            update(frame_count - 1)
            self.canvas.draw()
            return

        def start_animation() -> None:
            if self.anim is not None:
                try:
                    self.anim.event_source.stop()
                except Exception:
                    pass
            self._animate_on_next_render = False
            self.anim = FuncAnimation(
                figure,
                update,
                frames=frame_count,
                interval=32,
                blit=False,
                repeat=False,
            )
            self.canvas.draw_idle()

        self._start_animation_when_visible(canvas_widget, start_animation)

    def _render(self, animate: bool | None = None) -> None:
        items = self._prepare_items()
        if not items:
            items = list(self.sample_data.items())
        
        # We honor the animation parameter but fallback to False if not specified
        should_animate = animate if animate is not None else False
        
        self._render_summary(items)
        self._render_chart(items, animate=should_animate)
