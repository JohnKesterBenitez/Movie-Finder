from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta

import customtkinter as ctk


DEFAULT_PALETTE = {
    "surface": "#FFFFFF",
    "surface_alt": "#F5F7F6",
    "line": "#D9E5E1",
    "text": "#173330",
    "muted": "#6A8782",
    "brand": "#0D5E60",
    "brand_dark": "#094548",
    "available": "#CFEBDD",
    "available_text": "#165142",
    "reserved": "#F4E3B0",
    "reserved_text": "#7F5A12",
    "in_use": "#BCD9EE",
    "in_use_text": "#1D4D82",
    "selected": "#0D5E60",
    "selected_text": "#FFFFFF",
    "disabled": "#EEF2F1",
    "disabled_text": "#A1B1AD",
}


class DatePickerField(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        variable,
        get_status_map=None,
        min_date: date | None = None,
        palette: dict | None = None,
        on_change=None,
    ) -> None:
        super().__init__(parent, fg_color="transparent")
        self.variable = variable
        self.get_status_map = get_status_map or (lambda: {})
        self.min_date = min_date or date.today()
        self.palette = {**DEFAULT_PALETTE, **(palette or {})}
        self.on_change = on_change

        self.grid_columnconfigure(0, weight=1)

        display = ctk.CTkFrame(
            self,
            fg_color=self.palette["surface"],
            corner_radius=16,
            border_width=1,
            border_color=self.palette["line"],
            height=48,
        )
        display.grid(row=0, column=0, sticky="ew")
        display.grid_columnconfigure(0, weight=1)

        self.display_label = ctk.CTkLabel(
            display,
            text="",
            text_color=self.palette["text"],
            font=("Segoe UI", 13),
            anchor="w",
        )
        self.display_label.grid(row=0, column=0, sticky="ew", padx=(14, 8), pady=10)

        open_button = ctk.CTkButton(
            display,
            text="Calendar",
            width=112,
            height=34,
            corner_radius=12,
            fg_color=self.palette["brand"],
            hover_color=self.palette["brand_dark"],
            text_color="#FFFFFF",
            font=("Segoe UI", 12, "bold"),
            command=self.open_picker,
        )
        open_button.grid(row=0, column=1, padx=(0, 8), pady=7)

        self.variable.trace_add("write", self._sync_label)
        self._sync_label()

    def open_picker(self) -> None:
        CalendarPopup(
            parent=self,
            variable=self.variable,
            get_status_map=self.get_status_map,
            min_date=self.min_date,
            palette=self.palette,
            on_change=self.on_change,
        )

    def _sync_label(self, *_args) -> None:
        value = (self.variable.get() or "").strip()
        self.display_label.configure(text=value or "Select a date")


