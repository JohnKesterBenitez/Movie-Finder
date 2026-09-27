"""Guest notification centre — shows booking status updates."""

from __future__ import annotations

from datetime import datetime, timedelta

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


_STATUS_ICON = {
    "Pending": "⏳",
    "Reserved": "✅",
    "On Going": "🚀",
    "Completed": "🏁",
    "Cancelled": "🚫",
    "Rejected": "❌",
}

_STATUS_MESSAGE = {
    "Pending": "Your booking is pending approval. Please wait for the admin to review it.",
    "Reserved": "Great news! Your booking has been approved by the admin.",
    "On Going": "Your trip is now in progress. Enjoy!",
    "Completed": "Your trip has been completed. Thank you for choosing K3!",
    "Cancelled": "Your approved booking has been cancelled by the admin.",
    "Rejected": "Your booking request has been rejected by the admin.",
}

_STATUS_CARD_BG = {
    "Pending": "#FFF9E6",
    "Reserved": "#E2F7F3",
    "On Going": "#E8F0FB",
    "Completed": "#F2F4F5",
    "Cancelled": "#FBE7E6",
    "Rejected": "#F5E0E0",
}

_STATUS_ACCENT = {
    "Pending": "#D4A843",
    "Reserved": TEAL,
    "On Going": "#5A84B8",
    "Completed": "#91A4A8",
    "Cancelled": DANGER,
    "Rejected": "#C05050",
}


