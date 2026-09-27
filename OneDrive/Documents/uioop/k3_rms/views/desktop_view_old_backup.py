from datetime import datetime, timedelta
from pathlib import Path
import tkinter.messagebox as messagebox

import customtkinter as ctk
from PIL import Image

from k3_rms.config import (
    AppLoginSettings,
    CONTACT_NAME,
    CONTACT_PHONE,
    DISCLAIMER_TEXT,
    DESTINATIONS,
    FOOD_OPTIONS,
    OTHER_INCLUSIONS,
    TOUR_HEADLINE,
    TOUR_HIGHLIGHTS,
    TRANSIENT_OPTIONS,
)
from k3_rms.controllers.dashboard_controller import DashboardController
from k3_rms.controllers.reservation_controller import ReservationController
from k3_rms.exceptions import ApplicationError


class DesktopView(ctk.CTk):
    def __init__(
        self,
        reservation_controller: ReservationController,
        dashboard_controller: DashboardController,
        data_mode: str = "mysql",
        startup_notice: str | None = None,
        connect_database_callback=None,
        login_settings: AppLoginSettings | None = None,
    ) -> None:
        super().__init__()
        self.reservation_controller = reservation_controller
        self.dashboard_controller = dashboard_controller
        self.data_mode = data_mode
        self.startup_notice = startup_notice or "Ready."
        self.connect_database_callback = connect_database_callback
        self.login_settings = login_settings or AppLoginSettings.from_env()
        self.palette = {
            "bg": "#EEF4F1",
            "page": "#FBF8F3",
            "surface": "#FFFFFF",
            "surface_alt": "#F6ECDC",
            "brand": "#CDA17C",
            "brand_dark": "#A87451",
            "accent": "#A8DED7",
            "accent_dark": "#3F7D79",
            "text": "#1E3A37",
            "muted": "#70807B",
            "line": "#E5ECE7",
            "danger": "#C8645B",
            "good": "#DFF3E8",
            "status_available": "#DFF3E8",
            "status_available_text": "#1E5A46",
            "status_reserved": "#F7E6B9",
            "status_reserved_text": "#8C6115",
            "status_in_use": "#DCEAFB",
            "status_in_use_text": "#1F4F86",
            "status_completed": "#E9E8F8",
            "status_completed_text": "#59539A",
            "status_cancelled": "#F7DFDA",
            "status_cancelled_text": "#9E4A40",
        }
        self.page_frames: dict[str, ctk.CTkFrame] = {}
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        self.metric_targets: dict[str, list[ctk.CTkLabel]] = {}
        self.asset_sections: dict[str, ctk.CTkScrollableFrame] = {}
        self.hero_image = None
        self.logo_image = None
        self.brand_logo_label = None
        self.login_logo_image = None
        self.login_logo_label = None
        self.login_username_entry = None
        self.login_overlay = None
        self.login_feedback_label = None
        self.mode_label = None
        self.header_connect_button = None
        self.header_logout_button = None
        self.home_notice = None
        self.home_notice_button = None

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self._build_variables()
        self._build_window()
        self._build_shell()
        self._build_login_overlay()
        self._load_brand_images()
        self.show_page("home")
        self.refresh_dashboard(status_message=self.startup_notice)
        self._refresh_connection_state()
        self._show_login_overlay(initial=True)

    def run(self) -> None:
        self.mainloop()

    def _build_variables(self) -> None:
        default_departure = datetime.now().replace(
            hour=8,
            minute=0,
            second=0,
            microsecond=0,
        )
        if datetime.now().hour >= 15:
            default_departure = default_departure + timedelta(days=1)
        self.departure_slot_options = tuple(
            f"{hour:02d}:00" for hour in range(6, 13)
        )
        self.duration_options = tuple(str(hour) for hour in range(2, 11))
        self.party_size_options = tuple(str(size) for size in range(1, 21))
        self.departure_date_var = ctk.StringVar(value=default_departure.strftime("%Y-%m-%d"))
        self.departure_slot_var = ctk.StringVar(value="08:00")
        self.departure_var = ctk.StringVar(
            value=default_departure.strftime(ReservationController.DATETIME_FORMAT)
        )
        self.duration_var = ctk.StringVar(value="4")
        self.party_size_var = ctk.StringVar(value="6")
        self.return_preview_var = ctk.StringVar(value="Returns at 12:00 PM")
        self.name_var = ctk.StringVar()
        self.contact_var = ctk.StringVar()
        self.email_var = ctk.StringVar()
        self.destination_var = ctk.StringVar(value=self.reservation_controller.destinations()[0])
        self.notes_var = ctk.StringVar()
        self.action_code_var = ctk.StringVar()
        self.availability_var = ctk.StringVar(
            value="Choose a travel date, departure slot, and party size, then click Check Availability."
        )
        self.status_var = ctk.StringVar(value="Ready.")
        self.mode_var = ctk.StringVar(
            value="LIVE MYSQL" if self.data_mode == "mysql" else "DEMO MODE"
        )
        self.date_var = ctk.StringVar(value=datetime.now().strftime("%A, %d %B %Y"))
        self.asset_summary_var = ctk.StringVar(value="Loading asset summary...")
        self.login_user_var = ctk.StringVar(value=self.login_settings.username)
        self.login_password_var = ctk.StringVar()
        self.login_feedback_var = ctk.StringVar(value="Sign in to open the reservation dashboard.")
        self.login_hint_var = ctk.StringVar(
            value=(
                "Default login: admin / k3admin123"
                if self.login_settings.uses_default_credentials()
                else "Using the custom K3 app account configured in .env."
            )
        )
        for variable in (self.departure_date_var, self.departure_slot_var, self.duration_var):
            variable.trace_add("write", self._update_return_preview)
        self._update_return_preview()

    def _build_window(self) -> None:
        self.title("K3's Floating Cottage RMS")
        self.geometry("1540x980")
        self.minsize(1320, 900)
        self.configure(fg_color=self.palette["bg"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

    def _build_shell(self) -> None:
        self._build_header()
        self._admin_page()

        footer = ctk.CTkFrame(
            self,
            fg_color=self.palette["surface"],
            corner_radius=22,
            border_width=1,
            border_color=self.palette["line"],
        )
        footer.grid(row=2, column=0, sticky="ew", padx=30, pady=(0, 26))
        footer.grid_columnconfigure(0, weight=1)
        self.status_label = ctk.CTkLabel(
            footer,
            textvariable=self.status_var,
            text_color=self.palette["text"],
            font=("Segoe UI", 14),
            anchor="w",
            padx=16,
            pady=12,
        )
        self.status_label.grid(row=0, column=0, sticky="ew")

    def _build_header(self) -> None:
        header = ctk.CTkFrame(
            self,
            fg_color=self.palette["surface"],
            corner_radius=28,
            border_width=1,
            border_color=self.palette["line"],
        )
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(26, 14))
        header.grid_columnconfigure(1, weight=1)

        brand = ctk.CTkFrame(header, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="w", padx=26, pady=22)
        self.brand_logo_label = ctk.CTkLabel(
            brand,
            text="K3",
            width=92,
            height=92,
            corner_radius=18,
            fg_color=self.palette["surface_alt"],
            text_color=self.palette["accent_dark"],
            font=("Georgia", 24, "bold"),
        )
        self.brand_logo_label.grid(row=0, column=0, rowspan=3, padx=(0, 16))
        ctk.CTkLabel(
            brand,
            text="K3's Floating Cottage",
            text_color=self.palette["text"],
            font=("Georgia", 24, "bold"),
        ).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(
            brand,
            text="Calatagan Little Boracay Day Tour",
            text_color=self.palette["muted"],
            font=("Segoe UI", 13, "bold"),
        ).grid(row=1, column=1, sticky="w")
        ctk.CTkLabel(
            brand,
            text="Reservation Management System",
            text_color=self.palette["muted"],
            font=("Segoe UI", 12),
        ).grid(row=2, column=1, sticky="w")

        nav = ctk.CTkFrame(header, fg_color="transparent")
        nav.grid(row=0, column=1, sticky="n")
        for column, (page_name, label) in enumerate(
            (
                ("home", "Home"),
                ("reservations", "Reservations"),
                ("operations", "Operations"),
                ("assets", "Assets"),
            )
        ):
            button = ctk.CTkButton(
                nav,
                text=label,
                command=lambda name=page_name: self.show_page(name),
                width=142,
                height=42,
                corner_radius=16,
                fg_color="transparent",
                hover_color="#EDF6F3",
                text_color=self.palette["muted"],
                font=("Segoe UI", 14, "bold"),
                border_width=0,
            )
            button.grid(row=0, column=column, padx=8, pady=22)
            self.nav_buttons[page_name] = button

        meta = ctk.CTkFrame(header, fg_color="transparent")
        meta.grid(row=0, column=2, sticky="e", padx=26, pady=18)
        ctk.CTkLabel(
            meta,
            textvariable=self.date_var,
            text_color=self.palette["muted"],
            font=("Segoe UI", 12),
        ).grid(row=0, column=0, sticky="e", pady=(0, 8))
        self.mode_label = ctk.CTkLabel(
            meta,
            textvariable=self.mode_var,
            text_color=self.palette["surface"],
            fg_color=self.palette["accent_dark"] if self.data_mode == "mysql" else self.palette["brand_dark"],
            corner_radius=12,
            padx=12,
            pady=6,
            font=("Segoe UI", 11, "bold"),
        )
        self.mode_label.grid(row=1, column=0, sticky="e")
        self.header_connect_button = ctk.CTkButton(
            meta,
            text="Connect MySQL",
            command=self._open_database_dialog,
            width=132,
            height=34,
            corner_radius=12,
            fg_color=self.palette["surface_alt"],
            hover_color="#E5D6C5",
            text_color=self.palette["accent_dark"],
            font=("Segoe UI", 12, "bold"),
        )
        self.header_connect_button.grid(row=2, column=0, sticky="e", pady=(10, 0))
        self.header_logout_button = ctk.CTkButton(
            meta,
            text="Log Out",
            command=self._logout,
            width=132,
            height=34,
            corner_radius=12,
            fg_color="#F4DBD6",
            hover_color="#E8C3BC",
            text_color=self.palette["danger"],
            font=("Segoe UI", 12, "bold"),
        )
        self.header_logout_button.grid(row=3, column=0, sticky="e", pady=(10, 0))

    def _admin_page(self) -> None:
        """Main admin layout with frame-switching navigation.
        
        This method creates the primary admin interface with:
        - A bg_frame: main content area where different pages are loaded
        - Navigation sidebar
        - Proper frame clearing that only affects bg_frame
        """
        self.page_container = ctk.CTkFrame(self, fg_color="transparent")
        self.page_container.grid(row=1, column=0, sticky="nsew", padx=30, pady=(4, 16))
        self.page_container.grid_rowconfigure(0, weight=1)
        self.page_container.grid_columnconfigure(1, weight=1)

        # Sidebar Navigation
        sidebar = ctk.CTkFrame(
            self.page_container,
            fg_color=self.palette["surface"],
            corner_radius=20,
            border_width=1,
            border_color=self.palette["line"],
        )
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        sidebar.grid_rowconfigure(2, weight=1)
        sidebar.grid_columnconfigure(0, weight=1)

        # Sidebar Header
        ctk.CTkLabel(
            sidebar,
            text="MODULES",
            text_color=self.palette["muted"],
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(22, 8))

        # Navigation Menu
        nav_items = [
            ("home", "🏠 Home", self.palette["accent"]),
            ("reservations", "📅 Reservations", self.palette["brand"]),
            ("operations", "🚀 Operations", self.palette["accent"]),
            ("assets", "⚙️ Assets", self.palette["surface_alt"]),
        ]

        for menu_row, (page_name, label, color) in enumerate(nav_items, start=1):
            nav_button = ctk.CTkButton(
                sidebar,
                text=label,
                command=lambda name=page_name: self.show_page(name),
                fg_color="transparent",
                hover_color="#F0EDE5",
                text_color=self.palette["text"],
                anchor="w",
                font=("Segoe UI", 13, "bold"),
                corner_radius=14,
                height=48,
                border_width=0,
            )
            nav_button.grid(row=menu_row, column=0, sticky="ew", padx=12, pady=4)
            self.nav_buttons[page_name] = nav_button

        # Main Content Area Frame (bg_frame)
        self.bg_frame = ctk.CTkFrame(
            self.page_container,
            fg_color=self.palette["page"],
            corner_radius=28,
            border_width=1,
            border_color=self.palette["line"],
        )
        self.bg_frame.grid(row=0, column=1, sticky="nsew")
        self.bg_frame.grid_rowconfigure(0, weight=1)
        self.bg_frame.grid_columnconfigure(0, weight=1)

        # Build all pages inside the main content area
        self._build_home_page()
        self._build_reservations_page()
        self._build_operations_page()
        self._build_assets_page()

        # Show initial dashboard
        self.show_dashboard()

    def show_dashboard(self) -> None:
        """Display the main dashboard/home view.
        
        This function clears bg_frame and shows the home page lobby
        with action cards for different modules.
        """
        self._clear_bg_frame()
        self.show_page("home")
        page = self._create_page("home")
        page.grid_columnconfigure(0, weight=5)
        page.grid_columnconfigure(1, weight=3)
        page.grid_rowconfigure(1, weight=1)

        hero = ctk.CTkFrame(
            page,
            fg_color=self.palette["brand"],
            corner_radius=28,
            border_width=1,
            border_color=self.palette["line"],
        )
        hero.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 14))
        hero.grid_columnconfigure(0, weight=4)
        hero.grid_columnconfigure(1, weight=3)

        text_wrap = ctk.CTkFrame(hero, fg_color="transparent")
        text_wrap.grid(row=0, column=0, sticky="nsew", padx=28, pady=28)
        ctk.CTkLabel(
            text_wrap,
            text=TOUR_HEADLINE,
            text_color=self.palette["surface"],
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            text_wrap,
            text="Floating cottage day tours with four destinations and live booking control.",
            text_color=self.palette["surface"],
            font=("Georgia", 34, "bold"),
            justify="left",
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(18, 12))
        ctk.CTkLabel(
            text_wrap,
            text=(
                "No entrance fee, no corkage fee, pet friendly, and safe for kids, seniors, and "
                "PWD guests. First downpayment first serve secures the slot for your floating cottage."
            ),
            text_color=self.palette["surface"],
            font=("Segoe UI", 15),
            wraplength=520,
            justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(0, 18))

        hero_actions = ctk.CTkFrame(text_wrap, fg_color="transparent")
        hero_actions.grid(row=3, column=0, sticky="w")
        self._action_button(
            hero_actions,
            "Book a Cottage",
            lambda: self.show_page("reservations"),
            self.palette["accent"],
            self.palette["text"],
        ).grid(row=0, column=0, padx=(0, 10))
        self._action_button(
            hero_actions,
            "Manage Trips",
            lambda: self.show_page("operations"),
            self.palette["surface"],
            self.palette["accent_dark"],
        ).grid(row=0, column=1)

        image_card = ctk.CTkFrame(hero, fg_color="#8DD5CC", corner_radius=22, border_width=0)
        image_card.grid(row=0, column=1, sticky="nsew", padx=(0, 24), pady=24)
        image_card.grid_rowconfigure(0, weight=1)
        image_card.grid_columnconfigure(0, weight=1)
        self.hero_image_label = ctk.CTkLabel(image_card, text="Loading K3 logo...")
        self.hero_image_label.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)

        left = ctk.CTkFrame(page, fg_color="transparent")
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        left.grid_columnconfigure(0, weight=1)
        left.grid_columnconfigure(1, weight=1)
        left.grid_columnconfigure(2, weight=1)
        left.grid_rowconfigure(1, weight=1)

        self._metric_card(left, "active_reservations", "Active", 0, 0, self.palette["accent"])
        self._metric_card(left, "daily_bookings", "Today", 0, 1, self.palette["surface"])
        self._metric_card(left, "weekly_bookings", "This Week", 0, 2, self.palette["surface_alt"])

        self.home_reservations_frame = self._section_frame(left, "Upcoming Reservations")
        self.home_reservations_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(14, 0), padx=(0, 8))

        summary = self._section_frame(left, "Quick Summary")
        summary.grid(row=1, column=2, sticky="nsew", pady=(14, 0))
        ctk.CTkLabel(
            summary,
            textvariable=self.asset_summary_var,
            text_color=self.palette["muted"],
            font=("Segoe UI", 14),
            justify="left",
            wraplength=280,
        ).grid(row=1, column=0, sticky="nw", padx=18, pady=(0, 16))
        self.home_notice = ctk.CTkLabel(
            summary,
            text=self.startup_notice,
            text_color=self.palette["text"],
            fg_color=self.palette["surface_alt"],
            corner_radius=14,
            justify="left",
            wraplength=280,
            padx=14,
            pady=12,
            font=("Segoe UI", 12),
        )
        self.home_notice.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))
        self.home_notice_button = ctk.CTkButton(
            summary,
            text="Connect MySQL",
            command=self._open_database_dialog,
            height=38,
            corner_radius=12,
            fg_color=self.palette["accent"],
            hover_color=self.palette["accent_dark"],
            text_color=self.palette["text"],
            font=("Segoe UI", 13, "bold"),
        )
        self.home_notice_button.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 18))

        right = self._section_frame(page, "Tour Details")
        right.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        right.grid_rowconfigure(1, weight=1)
        details = ctk.CTkScrollableFrame(right, fg_color="transparent", height=520)
        details.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 18))
        details.grid_columnconfigure(0, weight=1)

        info_row = 0
        info_row = self._add_info_group(details, info_row, "Tour Essentials", TOUR_HIGHLIGHTS)
        info_row = self._add_info_group(details, info_row, "Four Destinations", DESTINATIONS)
        info_row = self._add_info_group(
            details,
            info_row,
            "Floating Cottage Inclusions",
            OTHER_INCLUSIONS,
        )
        info_row = self._add_info_group(details, info_row, "Food Options", FOOD_OPTIONS)
        info_row = self._add_info_group(
            details,
            info_row,
            "Transient House",
            TRANSIENT_OPTIONS,
        )
        self._add_info_group(
            details,
            info_row,
            "Disclaimer and Contact",
            (
                DISCLAIMER_TEXT,
                f"Contact person: {CONTACT_NAME}.",
                f"Call or message: {CONTACT_PHONE}.",
            ),
        )

    def _build_reservations_page(self) -> None:
        page = self._create_page("reservations")
        page.grid_columnconfigure(0, weight=6)
        page.grid_columnconfigure(1, weight=4)

        form = self._section_frame(page, "Reservation Studio")
        form.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        form.grid_columnconfigure(0, weight=1)
        form.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            form,
            text="Clear inputs, soft spacing, and fewer manual steps for faster booking.",
            text_color=self.palette["muted"],
            font=("Segoe UI", 14),
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=24, pady=(0, 18))

        self._field(form, "Full Name", self.name_var, 2, 0)
        self._field(form, "Contact Number", self.contact_var, 2, 1)
        self._field(form, "Email Address", self.email_var, 4, 0)
        self._dropdown(
            form,
            "Destination",
            self.destination_var,
            self.reservation_controller.destinations(),
            4,
            1,
        )
        self._field(form, "Travel Date (YYYY-MM-DD)", self.departure_date_var, 6, 0)
        self._dropdown(form, "Departure Slot", self.departure_slot_var, self.departure_slot_options, 6, 1)
        self._dropdown(form, "Duration in Hours", self.duration_var, self.duration_options, 8, 0)
        self._dropdown(form, "Party Size", self.party_size_var, self.party_size_options, 8, 1)
        self._field(form, "Notes / Special Request", self.notes_var, 10, 0)

        quick_info = ctk.CTkFrame(
            form,
            fg_color=self.palette["surface_alt"],
            corner_radius=18,
            border_width=0,
        )
        quick_info.grid(row=11, column=0, columnspan=2, sticky="ew", padx=24, pady=(2, 16))
        quick_info.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            quick_info,
            textvariable=self.return_preview_var,
            text_color=self.palette["text"],
            font=("Segoe UI", 13, "bold"),
            justify="left",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 4))
        ctk.CTkLabel(
            quick_info,
            text="Day tours must stay within 6:00 AM to 4:00 PM, and the form keeps the slot choices simple.",
            text_color=self.palette["muted"],
            font=("Segoe UI", 12),
            justify="left",
            wraplength=700,
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

        actions = ctk.CTkFrame(form, fg_color="transparent")
        actions.grid(row=12, column=0, columnspan=2, sticky="ew", padx=24, pady=(4, 24))
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)
        actions.grid_columnconfigure(2, weight=1)
        self._action_button(actions, "Autofill Guest", self.autofill_customer, self.palette["surface"], self.palette["accent_dark"]).grid(row=0, column=0, padx=(0, 8), sticky="ew")
        self._action_button(actions, "Check Availability", self.preview_availability, self.palette["brand"], self.palette["surface"]).grid(row=0, column=1, padx=4, sticky="ew")
        self._action_button(actions, "Confirm Reservation", self.create_reservation, self.palette["accent"], self.palette["text"]).grid(row=0, column=2, padx=(8, 0), sticky="ew")

        side = ctk.CTkFrame(page, fg_color="transparent")
        side.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        side.grid_rowconfigure((0, 1), weight=1)
        side.grid_columnconfigure(0, weight=1)

        availability = self._section_frame(side, "Live Availability")
        availability.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        ctk.CTkLabel(
            availability,
            text="Instant feedback from the current cottage and motorboat schedule.",
            text_color=self.palette["muted"],
            font=("Segoe UI", 13),
            justify="left",
            wraplength=420,
        ).grid(row=1, column=0, sticky="nw", padx=24, pady=(0, 14))
        ctk.CTkLabel(
            availability,
            textvariable=self.availability_var,
            text_color=self.palette["muted"],
            font=("Segoe UI", 14),
            justify="left",
            wraplength=420,
            fg_color=self.palette["surface_alt"],
            corner_radius=18,
            padx=18,
            pady=16,
        ).grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 24))

        tips = self._section_frame(side, "Breezy Booking Guide")
        tips.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        for row, text in enumerate(
            (
                "Use the dropdowns to avoid typing errors on time slots and group size.",
                "Green means available, amber means reserved, and blue means in use.",
                "Check availability first, then confirm once the guest is ready to pay.",
            ),
            start=1,
        ):
            ctk.CTkLabel(
                tips,
                text=text,
                text_color=self.palette["muted"],
                font=("Segoe UI", 13),
                justify="left",
                wraplength=420,
            ).grid(row=row, column=0, sticky="w", padx=24, pady=(0, 14))

    def _build_operations_page(self) -> None:
        page = self._create_page("operations")
        page.grid_columnconfigure(0, weight=3)
        page.grid_columnconfigure(1, weight=5)

        actions = self._section_frame(page, "Trip Operations")
        actions.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        actions.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            actions,
            text="Enter or load a reservation code, then update the trip.",
            text_color=self.palette["muted"],
            font=("Segoe UI", 13),
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 12))
        code_entry = ctk.CTkEntry(
            actions,
            textvariable=self.action_code_var,
            height=44,
            corner_radius=14,
            border_width=1,
            border_color=self.palette["line"],
            fg_color=self.palette["surface"],
            text_color=self.palette["text"],
        )
        code_entry.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))

        self._action_button(actions, "Start Trip", self.start_trip, self.palette["accent"], self.palette["text"]).grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 10))
        self._action_button(actions, "Complete Trip", self.complete_trip, self.palette["brand"], self.palette["surface"]).grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 10))
        self._action_button(actions, "Cancel Reservation", self.cancel_reservation, self.palette["danger"], self.palette["surface"]).grid(row=5, column=0, sticky="ew", padx=18, pady=(0, 18))

        self.operations_reservations_frame = self._section_frame(page, "Active Reservations")
        self.operations_reservations_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

    def _build_assets_page(self) -> None:
        page = self._create_page("assets")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)
        page.grid_rowconfigure(2, weight=1)

        metrics = ctk.CTkFrame(page, fg_color="transparent")
        metrics.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        metrics.grid_columnconfigure(0, weight=1)
        metrics.grid_columnconfigure(1, weight=1)
        metrics.grid_columnconfigure(2, weight=1)
        self._metric_card(metrics, "completed_trips", "Completed Trips", 0, 0, self.palette["surface"])
        self._metric_card(metrics, "cancellations", "Cancelled Trips", 0, 1, "#F4DBD6")
        self._metric_card(metrics, "active_reservations", "Live Reservations", 0, 2, self.palette["good"])

        board = self._section_frame(page, "Asset Status")
        board.grid(row=1, column=0, sticky="nsew")
        tabview = ctk.CTkTabview(
            board,
            fg_color=self.palette["surface"],
            segmented_button_fg_color=self.palette["surface_alt"],
            segmented_button_selected_color=self.palette["accent"],
            segmented_button_selected_hover_color=self.palette["accent_dark"],
            segmented_button_unselected_color=self.palette["surface"],
            segmented_button_unselected_hover_color="#EDF6F3",
            text_color=self.palette["text"],
            corner_radius=18,
        )
        tabview.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

        for key, label in (("cottages", "Floating Cottages"), ("motorboats", "Motorboats")):
            tab = tabview.add(label)
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_columnconfigure(0, weight=1)
            scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
            scroll.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
            scroll.grid_columnconfigure(0, weight=1)
            self.asset_sections[key] = scroll

        self.assignment_frame = self._section_frame(page, "Session Assignment Board")
        self.assignment_frame.grid(row=2, column=0, sticky="nsew", pady=(14, 0))

    def _build_login_overlay(self) -> None:
        self.login_overlay = ctk.CTkFrame(self, fg_color=self.palette["bg"], corner_radius=0)
        self.login_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.login_overlay.grid_columnconfigure(0, weight=1)
        self.login_overlay.grid_rowconfigure(0, weight=1)
        self.login_overlay.grid_rowconfigure(1, weight=0)
        self.login_overlay.grid_rowconfigure(2, weight=1)

        top_glow = ctk.CTkFrame(
            self.login_overlay,
            fg_color="#F4E3C8",
            corner_radius=170,
            border_width=0,
            width=340,
            height=340,
        )
        top_glow.place(relx=0.2, rely=0.1)

        bottom_glow = ctk.CTkFrame(
            self.login_overlay,
            fg_color="#D9EFE8",
            corner_radius=220,
            border_width=0,
            width=440,
            height=440,
        )
        bottom_glow.place(relx=0.68, rely=0.56)

        card = ctk.CTkFrame(
            self.login_overlay,
            fg_color=self.palette["surface"],
            corner_radius=36,
            border_width=1,
            border_color=self.palette["line"],
            width=500,
        )
        card.grid(row=1, column=0, pady=32)
        card.grid_columnconfigure(0, weight=1)

        badge = ctk.CTkLabel(
            card,
            text="STAFF LOGIN",
            text_color=self.palette["accent_dark"],
            fg_color="#E6F4F0",
            corner_radius=14,
            padx=14,
            pady=6,
            font=("Segoe UI", 11, "bold"),
        )
        badge.grid(row=0, column=0, pady=(28, 16))

        self.login_logo_label = ctk.CTkLabel(
            card,
            text="K3",
            width=144,
            height=144,
            corner_radius=24,
            fg_color=self.palette["surface_alt"],
            text_color=self.palette["accent_dark"],
            font=("Georgia", 30, "bold"),
        )
        self.login_logo_label.grid(row=1, column=0, pady=(0, 18))

        ctk.CTkLabel(
            card,
            text="K3's Floating Cottage",
            text_color=self.palette["text"],
            font=("Georgia", 28, "bold"),
            justify="center",
        ).grid(row=2, column=0, padx=40)
        ctk.CTkLabel(
            card,
            text="Reservation Management System",
            text_color=self.palette["muted"],
            font=("Segoe UI", 13, "bold"),
            justify="center",
        ).grid(row=3, column=0, pady=(8, 8), padx=40)
        ctk.CTkLabel(
            card,
            text="Sign in to manage bookings, trips, and floating cottage assignments.",
            text_color=self.palette["muted"],
            font=("Segoe UI", 14),
            justify="center",
            wraplength=360,
        ).grid(row=4, column=0, pady=(0, 20), padx=40)

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.grid(row=5, column=0, sticky="ew", padx=34)
        form.grid_columnconfigure(0, weight=1)

        username_entry = self._login_field(form, "Username", self.login_user_var, 0)
        self.login_username_entry = username_entry
        password_entry = self._login_field(
            form,
            "Password",
            self.login_password_var,
            2,
            password=True,
        )
        username_entry.bind("<Return>", lambda _event: self._attempt_login())
        password_entry.bind("<Return>", lambda _event: self._attempt_login())

        self.login_feedback_label = ctk.CTkLabel(
            card,
            textvariable=self.login_feedback_var,
            text_color=self.palette["muted"],
            font=("Segoe UI", 12),
            justify="center",
            wraplength=360,
        )
        self.login_feedback_label.grid(row=6, column=0, sticky="ew", padx=34, pady=(16, 8))

        ctk.CTkButton(
            card,
            text="Sign In",
            command=self._attempt_login,
            height=48,
            corner_radius=16,
            fg_color=self.palette["accent"],
            hover_color=self.palette["accent_dark"],
            text_color=self.palette["text"],
            font=("Segoe UI", 15, "bold"),
        ).grid(row=7, column=0, sticky="ew", padx=34, pady=(0, 12))

        ctk.CTkLabel(
            card,
            textvariable=self.login_hint_var,
            text_color=self.palette["accent_dark"],
            font=("Segoe UI", 12, "bold"),
            justify="center",
            wraplength=360,
        ).grid(row=8, column=0, sticky="ew", padx=34, pady=(0, 10))

        ctk.CTkLabel(
            card,
            text=f"Contact: {CONTACT_PHONE}",
            text_color=self.palette["muted"],
            font=("Segoe UI", 12),
            justify="center",
        ).grid(row=9, column=0, pady=(0, 28))

    def _create_page(self, name: str) -> ctk.CTkFrame:
        page = ctk.CTkFrame(self.bg_frame, fg_color="transparent")
        page.grid(row=0, column=0, sticky="nsew")
        self.page_frames[name] = page
        return page

    def _clear_bg_frame(self) -> None:
        """Clear all children from bg_frame except the page frames themselves."""
        for child in self.bg_frame.winfo_children():
            if child not in self.page_frames.values():
                child.destroy()

    def _section_frame(self, parent: ctk.CTkFrame, title: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(
            parent,
            fg_color=self.palette["page"],
            corner_radius=28,
            border_width=1,
            border_color=self.palette["line"],
        )
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame,
            text=title,
            text_color=self.palette["text"],
            font=("Segoe UI", 24, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(24, 12))
        return frame

    def _metric_card(
        self,
        parent: ctk.CTkFrame,
        key: str,
        title: str,
        row: int,
        column: int,
        color: str,
    ) -> None:
        card = ctk.CTkFrame(
            parent,
            fg_color=color,
            corner_radius=26,
            border_width=1,
            border_color=self.palette["line"],
            height=124,
        )
        card.grid(row=row, column=column, sticky="nsew", padx=8, pady=8)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card,
            text=title,
            text_color=self.palette["muted"],
            font=("Segoe UI", 14, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(20, 6))
        value_label = ctk.CTkLabel(
            card,
            text="0",
            text_color=self.palette["text"],
            font=("Segoe UI", 34, "bold"),
        )
        value_label.grid(row=1, column=0, sticky="w", padx=22, pady=(0, 18))
        self.metric_targets.setdefault(key, []).append(value_label)

    def _field(
        self,
        parent: ctk.CTkFrame,
        label: str,
        variable: ctk.StringVar,
        row: int,
        column: int,
    ) -> ctk.CTkEntry:
        self._field_label(parent, label, row, column)
        entry = ctk.CTkEntry(
            parent,
            textvariable=variable,
            height=48,
            corner_radius=16,
            border_width=1,
            border_color=self.palette["line"],
            fg_color=self.palette["surface"],
            text_color=self.palette["text"],
        )
        entry.grid(
            row=row + 1,
            column=column,
            sticky="ew",
            padx=18 if column == 0 else (8, 18),
            pady=(0, 14),
        )
        return entry

    def _dropdown(
        self,
        parent: ctk.CTkFrame,
        label: str,
        variable: ctk.StringVar,
        values: tuple[str, ...],
        row: int,
        column: int,
    ) -> None:
        self._field_label(parent, label, row, column)
        menu = ctk.CTkOptionMenu(
            parent,
            values=list(values),
            variable=variable,
            height=48,
            corner_radius=16,
            fg_color=self.palette["accent"],
            button_color=self.palette["accent_dark"],
            button_hover_color="#41766E",
            text_color=self.palette["text"],
            dropdown_fg_color=self.palette["surface"],
            dropdown_hover_color="#EDF6F3",
            dropdown_text_color=self.palette["text"],
        )
        menu.grid(row=row + 1, column=column, sticky="ew", padx=(8, 18), pady=(0, 14))

    def _field_label(self, parent: ctk.CTkFrame, label: str, row: int, column: int) -> None:
        ctk.CTkLabel(
            parent,
            text=label,
            text_color=self.palette["muted"],
            font=("Segoe UI", 12, "bold"),
        ).grid(
            row=row,
            column=column,
            sticky="w",
            padx=18 if column == 0 else (8, 18),
            pady=(0, 8),
        )

    def _login_field(
        self,
        parent: ctk.CTkFrame,
        label: str,
        variable: ctk.StringVar,
        row: int,
        password: bool = False,
    ) -> ctk.CTkEntry:
        ctk.CTkLabel(
            parent,
            text=label,
            text_color=self.palette["muted"],
            font=("Segoe UI", 13, "bold"),
        ).grid(row=row, column=0, sticky="w", padx=28, pady=(0, 6))
        entry = ctk.CTkEntry(
            parent,
            textvariable=variable,
            height=46,
            corner_radius=14,
            border_width=1,
            border_color=self.palette["line"],
            fg_color=self.palette["page"],
            text_color=self.palette["text"],
            show="*" if password else "",
        )
        entry.grid(row=row + 1, column=0, sticky="ew", padx=28, pady=(0, 10))
        return entry

    def _add_info_group(
        self,
        parent: ctk.CTkScrollableFrame,
        row: int,
        title: str,
        items: tuple[str, ...],
    ) -> int:
        ctk.CTkLabel(
            parent,
            text=title,
            text_color=self.palette["text"],
            font=("Segoe UI", 15, "bold"),
            justify="left",
        ).grid(row=row, column=0, sticky="w", padx=6, pady=(4, 8))
        next_row = row + 1
        for item in items:
            ctk.CTkLabel(
                parent,
                text=f"- {item}",
                text_color=self.palette["muted"],
                font=("Segoe UI", 13),
                justify="left",
                wraplength=320,
            ).grid(row=next_row, column=0, sticky="w", padx=6, pady=(0, 8))
            next_row += 1
        return next_row + 1

    def _action_button(
        self,
        parent: ctk.CTkFrame,
        text: str,
        command,
        fg_color: str,
        text_color: str,
    ) -> ctk.CTkButton:
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            fg_color=fg_color,
            hover_color=self.palette["accent_dark"] if fg_color == self.palette["accent"] else self.palette["brand_dark"],
            text_color=text_color,
            corner_radius=16,
            height=46,
            font=("Segoe UI", 14, "bold"),
        )

    def _attempt_login(self) -> None:
        username = self.login_user_var.get().strip()
        password = self.login_password_var.get()
        if username == self.login_settings.username and password == self.login_settings.password:
            self.login_feedback_var.set("Login successful. Opening dashboard...")
            if self.login_feedback_label is not None:
                self.login_feedback_label.configure(text_color=self.palette["accent_dark"])
            self._set_status(f"Welcome back, {username}.")
            self.after(150, self._hide_login_overlay)
            return

        self.login_password_var.set("")
        self.login_feedback_var.set("Incorrect username or password. Please try again.")
        if self.login_feedback_label is not None:
            self.login_feedback_label.configure(text_color=self.palette["danger"])

    def _update_return_preview(self, *_args) -> None:
        try:
            departure_time = datetime.strptime(
                f"{self.departure_date_var.get().strip()} {self.departure_slot_var.get().strip()}",
                ReservationController.DATETIME_FORMAT,
            )
            duration_hours = float(self.duration_var.get().strip())
            return_time = departure_time + timedelta(hours=duration_hours)
        except ValueError:
            self.return_preview_var.set("Select a valid travel date, slot, and duration.")
            return

        self.departure_var.set(departure_time.strftime(ReservationController.DATETIME_FORMAT))
        if return_time.hour > 16 or return_time.date() != departure_time.date():
            self.return_preview_var.set("Adjust the slot or duration so the trip ends by 4:00 PM.")
            return
        self.return_preview_var.set(
            f"Trip window: {departure_time.strftime('%b %d, %Y %I:%M %p')} to {return_time.strftime('%I:%M %p')}"
        )

    def _show_login_overlay(self, initial: bool = False) -> None:
        self.login_password_var.set("")
        self.login_feedback_var.set(
            "Sign in to open the reservation dashboard."
            if initial
            else "You have been logged out."
        )
        if self.login_feedback_label is not None:
            self.login_feedback_label.configure(text_color=self.palette["muted"])
        if self.login_overlay is not None:
            self.login_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.login_overlay.lift()
            if self.login_username_entry is not None:
                self.after(50, self.login_username_entry.focus_set)

    def _hide_login_overlay(self) -> None:
        if self.login_feedback_label is not None:
            self.login_feedback_label.configure(text_color=self.palette["muted"])
        if self.login_overlay is not None:
            self.login_overlay.place_forget()

    def _logout(self) -> None:
        self._show_login_overlay()
        self._set_status("Logged out. Sign in again to continue.")

    def show_page(self, name: str) -> None:
        self.page_frames[name].tkraise()
        for page_name, button in self.nav_buttons.items():
            if page_name == name:
                button.configure(
                    fg_color=self.palette["accent"],
                    hover_color=self.palette["accent_dark"],
                    text_color=self.palette["text"],
                )
            else:
                button.configure(
                    fg_color="transparent",
                    hover_color="#EDF6F3",
                    text_color=self.palette["muted"],
                )

    def refresh_dashboard(self, status_message: str | None = None) -> None:
        snapshot = self.dashboard_controller.get_dashboard_snapshot()
        metrics = snapshot["metrics"]
        for key, labels in self.metric_targets.items():
            for label in labels:
                label.configure(text=str(metrics.get(key, 0)))

        self._render_reservations(
            self.home_reservations_frame,
            snapshot["active_reservations"][:4],
            with_actions=False,
        )
        self._render_reservations(
            self.operations_reservations_frame,
            snapshot["active_reservations"],
            with_actions=True,
        )
        self._render_assets("cottages", snapshot["cottages"])
        self._render_assets("motorboats", snapshot["motorboats"])
        self._render_assignments(snapshot.get("session_assignments", []))
        self.asset_summary_var.set(self._build_asset_summary(snapshot))
        self._set_status(status_message or "Dashboard refreshed.")

    def autofill_customer(self) -> None:
        customer = self.reservation_controller.lookup_customer(
            self.email_var.get().strip() or None,
            self.contact_var.get().strip() or None,
        )
        if not customer:
            self._set_status("No guest matched that email or contact number.", tone="warning")
            messagebox.showinfo("Guest Lookup", "No guest matched that email or contact number.")
            return

        self.name_var.set(customer["full_name"] or "")
        self.contact_var.set(customer["contact_number"] or "")
        self.email_var.set(customer["email"] or "")
        self._set_status(f"Loaded guest details for {customer['full_name']}.")

    def preview_availability(self) -> None:
        try:
            result = self.reservation_controller.preview_availability(self._build_schedule_payload())
        except (ApplicationError, ValueError) as exc:
            self._set_status(str(exc), tone="danger")
            messagebox.showerror("Availability", str(exc))
            return

        departure_time = datetime.strptime(
            self.departure_var.get(),
            ReservationController.DATETIME_FORMAT,
        )
        return_time = departure_time + timedelta(hours=float(self.duration_var.get().strip()))
        self.availability_var.set(
            f"{departure_time.strftime('%b %d, %Y %I:%M %p')} to {return_time.strftime('%I:%M %p')}\n\n"
            "Recommended pairing: "
            f"{result['recommended']['cottage']['asset_code']} / {result['recommended']['motorboat']['asset_code']}\n"
            f"Cottage: {result['recommended']['cottage']['name']}\n"
            f"Motorboat: {result['recommended']['motorboat']['name']}\n"
            f"Available cottages: {len(result['cottages'])} | Available boats: {len(result['motorboats'])}"
        )
        self._set_status("Availability checked successfully.")

    def create_reservation(self) -> None:
        payload = self._build_schedule_payload()
        payload.update(
            {
                "full_name": self.name_var.get().strip(),
                "contact_number": self.contact_var.get().strip(),
                "email": self.email_var.get().strip(),
                "notes": self.notes_var.get().strip(),
            }
        )
        try:
            result = self.reservation_controller.create_reservation(payload)
        except (ApplicationError, ValueError) as exc:
            self._set_status(str(exc), tone="danger")
            messagebox.showerror("Reservation", str(exc))
            return

        reservation = result["reservation"]
        self.action_code_var.set(reservation["reservation_code"])
        self.availability_var.set(
            f"Reservation {reservation['reservation_code']} created for {reservation['full_name']}."
        )
        self.refresh_dashboard(
            status_message=f"Reservation {reservation['reservation_code']} created successfully."
        )
        self.show_page("operations")
        messagebox.showinfo(
            "Reservation Confirmed",
            (
                f"Reservation Code: {reservation['reservation_code']}\n"
                f"Cottage: {result['auto_assigned']['cottage']['asset_code']} - {result['auto_assigned']['cottage']['name']}\n"
                f"Motorboat: {result['auto_assigned']['motorboat']['asset_code']} - {result['auto_assigned']['motorboat']['name']}\n"
                f"Total Price: PHP {float(reservation['total_price']):,.2f}"
            ),
        )

    def start_trip(self) -> None:
        self._execute_status_change("start")

    def complete_trip(self) -> None:
        self._execute_status_change("complete")

    def cancel_reservation(self) -> None:
        self._execute_status_change("cancel")

    def _execute_status_change(self, action: str) -> None:
        code = self.action_code_var.get().strip()
        if not code:
            messagebox.showwarning("Reservation Code", "Enter or load a reservation code first.")
            return

        try:
            if action == "start":
                reservation = self.reservation_controller.start_trip(code)
                message = f"{reservation['reservation_code']} is now in use."
            elif action == "complete":
                reservation = self.reservation_controller.complete_trip(code)
                message = f"{reservation['reservation_code']} has been completed."
            else:
                reservation = self.reservation_controller.cancel_reservation(
                    code,
                    "Cancelled from Operations page.",
                )
                message = f"{reservation['reservation_code']} has been cancelled."
        except ApplicationError as exc:
            self._set_status(str(exc), tone="danger")
            messagebox.showerror("Trip Update", str(exc))
            return

        self.refresh_dashboard(status_message=message)
        self._set_status(message)

    def _build_schedule_payload(self) -> dict:
        travel_date = self.departure_date_var.get().strip()
        departure_slot = self.departure_slot_var.get().strip()
        try:
            duration_hours = float(self.duration_var.get().strip())
        except ValueError as exc:
            raise ValueError("Duration must be a valid number of hours.") from exc
        if duration_hours <= 0:
            raise ValueError("Duration must be greater than zero.")
        try:
            departure_time = datetime.strptime(
                f"{travel_date} {departure_slot}",
                ReservationController.DATETIME_FORMAT,
            )
        except ValueError as exc:
            raise ValueError(
                "Travel date must use YYYY-MM-DD and the departure slot must come from the dropdown."
            ) from exc
        return_time_value = departure_time + timedelta(hours=duration_hours)
        if departure_time.hour < 6 or return_time_value.hour > 16 or return_time_value.date() != departure_time.date():
            raise ValueError("Day tours must stay within 6:00 AM and 4:00 PM.")
        party_size = self.party_size_var.get().strip()
        if not party_size:
            raise ValueError("Select a party size.")
        self.departure_var.set(departure_time.strftime(ReservationController.DATETIME_FORMAT))
        return {
            "destination": self.destination_var.get(),
            "departure_time": departure_time.strftime(ReservationController.DATETIME_FORMAT),
            "return_time": return_time_value.strftime(ReservationController.DATETIME_FORMAT),
            "party_size": party_size,
        }

    def _render_reservations(
        self,
        section: ctk.CTkFrame,
        reservations: list[dict],
        with_actions: bool,
    ) -> None:
        self._clear_section_content(section)
        if not reservations:
            ctk.CTkLabel(
                section,
                text="No reservations to show right now.",
                text_color=self.palette["muted"],
                font=("Segoe UI", 14),
            ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 18))
            return

        for row_index, reservation in enumerate(reservations, start=1):
            card = ctk.CTkFrame(
                section,
                fg_color=self.palette["surface"],
                corner_radius=20,
                border_width=1,
                border_color=self.palette["line"],
            )
            card.grid(row=row_index, column=0, sticky="ew", padx=24, pady=(0, 12))
            card.grid_columnconfigure(0, weight=1)

            departure_value = reservation["departure_time"]
            if isinstance(departure_value, datetime):
                departure_text = departure_value.strftime("%b %d, %Y %I:%M %p")
            else:
                departure_text = str(departure_value)

            ctk.CTkLabel(
                card,
                text=f"{reservation['reservation_code']} | {reservation['full_name']}",
                text_color=self.palette["text"],
                font=("Segoe UI", 16, "bold"),
            ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 6))
            badge_bg, badge_text = self._status_style(reservation["status"])
            ctk.CTkLabel(
                card,
                text=reservation["status"],
                text_color=badge_text,
                fg_color=badge_bg,
                corner_radius=12,
                padx=12,
                pady=6,
                font=("Segoe UI", 11, "bold"),
            ).grid(row=0, column=1, sticky="e", padx=18, pady=(16, 6))
            ctk.CTkLabel(
                card,
                text=(
                    f"{reservation['destination']} | {departure_text} | "
                    f"Cottage {reservation['cottage_code']} | Boat {reservation['motorboat_code']}"
                ),
                text_color=self.palette["muted"],
                font=("Segoe UI", 13),
                justify="left",
                wraplength=700,
            ).grid(row=1, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 12))

            if with_actions:
                action_row = ctk.CTkFrame(card, fg_color="transparent")
                action_row.grid(row=2, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 16))
                self._mini_button(
                    action_row,
                    "Load Code",
                    self.palette["surface_alt"],
                    self.palette["accent_dark"],
                    lambda code=reservation["reservation_code"]: self.action_code_var.set(code),
                ).grid(row=0, column=0, padx=(0, 8))
                if reservation["status"] == "Reserved":
                    self._mini_button(
                        action_row,
                        "Start",
                        self.palette["accent"],
                        self.palette["text"],
                        lambda code=reservation["reservation_code"]: self._quick_change("start", code),
                    ).grid(row=0, column=1, padx=(0, 8))
                self._mini_button(
                    action_row,
                    "Complete",
                    self.palette["brand"],
                    self.palette["surface"],
                    lambda code=reservation["reservation_code"]: self._quick_change("complete", code),
                ).grid(row=0, column=2, padx=(0, 8))
                self._mini_button(
                    action_row,
                    "Cancel",
                    self.palette["danger"],
                    self.palette["surface"],
                    lambda code=reservation["reservation_code"]: self._quick_change("cancel", code),
                ).grid(row=0, column=3)

    def _render_assets(self, key: str, assets: list[dict]) -> None:
        frame = self.asset_sections[key]
        self._clear_children(frame)
        if not assets:
            ctk.CTkLabel(
                frame,
                text="No assets available.",
                text_color=self.palette["muted"],
                font=("Segoe UI", 14),
            ).grid(row=0, column=0, sticky="w", padx=10, pady=10)
            return

        for row_index, asset in enumerate(assets):
            row = ctk.CTkFrame(
                frame,
                fg_color=self.palette["surface"],
                corner_radius=18,
                border_width=1,
                border_color=self.palette["line"],
            )
            row.grid(row=row_index, column=0, sticky="ew", padx=8, pady=8)
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                row,
                text=f"{asset['asset_code']} | {asset['name']}",
                text_color=self.palette["text"],
                font=("Segoe UI", 15, "bold"),
            ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))
            ctk.CTkLabel(
                row,
                text=f"Capacity {asset['capacity']} | Base rate PHP {float(asset['base_rate']):,.2f}",
                text_color=self.palette["muted"],
                font=("Segoe UI", 12),
            ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 14))
            badge_bg, badge_text = self._status_style(asset["status"])
            ctk.CTkLabel(
                row,
                text=asset["status"],
                fg_color=badge_bg,
                text_color=badge_text,
                corner_radius=12,
                padx=12,
                pady=6,
                font=("Segoe UI", 11, "bold"),
            ).grid(row=0, column=1, rowspan=2, sticky="e", padx=16)

    def _render_assignments(self, assignments: list[dict]) -> None:
        self._clear_section_content(self.assignment_frame)
        if not assignments:
            ctk.CTkLabel(
                self.assignment_frame,
                text="No assignment rows available.",
                text_color=self.palette["muted"],
                font=("Segoe UI", 14),
            ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 18))
            return

        board = ctk.CTkScrollableFrame(self.assignment_frame, fg_color="transparent", height=240)
        board.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        board.grid_columnconfigure(0, weight=1)

        for row_index, assignment in enumerate(assignments):
            card = ctk.CTkFrame(
                board,
                fg_color=self.palette["surface"],
                corner_radius=16,
                border_width=1,
                border_color=self.palette["line"],
            )
            card.grid(row=row_index, column=0, sticky="ew", pady=6)
            card.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                card,
                text=(
                    f"{assignment['cottage_code']} | {assignment['cottage_name']} | "
                    f"Boat: {assignment.get('motorboat_code') or 'Unassigned'}"
                ),
                text_color=self.palette["text"],
                font=("Segoe UI", 14, "bold"),
            ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 4))

            if assignment.get("reservation_code"):
                if isinstance(assignment.get("departure_time"), datetime):
                    departure_text = assignment["departure_time"].strftime("%b %d, %Y %I:%M %p")
                else:
                    departure_text = str(assignment.get("departure_time"))
                detail = (
                    f"{assignment['reservation_code']} | {assignment['customer_name']} | "
                    f"{assignment['destination']} | {departure_text} | "
                    f"Status: {assignment.get('reservation_status')}"
                )
            else:
                detail = "No scheduled reservation for this cottage right now."

            ctk.CTkLabel(
                card,
                text=detail,
                text_color=self.palette["muted"],
                font=("Segoe UI", 12),
                wraplength=860,
                justify="left",
            ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 12))

    def _build_asset_summary(self, snapshot: dict) -> str:
        cottages = self._count_statuses(snapshot["cottages"])
        boats = self._count_statuses(snapshot["motorboats"])
        return (
            "Cottages\n"
            f"Available: {cottages['Available']} | Reserved: {cottages['Reserved']} | In Use: {cottages['In Use']}\n\n"
            "Motorboats\n"
            f"Available: {boats['Available']} | Reserved: {boats['Reserved']} | In Use: {boats['In Use']}"
        )

    def _count_statuses(self, assets: list[dict]) -> dict:
        counts = {"Available": 0, "Reserved": 0, "In Use": 0}
        for asset in assets:
            counts[asset["status"]] = counts.get(asset["status"], 0) + 1
        return counts

    def _load_brand_images(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        for candidate in (
            project_root / "k3_logo.jpg",
            project_root / "inspo_preview.png",
            project_root / "inspo.avif",
        ):
            if not candidate.exists():
                continue
            try:
                image = Image.open(candidate).convert("RGB")
                self.logo_image = ctk.CTkImage(light_image=image, size=(92, 92))
                self.login_logo_image = ctk.CTkImage(light_image=image, size=(144, 144))
                self.hero_image = ctk.CTkImage(light_image=image, size=(430, 250))
                if self.brand_logo_label is not None:
                    self.brand_logo_label.configure(image=self.logo_image, text="")
                if self.login_logo_label is not None:
                    self.login_logo_label.configure(image=self.login_logo_image, text="")
                self.hero_image_label.configure(image=self.hero_image, text="")
                return
            except Exception:
                continue
        self.hero_image_label.configure(text="Add k3_logo.jpg to the project root for the brand artwork.")

    def _quick_change(self, action: str, reservation_code: str) -> None:
        self.action_code_var.set(reservation_code)
        self._execute_status_change(action)

    def _refresh_connection_state(self) -> None:
        live_mode = self.data_mode == "mysql"
        self.mode_var.set("LIVE MYSQL" if live_mode else "DEMO MODE")
        if self.mode_label is not None:
            self.mode_label.configure(
                fg_color=self.palette["accent_dark"] if live_mode else self.palette["brand_dark"]
            )
        if self.header_connect_button is not None:
            self.header_connect_button.configure(
                text="Reconnect MySQL" if live_mode else "Connect MySQL"
            )
        if self.home_notice is not None:
            self.home_notice.configure(
                text=self.startup_notice,
                fg_color=self.palette["good"] if live_mode else self.palette["surface_alt"],
            )
        if self.home_notice_button is not None:
            self.home_notice_button.configure(
                text="Reconnect MySQL" if live_mode else "Connect MySQL",
                fg_color=self.palette["surface_alt"] if live_mode else self.palette["accent"],
                hover_color="#E5D6C5" if live_mode else self.palette["accent_dark"],
                text_color=self.palette["accent_dark"] if live_mode else self.palette["text"],
            )

    def _open_database_dialog(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Connect MySQL")
        dialog.geometry("420x360")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=self.palette["page"])
        dialog.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            dialog,
            text="MySQL Connection",
            text_color=self.palette["text"],
            font=("Segoe UI", 22, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(22, 6))
        ctk.CTkLabel(
            dialog,
            text="Save these settings and switch the app from demo mode to the live database.",
            text_color=self.palette["muted"],
            font=("Segoe UI", 13),
            justify="left",
            wraplength=360,
        ).grid(row=1, column=0, sticky="w", padx=22, pady=(0, 18))

        host_var = ctk.StringVar(value="localhost")
        port_var = ctk.StringVar(value="3306")
        user_var = ctk.StringVar(value="root")
        password_var = ctk.StringVar(value="")
        database_var = ctk.StringVar(value="k3_floating_cottage")

        self._dialog_field(dialog, "Host", host_var, 2)
        self._dialog_field(dialog, "Port", port_var, 4)
        self._dialog_field(dialog, "User", user_var, 6)
        self._dialog_field(dialog, "Password", password_var, 8, password=True)
        self._dialog_field(dialog, "Database", database_var, 10)

        actions = ctk.CTkFrame(dialog, fg_color="transparent")
        actions.grid(row=12, column=0, sticky="ew", padx=22, pady=(8, 22))
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            actions,
            text="Cancel",
            command=dialog.destroy,
            height=40,
            corner_radius=12,
            fg_color=self.palette["surface_alt"],
            hover_color="#E5D6C5",
            text_color=self.palette["accent_dark"],
            font=("Segoe UI", 13, "bold"),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="Connect",
            command=lambda: self._connect_database(
                dialog,
                host_var.get(),
                port_var.get(),
                user_var.get(),
                password_var.get(),
                database_var.get(),
            ),
            height=40,
            corner_radius=12,
            fg_color=self.palette["accent"],
            hover_color=self.palette["accent_dark"],
            text_color=self.palette["text"],
            font=("Segoe UI", 13, "bold"),
        ).grid(row=0, column=1, sticky="ew", padx=(8, 0))

    def _dialog_field(
        self,
        parent: ctk.CTkToplevel,
        label: str,
        variable: ctk.StringVar,
        row: int,
        password: bool = False,
    ) -> None:
        ctk.CTkLabel(
            parent,
            text=label,
            text_color=self.palette["muted"],
            font=("Segoe UI", 12, "bold"),
        ).grid(row=row, column=0, sticky="w", padx=22, pady=(0, 6))
        entry = ctk.CTkEntry(
            parent,
            textvariable=variable,
            height=40,
            corner_radius=12,
            border_width=1,
            border_color=self.palette["line"],
            fg_color=self.palette["surface"],
            text_color=self.palette["text"],
            show="*" if password else "",
        )
        entry.grid(row=row + 1, column=0, sticky="ew", padx=22, pady=(0, 10))

    def _connect_database(
        self,
        dialog: ctk.CTkToplevel,
        host: str,
        port: str,
        user: str,
        password: str,
        database: str,
    ) -> None:
        if self.connect_database_callback is None:
            messagebox.showerror("Connect MySQL", "No database connection callback is configured.")
            return
        try:
            context = self.connect_database_callback(host, port, user, password, database)
        except Exception as exc:
            self._set_status(f"MySQL connection failed: {exc}", tone="danger")
            messagebox.showerror("Connect MySQL", str(exc))
            return

        self._apply_context(context)
        dialog.destroy()
        messagebox.showinfo("Connect MySQL", "Connected. New reservations will now save to MySQL.")

    def _apply_context(self, context) -> None:
        self.reservation_controller = context.reservation_controller
        self.dashboard_controller = context.dashboard_controller
        self.data_mode = context.data_mode
        self.startup_notice = context.startup_notice
        self.destination_var.set(self.reservation_controller.destinations()[0])
        self._refresh_connection_state()
        self.refresh_dashboard(status_message=self.startup_notice)

    def _mini_button(self, parent, text: str, fg_color: str, text_color: str, command) -> ctk.CTkButton:
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            width=96,
            height=34,
            corner_radius=13,
            fg_color=fg_color,
            hover_color=self.palette["accent_dark"] if fg_color == self.palette["accent"] else self.palette["brand_dark"],
            text_color=text_color,
            font=("Segoe UI", 12, "bold"),
        )

    def _status_style(self, status: str) -> tuple[str, str]:
        return {
            "Available": (
                self.palette["status_available"],
                self.palette["status_available_text"],
            ),
            "Reserved": (
                self.palette["status_reserved"],
                self.palette["status_reserved_text"],
            ),
            "In Use": (
                self.palette["status_in_use"],
                self.palette["status_in_use_text"],
            ),
            "Completed": (
                self.palette["status_completed"],
                self.palette["status_completed_text"],
            ),
            "Cancelled": (
                self.palette["status_cancelled"],
                self.palette["status_cancelled_text"],
            ),
        }.get(status, (self.palette["surface_alt"], self.palette["text"]))

    def _set_status(self, message: str, tone: str = "info") -> None:
        self.status_var.set(message)
        self.status_label.configure(
            text_color={
                "info": self.palette["text"],
                "warning": self.palette["brand_dark"],
                "danger": self.palette["danger"],
            }.get(tone, self.palette["text"])
        )

    def _clear_section_content(self, section: ctk.CTkFrame) -> None:
        for child in section.winfo_children()[1:]:
            child.destroy()

    def _clear_children(self, widget) -> None:
        for child in widget.winfo_children():
            child.destroy()
