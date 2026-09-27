"""User profile screen with edit form and booking summary."""

from __future__ import annotations

import customtkinter as ctk

from controllers.booking_controller import BookingController
from controllers.login_controller import LoginController
from utils.theme import (
    BG,
    DIVIDER,
    DANGER,
    SUBTEXT,
    TEAL,
    TEAL_DARK,
    TEAL_LINE,
    TEXT,
    make_button,
    make_card,
    make_entry,
    make_label,
    top_strip,
)


class ProfileView(ctk.CTkFrame):
    SHELL_TITLE = "My Profile"
    SIDEBAR_ACTIVE = "profile"
    SHOW_SIDEBAR = True

    def __init__(self, parent, app):
        super().__init__(parent, fg_color=BG)
        self.app = app
        self.booking_ctrl = BookingController(app)
        self.login_ctrl = LoginController(app)
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        strip = top_strip(
            self,
            "My Profile",
            "Manage your bookings and account details.",
        )
        strip.grid(row=0, column=0, sticky="ew")

        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color="#A9CCC5",
            scrollbar_button_hover_color=TEAL,
        )
        scroll.grid(row=1, column=0, sticky="nsew", padx=18, pady=18)
        scroll.grid_columnconfigure(0, weight=1)

        self._render_edit_section(scroll)
        self._render_booking_section(scroll)

    def _render_edit_section(self, parent):
        user = self.app.session_user or {}

        make_label(parent, "Edit Account Details", 16, "bold", color=TEXT).grid(
            row=0,
            column=0,
            sticky="w",
            padx=10,
            pady=(0, 12),
        )

        form = make_card(parent)
        form.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 24))
        form.grid_columnconfigure((0, 1), weight=1)

        make_label(form, "Full Name", 12, "bold").grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(18, 4))
        self.e_name = make_entry(form)
        self.e_name.insert(0, user.get("name", ""))
        self.e_name.grid(row=1, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 12))

        make_label(form, "Email Address", 12, "bold").grid(row=2, column=0, sticky="w", padx=18, pady=(0, 4))
        self.e_email = make_entry(form)
        self.e_email.insert(0, user.get("email", ""))
        self.e_email.grid(row=3, column=0, sticky="ew", padx=(18, 8), pady=(0, 12))

        make_label(form, "Contact Number", 12, "bold").grid(row=2, column=1, sticky="w", padx=(8, 18), pady=(0, 4))
        self.e_phone = make_entry(form)
        self.e_phone.insert(0, user.get("contact", ""))
        self.e_phone.grid(row=3, column=1, sticky="ew", padx=(8, 18), pady=(0, 12))

        make_label(form, "New Password (leave blank to keep current)", 12, "bold").grid(
            row=4,
            column=0,
            sticky="w",
            padx=18,
            pady=(0, 4),
        )
        self.e_pass = make_entry(form, "Enter a new password")
        self.e_pass.configure(show="*")
        self.e_pass.grid(row=5, column=0, sticky="ew", padx=(18, 8), pady=(0, 12))

        make_label(form, "Confirm New Password", 12, "bold").grid(
            row=4,
            column=1,
            sticky="w",
            padx=(8, 18),
            pady=(0, 4),
        )
        self.e_conf = make_entry(form, "Repeat the new password")
        self.e_conf.configure(show="*")
        self.e_conf.grid(row=5, column=1, sticky="ew", padx=(8, 18), pady=(0, 12))

        self.lbl_status = make_label(form, "", 11, color=SUBTEXT)
        self.lbl_status.grid(row=6, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 10))

        make_button(form, "Save Changes", self._save_profile, height=44).grid(
            row=7,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=18,
            pady=(0, 18),
        )

    def _render_booking_section(self, parent):
        make_label(parent, "Current Booking", 16, "bold", color=TEXT).grid(
            row=2,
            column=0,
            sticky="w",
            padx=10,
            pady=(0, 12),
        )

        card = make_card(parent)
        card.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 18))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkFrame(card, fg_color=TEAL_LINE, height=4, corner_radius=16).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=1,
            pady=(1, 0),
        )

        reservations = self.booking_ctrl.get_my_reservations()
        if not reservations:
            make_label(card, "No booking available.", 13, color=SUBTEXT).grid(
                row=1,
                column=0,
                pady=28,
            )
            return

        current = reservations[-1]
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.grid(row=1, column=0, sticky="ew", padx=18, pady=16)
        content.grid_columnconfigure(0, weight=1)

        make_label(content, current["cottage_name"], 15, "bold").grid(row=0, column=0, sticky="w")
        make_label(content, f"{current['date']} @ {current['slot']}", 12, color=SUBTEXT).grid(
            row=0,
            column=1,
            sticky="w",
            padx=14,
        )
        make_button(
            content,
            "View Details",
            self._go_bookings,
            color="#E8F7F5",
            hover="#D8F2EF",
            fg=TEAL_DARK,
            width=104,
            height=32,
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=2, sticky="e")

    def _save_profile(self):
        user = self.app.session_user
        ok, msg = self.login_ctrl.update_profile(
            username=user["username"],
            name=self.e_name.get(),
            email=self.e_email.get(),
            contact=self.e_phone.get(),
            password=self.e_pass.get(),
            confirm_password=self.e_conf.get(),
        )

        self.lbl_status.configure(text=msg, text_color=(TEAL_DARK if ok else DANGER))
        if ok:
            self.e_pass.delete(0, "end")
            self.e_conf.delete(0, "end")
            self.app._refresh_sidebar_profile()
            
            from tkinter import messagebox
            messagebox.showinfo("Success", "Profile updated successfully.")

    def _go_bookings(self):
        from views.my_bookings_view import MyBookingsView

        self.app.navigate(MyBookingsView)