class CalendarPopup(ctk.CTkToplevel):
    WEEKDAYS = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")

    def __init__(
        self,
        parent,
        variable,
        get_status_map,
        min_date: date,
        palette: dict,
        on_change=None,
    ) -> None:
        super().__init__(parent)
        self.variable = variable
        self.get_status_map = get_status_map
        self.min_date = min_date
        self.palette = palette
        self.on_change = on_change
        self.selected_date = self._parse_date(variable.get()) or min_date
        self.visible_month = self.selected_date.replace(day=1)
        self.day_widgets: list[ctk.CTkBaseClass] = []

        self.title("Choose Date")
        self.geometry("430x430")
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.configure(fg_color=self.palette["surface"])

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=16, pady=16)
        container.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            container,
            text="<",
            width=40,
            height=34,
            corner_radius=12,
            fg_color=self.palette["surface_alt"],
            hover_color=self.palette["disabled"],
            text_color=self.palette["text"],
            command=lambda: self._change_month(-1),
        ).grid(row=0, column=0, sticky="w")

        self.month_label = ctk.CTkLabel(
            container,
            text="",
            text_color=self.palette["text"],
            font=("Segoe UI", 18, "bold"),
        )
        self.month_label.grid(row=0, column=1, pady=(0, 8))

        ctk.CTkButton(
            container,
            text=">",
            width=40,
            height=34,
            corner_radius=12,
            fg_color=self.palette["surface_alt"],
            hover_color=self.palette["disabled"],
            text_color=self.palette["text"],
            command=lambda: self._change_month(1),
        ).grid(row=0, column=2, sticky="e")

        legend = ctk.CTkFrame(
            container,
            fg_color=self.palette["surface_alt"],
            corner_radius=14,
        )
        legend.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        legend.grid_columnconfigure((0, 1, 2), weight=1)
        self._legend_chip(legend, 0, "Available", self.palette["available"], self.palette["available_text"])
        self._legend_chip(legend, 1, "Reserved", self.palette["reserved"], self.palette["reserved_text"])
        self._legend_chip(legend, 2, "On Going", self.palette["in_use"], self.palette["in_use_text"])

        self.calendar_frame = ctk.CTkFrame(container, fg_color="transparent")
        self.calendar_frame.grid(row=2, column=0, columnspan=3, sticky="nsew")
        self.calendar_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)

        for column, weekday in enumerate(self.WEEKDAYS):
            ctk.CTkLabel(
                self.calendar_frame,
                text=weekday,
                text_color=self.palette["muted"],
                font=("Segoe UI", 11, "bold"),
            ).grid(row=0, column=column, padx=2, pady=(0, 8))

        note = ctk.CTkLabel(
            container,
            text="Reserved dates already have a booking. Select a green date to avoid typo errors.",
            text_color=self.palette["muted"],
            font=("Segoe UI", 11),
            justify="left",
            wraplength=380,
        )
        note.grid(row=3, column=0, columnspan=3, sticky="w", pady=(12, 0))

        self._render_days()

    def _legend_chip(self, parent, column: int, text: str, fg_color: str, text_color: str) -> None:
        chip = ctk.CTkLabel(
            parent,
            text=text,
            fg_color=fg_color,
            text_color=text_color,
            corner_radius=10,
            padx=10,
            pady=4,
            font=("Segoe UI", 10, "bold"),
        )
        chip.grid(row=0, column=column, padx=8, pady=8)

    def _change_month(self, delta: int) -> None:
        year = self.visible_month.year
        month = self.visible_month.month + delta
        if month == 0:
            year -= 1
            month = 12
        elif month == 13:
            year += 1
            month = 1
        self.visible_month = date(year, month, 1)
        self._render_days()

    def _render_days(self) -> None:
        for widget in self.day_widgets:
            widget.destroy()
        self.day_widgets.clear()

        status_map = self.get_status_map() or {}
        self.month_label.configure(text=self.visible_month.strftime("%B %Y"))

        month_grid = calendar.Calendar(firstweekday=6).monthdatescalendar(
            self.visible_month.year,
            self.visible_month.month,
        )

        for row_index, week in enumerate(month_grid, start=1):
            for column, day_value in enumerate(week):
                widget = self._build_day_widget(day_value, status_map)
                widget.grid(row=row_index, column=column, padx=2, pady=2, sticky="nsew")
                self.day_widgets.append(widget)

    def _build_day_widget(self, day_value: date, status_map: dict[str, str]):
        if day_value.month != self.visible_month.month:
            return ctk.CTkLabel(
                self.calendar_frame,
                text="",
                width=52,
                height=42,
                fg_color="transparent",
            )

        if day_value < self.min_date:
            return ctk.CTkLabel(
                self.calendar_frame,
                text=str(day_value.day),
                width=52,
                height=42,
                fg_color=self.palette["disabled"],
                text_color=self.palette["disabled_text"],
                corner_radius=12,
                font=("Segoe UI", 12),
            )

        status = status_map.get(day_value.isoformat(), "Available")
        if status == "On Going":
            fg_color = self.palette["in_use"]
            text_color = self.palette["in_use_text"]
        elif status == "Reserved" or status == "Confirmed":
            fg_color = self.palette["reserved"]
            text_color = self.palette["reserved_text"]
        else:
            fg_color = self.palette["available"]
            text_color = self.palette["available_text"]

        hover_color = self.palette["brand_dark"]
        if day_value == self.selected_date:
            fg_color = self.palette["selected"]
            text_color = self.palette["selected_text"]

        return ctk.CTkButton(
            self.calendar_frame,
            text=str(day_value.day),
            width=52,
            height=42,
            corner_radius=12,
            fg_color=fg_color,
            hover_color=hover_color,
            text_color=text_color,
            font=("Segoe UI", 12, "bold"),
            command=lambda selected_day=day_value: self._select_date(selected_day),
        )

    def _select_date(self, selected_day: date) -> None:
        self.selected_date = selected_day
        self.variable.set(selected_day.isoformat())
        if self.on_change:
            self.on_change(selected_day.isoformat())
        self.destroy()

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        if not value:
            return None
        cleaned = value.strip()
        try:
            return datetime.strptime(cleaned, "%Y-%m-%d").date()
        except ValueError:
            parts = cleaned.split("-")
            if len(parts) != 3:
                return None
            try:
                return date(int(parts[0]), int(parts[1]), int(parts[2]))
            except ValueError:
                return None
