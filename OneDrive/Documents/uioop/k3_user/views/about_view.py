"""
views/about_view.py — Information about K3's Floating Cottage business.
"""

import customtkinter as ctk
from utils.theme import (
    BG, WHITE, TEAL, TEAL_DARK, TEXT, SUBTEXT, DIVIDER,
    make_label, make_card, top_strip
)

class AboutView(ctk.CTkFrame):
    SHELL_TITLE = "About Us"
    SIDEBAR_ACTIVE = "about"
    SHOW_SIDEBAR = True

    def __init__(self, parent, app):
        super().__init__(parent, fg_color=BG)
        self.app = app
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        strip = top_strip(
            self, 
            "About K3's Floating Cottage", 
            "Learn more about our services and how to reach us."
        )
        strip.grid(row=0, column=0, sticky="ew")

        # Main Scrollable Content
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        scroll.grid_columnconfigure(0, weight=1)

        # ── Business Story ──────────────────────────────────────────────────
        story_card = make_card(scroll)
        story_card.grid(row=0, column=0, sticky="ew", padx=10, pady=(0, 20))
        story_card.grid_columnconfigure(0, weight=1)

        make_label(story_card, "Calatagan Little Boracay Day Tour", 20, "bold", color=TEAL_DARK).grid(row=0, column=0, sticky="w", padx=24, pady=(24, 5))
        make_label(story_card, "Kiara Xena Delos Santos - Calatagan, Batangas", 12, color=SUBTEXT).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 15))
        
        description = (
            "Experience the beauty of Calatagan, Batangas with our unique Floating Cottage Day Tour! "
            "Unlike traditional beach resorts, our cottages are pulled by motor boats to visit four stunning "
            "destinations: the SandBar Area, Snorkeling Area, Starfish Area, and Little Boracay.\n\n"
            "We offer a safe and enjoyable environment for everyone—kids, seniors, and PWDs included. "
            "Enjoy the freedom of bringing your own food with NO corkage fees, or try our special Boodle Fight meals!"
        )
        make_label(story_card, description, 13, color=TEXT, wraplength=720, justify="left").grid(row=2, column=0, sticky="w", padx=24, pady=(0, 24))

        # ── Features & Inclusions ───────────────────────────────────────────
        feat_row = ctk.CTkFrame(scroll, fg_color="transparent")
        feat_row.grid(row=1, column=0, sticky="ew")
        feat_row.grid_columnconfigure((0, 1), weight=1)

        # Inclusions Card
        inc_card = make_card(feat_row)
        inc_card.grid(row=0, column=0, sticky="nsew", padx=10, pady=(0, 20))
        make_label(inc_card, "Floating Cottage Inclusions", 16, "bold", color=TEAL_DARK).pack(anchor="w", padx=24, pady=(24, 15))
        
        inclusions = [
            "✅  Free use of Griller",
            "✅  Life Vests & Life Guard",
            "✅  Dressing Room & Medicine Kit",
            "✅  Experienced Boat Man",
            "✅  Body Board & Foam (on request)",
            "✅  Maximum 20 Pax Capacity"
        ]
        for item in inclusions:
            make_label(inc_card, item, 12, color=TEXT).pack(anchor="w", padx=30, pady=4)

        # Highlights Card
        high_card = make_card(feat_row)
        high_card.grid(row=0, column=1, sticky="nsew", padx=10, pady=(0, 20))
        make_label(high_card, "Why Choose Us?", 16, "bold", color=TEAL_DARK).pack(anchor="w", padx=24, pady=(24, 15))
        
        highlights = [
            "💖  NO Entrance & Corkage Fees",
            "💖  Pet Friendly Environment",
            "💖  100% Safe for Kids & Seniors",
            "💖  Accommodating Tour Guides",
            "💖  Transient Houses Available",
            "💖  First Downpayment, First Serve"
        ]
        for item in highlights:
            make_label(high_card, item, 12, color=TEXT).pack(anchor="w", padx=30, pady=4)

        # ── Contact & Operating Hours ──────────────────────────────────────
        info_row = ctk.CTkFrame(scroll, fg_color="transparent")
        info_row.grid(row=2, column=0, sticky="ew")
        info_row.grid_columnconfigure((0, 1), weight=1)

        # Contact Details Card
        contact_card = make_card(info_row)
        contact_card.grid(row=0, column=0, sticky="nsew", padx=10, pady=0)
        make_label(contact_card, "Get in Touch", 16, "bold", color=TEAL_DARK).pack(anchor="w", padx=24, pady=(24, 15))
        
        contacts = [
            ("📞  Phone", "0961 738 6244"),
            ("📍  Location", "Little Boracay, Calatagan, Batangas"),
            ("⏰  Tour Hours", "6:00 AM - 4:00 PM")
        ]
        for icon_text, value in contacts:
            row = ctk.CTkFrame(contact_card, fg_color="transparent")
            row.pack(fill="x", padx=24, pady=6)
            make_label(row, icon_text, 12, "bold", color=SUBTEXT).pack(side="left")
            make_label(row, value, 12, "bold", color=TEXT).pack(side="right")

        # Disclaimer / Note
        note_card = ctk.CTkFrame(scroll, fg_color="#FDF2F2", corner_radius=15, border_width=1, border_color="#FADEDF")
        note_card.grid(row=3, column=0, sticky="ew", padx=10, pady=20)
        
        make_label(note_card, "⚠️  Important Disclaimer", 14, "bold", color="#C05050").pack(padx=24, pady=(20, 5), anchor="w")
        disclaimer = (
            "Little Boracay is NOT a beach front property. It is a unique island hopping experience where "
            "our floating cottages are towed by motor boats to reach the various destinations. "
            "Travel from Manila to Calatagan is approximately 3-4 hours."
        )
        make_label(note_card, disclaimer, 12, color=TEXT, wraplength=720, justify="left").pack(padx=24, pady=(0, 20), anchor="w")
