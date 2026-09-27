"""Guest reservation form for a selected cottage."""

from __future__ import annotations

from datetime import date, timedelta

import customtkinter as ctk

from controllers.booking_controller import BookingController
from k3_rms.widgets.date_picker import DatePickerField
from models.cottage_model import DESTINATIONS, DURATIONS, PARTY_SIZES, SLOTS
from utils.theme import (
    BG,
    CARD,
    DIVIDER,
    DANGER,
    SAND,
    SAND_DARK,
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
    make_dropdown,
    make_image,
    make_label,
)


class BookingView(ctk.CTkFrame):
    SHELL_TITLE = "Reservation Studio"
    SIDEBAR_ACTIVE = "browse"
    SHOW_SIDEBAR = True

    def __init__(self, parent, app, cottage: dict, draft: dict | None = None):
        super().__init__(parent, fg_color=BG)
        self.app = app
        self.cottage = cottage
        self.ctrl = BookingController(app)
        self.draft = draft or {}
        self.destination_labels = [self._destination_label(name) for name in DESTINATIONS]
        self.destination_lookup = dict(zip(self.destination_labels, DESTINATIONS))
        self.travel_date_var = ctk.StringVar(
            value=self.draft.get("travel_date", (date.today() + timedelta(days=1)).isoformat())
        )
        # Multi-destination state
        self.selected_destinations = {dest: False for dest in DESTINATIONS}
        if self.draft.get("destinations"):
            for d in self.draft["destinations"]:
                if d in self.selected_destinations:
                    self.selected_destinations[d] = True
        elif self.draft.get("destination"):
            if self.draft["destination"] in self.selected_destinations:
                self.selected_destinations[self.draft["destination"]] = True
        else:
            self.selected_destinations[DESTINATIONS[0]] = True

        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_strip()
        self._build_workspace()
        self._restore_draft()

    def _build_strip(self):
        from views.browse_view import BrowseView

        strip = ctk.CTkFrame(self, fg_color=TEAL_LIGHT, corner_radius=0, height=46)
        strip.grid(row=0, column=0, sticky="ew")
        strip.grid_columnconfigure(0, weight=1)
        strip.grid_propagate(False)

        trail = ctk.CTkFrame(strip, fg_color="transparent")
        trail.grid(row=0, column=0, sticky="w", padx=14)

        make_button(
            trail,
            "< Back to Browse",
            lambda: self.app.navigate(BrowseView),
            color="transparent",
            hover="#C9E8E4",
            fg=TEAL_DARK,
            height=30,
            width=138,
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=0, sticky="w")
        make_label(trail, "|", 12, "bold", color=SUBTEXT).grid(row=0, column=1, padx=8)
        make_label(
            trail,
            "Reservation Studio",
            12,
            "bold",
            color=TEAL_DARK,
        ).grid(row=0, column=2, sticky="w")

    def _build_workspace(self):
        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.grid(row=1, column=0, sticky="nsew", padx=16, pady=14)
        outer.grid_columnconfigure(0, weight=7)
        outer.grid_columnconfigure(1, weight=5)
        outer.grid_rowconfigure(0, weight=1)

        left = ctk.CTkScrollableFrame(
            outer,
            fg_color="transparent",
            scrollbar_button_color="#A9CCC5",
            scrollbar_button_hover_color=TEAL,
        )
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.grid_columnconfigure((0, 1), weight=1)

        make_label(left, "Reservation Studio", 22, "bold", color=TEXT).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(4, 2),
        )
        make_label(
            left,
            "Review your details first, then confirm the booking on the next screen.",
            12,
            color=SUBTEXT,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 14))

        user = self.app.session_user or {}
        info_card = ctk.CTkFrame(left, fg_color=TEAL_LIGHT, corner_radius=14)
        info_card.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        info_card.grid_columnconfigure(0, weight=1)
        make_label(info_card, "Booking As", 12, "bold", color=TEAL_DARK).grid(
            row=0,
            column=0,
            sticky="w",
            padx=16,
            pady=(12, 4),
        )
        make_label(
            info_card,
            f"{user.get('name', '')}  |  {user.get('contact', '')}  |  {user.get('email', '')}",
            12,
            color=TEXT,
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

        destination_note = ctk.CTkFrame(left, fg_color=TEAL_LIGHT, corner_radius=12)
        destination_note.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        destination_note.grid_columnconfigure(0, weight=1)
        make_label(destination_note, "Destination Guide", 12, "bold", color=TEAL_DARK).grid(
            row=0,
            column=0,
            sticky="w",
            padx=16,
            pady=(12, 4),
        )
        make_label(
            destination_note,
            "Your cottage reservation already covers the trip. Choose a preferred stop below for planning only.",
            11,
            color=TEXT,
            wraplength=520,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

        make_label(left, "Preferred Stop", 12, "bold").grid(row=4, column=0, sticky="w", pady=(0, 4))
        make_label(left, "Departure Slot", 12, "bold").grid(row=4, column=1, sticky="w", padx=(8, 0), pady=(0, 4))

        self.dest_buttons = {}
        dest_container = ctk.CTkFrame(left, fg_color="transparent")
        dest_container.grid(row=5, column=0, sticky="ew", padx=(0, 8), pady=(0, 12))
        
        for i, dest in enumerate(DESTINATIONS):
            btn = ctk.CTkButton(
                dest_container,
                text=self._destination_label(dest),
                width=80,
                height=42,
                corner_radius=10,
                font=("Segoe UI", 10, "bold"),
                command=lambda d=dest: self._toggle_destination(d)
            )
            btn.grid(row=i // 3, column=i % 3, padx=(0, 6), pady=4, sticky="w")
            self.dest_buttons[dest] = btn
        self._update_dest_button_styles()

        self.dd_slot = make_dropdown(left, SLOTS)
        self.dd_slot.set("08:00")
        self.dd_slot.grid(row=5, column=1, sticky="ew", padx=(8, 0), pady=(0, 12))

        make_label(left, "Travel Date", 12, "bold").grid(
            row=6,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 4),
        )
        self.date_picker = DatePickerField(
            left,
            variable=self.travel_date_var,
            min_date=date.today(),
            get_status_map=self._date_status_map,
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
        self.date_picker.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        make_label(left, "Duration (hours)", 12, "bold").grid(row=8, column=0, sticky="w", pady=(0, 4))
        self.dd_dur = make_dropdown(left, DURATIONS, command=self._on_duration_change)
        self.dd_dur.set("4")
        self.dd_dur.grid(row=9, column=0, sticky="ew", padx=(0, 8), pady=(0, 12))

        make_label(left, "Party Size", 12, "bold").grid(row=8, column=1, sticky="w", padx=(8, 0), pady=(0, 4))
        self.dd_party = make_dropdown(left, PARTY_SIZES)
        self.dd_party.set("2")
        self.dd_party.grid(row=9, column=1, sticky="ew", padx=(8, 0), pady=(0, 12))

        make_label(left, "Notes / Special Request", 12, "bold").grid(
            row=10,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 4),
        )
        self.txt_notes = ctk.CTkTextbox(
            left,
            height=98,
            fg_color=SAND,
            border_color=SAND_DARK,
            border_width=1,
            corner_radius=10,
            text_color=TEXT,
            font=("Segoe UI", 12),
        )
        self.txt_notes.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(0, 14))

        self.lbl_err = make_label(left, "", 11, color=DANGER)
        self.lbl_err.grid(row=12, column=0, columnspan=2, sticky="w", pady=(0, 8))

        make_button(left, "Review Booking", self._confirm, height=42).grid(
            row=13,
            column=0,
            columnspan=2,
            sticky="ew",
        )

        right = ctk.CTkFrame(outer, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)

        summary_card = make_card(right)
        summary_card.grid(row=0, column=0, sticky="new")
        summary_card.grid_columnconfigure(0, weight=1)
        accent = ctk.CTkFrame(summary_card, fg_color=TEAL_LINE, height=4, corner_radius=18)
        accent.grid(row=0, column=0, sticky="ew", padx=1, pady=(1, 0))

        row_index = 1
        if self.cottage.get("image"):
            preview = make_image(summary_card, self.cottage["image"], size=(260, 150), alt=self.cottage["name"])
            preview.grid(row=row_index, column=0, sticky="ew", padx=16, pady=(12, 8))
            row_index += 1

        make_label(summary_card, "Selected Cottage", 11, color=SUBTEXT).grid(
            row=row_index,
            column=0,
            sticky="w",
            padx=18,
            pady=(12, 4),
        )
        row_index += 1
        make_label(
            summary_card,
            f"{self.cottage['id']} | {self.cottage['name']}",
            16,
            "bold",
        ).grid(row=row_index, column=0, sticky="w", padx=18)
        row_index += 1
        make_label(
            summary_card,
            f"Capacity: {self.cottage['capacity']} pax",
            12,
            color=SUBTEXT,
        ).grid(row=row_index, column=0, sticky="w", padx=18, pady=(4, 10))
        row_index += 1

        ctk.CTkFrame(summary_card, height=1, fg_color=DIVIDER).grid(
            row=row_index,
            column=0,
            sticky="ew",
            padx=18,
            pady=(0, 12),
        )
        row_index += 1

        make_label(summary_card, f"Base Rate: PHP {self.cottage['rate']:,.2f} / hr", 12).grid(
            row=row_index,
            column=0,
            sticky="w",
            padx=18,
            pady=(0, 4),
        )
        row_index += 1
        self.lbl_total = make_label(
            summary_card,
            f"Estimated Total: PHP {self.cottage['rate'] * 4:,.2f}",
            15,
            "bold",
            color=TEAL_DARK,
        )
        self.lbl_total.grid(row=row_index, column=0, sticky="w", padx=18, pady=(0, 12))
        row_index += 1

        ctk.CTkFrame(summary_card, height=1, fg_color=DIVIDER).grid(
            row=row_index,
            column=0,
            sticky="ew",
            padx=18,
            pady=(0, 12),
        )
        row_index += 1

        make_label(summary_card, "Booking Guide", 13, "bold").grid(
            row=row_index,
            column=0,
            sticky="w",
            padx=18,
            pady=(0, 6),
        )
        row_index += 1
        guide_items = [
            ("Green", "Available"),
            ("Amber", "Reserved"),
            ("Blue", "On Going"),
            ("Slots", "Day tours run from 6AM to 4PM"),
        ]
        for label, value in guide_items:
            row = ctk.CTkFrame(summary_card, fg_color="transparent")
            row.grid(row=row_index, column=0, sticky="ew", padx=18, pady=2)
            make_label(row, f"{label}:", 11, "bold").grid(row=0, column=0, sticky="w", padx=(0, 6))
            make_label(row, value, 11, color=SUBTEXT).grid(row=0, column=1, sticky="w")
            row_index += 1

        chip_row = ctk.CTkFrame(summary_card, fg_color="transparent")
        chip_row.grid(row=row_index, column=0, sticky="w", padx=18, pady=(10, 14))
        for index, destination in enumerate(DESTINATIONS[:3]):
            colors = (
                ("#E8F7F5", TEAL_DARK),
                ("#EAF2FB", "#5A84B8"),
                ("#FFF3E8", "#C68A52"),
            )[index]
            info_chip(chip_row, destination.replace(" Area", ""), colors[0], colors[1]).grid(
                row=0,
                column=index,
                padx=(0, 8),
            )

    def _restore_draft(self):
        if not self.draft:
            self._on_duration_change(self.dd_dur.get())
            return
        self.dd_slot.set(self.draft.get("slot", "08:00"))
        self.dd_dur.set(str(self.draft.get("hours", "4")))
        self.dd_party.set(str(self.draft.get("party", "2")))
        self.txt_notes.insert("1.0", self.draft.get("notes", ""))
        self._on_duration_change(self.dd_dur.get())

    def _toggle_destination(self, dest):
        self.selected_destinations[dest] = not self.selected_destinations[dest]
        if not any(self.selected_destinations.values()):
            self.selected_destinations[dest] = True
        self._update_dest_button_styles()
        self._on_duration_change(self.dd_dur.get())

    def _update_dest_button_styles(self):
        from k3_user.models.cottage_model import BoatModel
        all_boats = {b["name"]: b for b in BoatModel.get_all()}
        
        for dest, btn in self.dest_buttons.items():
            asset = all_boats.get(dest)
            rate = float(asset["rate"]) if asset else 0
            price_text = f"\n+PHP {rate:,.0f}" if rate > 0 else "\nIncluded"
            
            display_text = f"{self._destination_label(dest)}{price_text}"
            btn.configure(text=display_text)
            
            if self.selected_destinations[dest]:
                btn.configure(fg_color=TEAL, hover_color=TEAL_DARK, text_color=WHITE)
            else:
                btn.configure(fg_color=WHITE, hover_color=TEAL_LIGHT, text_color=TEXT)

    def _on_duration_change(self, value):
        try:
            # Sum up destination rates
            from k3_user.models.cottage_model import BoatModel
            all_boats = BoatModel.get_all()
            selected_names = [d for d, active in self.selected_destinations.items() if active]
            selected_assets = [b for b in all_boats if b["name"] in selected_names]
            
            total = self.ctrl.calculate_total(self.cottage, selected_assets, int(value))
            self.lbl_total.configure(text=f"Estimated Total: PHP {total:,.2f}")
        except Exception:
            pass

    def _confirm(self):
        selected_names = [d for d, active in self.selected_destinations.items() if active]
        ok, msg, draft = self.ctrl.prepare_booking(
            cottage=self.cottage,
            destinations=selected_names,
            travel_date=self.travel_date_var.get(),
            slot=self.dd_slot.get(),
            hours=int(self.dd_dur.get()),
            party=int(self.dd_party.get()),
            notes=self.txt_notes.get("1.0", "end").strip(),
        )
        if not ok:
            self.lbl_err.configure(text=msg)
            return

        self.lbl_err.configure(text="")
        from views.confirm_view import ConfirmView

        self.app.navigate(ConfirmView, booking_draft=draft)

    def _date_status_map(self) -> dict[str, str]:
        from models.reservation_model import ReservationModel

        return ReservationModel.get_date_status_map(cottage_id=self.cottage["id"])

    def _selected_destination(self) -> str:
        return self.destination_lookup.get(self.seg_dest.get(), DESTINATIONS[0])

    def _destination_label(self, value: str) -> str:
        return value.replace(" Area", "")
