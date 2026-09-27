"""List all reservations of the logged-in user."""

from __future__ import annotations

import customtkinter as ctk

from controllers.booking_controller import BookingController
from utils.theme import (
    BG,
    CARD,
    DANGER,
    DANGER_SOFT,
    DIVIDER,
    SUBTEXT,
    TEAL,
    TEAL_DARK,
    TEAL_LIGHT,
    TEAL_LINE,
    TEXT,
    WHITE,
    make_button,
    make_card,
    make_label,
    make_status_badge,
    top_strip,
)


class MyBookingsView(ctk.CTkFrame):
    SHELL_TITLE = "My Bookings"
    SIDEBAR_ACTIVE = "bookings"
    SHOW_SIDEBAR = True

    def __init__(self, parent, app):
        super().__init__(parent, fg_color=BG)
        self.app = app
        self.ctrl = BookingController(app)
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        strip = top_strip(self, "My Bookings")
        strip.grid(row=0, column=0, sticky="ew")

        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color="#A9CCC5",
            scrollbar_button_hover_color=TEAL,
        )
        scroll.grid(row=1, column=0, sticky="nsew", padx=18, pady=18)
        scroll.grid_columnconfigure(0, weight=1)

        reservations = list(reversed(self.ctrl.get_my_reservations()))
        make_label(scroll, f"Your Reservations ({len(reservations)})", 16, "bold", color=TEXT).grid(
            row=0,
            column=0,
            sticky="w",
            padx=10,
            pady=(0, 14),
        )

        if not reservations:
            empty = make_card(scroll)
            empty.grid(row=1, column=0, sticky="ew", padx=8)
            empty.grid_columnconfigure(0, weight=1)
            make_label(empty, "You have no reservations yet.", 14, "bold", color=TEXT).grid(
                row=0,
                column=0,
                pady=(30, 6),
            )
            make_label(empty, "Create a reservation to see it here.", 12, color=SUBTEXT).grid(
                row=1,
                column=0,
                pady=(0, 16),
            )
            make_button(empty, "Make a Reservation", self._go_browse, width=220).grid(
                row=2,
                column=0,
                pady=(0, 28),
            )
            return

        for index, reservation in enumerate(reservations, start=1):
            card = make_card(scroll)
            card.grid(row=index, column=0, sticky="ew", padx=8, pady=8)
            card.grid_columnconfigure(0, weight=1)

            status = reservation.get("status", "Confirmed")
            accent_color = DANGER if status == "Cancelled" else TEAL_LINE
            ctk.CTkFrame(card, fg_color=accent_color, height=4, corner_radius=16).grid(
                row=0,
                column=0,
                sticky="ew",
                padx=1,
                pady=(1, 0),
            )

            header = ctk.CTkFrame(card, fg_color="transparent")
            header.grid(row=1, column=0, sticky="ew", padx=18, pady=(14, 2))
            header.grid_columnconfigure(0, weight=1)
            make_label(
                header,
                f"{reservation['cottage_id']} | {reservation['cottage_name']}",
                15,
                "bold",
            ).grid(row=0, column=0, sticky="w")
            make_status_badge(header, status).grid(row=0, column=1, sticky="e")

            make_label(
                card,
                f"Ref: {reservation['ref']}",
                11,
                color=SUBTEXT,
            ).grid(row=2, column=0, sticky="w", padx=18, pady=(0, 6))

            details = ctk.CTkFrame(card, fg_color="transparent")
            details.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 6))
            detail_values = [
                reservation["destination"],
                f"{reservation['date']}  {reservation['slot']}",
                f"{reservation['hours']} hr(s)",
                f"{reservation['party']} pax",
                f"PHP {reservation['total']:,.2f}",
            ]
            for column, value in enumerate(detail_values):
                make_label(details, value, 11, color=SUBTEXT).grid(
                    row=0,
                    column=column,
                    sticky="w",
                    padx=(0, 16),
                )

            ctk.CTkFrame(card, height=1, fg_color=DIVIDER).grid(
                row=4,
                column=0,
                sticky="ew",
                padx=18,
                pady=10,
            )

            booked_text = str(reservation.get("created_at", "")).replace("T", " ")
            make_label(
                card,
                f"Booked: {booked_text[:16]}",
                11,
                color=SUBTEXT,
            ).grid(row=5, column=0, sticky="w", padx=18, pady=(0, 16))

    def _go_browse(self):
        from views.browse_view import BrowseView

        self.app.navigate(BrowseView)
