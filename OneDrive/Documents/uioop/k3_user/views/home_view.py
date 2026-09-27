"""
views/home_view.py — Main landing page matching the K3 admin-style design.
"""

import os
import customtkinter as ctk
from PIL import Image
from utils.theme import (
    BG, WHITE, TEAL, TEAL_DARK, TEAL_LIGHT, TEXT, SUBTEXT, DANGER, DIVIDER,
    make_label, make_button
)
from models.cottage_model import CottageModel, BoatModel
from models.reservation_model import ReservationModel

# Resolve assets path relative to this file
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")


def _load_card_image(filename, size=(100, 100)):
    """Load an image from the assets folder and return a CTkImage, or None."""
    path = os.path.join(ASSETS_DIR, filename)
    if os.path.exists(path):
        try:
            img = Image.open(path)
            return ctk.CTkImage(light_image=img, dark_image=img, size=size)
        except Exception:
            pass
    return None


class HomeView(ctk.CTkFrame):

    def __init__(self, parent, app):
        super().__init__(parent, fg_color=BG)
        self.app = app
        self._images = []          # prevent garbage-collection of CTkImage refs
        self._build()

    def _build(self):
        # ── Nav bar ──────────────────────────────────────────────────────────
        nav = ctk.CTkFrame(self, fg_color=WHITE, height=64, corner_radius=0)
        nav.pack(fill="x")
        nav.pack_propagate(False)

        # Left: Branding
        make_label(nav, "🏡  K3's Floating Cottage", 16, "bold",
                   color=TEAL_DARK).place(x=24, rely=0.5, anchor="w")

        # Right: User Context
        name = self.app.session_user.get('name', 'Guest') if self.app.session_user else "Guest"
        make_label(nav, f"Welcome, {name}", 12, color=SUBTEXT).place(relx=1.0, x=-40, rely=0.5, anchor="e")

        # Subtle bottom border
        ctk.CTkFrame(nav, fg_color=DIVIDER, height=1).place(relx=0, rely=1.0, relwidth=1.0, anchor="sw")

        # ── Hero section ─────────────────────────────────────────────────────
        hero = ctk.CTkFrame(self, fg_color=TEAL_LIGHT, corner_radius=0, height=200)
        hero.pack(fill="x")
        hero.pack_propagate(False)

        # Count active trips
        all_res = ReservationModel.get_all()
        active = [r for r in all_res if r.get("status") in ("Confirmed", "On Going")]
        active_count = len(active)

        make_label(hero, "Live Cottage & Boat Monitoring", 28, "bold",
                   color=TEXT).place(relx=0.5, rely=0.45, anchor="center")
        make_label(hero,
                   f"Currently Monitoring {active_count} Active Trip{'s' if active_count != 1 else ''}",
                   13, color=SUBTEXT
                   ).place(relx=0.5, rely=0.70, anchor="center")

        # ── Cards section ────────────────────────────────────────────────────
        card_area = ctk.CTkFrame(self, fg_color="#FDF8F0", corner_radius=0)
        card_area.pack(fill="both", expand=True)

        card_row = ctk.CTkFrame(card_area, fg_color="transparent")
        card_row.place(relx=0.5, rely=0.45, anchor="center")

        # Card definitions: (emoji_fallback, title, action, bg_color, image_file)
        cards = [
            ("📋", "Reservations", "reserve",   "#E8F6F4", "reservation.png"),
            ("⚙️", "Operations",   "operations", "#FFF8E1", "operations.png"),
        ]

        for i, (emoji, title, action, bg, img_file) in enumerate(cards):
            card = ctk.CTkFrame(card_row, fg_color=WHITE, corner_radius=20,
                                border_width=1, border_color=DIVIDER,
                                width=240, height=260, cursor="hand2")
            card.grid(row=0, column=i, padx=20, pady=10)
            card.grid_propagate(False)

            # Try to load image; fall back to emoji
            ctk_img = _load_card_image(img_file, size=(120, 120))

            if ctk_img:
                self._images.append(ctk_img)
                img_label = ctk.CTkLabel(card, image=ctk_img, text="",
                                         fg_color="transparent")
                img_label.place(relx=0.5, rely=0.38, anchor="center")
                img_label.bind("<Button-1>", lambda e, a=action: self._go(a))
            else:
                # Emoji fallback inside a colored circle
                icon_bg = ctk.CTkFrame(card, fg_color=bg, corner_radius=50,
                                       width=100, height=100)
                icon_bg.place(relx=0.5, rely=0.38, anchor="center")
                icon_bg.grid_propagate(False)
                lbl = make_label(icon_bg, emoji, 40)
                lbl.place(relx=0.5, rely=0.5, anchor="center")
                icon_bg.bind("<Button-1>", lambda e, a=action: self._go(a))
                lbl.bind("<Button-1>", lambda e, a=action: self._go(a))

            # Title
            title_lbl = make_label(card, title, 15, "bold", color=TEXT)
            title_lbl.place(relx=0.5, rely=0.82, anchor="center")

            # Bind click to the card and title
            card.bind("<Button-1>", lambda e, a=action: self._go(a))
            title_lbl.bind("<Button-1>", lambda e, a=action: self._go(a))

    # ── Routing ───────────────────────────────────────────────────────────────
    def _go(self, dest: str):
        from views.browse_view      import BrowseView
        from views.my_bookings_view import MyBookingsView
        from views.dashboard_view   import DashboardView

        routes = {
            "reserve":    BrowseView,
            "operations": MyBookingsView,
            "dashboard":  DashboardView,
        }
        cls = routes.get(dest)
        if cls:
            self.app.navigate(cls)
