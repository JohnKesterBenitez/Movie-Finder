"""Guest browse-and-book screen."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import customtkinter as ctk

from k3_rms.widgets.date_picker import DatePickerField
from models.cottage_model import BoatModel, CottageModel, DESTINATIONS
from utils.theme import (
    BG,
    CARD,
    DIVIDER,
    DANGER,
    DESTINATION_CHIP_COLORS,
    SUBTEXT,
    TEAL,
    TEAL_DARK,
    TEAL_LIGHT,
    TEAL_LINE,
    TEXT,
    WHITE,
    info_chip,
    make_button,
    make_card,
    make_image,
    make_label,
    make_status_badge,
)


class BrowseView(ctk.CTkFrame):
    SHELL_TITLE = "Browse and Book"
    SIDEBAR_ACTIVE = "browse"
    SHOW_SIDEBAR = True

    def __init__(self, parent, app):
        super().__init__(parent, fg_color=BG)
        self.app = app
        self._current_tab = "cottage"
        self.travel_date_var = ctk.StringVar(value=(date.today() + timedelta(days=1)).isoformat())
        self.workspace_hint_var = ctk.StringVar()
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_banner()
        self._build_workspace()
        self._render_items()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=WHITE, corner_radius=0, height=64)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_propagate(False)

        # Branding (Middle/Left)
        make_label(header, "K3's Floating Cottage", 16, "bold", color=TEAL_DARK).grid(
            row=0,
            column=0,
            sticky="w",
            padx=30,
        )

        # Right: Welcome Message (with more padding)
        welcome_frame = ctk.CTkFrame(header, fg_color="transparent")
        welcome_frame.grid(row=0, column=1, padx=40)
        
        name = self.app.session_user.get('name', 'Guest')
        make_label(welcome_frame, f"Welcome,", 12, color=SUBTEXT).pack(side="left")
        make_label(welcome_frame, f" {name}", 12, "bold", color=TEXT).pack(side="left")

        # Subtle bottom border
        ctk.CTkFrame(self, fg_color=DIVIDER, height=1, corner_radius=0).grid(row=0, column=0, sticky="esw")

    def _build_banner(self):
        banner = ctk.CTkFrame(self, fg_color=TEAL_LIGHT, corner_radius=0, height=102)
        banner.grid(row=1, column=0, sticky="ew")
        banner.grid_propagate(False)
        make_label(banner, "Browse and Book", 27, "bold", color=TEAL_DARK).place(
            relx=0.5,
            rely=0.38,
            anchor="center",
        )
        make_label(
            banner,
            "Choose a date first, then see which cottages are still available.",
            12,
            color=TEXT,
        ).place(relx=0.5, rely=0.70, anchor="center")

    def _build_workspace(self):
        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.grid(row=2, column=0, sticky="nsew", padx=18, pady=18)
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(0, weight=1)

        workspace = make_card(outer)
        workspace.grid(row=0, column=0, sticky="nsew")
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_rowconfigure(2, weight=1)

        top = ctk.CTkFrame(workspace, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=28, pady=(18, 8))
        top.grid_columnconfigure(0, weight=0)
        top.grid_columnconfigure(1, weight=1)
        top.grid_columnconfigure(2, weight=0)

        tab_bar = ctk.CTkFrame(top, fg_color=TEAL_LIGHT, corner_radius=12, height=40)
        tab_bar.grid(row=0, column=0, sticky="w")
        tab_bar.grid_columnconfigure((0, 1), weight=1)

        self._btn_cottages = ctk.CTkButton(
            tab_bar,
            text="Floating Cottages",
            fg_color=TEAL,
            hover_color=TEAL_DARK,
            text_color=WHITE,
            corner_radius=10,
            width=132,
            height=32,
            font=("Segoe UI", 11, "bold"),
            command=lambda: self._switch_tab("cottage"),
        )
        self._btn_cottages.grid(row=0, column=0, padx=4, pady=4)

        self._btn_boats = ctk.CTkButton(
            tab_bar,
            text="Destinations",
            fg_color="transparent",
            hover_color=TEAL_LIGHT,
            text_color=SUBTEXT,
            corner_radius=10,
            width=112,
            height=32,
            font=("Segoe UI", 11),
            command=lambda: self._switch_tab("boat"),
        )
        self._btn_boats.grid(row=0, column=1, padx=(0, 4), pady=4)

        self.date_picker = DatePickerField(
            top,
            variable=self.travel_date_var,
            min_date=date.today(),
            get_status_map=lambda: {},
            on_change=lambda _value: self._render_items(),
            palette={
                "surface": WHITE,
                "surface_alt": TEAL_LIGHT,
                "line": "#D9E7E3",
                "text": TEXT,
                "muted": SUBTEXT,
                "brand": TEAL,
                "brand_dark": TEAL_DARK,
                "available": "#DBF2EE",
                "available_text": TEAL_DARK,
                "reserved": "#F4E2B2",
                "reserved_text": "#7A5A16",
                "in_use": "#C8DDF5",
                "in_use_text": "#275B97",
            },
        )
        self.date_picker.grid(row=0, column=2, sticky="e")

        ctk.CTkLabel(
            workspace,
            textvariable=self.workspace_hint_var,
            font=("Segoe UI", 11),
            text_color=SUBTEXT,
        ).grid(row=1, column=0, sticky="w", padx=28, pady=(0, 4))

        self._scroll = ctk.CTkScrollableFrame(workspace, fg_color="transparent")
        self._scroll.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 18))
        self._scroll.grid_columnconfigure((0, 1), weight=1)
        self._update_workspace_hint()

    def _switch_tab(self, tab: str):
        self._current_tab = tab
        if tab == "cottage":
            self._btn_cottages.configure(fg_color=TEAL, text_color=WHITE, font=("Segoe UI", 11, "bold"))
            self._btn_boats.configure(fg_color="transparent", text_color=SUBTEXT, font=("Segoe UI", 11))
        else:
            self._btn_boats.configure(fg_color=TEAL, text_color=WHITE, font=("Segoe UI", 11, "bold"))
            self._btn_cottages.configure(fg_color="transparent", text_color=SUBTEXT, font=("Segoe UI", 11))
        self._update_workspace_hint()
        self._render_items()

    def _update_workspace_hint(self):
        if self._current_tab == "cottage":
            self.workspace_hint_var.set("Choose a date first, then pick your cottage.")
            return
        self.workspace_hint_var.set(
            "Browse each destination as a guide. You can select multiple stops when you book a cottage."
        )

    def _render_items(self):
        for widget in self._scroll.winfo_children():
            widget.destroy()

        selected_date = (self.travel_date_var.get() or "").strip()
        if self._current_tab == "cottage":
            items = CottageModel.get_all(selected_date)
            title = f"Floating Cottages ({len(items)})"
        else:
            items = BoatModel.get_guides()
            title = f"Destination Guide ({len(items)})"

        make_label(self._scroll, title, 17, "bold", color=TEXT).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            padx=8,
            pady=(2, 14),
        )

        if not items:
            make_label(
                self._scroll,
                "No items are available for the selected date.",
                14,
                color=SUBTEXT,
            ).grid(row=1, column=0, columnspan=2, pady=32)
            return

        for index, item in enumerate(items):
            if self._current_tab == "cottage":
                self._render_cottage_card(index, item)
                continue
            self._render_destination_card(index, item)

    def _render_cottage_card(self, index: int, item: dict):
        card = make_card(self._scroll)
        card.grid(row=index // 2 + 1, column=index % 2, sticky="nsew", padx=8, pady=8)
        card.grid_columnconfigure(0, weight=1)

        top_color = TEAL_LINE if item["status"] != "Cancelled" else DANGER
        top_strip = ctk.CTkFrame(card, fg_color=top_color, height=4, corner_radius=16)
        top_strip.grid(row=0, column=0, sticky="ew", padx=1, pady=(1, 0))

        content_row = 1
        if item.get("image"):
            image = make_image(card, item["image"], size=(350, 152), alt=item["name"])
            image.grid(row=content_row, column=0, sticky="ew", padx=12, pady=(14, 8))
            content_row += 1

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.grid(row=content_row, column=0, sticky="ew", padx=18, pady=(12, 0))
        header.grid_columnconfigure(0, weight=1)
        make_label(
            header,
            f"{item['id']} | {item['name']}",
            15,
            "bold",
        ).grid(row=0, column=0, sticky="w")
        make_status_badge(header, item["status"]).grid(row=0, column=1, sticky="e")
        content_row += 1

        meta = ctk.CTkFrame(card, fg_color="transparent")
        meta.grid(row=content_row, column=0, sticky="w", padx=18, pady=(4, 6))
        meta.grid_columnconfigure((0, 1), weight=0)
        make_label(meta, f"Capacity: {item['capacity']} pax", 11, color=SUBTEXT).grid(row=0, column=0, sticky="w")
        make_label(
            meta,
            f"|  PHP {item['rate']:,.2f} / hr",
            11,
            color=SUBTEXT,
        ).grid(row=0, column=1, sticky="w", padx=(8, 0))
        content_row += 1

        make_button(
            card,
            "Book Now" if item["status"] == "Available" else "Unavailable for Selected Date",
            (lambda asset=item: self._book(asset)) if item["status"] == "Available" else (lambda: None),
            color=TEAL if item["status"] == "Available" else "#D7E2E0",
            hover=TEAL_DARK if item["status"] == "Available" else "#D7E2E0",
            fg=WHITE if item["status"] == "Available" else SUBTEXT,
            state="normal" if item["status"] == "Available" else "disabled",
            height=36,
        ).grid(row=content_row, column=0, sticky="ew", padx=18, pady=(8, 12))
        content_row += 1

        chip_row = ctk.CTkFrame(card, fg_color="transparent")
        chip_row.grid(row=content_row, column=0, sticky="w", padx=18, pady=(0, 16))
        chip_labels = DESTINATIONS[:3]
        for chip_index, chip_text in enumerate(chip_labels):
            bg_color, fg_color = DESTINATION_CHIP_COLORS[chip_index % len(DESTINATION_CHIP_COLORS)]
            info_chip(chip_row, chip_text.replace(" Area", ""), bg_color, fg_color).grid(
                row=0,
                column=chip_index,
                padx=(0, 8),
            )

    def _render_destination_card(self, index: int, item: dict):
        card = make_card(self._scroll)
        card.grid(row=index // 2 + 1, column=index % 2, sticky="nsew", padx=8, pady=8)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkFrame(card, fg_color=TEAL_LINE, height=4, corner_radius=16).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=1,
            pady=(1, 0),
        )

        content_row = 1
        if item.get("image"):
            image = make_image(card, item["image"], size=(350, 152), alt=f"{item['name']} destination photo")
            image.grid(row=content_row, column=0, sticky="ew", padx=12, pady=(14, 8))
            content_row += 1

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.grid(row=content_row, column=0, sticky="ew", padx=18, pady=(12, 0))
        header.grid_columnconfigure(0, weight=1)
        make_label(
            header,
            f"{item['id']} | {item['name']}",
            15,
            "bold",
        ).grid(row=0, column=0, sticky="w")
        info_chip(header, "Info Only", TEAL_LIGHT, TEAL_DARK).grid(row=0, column=1, sticky="e")
        content_row += 1

        make_label(
            card,
            item.get("summary", "Scenic floating cottage stop."),
            12,
            color=TEXT,
            wraplength=340,
            justify="left",
        ).grid(row=content_row, column=0, sticky="w", padx=18, pady=(6, 8))
        content_row += 1

        highlights = ctk.CTkFrame(card, fg_color="transparent")
        highlights.grid(row=content_row, column=0, sticky="w", padx=18, pady=(0, 10))
        for chip_index, chip_text in enumerate(item.get("highlights", ())[:3]):
            bg_color, fg_color = DESTINATION_CHIP_COLORS[chip_index % len(DESTINATION_CHIP_COLORS)]
            info_chip(highlights, chip_text, bg_color, fg_color).grid(
                row=0,
                column=chip_index,
                padx=(0, 8),
            )
        content_row += 1

        make_label(
            card,
            item.get(
                "booking_note",
                "Included in your floating cottage experience. No separate destination booking is required.",
            ),
            11,
            color=SUBTEXT,
            wraplength=340,
            justify="left",
        ).grid(row=content_row, column=0, sticky="w", padx=18, pady=(0, 10))
        content_row += 1

        if not self._has_image_file(item.get("image")):
            make_label(
                card,
                item.get("image_hint", "Upload a destination photo later."),
                10,
                color=SUBTEXT,
                wraplength=340,
                justify="left",
            ).grid(row=content_row, column=0, sticky="w", padx=18, pady=(0, 16))

    def _has_image_file(self, image_path: str | None) -> bool:
        if not image_path:
            return False
        guest_root = Path(__file__).resolve().parent.parent
        project_root = guest_root.parent
        return any(
            candidate.exists()
            for candidate in (
                guest_root / image_path,
                project_root / image_path,
            )
        )

    def _book(self, item: dict):
        from views.booking_view import BookingView

        self.app.navigate(BookingView, cottage=item, draft={"travel_date": self.travel_date_var.get()})

    def _go(self, dest: str):
        from views.my_bookings_view import MyBookingsView
        from views.profile_view import ProfileView

        routes = {
            "my_bookings": MyBookingsView,
            "profile": ProfileView,
        }
        cls = routes.get(dest)
        if cls is not None:
            self.app.navigate(cls)