def _relative_time(value) -> str:
    if not isinstance(value, datetime):
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except (ValueError, TypeError):
                return ""
        else:
            return ""
    delta = datetime.now() - value
    if delta < timedelta(minutes=1):
        return "Just now"
    if delta < timedelta(hours=1):
        minutes = max(int(delta.total_seconds() // 60), 1)
        return f"{minutes} min ago"
    if delta < timedelta(days=1):
        hours = max(int(delta.total_seconds() // 3600), 1)
        return f"{hours} hr ago"
    if delta < timedelta(days=7):
        days = max(delta.days, 1)
        return f"{days} day{'s' if days != 1 else ''} ago"
    return value.strftime("%b %d, %Y")


class NotificationsView(ctk.CTkFrame):
    SHELL_TITLE = "Notifications"
    SIDEBAR_ACTIVE = "notifications"
    SHOW_SIDEBAR = True

    def __init__(self, parent, app):
        super().__init__(parent, fg_color=BG)
        self.app = app
        self.ctrl = BookingController(app)
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        strip = top_strip(self, "Notifications", "Stay updated on your booking and payment status")
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
        payments = self.ctrl.get_my_payments()
        notifications = self._build_notifications(reservations, payments)

        # Header with count
        header = ctk.CTkFrame(scroll, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=4, pady=(0, 14))
        header.grid_columnconfigure(0, weight=1)

        make_label(header, f"Updates ({len(notifications)})", 16, "bold", color=TEXT).grid(
            row=0, column=0, sticky="w",
        )

        make_button(
            header,
            "⟳  Refresh",
            lambda: self.app.navigate(NotificationsView),
            color=TEAL_LIGHT,
            hover="#BFE5E0",
            fg=TEAL_DARK,
            width=100,
            height=34,
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=1, sticky="e")

        if not notifications:
            empty = make_card(scroll)
            empty.grid(row=1, column=0, sticky="ew", padx=4)
            empty.grid_columnconfigure(0, weight=1)
            make_label(empty, "No notifications yet.", 14, "bold", color=TEXT).grid(
                row=0, column=0, pady=(30, 6),
            )
            make_label(empty, "Status updates and payment records will appear here.", 12, color=SUBTEXT).grid(
                row=1, column=0, pady=(0, 28),
            )
            return

        for idx, notif in enumerate(notifications, start=1):
            self._notification_card(scroll, notif, idx)

    def _build_notifications(self, reservations: list[dict], payments: list[dict]) -> list[dict]:
        notifications = []
        
        # Booking Status Notifications
        for r in reservations:
            status = r.get("status", "Pending")
            notes = r.get("notes", "") or ""
            created = r.get("created_at", "")

            display_status = status
            if status == "Cancelled" and "rejected" in notes.lower():
                display_status = "Rejected"

            if isinstance(created, str):
                try:
                    created_dt = datetime.fromisoformat(created)
                except (ValueError, TypeError):
                    created_dt = None
            else:
                created_dt = created

            notifications.append({
                "type": "status",
                "ref": r.get("ref", ""),
                "subtitle": f"{r.get('cottage_id', '')} • {r.get('cottage_name', '')} • {r.get('destination', '')}",
                "status": display_status,
                "created_at": created_dt,
                "icon": _STATUS_ICON.get(display_status, "📋"),
                "message": _STATUS_MESSAGE.get(display_status, "Status update for your booking."),
                "card_bg": _STATUS_CARD_BG.get(display_status, CARD),
                "accent": _STATUS_ACCENT.get(display_status, TEAL),
            })

        # Payment Transaction Notifications
        for p in payments:
            p_status = p.get("payment_status", "Unpaid")
            recorded = p.get("recorded_at")
            
            if isinstance(recorded, str):
                try:
                    recorded_dt = datetime.fromisoformat(recorded)
                except (ValueError, TypeError):
                    recorded_dt = None
            else:
                recorded_dt = recorded

            # Different styling for payment notifications
            icon = "🧾"
            if p_status == "Paid": icon = "✅"
            elif p_status == "Refunded": icon = "🔄"
            
            msg = f"Payment Transaction: {p_status}"
            details = f"Amount: PHP {float(p.get('payment_amount') or 0):,.2f} | Method: {p.get('payment_method') or 'Not Specified'} | Balance: PHP {float(p.get('balance_due') or 0):,.2f}"

            notifications.append({
                "type": "payment",
                "ref": p.get("reservation_code", ""),
                "subtitle": details,
                "status": p_status,
                "created_at": recorded_dt,
                "icon": icon,
                "message": msg,
                "card_bg": "#EEF7F2" if p_status == "Paid" else "#FDF5E0",
                "accent": "#4CAF50" if p_status == "Paid" else "#FF9800",
            })

        # Sort newest first
        notifications.sort(
            key=lambda n: n.get("created_at") or datetime.min,
            reverse=True,
        )
        return notifications

    def _notification_card(self, parent, notif: dict, idx: int):
        card = ctk.CTkFrame(
            parent,
            fg_color=notif["card_bg"],
            corner_radius=18,
            border_width=1,
            border_color=DIVIDER,
        )
        card.grid(row=idx, column=0, sticky="ew", padx=4, pady=(0, 10))
        card.grid_columnconfigure(0, weight=1)

        # Accent bar at top
        ctk.CTkFrame(
            card,
            fg_color=notif["accent"],
            height=4,
            corner_radius=16,
        ).grid(row=0, column=0, sticky="ew", padx=1, pady=(1, 0))

        # Header: Icon + Message + Time
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.grid(row=1, column=0, sticky="ew", padx=18, pady=(12, 4))
        header.grid_columnconfigure(0, weight=1)

        make_label(
            header,
            f"{notif['icon']}  {notif['message']}",
            13,
            "bold",
            color=TEXT,
        ).grid(row=0, column=0, sticky="w")

        time_text = _relative_time(notif["created_at"])
        if time_text:
            make_label(header, time_text, 11, color=SUBTEXT).grid(
                row=0, column=1, sticky="e", padx=(8, 0),
            )

        # Details
        details = ctk.CTkFrame(card, fg_color="transparent")
        details.grid(row=2, column=0, sticky="ew", padx=18, pady=(2, 4))

        detail_text = f"{notif['ref']}  •  {notif['subtitle']}"
        make_label(details, detail_text, 11, color=SUBTEXT).grid(
            row=0, column=0, sticky="w",
        )

        # Status badge
        badge_row = ctk.CTkFrame(card, fg_color="transparent")
        badge_row.grid(row=3, column=0, sticky="w", padx=18, pady=(2, 14))
        
        # Use existing status badge utility
        badge_text = notif["status"]
        if notif["type"] == "payment":
            badge_text = f"Payment: {badge_text}"
        
        make_status_badge(badge_row, notif["status"]).grid(row=0, column=0)
