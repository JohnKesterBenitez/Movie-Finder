"""
Asset dashboard showing stats, cottages, and destinations.
"""

import customtkinter as ctk

from models.cottage_model import BoatModel, CottageModel
from models.reservation_model import ReservationModel
from utils.theme import (
    BG,
    DIVIDER,
    SUBTEXT,
    TEAL_DARK,
    TEAL_LIGHT,
    TEXT,
    WHITE,
    make_button,
    make_label,
    make_status_badge,
)


class DashboardView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=BG)
        self.app = app
        self._build()

    def _build(self):
        from views.home_view import HomeView

        nav = ctk.CTkFrame(self, fg_color=TEAL_LIGHT, height=56, corner_radius=0)
        nav.pack(fill="x")
        nav.pack_propagate(False)

        make_label(nav, "Dashboard", 15, "bold", color=TEAL_DARK).place(
            x=24,
            rely=0.5,
            anchor="w",
        )

        make_button(
            nav,
            "Back",
            lambda: self.app.navigate(HomeView),
            color="transparent",
            hover="#BFE5E0",
            fg=TEAL_DARK,
            width=90,
            height=36,
        ).place(relx=1.0, x=-20, rely=0.5, anchor="e")

        scroll = ctk.CTkScrollableFrame(self, fg_color=BG)
        scroll.pack(fill="both", expand=True, padx=0, pady=0)
        scroll.grid_columnconfigure(0, weight=1)

        body = ctk.CTkFrame(scroll, fg_color="transparent")
        body.grid(row=0, column=0, sticky="ew", padx=40, pady=24)
        body.grid_columnconfigure(0, weight=1)

        make_label(body, "Asset Dashboard", 22, "bold", color=TEXT).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 16),
        )

        all_reservations = ReservationModel.get_all()
        completed = len([item for item in all_reservations if item.get("status") == "Completed"])
        cancelled = len([item for item in all_reservations if item.get("status") == "Cancelled"])
        live = len([item for item in all_reservations if item.get("status") in ("Confirmed", "On Going", "Reserved")])

        stats_row = ctk.CTkFrame(body, fg_color="transparent")
        stats_row.grid(row=1, column=0, sticky="ew", pady=(0, 28))
        stats_row.grid_columnconfigure((0, 1, 2), weight=1)

        stat_data = [
            ("Completed Trips", completed, "#E8F6F4", "#C8E8E3", TEAL_DARK),
            ("Cancelled Trips", cancelled, "#FCE8E8", "#F5D0D0", "#C05050"),
            ("Live Reservations", live, "#E8F6F4", "#C8E8E3", TEAL_DARK),
        ]

        for index, (label, count, bg_color, border_color, text_color) in enumerate(stat_data):
            card = ctk.CTkFrame(
                stats_row,
                fg_color=bg_color,
                corner_radius=14,
                border_width=1,
                border_color=border_color,
                height=100,
            )
            card.grid(row=0, column=index, padx=6, sticky="ew")
            card.grid_propagate(False)

            make_label(card, label, 12, color=SUBTEXT).place(x=20, y=18)
            make_label(card, str(count), 32, "bold", color=text_color).place(x=20, y=48)

        self._build_asset_section(
            body,
            row=2,
            icon="C",
            title="Floating Cottages",
            items=CottageModel.get_all(),
        )
        self._build_asset_section(
            body,
            row=3,
            icon="D",
            title="Destinations",
            items=BoatModel.get_all(),
        )

    def _build_asset_section(self, parent, row, icon, title, items):
        section = ctk.CTkFrame(parent, fg_color="transparent")
        section.grid(row=row, column=0, sticky="ew", pady=(0, 20))
        section.grid_columnconfigure(0, weight=1)

        make_label(section, f"{icon}  {title}", 18, "bold", color=TEXT).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 12),
        )

        for index, item in enumerate(items):
            card = ctk.CTkFrame(
                section,
                fg_color=WHITE,
                corner_radius=14,
                border_width=1,
                border_color=DIVIDER,
            )
            card.grid(row=index + 1, column=0, sticky="ew", pady=4)
            card.grid_columnconfigure(0, weight=1)

            content = ctk.CTkFrame(card, fg_color="transparent")
            content.grid(row=0, column=0, sticky="ew", padx=20, pady=16)
            content.grid_columnconfigure(0, weight=1)

            make_label(
                content,
                f"{item['id']}  |  {item['name']}",
                14,
                "bold",
                color=TEXT,
            ).grid(row=0, column=0, sticky="w")
            make_label(
                content,
                f"Capacity {item['capacity']}  |  Base rate PHP {item['rate']:,.2f}",
                11,
                color=SUBTEXT,
            ).grid(row=1, column=0, sticky="w", pady=(2, 0))

            if item["status"] != "Available":
                make_status_badge(content, item["status"]).grid(
                    row=0,
                    column=1,
                    rowspan=2,
                    padx=(12, 0),
                )
