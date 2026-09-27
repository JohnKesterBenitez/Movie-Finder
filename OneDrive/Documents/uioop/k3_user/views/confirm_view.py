"""Guest booking review and confirmation screen."""

from __future__ import annotations

import customtkinter as ctk

from controllers.booking_controller import BookingController
from utils.theme import (
    BG,
    CARD,
    DANGER,
    DIVIDER,
    SUBTEXT,
    TEAL,
    TEAL_DARK,
    TEAL_LIGHT,
    TEXT,
    WHITE,
    make_button,
    make_card,
    make_label,
)


class ConfirmView(ctk.CTkFrame):
    SHELL_TITLE = "Booking Review"
    SIDEBAR_ACTIVE = None
    SHOW_SIDEBAR = False

    def __init__(
        self,
        parent,
        app,
        reservation: dict | None = None,
        booking_draft: dict | None = None,
    ):
        super().__init__(parent, fg_color=BG)
        self.app = app
        self.ctrl = BookingController(app)
        self.reservation = reservation
        self.booking_draft = booking_draft
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        ctk.CTkFrame(
            self,
            width=280,
            height=280,
            corner_radius=140,
            fg_color=TEAL_LIGHT,
        ).place(x=-120, y=-40)

        body = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color="#A9CCC5",
            scrollbar_button_hover_color=TEAL,
        )
        body.grid(row=0, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        card = make_card(body, width=560)
        card.grid(row=0, column=0, sticky="n", padx=28, pady=22)
        card.grid_columnconfigure(0, weight=1)

        is_confirmed = self.reservation is not None
        if is_confirmed:
            icon_holder = ctk.CTkFrame(card, fg_color=TEAL_LIGHT, width=72, height=72, corner_radius=36)
            icon_holder.grid(row=0, column=0, pady=(18, 10))
            icon_holder.grid_propagate(False)
            make_label(icon_holder, "OK", 19, "bold", color=TEAL_DARK).place(relx=0.5, rely=0.5, anchor="center")
            make_label(card, "Reservation Confirmed!", 21, "bold", color=TEAL_DARK).grid(row=1, column=0, pady=(0, 3))
            make_label(
                card,
                f"Reference: {self.reservation['ref']}",
                12,
                color=SUBTEXT,
                wraplength=460,
                justify="center",
            ).grid(row=2, column=0, pady=(0, 14))
        else:
            make_label(card, "Review", 16, "bold", color=TEAL_DARK).grid(row=0, column=0, pady=(18, 4))
            make_label(card, "Review Your Booking", 21, "bold", color=TEAL_DARK).grid(row=1, column=0, pady=(0, 3))
            make_label(
                card,
                "Check the details below, then finalize the booking.",
                12,
                color=SUBTEXT,
                wraplength=420,
                justify="center",
            ).grid(row=2, column=0, pady=(0, 16))

        details = ctk.CTkFrame(card, fg_color=TEAL_LIGHT, corner_radius=14)
        details.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 12))
        details.grid_columnconfigure(0, weight=1)
        details.grid_columnconfigure(1, weight=1)

        for index, (label, value) in enumerate(self._detail_rows()):
            top_pad = 14 if index == 0 else 9
            make_label(details, label, 11, color=SUBTEXT).grid(
                row=index,
                column=0,
                sticky="w",
                padx=18,
                pady=(top_pad, 0),
            )
            make_label(details, value, 12, "bold", color=TEXT).grid(
                row=index,
                column=1,
                sticky="e",
                padx=18,
                pady=(top_pad, 0),
            )

        ctk.CTkFrame(details, fg_color="transparent", height=14).grid(
            row=len(self._detail_rows()),
            column=0,
            columnspan=2,
        )

        self.error_label = make_label(card, "", 11, color=DANGER)
        self.error_label.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 8))

        button_row = ctk.CTkFrame(card, fg_color="transparent")
        button_row.grid(row=5, column=0, sticky="ew", padx=18, pady=(0, 18))
        button_row.grid_columnconfigure((0, 1), weight=1)

        if is_confirmed:
            make_button(
                button_row,
                "Back",
                lambda: self._go("back"),
                color=TEAL_LIGHT,
                hover="#CBEAE6",
                fg=TEAL_DARK,
                height=42,
            ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
            make_button(
                button_row,
                "Generate Receipt",
                self._generate_receipt,
                height=42,
            ).grid(row=0, column=1, sticky="ew", padx=(6, 0))
        else:
            make_button(
                button_row,
                "Back to Edit",
                lambda: self._go("edit"),
                color=TEAL_LIGHT,
                hover="#CBEAE6",
                fg=TEAL_DARK,
                height=42,
            ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
            make_button(
                button_row,
                "Confirm Booking",
                self._submit_booking,
                height=42,
            ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def _detail_rows(self) -> list[tuple[str, str]]:
        if self.reservation is not None:
            return [
                ("Guest", self.reservation["name"]),
                ("Contact", self.reservation["contact"]),
                ("Cottage", f"{self.reservation['cottage_id']} | {self.reservation['cottage_name']}"),
                ("Destinations", self.reservation["destination"]),
                ("Date", self.reservation["date"]),
                ("Departure", self.reservation["slot"]),
                ("Duration", f"{self.reservation['hours']} hour(s)"),
                ("Party Size", f"{self.reservation['party']} pax"),
                ("Total", f"PHP {self.reservation['total']:,.2f}"),
            ]

        draft = self.booking_draft or {}
        guest = draft.get("guest_info", {})
        cottage = draft.get("cottage", {})
        
        # Format destinations for display
        dest_val = ""
        if "destinations" in draft:
            dest_val = ", ".join(draft["destinations"])
        else:
            dest_val = draft.get("destination", "")

        return [
            ("Guest", guest.get("name", "")),
            ("Contact", guest.get("contact", "")),
            ("Cottage", f"{cottage.get('id', '')} | {cottage.get('name', '')}"),
            ("Destinations", dest_val),
            ("Date", draft.get("travel_date", "")),
            ("Departure", draft.get("slot", "")),
            ("Duration", f"{draft.get('hours', 0)} hour(s)"),
            ("Party Size", f"{draft.get('party', 0)} pax"),
            ("Total", f"PHP {float(draft.get('total', 0)):,.2f}"),
        ]

    def _generate_receipt(self):
        if not self.reservation:
            return
        
        try:
            import os
            from fpdf import FPDF
            from tkinter import messagebox
            
            res = self.reservation
            pdf = FPDF()
            pdf.add_page()
            
            # Colors
            TEAL_RGB = (45, 115, 105)
            GRAY_RGB = (100, 100, 100)
            BLACK_RGB = (50, 50, 50)
            
            # Header
            pdf.set_font("Helvetica", "B", 22)
            pdf.set_text_color(*TEAL_RGB)
            pdf.cell(0, 20, "ISLABOOK RESERVATION", new_x="LMARGIN", new_y="NEXT", align="C")
            
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(*GRAY_RGB)
            pdf.cell(0, 10, f"Booking Receipt: {res['ref']}", new_x="LMARGIN", new_y="NEXT", align="C")
            pdf.ln(10)
            
            # Line
            pdf.set_draw_color(200, 200, 200)
            pdf.line(20, 50, 190, 50)
            pdf.ln(5)
            
            # Details Table-like layout
            def add_row(label, value):
                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(*BLACK_RGB)
                pdf.cell(50, 10, label, new_x="RIGHT", new_y="TOP")
                pdf.set_font("Helvetica", "", 11)
                pdf.cell(0, 10, str(value), new_x="LMARGIN", new_y="NEXT")
            
            add_row("Guest Name:", res['name'])
            add_row("Contact No:", res['contact'])
            add_row("Email:", res['email'] if res.get('email') else "N/A")
            add_row("Cottage:", f"{res['cottage_id']} | {res['cottage_name']}")
            
            # Multi-line destinations
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(50, 10, "Destinations:", new_x="RIGHT", new_y="TOP")
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 10, res['destination'])
            
            add_row("Travel Date:", res['date'])
            add_row("Departure Time:", res['slot'])
            add_row("Duration:", f"{res['hours']} hour(s)")
            add_row("Party Size:", f"{res['party']} pax")
            
            pdf.ln(10)
            pdf.set_draw_color(*TEAL_RGB)
            pdf.set_line_width(0.5)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(5)
            
            # Total
            pdf.set_font("Helvetica", "B", 16)
            pdf.set_text_color(*BLACK_RGB)
            pdf.cell(100, 15, "TOTAL PRICE PAID:", new_x="RIGHT", new_y="TOP")
            pdf.set_text_color(*TEAL_RGB)
            pdf.cell(0, 15, f"PHP {res['total']:,.2f}", new_x="LMARGIN", new_y="NEXT", align="R")
            
            pdf.ln(20)
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(128, 128, 128)
            pdf.cell(0, 10, "Thank you for choosing K3's Floating Cottage!", new_x="LMARGIN", new_y="NEXT", align="C")
            pdf.cell(0, 10, f"Generated on: {res['created_at']}", new_x="LMARGIN", new_y="NEXT", align="C")

            # Ask user where to save
            from tkinter import filedialog
            filename = f"Receipt_{res['ref']}.pdf"
            path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile=filename,
                title="Save Receipt",
            )
            if not path:
                return  # User cancelled

            pdf.output(path)
            messagebox.showinfo("Receipt", f"PDF Receipt saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate PDF: {str(e)}")

    def _submit_booking(self):
        ok, msg, reservation = self.ctrl.submit_booking(self.booking_draft or {})
        if not ok:
            self.error_label.configure(text=msg)
            return

        self.error_label.configure(text="")
        self.app.navigate(type(self), reservation=reservation)

    def _go(self, dest: str):
        from views.booking_view import BookingView
        from views.browse_view import BrowseView
        from views.my_bookings_view import MyBookingsView

        if dest == "edit":
            self.app.navigate(
                BookingView,
                cottage=self.booking_draft["cottage"],
                draft=self.booking_draft,
            )
            return
        if dest == "back" or dest == "book_again":
            self.app.navigate(BrowseView)
            return
        if dest == "my_bookings":
            self.app.navigate(MyBookingsView)
