from datetime import date as date_type, datetime, timedelta
from pathlib import Path
import queue
import re
import sys
import threading
import tkinter.messagebox as messagebox

import customtkinter as ctk
from CTkTable import CTkTable
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from PIL import Image, ImageFilter

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
from k3_rms.controllers.auth_controller import AuthController
from k3_rms.controllers.dashboard_controller import DashboardController
from k3_rms.controllers.reservation_controller import ReservationController
from k3_rms.cottage_media import COTTAGE_IMAGE_MAP
from k3_rms.exceptions import ApplicationError
from k3_rms.ui_scaling import apply_customtkinter_scaling
from k3_rms.widgets.destination_popularity_card import DestinationPopularityCard
from k3_rms.widgets.date_picker import DatePickerField


class DesktopView(ctk.CTk):
    def __init__(
        self,
        reservation_controller: ReservationController,
        dashboard_controller: DashboardController,
        auth_controller: AuthController,
        login_settings: AppLoginSettings | None = None,
        data_mode: str = "mysql",
        startup_notice: str | None = None,
        connect_database_callback=None,
        launch_user_portal_callback=None,
    ) -> None:
        super().__init__()
        self.reservation_controller = reservation_controller
        self.dashboard_controller = dashboard_controller
        self.auth_controller = auth_controller
        self.login_settings = login_settings or AppLoginSettings()
        self.data_mode = data_mode
        self.startup_notice = startup_notice or "Ready."
        self.connect_database_callback = connect_database_callback
        self.launch_user_portal_callback = launch_user_portal_callback
        self.palette = {
            "bg": "#F5F3F0",  # Soft off-white/light beige background
            "page": "#FDFCFB",  # Slightly warmer white for cards
            "surface": "#FFFFFF",  # Pure white for cards
            "surface_alt": "#F9F7F4",  # Light beige alt
            "brand": "#0D5E60",  # Deep teal primary
            "brand_dark": "#094548",  # Darker teal
            "accent": "#7FD4D0",  # Aqua blue
            "accent_dark": "#4FA8A5",  # Darker aqua
            "sand": "#D4BDAA",  # Warm sand/tan
            "sage": "#B5C9A8",  # Sage green
            "coral": "#E8A399",  # Soft coral for logout
            "text": "#0D5E60",  # Deep teal for typography
            "text_secondary": "#6B7B79",  # Muted text
            "muted": "#9BA9A7",  # Muted accents
            "line": "#E8E4E0",  # Subtle borders
            "hover": "#F0F4F4",
            "sidebar_active": "#F0F4F4",
            "sidebar_hover": "#F9F7F4",
            "danger": "#D0757A",
            "good": "#C5E3D4",
            "status_available": "#C5E3D4",
            "status_available_text": "#0D5E60",
            "status_reserved": "#F7E6B9",
            "status_reserved_text": "#8C6115",
            "status_in_use": "#B8D4E8",
            "status_in_use_text": "#1F4F86",
            "status_completed": "#D4C9E8",
            "status_completed_text": "#59539A",
            "status_cancelled": "#E8B5B0",
            "status_cancelled_text": "#9E4A40",
        }
        self.page_frames: dict[str, ctk.CTkFrame] = {}
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        self.metric_targets: dict[str, list[ctk.CTkLabel]] = {}
        self.asset_sections: dict[str, ctk.CTkScrollableFrame] = {}
        self.current_page = "home"  # Track current page
        self.current_page_label = None  # Display current page name
        self.back_button = None  # Back button reference
        self.hero_image_label = None
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
        self.home_active_reservations_label = None
        self.home_reservations_frame = None
        self.operations_reservations_frame = None
        self.operations_reservations_table_frame = None
        self.payments_summary_frame = None
        self.payments_table_frame = None
        self.dashboard_overview_reservations_frame = None
        self.todays_bookings_frame = None
        self.dashboard_overview_reservations_frame = None
        self.dashboard_overview_summary_frame = None
        self.dashboard_guest_summary_frame = None
        self.dashboard_guest_table_frame = None
        self.dashboard_destination_popularity_card = None
        self.dashboard_destinations_table_frame = None
        self.dashboard_cottage_popularity_card = None
        self.dashboard_cottages_table_frame = None
        self.dashboard_cottage_performance_summary_frame = None
        self.dashboard_cottage_period_graph_frame = None
        self.dashboard_all_cottages_performance_frame = None
        self.dashboard_cottage_weekly_leaders_frame = None
        self.dashboard_cottage_monthly_leaders_frame = None
        self.dashboard_cottage_yearly_leaders_frame = None
        self.dashboard_bookings_summary_frame = None
        self.dashboard_bookings_frame = None
        self.dashboard_asset_analytics_frame = None
        self.dashboard_asset_analytics_summary_frame = None
        self.dashboard_asset_analytics_chart_frame = None
        self.asset_analytics_canvas = None
        self.asset_analytics_figure = None
        self.asset_analytics_chart_card = None
        self.asset_analytics_canvas_host = None
        self.anim = None
        self.cottage_leader_anim = None
        self.asset_analytics_visibility_job = None
        self._dashboard_refresh_active = False
        self._dashboard_refresh_request_id = 0
        self._dashboard_refresh_pending_request: tuple[date_type | None, str | None] | None = None
        self._dashboard_refresh_results: queue.Queue = queue.Queue()
        self.dashboard_tabview = None
        self.dashboard_section_frames: dict[str, ctk.CTkFrame] = {}
        self.dashboard_section_buttons: dict[str, ctk.CTkButton] = {}
        self.dashboard_current_section = "overview"
        self.asset_tab_frames: dict[str, ctk.CTkFrame] = {}
        self.asset_tab_buttons: dict[str, ctk.CTkButton] = {}
        self.asset_current_tab = "destinations"
        self.dashboard_bookings_current_tab = "pending"
        self.cottage_option_menu = None
        self.cottage_assets_by_label: dict[str, dict] = {}
        self.cottage_option_values: tuple[str, ...] = ()
        self.selected_cottage_image = None
        self.selected_cottage_image_label = None
        self.selected_cottage_status_label = None
        self.asset_cottage_filter_menu = None
        self.asset_destination_filter_menu = None
        self.asset_cottage_filter_values: tuple[str, ...] = ("All Cottages",)
        self.asset_destination_filter_values: tuple[str, ...] = ("All Destinations",)
        self.last_dashboard_snapshot: dict | None = None
        self.asset_sort_state = {
            "cottages": {"key": "status", "descending": False},
            "destinations": {"key": "status", "descending": False},
        }
        self.filtered_asset_counts: dict[str, tuple[int, int]] = {}
        self.reservation_sort_key = "departure_time"
        self.reservation_sort_descending = False
        self.payment_sort_key = "departure_time"
        self.payment_sort_descending = False
        self.destination_assets_by_name: dict[str, dict] = {}
        self.destination_checkboxes: dict[str, ctk.CTkCheckBox] = {}
        
        # Admin profile panel state
        self.profile_dropdown = None
        self.profile_dropdown_visible = False
        self.notifications_panel = None
        self.notifications_visible = False
        self.unread_notifications_count = 0
        self.notification_items: list[dict] = []
        self.seen_notification_ids: set[str] = set()
        self.user_portal_handle = None
        self.guest_portal_host = None
        self.guest_portal_shell = None

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.screen_profile = apply_customtkinter_scaling(
            self.winfo_screenwidth(),
            self.winfo_screenheight(),
        )
        self._build_variables()
        self._build_window()
        self._build_shell()
        self._build_login_overlay()
        self._load_brand_images()
        self.show_dashboard()
        self.refresh_dashboard(status_message=self.startup_notice)
        self._refresh_connection_state()
        self._show_login_overlay(initial=True)
        self.after(60, self._drain_dashboard_refresh_results)
        self.after(15000, self._poll_notifications)

    def run(self) -> None:
        self.mainloop()

    def _refresh_cottage_catalog(
        self,
        cottages: list[dict] | None = None,
        destinations: list[dict] | None = None,
    ) -> None:
        current_value = self.cottage_var.get().strip() if hasattr(self, "cottage_var") else ""
        self.cottage_assets_by_label = {}
        values: list[str] = []

        source = cottages
        if source is None:
            source = self.reservation_controller.cottages(self._parse_ui_date(self.departure_date_var.get()))
        for cottage in source:
            asset_code = cottage.get("asset_code")
            if not asset_code:
                continue
            label = f"{asset_code} | {cottage.get('name', 'Cottage')}"
            self.cottage_assets_by_label[label] = dict(cottage)
            values.append(label)

        if not values:
            values = ["No cottages available"]

        self.cottage_option_values = tuple(values)
        if self.cottage_option_menu is not None:
            self.cottage_option_menu.configure(values=list(self.cottage_option_values))

        next_value = current_value if current_value in self.cottage_option_values else self.cottage_option_values[0]
        if self.cottage_var.get() != next_value:
            self.cottage_var.set(next_value)
        self._update_selected_cottage_preview()
        self._refresh_destination_catalog(destinations)
        self._update_live_reservation_summary()

    def _refresh_destination_catalog(self, destinations: list[dict] | None = None) -> None:
        try:
            source = (
                destinations
                if destinations is not None
                else self.reservation_controller.asset_model.list_destinations(
                    self._parse_ui_date(self.departure_date_var.get()) if hasattr(self, "departure_date_var") else None
                )
            )
            self.destination_assets_by_name = {d["name"]: d for d in source}
            self._refresh_destination_checkbox_labels()
        except Exception:
            pass

    def _refresh_destination_checkbox_labels(self) -> None:
        for name, checkbox in self.destination_checkboxes.items():
            asset = self.destination_assets_by_name.get(name)
            rate = float(asset.get("base_rate", 0)) if asset else 0
            rate_text = f" (+PHP {rate:,.0f})" if rate > 0 else " (Included)"
            checkbox.configure(text=f"{name}{rate_text}")

    def _selected_cottage_asset(self) -> dict | None:
        return self.cottage_assets_by_label.get(self.cottage_var.get().strip())

    def _resolve_cottage_image_path(self, asset_code: str | None) -> Path | None:
        if not asset_code:
            return None
        relative_path = COTTAGE_IMAGE_MAP.get(asset_code)
        if not relative_path:
            return None
        project_root = Path(__file__).resolve().parents[2]
        image_path = project_root / "k3_user" / relative_path
        return image_path if image_path.exists() else None

    def _update_selected_cottage_preview(self, *_args) -> None:
        asset = self._selected_cottage_asset()
        if asset is None:
            self.selected_cottage_name_var.set("Choose a cottage to preview")
            self.selected_cottage_meta_var.set("The selected cottage image, status, and base rate will appear here.")
            if self.selected_cottage_status_label is not None:
                self.selected_cottage_status_label.configure(
                    text="Not Selected",
                    fg_color=self.palette["surface_alt"],
                    text_color=self.palette["muted"],
                )
            if self.selected_cottage_image_label is not None:
                self.selected_cottage_image_label.configure(image=None, text="Preview unavailable")
            self.selected_cottage_image = None
            return

        asset_code = asset.get("asset_code")
        self.selected_cottage_name_var.set(f"{asset_code} | {asset.get('name', 'Cottage')}")
        self.selected_cottage_meta_var.set(
            f"Capacity: {asset.get('capacity', 0)} pax  |  Base rate: PHP {float(asset.get('base_rate', 0)):,.2f}"
        )
        status = asset.get("status", "Available")
        badge_bg, badge_text = self._status_style(status)
        if self.selected_cottage_status_label is not None:
            self.selected_cottage_status_label.configure(
                text=status,
                fg_color=badge_bg,
                text_color=badge_text,
            )

        if self.selected_cottage_image_label is None:
            return

        image_path = self._resolve_cottage_image_path(asset_code)
        if image_path is None:
            self.selected_cottage_image = None
            self.selected_cottage_image_label.configure(image=None, text="Preview unavailable")
            return

        try:
            image = Image.open(image_path).convert("RGBA")
            self.selected_cottage_image = ctk.CTkImage(light_image=image, dark_image=image, size=(320, 180))
            self.selected_cottage_image_label.configure(image=self.selected_cottage_image, text="")
        except Exception:
            self.selected_cottage_image = None
            self.selected_cottage_image_label.configure(image=None, text="Preview unavailable")

    def _handle_reservation_date_change(self, *_args) -> None:
        self._refresh_cottage_catalog()
        self._update_return_preview()

    def _parse_ui_date(self, value: str | None) -> date_type | None:
        if not value:
            return None
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d").date()
        except ValueError:
            return None

    @staticmethod
    def _natural_sort_key(value) -> list[object]:
        return [
            int(chunk) if chunk.isdigit() else chunk.lower()
            for chunk in re.split(r"(\d+)", str(value or ""))
            if chunk != ""
        ]

    @staticmethod
    def _asset_status_priority(status: str | None) -> int:
        return {
            "Available": 0,
            "Reserved": 1,
            "On Going": 2,
            "Completed": 3,
            "Cancelled": 4,
        }.get(status or "", 5)

    @staticmethod
    def _reservation_status_priority(status: str | None) -> int:
        return {
            "Pending": 0,
            "Confirmed": 0,
            "Approved": 1,
            "Reserved": 1,
            "On Going": 1,
            "Completed": 2,
            "Cancelled": 3,
        }.get(status or "", 4)

    @staticmethod
    def _payment_status_priority(status: str | None) -> int:
        return {
            "Unpaid": 0,
            "Partially Paid": 1,
            "Paid": 2,
            "Refunded": 3,
        }.get(status or "", 4)

    def _selected_asset_reference_date(self) -> date_type:
        return self._parse_ui_date(self.asset_table_date_var.get()) or date_type.today()

    def _refresh_asset_filter_options(self, snapshot: dict | None) -> None:
        cottages = snapshot.get("cottages", []) if snapshot else []
        destinations = snapshot.get("destinations", []) if snapshot else []

        cottage_values = ["All Cottages"] + [
            f"{asset.get('asset_code', '')} | {asset.get('name', 'Cottage')}"
            for asset in cottages
            if asset.get("asset_code")
        ]
        destination_values = ["All Destinations"] + [
            f"{asset.get('asset_code', '')} | {asset.get('name', 'Destination')}"
            for asset in destinations
            if asset.get("asset_code")
        ]

        self.asset_cottage_filter_values = tuple(dict.fromkeys(cottage_values))
        self.asset_destination_filter_values = tuple(dict.fromkeys(destination_values))

        current_cottage = self.asset_cottage_filter_var.get().strip()
        current_destination = self.asset_destination_filter_var.get().strip()

        if self.asset_cottage_filter_menu is not None:
            self.asset_cottage_filter_menu.configure(values=list(self.asset_cottage_filter_values))
        if self.asset_destination_filter_menu is not None:
            self.asset_destination_filter_menu.configure(values=list(self.asset_destination_filter_values))

        self.asset_cottage_filter_var.set(
            current_cottage if current_cottage in self.asset_cottage_filter_values else self.asset_cottage_filter_values[0]
        )
        self.asset_destination_filter_var.set(
            current_destination if current_destination in self.asset_destination_filter_values else self.asset_destination_filter_values[0]
        )

    def _reservation_status_matches_filter(self, status: str | None) -> bool:
        selected = self.reservation_status_filter_var.get().strip()
        if not selected or selected == "All":
            return True
        normalized = selected.lower()
        value = (status or "").strip().lower()
        if normalized == "pending":
            return value in {"pending", "confirmed"}
        if normalized in {"approved", "approved / reserved", "reserved"}:
            return value in {"approved", "reserved", "on going"}
        return value == normalized

    def _filtered_sorted_assets(self, key: str, assets: list[dict]) -> list[dict]:
        availability = self.asset_availability_filter_var.get().strip()
        selected_label = (
            self.asset_cottage_filter_var.get().strip()
            if key == "cottages"
            else self.asset_destination_filter_var.get().strip()
        )
        all_label = "All Cottages" if key == "cottages" else "All Destinations"

        filtered: list[dict] = []
        for asset in assets:
            asset_code = str(asset.get("asset_code") or "")
            name = str(asset.get("name") or "")
            status = str(asset.get("status") or "Available")
            asset_label = f"{asset_code} | {name}"
            if availability and availability != "All" and status != availability:
                continue
            if selected_label and selected_label != all_label and asset_label != selected_label:
                continue
            filtered.append(asset)

        sort_state = self.asset_sort_state.get(key, {"key": "status", "descending": False})
        sort_key = sort_state["key"]
        descending = bool(sort_state["descending"])

        def sort_value(asset: dict):
            if sort_key == "status":
                return (
                    self._asset_status_priority(asset.get("status")),
                    self._natural_sort_key(asset.get("name")),
                    self._natural_sort_key(asset.get("asset_code")),
                )
            if sort_key == "asset_code":
                return self._natural_sort_key(asset.get("asset_code"))
            if sort_key == "name":
                return self._natural_sort_key(asset.get("name"))
            if sort_key == "capacity":
                return (int(asset.get("capacity") or 0), self._natural_sort_key(asset.get("name")))
            if sort_key == "base_rate":
                return (float(asset.get("base_rate") or 0), self._natural_sort_key(asset.get("name")))
            return self._natural_sort_key(asset.get("name"))

        return sorted(filtered, key=sort_value, reverse=descending)

    def _filtered_sorted_reservations(self, reservations: list[dict]) -> list[dict]:
        search_text = self.reservation_search_var.get().strip().lower()
        cottage_filter = self.reservation_cottage_filter_var.get().strip().lower()
        selected_date = self._parse_ui_date(self.reservation_filter_date_var.get())

        filtered: list[dict] = []
        for reservation in reservations:
            departure_time = reservation.get("departure_time")
            created_at = reservation.get("created_at")
            departure_text = (
                departure_time.strftime("%Y-%m-%d %H:%M")
                if isinstance(departure_time, datetime)
                else str(departure_time or "")
            )
            friendly_departure_text = (
                departure_time.strftime("%b %d, %Y %I:%M %p")
                if isinstance(departure_time, datetime)
                else departure_text
            )
            created_text = (
                created_at.strftime("%Y-%m-%d %H:%M")
                if isinstance(created_at, datetime)
                else str(created_at or "")
            )
            friendly_created_text = (
                created_at.strftime("%b %d, %Y %I:%M %p")
                if isinstance(created_at, datetime)
                else created_text
            )
            search_blob = " ".join(
                [
                    str(reservation.get("reservation_code") or ""),
                    str(reservation.get("full_name") or ""),
                    str(reservation.get("contact_number") or ""),
                    str(reservation.get("email") or ""),
                    str(reservation.get("cottage_code") or ""),
                    str(reservation.get("cottage_name") or ""),
                    str(reservation.get("destination") or ""),
                    departure_text,
                    friendly_departure_text,
                    created_text,
                    friendly_created_text,
                ]
            ).lower()

            cottage_blob = f"{reservation.get('cottage_code') or ''} {reservation.get('cottage_name') or ''}".lower()
            if search_text and search_text not in search_blob:
                continue
            if cottage_filter and cottage_filter not in cottage_blob:
                continue
            if selected_date and (
                not isinstance(departure_time, datetime) or departure_time.date() != selected_date
            ):
                continue
            if not self._reservation_status_matches_filter(reservation.get("status")):
                continue
            filtered.append(reservation)

        sort_key = self.reservation_sort_key
        descending = self.reservation_sort_descending
        now = datetime.now()

        def reservation_value(reservation: dict):
            if sort_key == "reservation_code":
                return self._natural_sort_key(reservation.get("reservation_code"))
            if sort_key == "cottage_name":
                return (
                    self._natural_sort_key(reservation.get("cottage_name")),
                    self._natural_sort_key(reservation.get("cottage_code")),
                )
            if sort_key == "full_name":
                return self._natural_sort_key(reservation.get("full_name"))
            if sort_key == "contact_number":
                return self._natural_sort_key(reservation.get("contact_number"))
            if sort_key == "status":
                return (
                    self._reservation_status_priority(reservation.get("status")),
                    reservation.get("departure_time") or datetime.max,
                )
            if sort_key == "total_price":
                return float(reservation.get("total_price") or 0)
            if sort_key == "created_at":
                return reservation.get("created_at") or datetime.min
            return reservation.get("departure_time") or datetime.max

        if sort_key == "departure_time" and not descending:
            return sorted(
                filtered,
                key=lambda reservation: (
                    0 if isinstance(reservation.get("departure_time"), datetime) and reservation["departure_time"] >= now else 1,
                    reservation.get("departure_time") if isinstance(reservation.get("departure_time"), datetime) and reservation["departure_time"] >= now else datetime.max,
                    -reservation["departure_time"].timestamp() if isinstance(reservation.get("departure_time"), datetime) and reservation["departure_time"] < now else 0,
                ),
            )
        return sorted(filtered, key=reservation_value, reverse=descending)

    def _payment_status_matches_filter(self, status: str | None) -> bool:
        selected = self.payment_status_filter_var.get().strip()
        if not selected or selected == "All":
            return True
        return (status or "").strip().lower() == selected.lower()

    def _filtered_sorted_payments(self, reservations: list[dict]) -> list[dict]:
        search_text = self.payment_search_var.get().strip().lower()
        selected_date = self._parse_ui_date(self.payment_filter_date_var.get())

        filtered: list[dict] = []
        for reservation in reservations:
            departure_time = reservation.get("departure_time")
            paid_at = reservation.get("paid_at")
            departure_text = (
                departure_time.strftime("%Y-%m-%d %H:%M")
                if isinstance(departure_time, datetime)
                else str(departure_time or "")
            )
            paid_text = (
                paid_at.strftime("%Y-%m-%d %H:%M")
                if isinstance(paid_at, datetime)
                else str(paid_at or "")
            )
            search_blob = " ".join(
                [
                    str(reservation.get("reservation_code") or ""),
                    str(reservation.get("full_name") or ""),
                    str(reservation.get("contact_number") or ""),
                    str(reservation.get("email") or ""),
                    str(reservation.get("cottage_code") or ""),
                    str(reservation.get("cottage_name") or ""),
                    str(reservation.get("destination") or ""),
                    str(reservation.get("payment_status") or ""),
                    str(reservation.get("payment_method") or ""),
                    departure_text,
                    paid_text,
                ]
            ).lower()

            if search_text and search_text not in search_blob:
                continue
            if selected_date and (
                not isinstance(departure_time, datetime) or departure_time.date() != selected_date
            ):
                continue
            if not self._payment_status_matches_filter(reservation.get("payment_status")):
                continue
            filtered.append(reservation)

        sort_key = self.payment_sort_key
        descending = self.payment_sort_descending
        now = datetime.now()

        def billing_value(reservation: dict):
            if sort_key == "reservation_code":
                return self._natural_sort_key(reservation.get("reservation_code"))
            if sort_key == "full_name":
                return self._natural_sort_key(reservation.get("full_name"))
            if sort_key == "cottage_name":
                return (
                    self._natural_sort_key(reservation.get("cottage_name")),
                    self._natural_sort_key(reservation.get("cottage_code")),
                )
            if sort_key == "payment_status":
                return (
                    self._payment_status_priority(reservation.get("payment_status")),
                    reservation.get("departure_time") or datetime.max,
                )
            if sort_key == "total_price":
                return float(reservation.get("total_price") or 0)
            if sort_key == "amount_paid":
                return float(reservation.get("amount_paid") or 0)
            if sort_key == "balance_due":
                return float(reservation.get("balance_due") or 0)
            if sort_key == "payment_method":
                return self._natural_sort_key(reservation.get("payment_method"))
            if sort_key == "status":
                return (
                    self._reservation_status_priority(reservation.get("status")),
                    reservation.get("departure_time") or datetime.max,
                )
            if sort_key == "paid_at":
                return reservation.get("paid_at") or datetime.min
            return reservation.get("departure_time") or datetime.max

        if sort_key == "departure_time" and not descending:
            return sorted(
                filtered,
                key=lambda reservation: (
                    0 if isinstance(reservation.get("departure_time"), datetime) and reservation["departure_time"] >= now else 1,
                    reservation.get("departure_time") if isinstance(reservation.get("departure_time"), datetime) and reservation["departure_time"] >= now else datetime.max,
                    -reservation["departure_time"].timestamp() if isinstance(reservation.get("departure_time"), datetime) and reservation["departure_time"] < now else 0,
                ),
            )
        return sorted(filtered, key=billing_value, reverse=descending)

    def _apply_asset_filters(self) -> None:
        self.refresh_dashboard(status_message="Asset filters applied.")

    def _reset_asset_filters(self) -> None:
        self.asset_table_date_var.set(date_type.today().isoformat())
        self.asset_availability_filter_var.set("All")
        self.asset_cottage_filter_var.set("All Cottages")
        self.asset_destination_filter_var.set("All Destinations")
        self.asset_sort_state = {
            "cottages": {"key": "status", "descending": False},
            "destinations": {"key": "status", "descending": False},
        }
        self.refresh_dashboard(status_message="Asset filters reset.")

    def _apply_reservation_filters(self) -> None:
        self._rerender_tables_from_snapshot()
        self._set_status("Reservation filters applied.")

    def _reset_reservation_filters(self) -> None:
        self.reservation_filter_date_var.set("")
        self.reservation_status_filter_var.set("All")
        self.reservation_cottage_filter_var.set("")
        self.reservation_search_var.set("")
        self.reservation_sort_key = "departure_time"
        self.reservation_sort_descending = False
        self._rerender_tables_from_snapshot()
        self._set_status("Reservation filters reset.")

    def _apply_payment_filters(self) -> None:
        self._rerender_tables_from_snapshot()
        self._set_status("Payment filters applied.")

    def _reset_payment_filters(self) -> None:
        self.payment_filter_date_var.set("")
        self.payment_status_filter_var.set("All")
        self.payment_search_var.set("")
        self.payment_sort_key = "departure_time"
        self.payment_sort_descending = False
        self._rerender_tables_from_snapshot()
        self._set_status("Payment filters reset.")

    def _toggle_asset_sort(self, key: str, column: str) -> None:
        state = self.asset_sort_state.setdefault(key, {"key": "status", "descending": False})
        if state["key"] == column:
            state["descending"] = not state["descending"]
        else:
            state["key"] = column
            state["descending"] = False
        self._rerender_tables_from_snapshot()

    def _toggle_reservation_sort(self, column: str) -> None:
        if self.reservation_sort_key == column:
            self.reservation_sort_descending = not self.reservation_sort_descending
        else:
            self.reservation_sort_key = column
            self.reservation_sort_descending = False
        self._rerender_tables_from_snapshot()

    def _toggle_payment_sort(self, column: str) -> None:
        if self.payment_sort_key == column:
            self.payment_sort_descending = not self.payment_sort_descending
        else:
            self.payment_sort_key = column
            self.payment_sort_descending = False
        self._rerender_tables_from_snapshot()

    def _rerender_tables_from_snapshot(self) -> None:
        if not self.last_dashboard_snapshot:
            return
        snapshot = self.last_dashboard_snapshot
        if self.current_page == "operations":
            if self.operations_reservations_table_frame is not None:
                self._render_reservations_table(snapshot.get("reservations", []))
            if hasattr(self, "_ops_content_frame") and self._ops_content_frame is not None:
                self._render_operations_current_tab()
            return
        if self.current_page == "payments":
            if self.payments_summary_frame is not None or self.payments_table_frame is not None:
                self._render_payments_page(snapshot.get("reservations", []))
            return
        if self.current_page == "dashboard" and self.dashboard_current_section == "assets":
            self._render_assets("cottages", snapshot.get("cottages", []))
            self._render_assets("destinations", snapshot.get("destinations", []))

    def _queue_dashboard_refresh(
        self,
        reference_date: date_type | None,
        status_message: str | None,
    ) -> None:
        self._dashboard_refresh_pending_request = (reference_date, status_message)
        if self._dashboard_refresh_active:
            self._set_status("Refreshing dashboard...")
            return
        self._start_pending_dashboard_refresh()

    def _start_pending_dashboard_refresh(self) -> None:
        if self._dashboard_refresh_pending_request is None:
            return
        reference_date, status_message = self._dashboard_refresh_pending_request
        self._dashboard_refresh_pending_request = None
        self._dashboard_refresh_active = True
        self._dashboard_refresh_request_id += 1
        request_id = self._dashboard_refresh_request_id
        self._set_status("Refreshing dashboard...")
        worker = threading.Thread(
            target=self._load_dashboard_snapshot_in_background,
            args=(request_id, reference_date, status_message),
            daemon=True,
        )
        worker.start()

    def _load_dashboard_snapshot_in_background(
        self,
        request_id: int,
        reference_date: date_type | None,
        status_message: str | None,
    ) -> None:
        snapshot: dict | None = None
        error: Exception | None = None
        try:
            snapshot = self.dashboard_controller.get_dashboard_snapshot(reference_date)
        except Exception as exc:
            error = exc
        self._dashboard_refresh_results.put(
            (request_id, snapshot, status_message, error)
        )

    def _drain_dashboard_refresh_results(self) -> None:
        if not self.winfo_exists():
            return
        try:
            while True:
                request_id, snapshot, status_message, error = self._dashboard_refresh_results.get_nowait()
                self._complete_dashboard_refresh(
                    request_id,
                    snapshot,
                    status_message,
                    error,
                )
        except queue.Empty:
            pass
        self.after(60, self._drain_dashboard_refresh_results)

    def _complete_dashboard_refresh(
        self,
        request_id: int,
        snapshot: dict | None,
        status_message: str | None,
        error: Exception | None,
    ) -> None:
        if not self.winfo_exists():
            return
        self._dashboard_refresh_active = False

        if error is not None or snapshot is None:
            self._set_status(f"Dashboard refresh failed: {error}", tone="danger")
        else:
            self._apply_dashboard_snapshot(snapshot, status_message)

        if self._dashboard_refresh_pending_request is not None and request_id == self._dashboard_refresh_request_id:
            self._start_pending_dashboard_refresh()

    def _apply_dashboard_snapshot(self, snapshot: dict, status_message: str | None) -> None:
        self.last_dashboard_snapshot = snapshot
        self._refresh_asset_filter_options(snapshot)
        # Keep the reservation form bound to its own selected travel date instead of
        # overwriting it with the dashboard asset snapshot date.
        self._refresh_cottage_catalog()
        self._update_home_active_reservations(snapshot)
        self.asset_summary_var.set(self._build_asset_summary(snapshot))
        self._refresh_notifications_cache()
        self._render_visible_snapshot(snapshot)
        self._set_status(status_message or "Dashboard refreshed.")

    def _update_home_active_reservations(self, snapshot: dict) -> None:
        if self.home_active_reservations_label is None:
            return
        active_trips = int(snapshot.get("metrics", {}).get("active_reservations") or 0)
        summary_text = f"{active_trips} active reservations | Manage your floating cottage with ease"
        self.home_active_reservations_label.configure(text=summary_text)

    def _render_visible_snapshot(
        self,
        snapshot: dict,
        replay_animations: bool = False,
    ) -> None:
        reservations = snapshot.get("reservations", [])

        if self.current_page == "home":
            if self.home_reservations_frame:
                self._render_reservations(
                    self.home_reservations_frame,
                    snapshot.get("active_reservations", [])[:4],
                    with_actions=False,
                )
            return

        if self.current_page == "operations":
            if self.operations_reservations_frame is not None and self.operations_reservations_table_frame is None:
                self._render_reservations(
                    self.operations_reservations_frame,
                    snapshot.get("active_reservations", []),
                    with_actions=True,
                )
            elif self.operations_reservations_table_frame is not None:
                self._render_reservations_table(reservations)
            if hasattr(self, "_ops_content_frame") and self._ops_content_frame is not None:
                self._render_operations_current_tab()
            return

        if self.current_page == "payments":
            if self.payments_summary_frame is not None or self.payments_table_frame is not None:
                self._render_payments_page(reservations)
            return

        if self.current_page != "dashboard":
            return

        if self.dashboard_current_section == "overview":
            if self.dashboard_asset_analytics_summary_frame or self.dashboard_asset_analytics_chart_frame:
                self._render_asset_analytics(reservations, animate=replay_animations)
            if self.dashboard_cottage_period_graph_frame:
                leader_data = self._build_cottage_leader_rows(
                    reservations,
                    snapshot.get("cottages", []),
                )
                self._render_cottage_period_graph(
                    self.dashboard_cottage_period_graph_frame,
                    leader_data,
                )
            if self.dashboard_overview_summary_frame:
                self._render_overview_dashboard(reservations)
            if self.dashboard_overview_reservations_frame:
                self._render_reservations(
                    self.dashboard_overview_reservations_frame,
                    self._dashboard_reservation_feed(reservations, limit=4),
                    with_actions=False,
                )
            if self.todays_bookings_frame:
                self._render_todays_bookings(reservations)
            return

        if self.dashboard_current_section == "assets":
            self._render_assets("cottages", snapshot.get("cottages", []))
            self._render_assets("destinations", snapshot.get("destinations", []))
            if self.asset_current_tab == "cottages":
                self._render_cottage_dashboard(
                    reservations,
                    snapshot.get("cottages", []),
                    animate=replay_animations,
                )
            else:
                self._render_destination_dashboard(
                    reservations,
                    snapshot.get("destinations", []),
                    animate=replay_animations,
                )
            return

        if self.dashboard_current_section == "guests":
            if self.dashboard_guest_summary_frame or self.dashboard_guest_table_frame:
                self._render_guest_dashboard(reservations)
            return

        if self.dashboard_current_section == "bookings":
            if self.dashboard_bookings_summary_frame or self.dashboard_bookings_frame:
                self._render_dashboard_bookings(reservations)

    def _build_variables(self) -> None:
        default_departure = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
        if datetime.now().hour >= 15:
            default_departure = default_departure + timedelta(days=1)
        self.departure_slot_options = tuple(f"{hour:02d}:00" for hour in range(6, 13))
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
        self.cottage_var = ctk.StringVar(value="")
        
        # Multi-Destination state
        self.destination_vars: dict[str, ctk.BooleanVar] = {}
        for dest in self.reservation_controller.destinations():
            var = ctk.BooleanVar(value=False)
            var.trace_add("write", lambda *args: self._update_live_reservation_summary())
            self.destination_vars[dest] = var
            
        # Default first one to True
        if self.destination_vars:
            first_dest = self.reservation_controller.destinations()[0]
            self.destination_vars[first_dest].set(True)
            
        # Ensure we have the asset data for pricing
        self._refresh_destination_catalog()
            
        self.notes_var = ctk.StringVar()
        self.action_code_var = ctk.StringVar()
        self.asset_table_date_var = ctk.StringVar(value=date_type.today().isoformat())
        self.asset_availability_filter_var = ctk.StringVar(value="All")
        self.asset_cottage_filter_var = ctk.StringVar(value="All Cottages")
        self.asset_destination_filter_var = ctk.StringVar(value="All Destinations")
        self.asset_filter_summary_var = ctk.StringVar(
            value="Sort by the headers or filter by date, availability, cottage, and destination."
        )
        self.reservation_filter_date_var = ctk.StringVar(value="")
        self.reservation_status_filter_var = ctk.StringVar(value="All")
        self.reservation_cottage_filter_var = ctk.StringVar()
        self.reservation_search_var = ctk.StringVar()
        self.reservation_summary_var = ctk.StringVar(
            value="Upcoming reservations will be prioritized once bookings load."
        )
        self.payment_filter_date_var = ctk.StringVar(value="")
        self.payment_status_filter_var = ctk.StringVar(value="All")
        self.payment_search_var = ctk.StringVar()
        self.payment_summary_var = ctk.StringVar(
            value="Payment records will be organized here once reservations load."
        )
        self.selected_cottage_name_var = ctk.StringVar(value="Choose a cottage to preview")
        self.selected_cottage_meta_var = ctk.StringVar(
            value="The selected cottage image, status, and base rate will appear here."
        )
        self.availability_var = ctk.StringVar(
            value="Choose a travel date, departure slot, and party size, then click Check Availability."
        )
        self.status_var = ctk.StringVar(value="Ready.")
        self.mode_var = ctk.StringVar(
            value="LIVE MYSQL" if self.data_mode == "mysql" else "DEMO MODE"
        )
        self.date_var = ctk.StringVar(value=datetime.now().strftime("%A, %d %B %Y"))
        self.asset_summary_var = ctk.StringVar(value="Loading asset summary...")
        
        # Live Summary Variables
        self.live_price_text_var = ctk.StringVar(value="PHP 0.00")
        self.live_capacity_text_var = ctk.StringVar(value="Capacity: --")
        self.live_time_text_var = ctk.StringVar(value="Ends at: --")
        
        # Tracers for live updates
        for var in [self.cottage_var, self.duration_var, self.party_size_var, self.departure_slot_var]:
            var.trace_add("write", lambda *args: self._update_live_reservation_summary())
        self.login_user_var = ctk.StringVar(value="")
        self.login_password_var = ctk.StringVar()
        self.login_feedback_var = ctk.StringVar(value="Sign in to open the reservation dashboard.")
        self.login_hint_var = ctk.StringVar(
            value=(
                "Default login: admin / k3admin123"
                if self.login_settings.uses_default_credentials()
                else "Using the custom K3 app account configured in .env."
            )
        )
        self._refresh_cottage_catalog()
        self.cottage_var.trace_add("write", self._update_selected_cottage_preview)
        self.departure_date_var.trace_add("write", self._handle_reservation_date_change)
        for variable in (self.departure_slot_var, self.duration_var):
            variable.trace_add("write", self._update_return_preview)
        self._update_return_preview()

    def _build_window(self) -> None:
        screen_width = self.screen_profile.screen_width
        screen_height = self.screen_profile.screen_height
        initial_width = min(1540, max(960, screen_width - 80))
        initial_height = min(980, max(700, screen_height - 80))
        min_width = min(1320, initial_width)
        min_height = min(900, initial_height)
        self.title("K3's Floating Cottage RMS")
        self.geometry(f"{initial_width}x{initial_height}")
        self.minsize(min_width, min_height)
        self.configure(fg_color=self.palette["bg"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.after(0, self._maximize_window)

    def _maximize_window(self) -> None:
        try:
            self.state("zoomed")
        except Exception:
            try:
                self.attributes("-fullscreen", True)
            except Exception:
                pass

    def _build_shell(self) -> None:
        self._build_header()
        self._admin_page()

        # Minimalist footer with soft styling
        footer = ctk.CTkFrame(
            self,
            fg_color=self.palette["surface"],
            border_width=1,
            border_color=self.palette["line"],
        )
        footer.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        footer.grid_columnconfigure(0, weight=1)
        self.status_label = ctk.CTkLabel(
            footer,
            textvariable=self.status_var,
            text_color=self.palette["text_secondary"],
            font=("Segoe UI", 12),
            anchor="w",
            padx=28,
            pady=14,
        )
        self.status_label.grid(row=0, column=0, sticky="ew")

    def _build_header(self) -> None:
        """Modern Admin Profile Panel header with logo, notifications, and profile dropdown."""
        header = ctk.CTkFrame(
            self, 
            fg_color=self.palette["surface"], 
            border_width=1, 
            border_color=self.palette["line"],
            height=48
        )
        header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header.grid_propagate(False)  # Lock frame height - don't expand based on children
        header.pack_propagate(False)
        header.grid_columnconfigure(0, weight=0)  # Logo - left, fixed
        header.grid_columnconfigure(1, weight=0)  # Back button
        header.grid_columnconfigure(2, weight=1)  # Spacer - center
        header.grid_columnconfigure(3, weight=0)  # Icons - right, fixed

        # ===== LEFT: Logo & Brand (Clickable to go home) =====
        logo_frame = ctk.CTkFrame(header, fg_color="transparent", cursor="hand2")
        logo_frame.grid(row=0, column=0, sticky="w", padx=(20, 14), pady=8)
        logo_frame.bind("<Button-1>", lambda e: self.show_page("home"))
        
        # Load logo image with fallback to text label
        self.logo_image = None
        try:
            # Load k3_logo.jpg
            project_root = Path(__file__).parent.parent.parent
            logo_path = project_root / "images" / "k3_logo.jpg"
            if not logo_path.exists():
                logo_path = project_root / "k3_logo.jpg"
            if logo_path.exists():
                pil_image = Image.open(logo_path).convert("RGBA")
                pil_image = pil_image.resize((32, 32), Image.Resampling.LANCZOS)
                self.logo_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(32, 32))
                self.brand_logo_label = ctk.CTkLabel(
                    logo_frame,
                    image=self.logo_image,
                    text="",
                    cursor="hand2",
                )
            else:
                raise FileNotFoundError(f"Logo not found at {logo_path}")
        except Exception as e:
            # Fallback to plain text label if image not found
            print(f"Could not load logo image: {e}. Using text fallback.")
            self.brand_logo_label = ctk.CTkLabel(
                logo_frame,
                text="K3",
                text_color=self.palette["text"],
                font=("Segoe UI", 12, "bold"),
                cursor="hand2",
            )
        
        self.brand_logo_label.grid(row=0, column=0, padx=(0, 8), pady=0)
        self.brand_logo_label.bind("<Button-1>", lambda e: self.show_page("home"))
        
        self.current_page_label = ctk.CTkLabel(
            logo_frame,
            text="K3's Floating Cottage",
            text_color=self.palette["text"],
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
        )
        self.current_page_label.grid(row=0, column=1, sticky="w")
        self.current_page_label.bind("<Button-1>", lambda e: self.show_page("home"))
        
        # Add hover effects to logo
        def on_logo_enter(e):
            self.brand_logo_label.configure(text_color=self.palette["accent"])
            self.current_page_label.configure(text_color=self.palette["accent"])
        
        def on_logo_leave(e):
            self.brand_logo_label.configure(text_color=self.palette["text"])
            self.current_page_label.configure(text_color=self.palette["text"])
        
        self.brand_logo_label.bind("<Enter>", on_logo_enter)
        self.brand_logo_label.bind("<Leave>", on_logo_leave)
        self.current_page_label.bind("<Enter>", on_logo_enter)
        self.current_page_label.bind("<Leave>", on_logo_leave)
        logo_frame.bind("<Enter>", on_logo_enter)
        logo_frame.bind("<Leave>", on_logo_leave)

        # ===== CENTER: Spacer =====
        spacer = ctk.CTkFrame(header, fg_color="transparent")
        spacer.grid(row=0, column=2, sticky="ew")

        # ===== RIGHT: Icons Panel (Notifications & Admin Settings) =====
        icons_panel = ctk.CTkFrame(header, fg_color="transparent")
        icons_panel.grid(row=0, column=3, sticky="ne", padx=14, pady=2)
        icons_panel.grid_columnconfigure((0, 2, 4), weight=0)  # Buttons
        icons_panel.grid_columnconfigure((1, 3), weight=0)  # Dividers

        # Notification Bell - Wrapped in hover-highlight frame
        notification_frame = ctk.CTkFrame(
            icons_panel,
            fg_color="transparent",
            corner_radius=6,
            cursor="hand2"
        )
        notification_frame.grid(row=0, column=0, padx=0, pady=0)
        
        notification_btn = ctk.CTkLabel(
            notification_frame,
            text="🔔",
            font=("Segoe UI", 16),
            cursor="hand2",
            text_color=self.palette["text"],
        )
        notification_btn.pack(padx=8, pady=4)
        self.notification_badge = ctk.CTkLabel(
            notification_frame,
            text="0",
            fg_color=self.palette["coral"],
            text_color="#FFFFFF",
            corner_radius=9,
            width=18,
            height=18,
            font=("Segoe UI", 9, "bold"),
        )
        self.notification_badge.place_forget()
        
        def on_notif_enter(e):
            notification_frame.configure(fg_color=self.palette["hover"])
        
        def on_notif_leave(e):
            notification_frame.configure(fg_color="transparent")
        
        notification_frame.bind("<Enter>", on_notif_enter)
        notification_frame.bind("<Leave>", on_notif_leave)
        notification_btn.bind("<Enter>", on_notif_enter)
        notification_btn.bind("<Leave>", on_notif_leave)
        notification_frame.bind("<Button-1>", lambda e: self._toggle_notifications_panel())
        notification_btn.bind("<Button-1>", lambda e: self._toggle_notifications_panel())

        # Divider
        divider = ctk.CTkLabel(
            icons_panel,
            text="|",
            text_color=self.palette["line"],
            font=("Segoe UI", 12),
        )
        divider.grid(row=0, column=1, padx=6, pady=0)

        # Action Button (Logout / Back)
        self.action_frame = ctk.CTkFrame(
            icons_panel,
            fg_color="transparent",
            corner_radius=6,
            cursor="hand2"
        )
        self.action_frame.grid(row=0, column=4, padx=0, pady=0)
        
        self.action_content_frame = ctk.CTkFrame(self.action_frame, fg_color="transparent")
        self.action_content_frame.pack(padx=8, pady=4)
        
        self.action_icon_label = ctk.CTkLabel(
            self.action_content_frame,
            text="🚪",
            font=("Segoe UI", 14),
            cursor="hand2",
            text_color=self.palette["text"],
        )
        self.action_icon_label.pack(side="left", padx=(0, 3))
        
        self.action_text_label = ctk.CTkLabel(
            self.action_content_frame,
            text="Logout",
            font=("Segoe UI", 10),
            cursor="hand2",
            text_color=self.palette["text"],
        )
        self.action_text_label.pack(side="left")
        
        self._action_button_mode = "logout"
        
        def on_action_enter(e):
            if self._action_button_mode == "logout":
                self.action_frame.configure(fg_color="#FDE8E8")
                self.action_icon_label.configure(text_color=self.palette["danger"])
                self.action_text_label.configure(text_color=self.palette["danger"])
            else:
                self.action_frame.configure(fg_color=self.palette["surface_alt"])
        
        def on_action_leave(e):
            self.action_frame.configure(fg_color="transparent")
            self.action_icon_label.configure(text_color=self.palette["text"])
            self.action_text_label.configure(text_color=self.palette["text"])
            
        self.action_frame.bind("<Enter>", on_action_enter)
        self.action_frame.bind("<Leave>", on_action_leave)
        self.action_content_frame.bind("<Enter>", on_action_enter)
        self.action_content_frame.bind("<Leave>", on_action_leave)
        self.action_icon_label.bind("<Enter>", on_action_enter)
        self.action_icon_label.bind("<Leave>", on_action_leave)
        self.action_text_label.bind("<Enter>", on_action_enter)
        self.action_text_label.bind("<Leave>", on_action_leave)
        
        def handle_action_click(e):
            if self._action_button_mode == "logout":
                self._logout()
            else:
                self.show_page("home")
                
        self.action_frame.bind("<Button-1>", handle_action_click)
        self.action_content_frame.bind("<Button-1>", handle_action_click)
        self.action_icon_label.bind("<Button-1>", handle_action_click)
        self.action_text_label.bind("<Button-1>", handle_action_click)

        # Divider 2
        divider2 = ctk.CTkLabel(
            icons_panel,
            text="|",
            text_color=self.palette["line"],
            font=("Segoe UI", 12),
        )
        divider2.grid(row=0, column=3, padx=6, pady=0)

        # Admin Button - Wrapped in hover-highlight frame with person icon + text
        admin_frame = ctk.CTkFrame(
            icons_panel,
            fg_color="transparent",
            corner_radius=6,
            cursor="hand2"
        )
        admin_frame.grid(row=0, column=2, padx=0, pady=0)
        
        admin_content_frame = ctk.CTkFrame(admin_frame, fg_color="transparent")
        admin_content_frame.pack(padx=8, pady=4)
        
        admin_icon_label = ctk.CTkLabel(
            admin_content_frame,
            text="👤",
            font=("Segoe UI", 14),
            cursor="hand2",
            text_color=self.palette["text"],
        )
        admin_icon_label.pack(side="left", padx=(0, 3))
        
        admin_text_label = ctk.CTkLabel(
            admin_content_frame,
            text="admin ▾",
            font=("Segoe UI", 10),
            cursor="hand2",
            text_color=self.palette["text"],
        )
        admin_text_label.pack(side="left")
        
        def on_admin_enter(e):
            admin_frame.configure(fg_color=self.palette["hover"])
        
        def on_admin_leave(e):
            admin_frame.configure(fg_color="transparent")
        
        admin_frame.bind("<Enter>", on_admin_enter)
        admin_frame.bind("<Leave>", on_admin_leave)
        admin_content_frame.bind("<Enter>", on_admin_enter)
        admin_content_frame.bind("<Leave>", on_admin_leave)
        admin_icon_label.bind("<Enter>", on_admin_enter)
        admin_icon_label.bind("<Leave>", on_admin_leave)
        admin_text_label.bind("<Enter>", on_admin_enter)
        admin_text_label.bind("<Leave>", on_admin_leave)
        
        admin_frame.bind("<Button-1>", lambda e: self._show_admin_settings_modal())
        admin_content_frame.bind("<Button-1>", lambda e: self._show_admin_settings_modal())
        admin_icon_label.bind("<Button-1>", lambda e: self._show_admin_settings_modal())
        admin_text_label.bind("<Button-1>", lambda e: self._show_admin_settings_modal())
        
        # Store notifications panel reference
        self.notifications_panel = None
        self.notifications_visible = False
        
        # Store header reference for popups
        self.header = header
        
        # Keep these for compatibility
        self.mode_label = None
        self.header_connect_button = None
        self.back_button = None
        self.header_logout_button = None

    def _toggle_profile_dropdown(self) -> None:
        """Toggle profile dropdown visibility."""
        if self.profile_dropdown_visible:
            self._hide_profile_dropdown()
        else:
            self._show_profile_dropdown()

    def _show_profile_dropdown(self) -> None:
        """Show the admin profile dropdown menu."""
        if self.profile_dropdown_visible:
            return
        
        # Close notifications panel if open
        if self.notifications_visible:
            self._hide_notifications_panel()
        
        self.profile_dropdown_visible = True
        
        # Create a dropdown frame positioned below the profile avatar
        self.profile_dropdown = ctk.CTkFrame(
            self,
            fg_color=self.palette["surface"],
            corner_radius=16,
            border_width=1,
            border_color=self.palette["line"],
            width=280,
        )
        self.profile_dropdown.grid(row=1, column=0, sticky="ne", padx=(0, 30), pady=(0, 10))
        self.profile_dropdown.grid_columnconfigure(0, weight=1)
        
        profile_items = [
            ("👤 Edit Profile", "Edit your admin profile information"),
            ("🎨 Change Logo & Branding", "Customize resort branding"),
            ("🔐 Update Login Credentials", "Change your password and security settings"),
            ("⚙️ System Settings", "Configure application preferences"),
        ]
        
        # Add menu items
        for idx, (title, subtitle) in enumerate(profile_items):
            self._create_profile_menu_item(self.profile_dropdown, title, subtitle, idx)
        
        # Add divider
        divider = ctk.CTkFrame(self.profile_dropdown, fg_color=self.palette["line"], height=1)
        divider.grid(row=len(profile_items), column=0, sticky="ew", padx=0, pady=8)
        
        # Add logout button
        logout_btn = ctk.CTkButton(
            self.profile_dropdown,
            text="🚪 Log Out",
            command=self._handle_logout_from_dropdown,
            fg_color=self.palette["coral"],
            hover_color="#DE9089",
            text_color="#FFFFFF",
            font=("Segoe UI", 12, "bold"),
            corner_radius=12,
            height=40,
        )
        logout_btn.grid(row=len(profile_items) + 1, column=0, sticky="ew", padx=12, pady=8)
        
        # Bind outside click to close dropdown
        self.bind("<Button-1>", self._on_window_click)

    def _hide_profile_dropdown(self) -> None:
        """Hide the profile dropdown."""
        self.profile_dropdown_visible = False
        if self.profile_dropdown:
            self.profile_dropdown.grid_forget()
            self.profile_dropdown = None
        self.unbind("<Button-1>")

    def _create_profile_menu_item(self, parent, title: str, subtitle: str, row: int) -> None:
        """Create a menu item in the profile dropdown."""
        item_frame = ctk.CTkFrame(
            parent,
            fg_color=self.palette["surface"],
            corner_radius=12,
            cursor="hand2",
        )
        item_frame.grid(row=row, column=0, sticky="ew", padx=8, pady=6)
        item_frame.grid_columnconfigure(0, weight=1)
        
        # Bind hover effects
        def on_enter(e):
            item_frame.configure(fg_color=self.palette["surface_alt"])
        
        def on_leave(e):
            item_frame.configure(fg_color=self.palette["surface"])
        
        item_frame.bind("<Enter>", on_enter)
        item_frame.bind("<Leave>", on_leave)
        
        # Title
        title_label = ctk.CTkLabel(
            item_frame,
            text=title,
            text_color=self.palette["text"],
            font=("Segoe UI", 12, "bold"),
            cursor="hand2",
            anchor="w",
            padx=12,
            pady=(8, 2),
        )
        title_label.grid(row=0, column=0, sticky="ew")
        title_label.bind("<Button-1>", lambda e: self._on_profile_menu_click(title))
        title_label.bind("<Enter>", on_enter)
        title_label.bind("<Leave>", on_leave)
        
        # Subtitle
        subtitle_label = ctk.CTkLabel(
            item_frame,
            text=subtitle,
            text_color=self.palette["muted"],
            font=("Segoe UI", 10),
            cursor="hand2",
            anchor="w",
            padx=12,
            pady=(0, 8),
            wraplength=250,
            justify="left",
        )
        subtitle_label.grid(row=1, column=0, sticky="ew")
        subtitle_label.bind("<Button-1>", lambda e: self._on_profile_menu_click(title))
        subtitle_label.bind("<Enter>", on_enter)
        subtitle_label.bind("<Leave>", on_leave)

    def _on_profile_menu_click(self, menu_item: str) -> None:
        """Handle profile menu item clicks."""
        self._hide_profile_dropdown()
        
        if "Edit Profile" in menu_item:
            self._set_status("Edit Profile feature coming soon.")
            messagebox.showinfo("Edit Profile", "Profile editing interface will be implemented soon.")
        elif "Logo & Branding" in menu_item:
            self._set_status("Change Logo & Branding feature coming soon.")
            messagebox.showinfo("Branding", "Logo and branding customization interface will be implemented soon.")
        elif "Login Credentials" in menu_item:
            self._set_status("Update Login Credentials feature coming soon.")
            messagebox.showinfo("Security", "Password change interface will be implemented soon.")
        elif "System Settings" in menu_item:
            self._set_status("System Settings feature coming soon.")
            messagebox.showinfo("Settings", "System configuration interface will be implemented soon.")

    def _handle_logout_from_dropdown(self) -> None:
        """Handle logout from profile dropdown."""
        self._hide_profile_dropdown()
        self._logout()

    def _toggle_notifications_panel(self) -> None:
        """Toggle notifications panel visibility."""
        if self.notifications_visible:
            self._hide_notifications_panel()
        else:
            self._show_notifications_panel()

    def _show_notifications_panel(self) -> None:
        """Show the notifications side panel."""
        if self.notifications_visible:
            return
        
        # Close profile dropdown if open
        if self.profile_dropdown_visible:
            self._hide_profile_dropdown()
        
        self.notifications_visible = True
        
        # Create notifications panel as a side frame
        self.notifications_panel = ctk.CTkFrame(
            self,
            fg_color=self.palette["surface"],
            corner_radius=16,
            border_width=1,
            border_color=self.palette["line"],
            width=360,
        )
        self.notifications_panel.grid(row=1, column=0, sticky="ne", padx=(0, 12), pady=(0, 20))
        self.notifications_panel.grid_propagate(False)
        self.notifications_panel.grid_columnconfigure(0, weight=1)
        
        # Header
        header_frame = ctk.CTkFrame(self.notifications_panel, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 12))
        header_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            header_frame,
            text="🔔 Notifications",
            text_color=self.palette["text"],
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")
        
        close_btn = ctk.CTkButton(
            header_frame,
            text="✕",
            command=self._hide_notifications_panel,
            fg_color=self.palette["surface_alt"],
            hover_color=self.palette["line"],
            text_color=self.palette["text"],
            font=("Segoe UI", 14),
            width=32,
            height=32,
            corner_radius=8,
        )
        close_btn.grid(row=0, column=1, sticky="e")
        
        # Divider
        divider = ctk.CTkFrame(self.notifications_panel, fg_color=self.palette["line"], height=1)
        divider.grid(row=1, column=0, sticky="ew", padx=0, pady=4)
        
        # Notifications content
        scroll_frame = ctk.CTkScrollableFrame(
            self.notifications_panel,
            fg_color="transparent",
            scrollbar_button_color=self.palette["sand"],
            scrollbar_button_hover_color=self.palette["accent"],
        )
        scroll_frame.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
        scroll_frame.grid_columnconfigure(0, weight=1)
        self.notifications_panel.grid_rowconfigure(2, weight=1)
        
        # Sample notifications
        notifications_data = [
            {
                "icon": "📅",
                "category": "Upcoming Reservation",
                "title": "Booking in 2 hours",
                "description": "Guest arriving for 6-hour cottage session",
                "time": "10:30 AM",
            },
            {
                "icon": "💳",
                "category": "Payment",
                "title": "Payment expiring soon",
                "description": "Invoice #K3-2024-156 due in 3 days",
                "time": "9:15 AM",
            },
            {
                "icon": "🛠️",
                "category": "Maintenance",
                "title": "Scheduled maintenance",
                "description": "Cottage 2 - Engine service completed",
                "time": "Yesterday",
            },
            {
                "icon": "⚠️",
                "category": "Alert",
                "title": "Destination status",
                "description": "Destination 1 - Fuel level low",
                "time": "2 days ago",
            },
        ]
        
        for idx, notif in enumerate(notifications_data):
            self._create_notification_item(scroll_frame, notif, idx)

    def _hide_notifications_panel(self) -> None:
        """Hide the notifications panel."""
        self.notifications_visible = False
        if self.notifications_panel:
            self.notifications_panel.grid_forget()
            self.notifications_panel = None

    def _create_notification_item(self, parent, notification: dict, row: int) -> None:
        """Create a notification item in the notifications panel."""
        item_frame = ctk.CTkFrame(
            parent,
            fg_color=self.palette["page"],
            corner_radius=12,
        )
        item_frame.grid(row=row, column=0, sticky="ew", padx=12, pady=8)
        item_frame.grid_columnconfigure(0, weight=0)
        item_frame.grid_columnconfigure(1, weight=1)
        
        # Icon
        icon_label = ctk.CTkLabel(
            item_frame,
            text=notification["icon"],
            text_color=self.palette["text"],
            font=("Segoe UI", 20),
            width=44,
        )
        icon_label.grid(row=0, column=0, rowspan=3, padx=12, pady=10)
        
        # Category badge
        category_label = ctk.CTkLabel(
            item_frame,
            text=notification["category"],
            text_color=self.palette["accent_dark"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        category_label.grid(row=0, column=1, sticky="w", pady=(10, 2), padx=(0, 12))
        
        # Title
        title_label = ctk.CTkLabel(
            item_frame,
            text=notification["title"],
            text_color=self.palette["text"],
            font=("Segoe UI", 12, "bold"),
            anchor="w",
        )
        title_label.grid(row=1, column=1, sticky="w", padx=(0, 12))
        
        # Description
        desc_label = ctk.CTkLabel(
            item_frame,
            text=notification["description"],
            text_color=self.palette["muted"],
            font=("Segoe UI", 11),
            anchor="w",
            wraplength=260,
            justify="left",
        )
        desc_label.grid(row=2, column=1, sticky="w", padx=(0, 12), pady=(2, 8))
        
        # Time
        time_label = ctk.CTkLabel(
            item_frame,
            text=notification["time"],
            text_color=self.palette["muted"],
            font=("Segoe UI", 9),
            anchor="e",
        )
        time_label.grid(row=0, column=2, sticky="ne", padx=12, pady=10)

    def _on_window_click(self, event) -> None:
        """Close dropdowns when clicking outside them."""
        # Check if click is outside the dropdown
        if self.profile_dropdown and self.profile_dropdown.winfo_exists():
            if not self._is_click_on_widget(event, self.profile_dropdown):
                self._hide_profile_dropdown()

    def _is_click_on_widget(self, event, widget) -> bool:
        """Check if a click event is on a specific widget."""
        try:
            x = widget.winfo_rootx()
            y = widget.winfo_rooty()
            w = widget.winfo_width()
            h = widget.winfo_height()
            
            return x <= event.x_root <= x + w and y <= event.y_root <= y + h
        except Exception:
            return False

    def _animate_notification_badge(self) -> None:
        """Animate the notification badge with a subtle pulse effect."""
        if not hasattr(self, 'notification_badge'):
            return
        
        def pulse(step=0):
            colors = [
                self.palette["coral"],
                "#F5A89C",
                self.palette["coral"],
            ]
            if step < len(colors):
                try:
                    self.notification_badge.configure(fg_color=colors[step])
                    self.after(150, lambda: pulse(step + 1))
                except Exception:
                    pass
        
        pulse()

    def _animate_dropdown_appear(self) -> None:
        """Smooth appearance animation for dropdown."""
        if self.profile_dropdown and self.profile_dropdown.winfo_exists():
            try:
                # Fade-in effect by gradually adjusting opacity
                self.profile_dropdown.grid(row=1, column=0, sticky="ne", padx=(0, 30), pady=(0, 10))
            except Exception:
                pass

    def _add_hover_shine_effect(self, widget, enter_color, leave_color) -> None:
        """Add a hover shine effect to a widget."""
        def on_enter(e):
            widget.configure(text_color=enter_color)
        
        def on_leave(e):
            widget.configure(text_color=leave_color)
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def _on_window_resize(self, event) -> None:
        """Update background image size on window resize."""
        try:
            if hasattr(self, 'login_bg_label') and hasattr(self, 'login_bg_image'):
                # The background already uses relwidth=1 and relheight=1
                # so it should automatically scale with window size
                pass
        except Exception:
            pass

    def _admin_page(self) -> None:
        """Modern minimalist layout with full-width content area."""
        self.page_container = ctk.CTkFrame(self, fg_color=self.palette["bg"])
        self.page_container.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.page_container.grid_rowconfigure(0, weight=1)
        self.page_container.grid_columnconfigure(0, weight=1)

        # Main content area - full width
        self.bg_frame = ctk.CTkFrame(
            self.page_container,
            fg_color=self.palette["bg"],
        )
        self.bg_frame.grid(row=0, column=0, sticky="nsew")
        self.bg_frame.grid_rowconfigure(0, weight=1)
        self.bg_frame.grid_columnconfigure(0, weight=1)

        # Build all pages inside bg_frame
        self._build_home_page()
        self._build_reservations_page()
        self._build_operations_page()
        self._build_payments_page()
        self._build_dashboard_page()

    def show_dashboard(self) -> None:
        """Display the main dashboard/home view with action cards lobby."""
        self.show_page("home")

    def _create_page(self, name: str) -> ctk.CTkFrame:
        """Create a new page frame inside bg_frame."""
        page = ctk.CTkFrame(self.bg_frame, fg_color="transparent")
        page.grid(row=0, column=0, sticky="nsew")
        self.page_frames[name] = page
        return page

    def _build_home_page(self) -> None:
        """Build minimalist home page with 3 card-based module layout."""
        page = self._create_page("home")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(0, weight=1)  # Top spacer
        page.grid_rowconfigure(1, weight=0)  # Title section
        page.grid_rowconfigure(2, weight=1)  # Central spacer
        page.grid_rowconfigure(3, weight=0)  # Cards container
        page.grid_rowconfigure(4, weight=1)  # Bottom spacer

        # Top padding spacer
        ctk.CTkFrame(page, fg_color="transparent").grid(row=0, column=0, sticky="nsew")

        # Title section - elegant and minimalist
        title_frame = ctk.CTkFrame(page, fg_color="transparent")
        title_frame.grid(row=1, column=0, sticky="ew", padx=60, pady=(40, 15))
        title_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            title_frame,
            text="Floating Cottage Reservation and Management System",
            text_color=self.palette["text"],
            font=("Segoe UI", 30, "bold"),
            wraplength=920,
            justify="center",
        ).grid(row=0, column=0, sticky="ew")
        
        # Dynamic subtitle with active reservations
        self.home_active_reservations_label = ctk.CTkLabel(
            title_frame,
            text="Loading active reservations | Manage your floating cottage with ease",
            text_color=self.palette["text_secondary"],
            font=("Segoe UI", 13),
        )
        self.home_active_reservations_label.grid(row=1, column=0, pady=(8, 0))

        # Central spacer - pushes cards to center
        ctk.CTkFrame(page, fg_color="transparent").grid(row=2, column=0, sticky="nsew")

        # Navigation Cards Grid - 4 minimalist cards in center
        cards_frame = ctk.CTkFrame(page, fg_color="transparent")
        cards_frame.grid(row=3, column=0, sticky="ew", padx=60, pady=(20, 40))
        cards_frame.grid_columnconfigure(0, weight=1)  # Left spacer
        cards_frame.grid_columnconfigure(1, weight=0)  # Card 1
        cards_frame.grid_columnconfigure(2, weight=0)  # Card 2
        cards_frame.grid_columnconfigure(3, weight=0)  # Card 3
        cards_frame.grid_columnconfigure(4, weight=0)  # Card 4
        cards_frame.grid_columnconfigure(5, weight=1)  # Right spacer
        
        # Module cards with minimalist design
        modules = [
            {
                "page": "reservations",
                "icon": "📅",
                "title": "Reservations",
                "subtitle": "Book and manage guest reservations",
                "button_color": self.palette["accent"],
                "button_hover": self.palette["accent_dark"],
            },
            {
                "page": "operations",
                "icon": "⚙️",
                "title": "Operations",
                "subtitle": "Monitor assets and daily operations",
                "button_color": self.palette["sand"],
                "button_hover": "#C0AA98",
            },
            {
                "page": "dashboard",
                "icon": "📊",
                "title": "Dashboard",
                "subtitle": "View analytics and insights",
                "button_color": self.palette["sage"],
                "button_hover": "#A3B896",
            },
            {
                "page": "payments",
                "icon": "$",
                "title": "Payments",
                "subtitle": "Track unpaid, partial, paid, and refunded reservations",
                "button_color": self.palette["brand"],
                "button_hover": self.palette["brand_dark"],
            },
        ]
        
        for col, module in enumerate(modules, start=1):
            self._create_minimalist_nav_card(cards_frame, module, col)

        # Bottom spacer
        ctk.CTkFrame(page, fg_color="transparent").grid(row=4, column=0, sticky="nsew")

    def _create_minimalist_nav_card(self, parent, module, column):
        """Create a minimalist navigation card with centered icon, title, subtitle, and pill button."""
        # Main card frame - white with soft rounded corners
        card = ctk.CTkFrame(
            parent,
            fg_color=self.palette["surface"],
            corner_radius=20,
            border_width=1,
            border_color=self.palette["line"],
            width=250,
            height=280,
        )
        card.grid_propagate(False)  # Enforce consistent card sizes
        card.grid(row=0, column=column, sticky="n", padx=16, pady=0)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(3, weight=1)  # Push the button to the bottom
        
        # Centered large minimalist icon
        icon_label = ctk.CTkLabel(
            card,
            text=module["icon"],
            text_color=self.palette["text"],
            font=("Segoe UI", 56),
        )
        icon_label.grid(row=1, column=0, pady=(24, 12))
        
        # Bold title
        title_label = ctk.CTkLabel(
            card,
            text=module["title"],
            text_color=self.palette["text"],
            font=("Segoe UI", 18, "bold"),
        )
        title_label.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 6))
        
        # Descriptive subtitle
        subtitle_label = ctk.CTkLabel(
            card,
            text=module["subtitle"],
            text_color=self.palette["text_secondary"],
            font=("Segoe UI", 12),
            wraplength=210,
            justify="center",
        )
        subtitle_label.grid(row=3, column=0, sticky="n", padx=20, pady=(0, 10))
        
        # Full-width pill-shaped button at bottom
        button = ctk.CTkButton(
            card,
            text=f"Open {module['title']}",
            command=lambda: self.show_page(module["page"]),
            fg_color=module["button_color"],
            hover_color=module["button_hover"],
            text_color="#FFFFFF",
            font=("Segoe UI", 12, "bold"),
            corner_radius=18,  # Pill shape
            height=42,
            border_width=0,
        )
        button.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 24))

    def _create_action_card(self, parent, emoji, title, description, button_text, command, bg_color, row, column):
        """Create an action card with title, emoji, description, and button. Entire card is clickable."""
        card = ctk.CTkFrame(
            parent,
            fg_color=bg_color,
            corner_radius=15,
            border_width=1,
            border_color=self.palette["line"],
            cursor="hand2",
        )
        card.grid(row=row, column=column, sticky="nsew", padx=8, pady=8)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure((0, 1, 2, 3), weight=0)
        
        # Bind card click to command
        card.bind("<Button-1>", lambda e: command())

        # Emoji/Icon
        emoji_label = ctk.CTkLabel(
            card,
            text=emoji,
            text_color=self.palette["text"],
            font=("Segoe UI", 28),
            cursor="hand2",
        )
        emoji_label.grid(row=0, column=0, sticky="w", padx=20, pady=(16, 8))
        emoji_label.bind("<Button-1>", lambda e: command())

        # Title
        title_label = ctk.CTkLabel(
            card,
            text=title,
            text_color=self.palette["text"],
            font=("Segoe UI", 18, "bold"),
            cursor="hand2",
        )
        title_label.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 8))
        title_label.bind("<Button-1>", lambda e: command())

        # Description
        desc_label = ctk.CTkLabel(
            card,
            text=description,
            text_color=self.palette["muted"],
            font=("Segoe UI", 12),
            wraplength=280,
            justify="left",
            cursor="hand2",
        )
        desc_label.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 14))
        desc_label.bind("<Button-1>", lambda e: command())

        # Button
        button = ctk.CTkButton(
            card,
            text=button_text,
            command=command,
            fg_color=self.palette["accent"],
            hover_color=self.palette["accent_dark"],
            text_color=self.palette["text"],
            font=("Segoe UI", 12, "bold"),
            corner_radius=12,
            height=38,
        )
        button.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 16))

    def _create_image_nav_card(self, parent, page_name, image_path, label, column):
        """Create a clickable navigation card with large image - elegant card style."""
        # Main card frame with subtle styling
        card = ctk.CTkFrame(
            parent,
            fg_color=self.palette["surface"],
            corner_radius=16,
            border_width=1,
            border_color=self.palette["line"]
        )
        card.grid(row=0, column=column, sticky="", padx=12, pady=0)
        card.grid_columnconfigure(0, weight=0)
        card.grid_rowconfigure((0, 1), weight=0)
        
        # Load and display image - LARGE (300x200)
        try:
            if image_path.exists():
                image = Image.open(image_path).convert("RGBA")
                nav_image = ctk.CTkImage(light_image=image, size=(240, 160))
                img_label = ctk.CTkLabel(
                    card,
                    image=nav_image,
                    text="",
                    cursor="hand2",
                    fg_color="transparent",
                )
                img_label.image = nav_image  # Keep reference
                img_label.grid(row=0, column=0, sticky="", padx=12, pady=(12, 10))
                img_label.bind("<Button-1>", lambda e: self.show_page(page_name))
        except Exception:
            pass
        
        # Label below image - elegant typography
        label_widget = ctk.CTkLabel(
            card,
            text=label,
            text_color=self.palette["text"],
            font=("Segoe UI", 16, "bold"),
            cursor="hand2",
        )
        label_widget.grid(row=1, column=0, sticky="", padx=12, pady=(0, 12))
        label_widget.bind("<Button-1>", lambda e: self.show_page(page_name))

    def _build_reservations_page(self) -> None:
        page = self._create_page("reservations")
        page.grid_rowconfigure(0, weight=1)
        page.grid_columnconfigure(0, weight=1)
        
        # Scrollable container for all content with slim, modern scrollbar
        scroll_frame = ctk.CTkScrollableFrame(
            page,
            fg_color="transparent",
            scrollbar_button_color=self.palette["sand"],
            scrollbar_button_hover_color=self.palette["accent"],
        )
        scroll_frame.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        scroll_frame.grid_columnconfigure(0, weight=6)
        scroll_frame.grid_columnconfigure(1, weight=4)

        form = self._section_frame(scroll_frame, "Reservation Studio")
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
        self._field(form, "Contact Number", self.contact_var, 2, 1, numeric_only=True)
        self._field(form, "Email Address", self.email_var, 4, 0)
        self._multi_destination_selector(form, "Destinations (Select all that apply)", 4, 1)
        self._dropdown(
            form,
            "Cottage",
            self.cottage_var,
            self.cottage_option_values,
            6,
            0,
        )
        self._date_picker_field(form, "Travel Date", self.departure_date_var, 6, 1)
        self._dropdown(form, "Departure Slot", self.departure_slot_var, self.departure_slot_options, 8, 0)
        self._dropdown(form, "Duration in Hours", self.duration_var, self.duration_options, 8, 1)
        self._dropdown(form, "Party Size", self.party_size_var, self.party_size_options, 10, 0)
        self._field(form, "Notes / Special Request", self.notes_var, 10, 1)

        self.summary_box = ctk.CTkFrame(
            form,
            fg_color=self.palette["surface_alt"],
            corner_radius=18,
        )
        self.summary_box.grid(row=12, column=0, columnspan=2, sticky="ew", padx=24, pady=(2, 16))
        for i in range(3):
            self.summary_box.grid_columnconfigure(i, weight=1)

        # 1. Price
        ctk.CTkLabel(
            self.summary_box,
            textvariable=self.live_price_text_var,
            text_color=self.palette["brand"],
            font=("Segoe UI", 14, "bold"),
        ).grid(row=0, column=0, padx=15, pady=15, sticky="w")

        # 2. Capacity
        self.capacity_label = ctk.CTkLabel(
            self.summary_box,
            textvariable=self.live_capacity_text_var,
            text_color=self.palette["text"],
            font=("Segoe UI", 13, "bold"),
        )
        self.capacity_label.grid(row=0, column=1, padx=15, pady=15, sticky="n")

        # 3. Time
        ctk.CTkLabel(
            self.summary_box,
            textvariable=self.live_time_text_var,
            text_color=self.palette["muted"],
            font=("Segoe UI", 13, "bold"),
        ).grid(row=0, column=2, padx=15, pady=15, sticky="e")

        actions = ctk.CTkFrame(form, fg_color="transparent")
        actions.grid(row=13, column=0, columnspan=2, sticky="ew", padx=24, pady=(4, 24))
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)
        actions.grid_columnconfigure(2, weight=1)
        self._action_button(actions, "Clear Form", self._clear_reservation_form, self.palette["surface"], self.palette["text"]).grid(row=0, column=0, padx=(0, 4), sticky="ew")
        self._action_button(actions, "Check Availability", self.preview_availability, self.palette["brand"], self.palette["surface"]).grid(row=0, column=1, padx=4, sticky="ew")
        self._action_button(actions, "Confirm Reservation", self.create_reservation, self.palette["accent"], self.palette["text"]).grid(row=0, column=2, padx=(4, 0), sticky="ew")

        side = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        side.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        side.grid_rowconfigure(1, weight=1)
        side.grid_rowconfigure(2, weight=1)
        side.grid_columnconfigure(0, weight=1)

        selected_cottage = self._section_frame(side, "Selected Cottage")
        selected_cottage.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        self.selected_cottage_image_label = ctk.CTkLabel(
            selected_cottage,
            text="Preview unavailable",
            text_color=self.palette["muted"],
            fg_color=self.palette["surface_alt"],
            corner_radius=18,
            height=180,
        )
        self.selected_cottage_image_label.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 16))
        ctk.CTkLabel(
            selected_cottage,
            textvariable=self.selected_cottage_name_var,
            text_color=self.palette["text"],
            font=("Segoe UI", 15, "bold"),
            justify="left",
            wraplength=420,
        ).grid(row=2, column=0, sticky="w", padx=24, pady=(0, 6))
        ctk.CTkLabel(
            selected_cottage,
            textvariable=self.selected_cottage_meta_var,
            text_color=self.palette["muted"],
            font=("Segoe UI", 12),
            justify="left",
            wraplength=420,
        ).grid(row=3, column=0, sticky="w", padx=24, pady=(0, 10))
        self.selected_cottage_status_label = ctk.CTkLabel(
            selected_cottage,
            text="Not Selected",
            fg_color=self.palette["surface_alt"],
            text_color=self.palette["muted"],
            corner_radius=12,
            padx=12,
            pady=4,
            font=("Segoe UI", 11, "bold"),
        )
        self.selected_cottage_status_label.grid(row=4, column=0, sticky="w", padx=24, pady=(0, 24))

        availability = self._section_frame(side, "Live Availability")
        availability.grid(row=1, column=0, sticky="nsew", pady=(10, 10))
        ctk.CTkLabel(
            availability,
            text="Instant feedback from the current cottage and destination schedule.",
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
        tips.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
        for row_idx, text in enumerate(
            (
                "Pick the exact cottage first so the booking matches the guest's preferred unit.",
                "Green means available, amber means reserved, and blue means on going.",
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
            ).grid(row=row_idx, column=0, sticky="w", padx=24, pady=(0, 14))
        self._update_selected_cottage_preview()


    def _open_dashboard_navigation(self, target: str) -> None:
        self._set_dashboard_navigation_state(target)
        self.show_page(target)

    def _set_dashboard_navigation_state(self, active_target: str) -> None:
        for target, button in self.nav_buttons.items():
            if target == active_target:
                button.configure(fg_color=self.palette["hover"], text_color=self.palette["brand"])
            else:
                button.configure(fg_color="transparent", text_color=self.palette["text_secondary"])

    def _build_login_overlay(self) -> None:
        """Island-Inspired Split-Layout Login Overlay with Enhanced Aesthetics."""
        # Refined system palette for the login screen
        BG_RIGHT = self.palette["bg"]               # #F5F3F0 Soft light beige
        CARD_COLOR = self.palette["surface"]        # #FFFFFF Pure white
        TEXT_PRIMARY = self.palette["text"]         # #0D5E60 Deep teal
        TEXT_SECONDARY = self.palette["text_secondary"] # #6B7B79 Muted teal/gray
        TEXT_MUTED = self.palette["muted"]          # #9BA9A7 Lighter muted text
        ACCENT_COLOR = self.palette["accent"]       # #7FD4D0 Aqua
        ACCENT_DARK = self.palette["brand"]         # #0D5E60 Deep teal brand
        ACCENT_HOVER = self.palette["accent_dark"]  # #4FA8A5 Darker aqua
        BORDER_COLOR = self.palette["line"]         # #E8E4E0 Soft beige line
        SHADOW_COLOR = "#E2D5C8"                    # Soft sand shadow
        
        self.login_overlay = ctk.CTkFrame(self, fg_color=BG_RIGHT, corner_radius=0)
        self.login_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Split Layout: Left Side (Image Background)
        left_frame = ctk.CTkFrame(self.login_overlay, corner_radius=0, fg_color=ACCENT_DARK)
        left_frame.place(relx=0, rely=0, relwidth=0.55, relheight=1)

        # Split Layout: Right Side
        right_frame = ctk.CTkFrame(self.login_overlay, fg_color="transparent")
        right_frame.place(relx=0.55, rely=0, relwidth=0.45, relheight=1)

        # Load the login artwork for the left side.
        project_root = Path(__file__).resolve().parents[2]
        bg_path = project_root / "images" / "login_interface_art.png"
        if not bg_path.exists():
            bg_path = project_root / "images" / "islabook.png"

        self.login_bg_label = ctk.CTkLabel(left_frame, text="")
        self.login_bg_label.place(relx=0.5, rely=0.5, anchor="center")

        if bg_path.exists():
            try:
                self._login_bg_pil = Image.open(bg_path).convert("RGBA")
                
                # Zoom out by scaling down the image size
                scale_factor = 0.75  # Adjust this value to zoom more or less
                new_width = int(self._login_bg_pil.width * scale_factor)
                new_height = int(self._login_bg_pil.height * scale_factor)
                
                self.login_bg_image = ctk.CTkImage(light_image=self._login_bg_pil, size=(new_width, new_height))
                self.login_bg_label.configure(image=self.login_bg_image)
            except Exception as e:
                print(f"Failed to load background image: {e}")

        # Center Container in Right Frame
        center_container = ctk.CTkFrame(right_frame, fg_color="transparent")
        center_container.place(relx=0.5, rely=0.5, anchor="center")

        # Main Minimalist Card
        card = ctk.CTkFrame(
            center_container,
            fg_color=CARD_COLOR,
            corner_radius=24,
            border_width=1,
            border_color=BORDER_COLOR,
            width=400,
            height=580,
            bg_color="transparent",
        )
        card.pack(pady=10, padx=10)
        card.pack_propagate(False)

        # Register Link (Packed at bottom of card)
        register_frame = ctk.CTkFrame(card, fg_color="transparent")
        register_frame.pack(side="bottom", pady=(0, 24))
        
        ctk.CTkLabel(
            register_frame,
            text="Don't have an account?",
            text_color=TEXT_SECONDARY,
            font=("Century Gothic", 13),
        ).pack(side="left", padx=(0, 8))
        
        register_btn = ctk.CTkButton(
            register_frame,
            text="Sign Up",
            command=self._open_guest_signup_portal,
            fg_color="transparent",
            hover_color=CARD_COLOR,
            text_color=ACCENT_DARK,
            font=("Century Gothic", 13, "bold"),
            height=24,
            width=80,
            cursor="hand2"
        )
        register_btn.pack(side="left")

        # Top Logo in Card - properly sized and visually centered
        logo_frame = ctk.CTkFrame(card, fg_color="transparent")
        logo_frame.pack(pady=(28, 12))

        project_root = Path(__file__).resolve().parents[2]
        logo_path = project_root / "images" / "logo.png"
        if not logo_path.exists():
            logo_path = project_root / "images" / "k3_logo.jpg"
        if not logo_path.exists():
            logo_path = project_root / "k3_logo.jpg"

        if logo_path.exists():
            try:
                logo_pil = Image.open(logo_path).convert("RGBA")
                logo_pil = logo_pil.resize((80, 80), Image.Resampling.LANCZOS)
                self.login_logo_image = ctk.CTkImage(light_image=logo_pil, size=(80, 80))
                logo_label = ctk.CTkLabel(logo_frame, image=self.login_logo_image, text="")
                logo_label.pack()
            except Exception:
                ctk.CTkLabel(logo_frame, text="🌴", font=("Segoe UI", 64)).pack()
        else:
            ctk.CTkLabel(logo_frame, text="🌴", font=("Segoe UI", 64)).pack()

        logo_frame.pack_forget()

        # Title Section
        title_frame = ctk.CTkFrame(card, fg_color="transparent")
        title_frame.pack(pady=(54, 18))
        
        ctk.CTkLabel(
            title_frame,
            text="Sign In",
            text_color=TEXT_PRIMARY,
            font=("Century Gothic", 34, "bold"),
        ).pack(pady=(0, 0))

        # Form Area
        form_frame = ctk.CTkFrame(card, fg_color="transparent")
        form_frame.pack(fill="x", padx=52)

        # Polished Username Input
        ctk.CTkLabel(
            form_frame,
            text="Username",
            text_color=TEXT_PRIMARY,
            font=("Century Gothic", 13, "bold"),
        ).pack(anchor="w", padx=4, pady=(0, 6))

        username_entry = ctk.CTkEntry(
            form_frame,
            textvariable=self.login_user_var,
            height=50,
            corner_radius=14,
            border_width=1.5,
            border_color=BORDER_COLOR,
            fg_color=BG_RIGHT,
            text_color=TEXT_PRIMARY,
            font=("Century Gothic", 14),
            placeholder_text="👤  Email or Username",
            placeholder_text_color=TEXT_MUTED,
        )
        username_entry.pack(fill="x", pady=(0, 8))
        self.login_username_entry = username_entry

        # Polished Password Input
        ctk.CTkLabel(
            form_frame,
            text="Password",
            text_color=TEXT_PRIMARY,
            font=("Century Gothic", 13, "bold"),
        ).pack(anchor="w", padx=4, pady=(0, 6))

        password_entry = ctk.CTkEntry(
            form_frame,
            textvariable=self.login_password_var,
            height=50,
            corner_radius=14,
            border_width=1.5,
            border_color=BORDER_COLOR,
            fg_color=BG_RIGHT,
            text_color=TEXT_PRIMARY,
            font=("Century Gothic", 14),
            show="•",
            placeholder_text="🔒  Password",
            placeholder_text_color=TEXT_MUTED,
        )
        password_entry.pack(fill="x", pady=(0, 8))

        def toggle_pw_show():
            if password_entry.cget("show") == "•":
                password_entry.configure(show="")
                pw_toggle_btn.configure(text="O")
            else:
                password_entry.configure(show="•")
                pw_toggle_btn.configure(text="Ø")

        pw_toggle_btn = ctk.CTkButton(
            password_entry,
            text="Ø",
            width=28,
            height=28,
            corner_radius=8,
            fg_color="transparent",
            hover_color=self.palette["surface_alt"] if "surface_alt" in self.palette else BG_RIGHT,
            text_color=TEXT_MUTED,
            font=("Segoe UI", 14, "bold"),
            command=toggle_pw_show,
        )
        pw_toggle_btn.place(relx=1.0, rely=0.5, anchor="e", x=-8)

        # Focus Animations for inputs
        def on_focus_in(entry):
            entry.configure(border_color=ACCENT_COLOR, fg_color=CARD_COLOR)
            
        def on_focus_out(entry):
            entry.configure(border_color=BORDER_COLOR, fg_color=BG_RIGHT)

        username_entry.bind("<FocusIn>", lambda e: on_focus_in(username_entry))
        username_entry.bind("<FocusOut>", lambda e: on_focus_out(username_entry))
        password_entry.bind("<FocusIn>", lambda e: on_focus_in(password_entry))
        password_entry.bind("<FocusOut>", lambda e: on_focus_out(password_entry))
        
        password_entry.bind("<Return>", lambda _event: self._attempt_login())
        username_entry.bind("<Return>", lambda _event: self._attempt_login())

        # Forgot Password Link (Refined)
        forgot_pw_btn = ctk.CTkButton(
            form_frame,
            text="Forgot password?",
            command=self._open_recovery_dialog,
            fg_color="transparent",
            hover_color=CARD_COLOR,
            text_color=ACCENT_DARK,
            font=("Century Gothic", 13, "bold"),
            height=24,
            cursor="hand2"
        )
        forgot_pw_btn.pack(anchor="e", pady=(0, 6))

        # Feedback Label
        self.login_feedback_label = ctk.CTkLabel(
            form_frame,
            textvariable=self.login_feedback_var,
            text_color=TEXT_SECONDARY,
            font=("Century Gothic", 13),
            justify="center",
            wraplength=340,
        )
        self.login_feedback_label.pack(fill="x", pady=(0, 8))

        # Custom button animation wrappers
        def on_enter_btn(e, btn):
            btn.configure(fg_color=ACCENT_HOVER)
        def on_leave_btn(e, btn):
            btn.configure(fg_color=ACCENT_DARK) # Fallback to solid brand teal

        # Unified Login Button
        sign_in_btn = ctk.CTkButton(
            form_frame,
            text="Sign In",
            command=self._attempt_login,
            height=44,
            corner_radius=12,
            fg_color=ACCENT_DARK,
            hover_color=ACCENT_HOVER,
            text_color="#FFFFFF",
            font=("Century Gothic", 14, "bold"),
            cursor="hand2",
        )
        sign_in_btn.pack(fill="x", pady=(0, 20))
        sign_in_btn.bind("<Enter>", lambda e: on_enter_btn(e, sign_in_btn))
        sign_in_btn.bind("<Leave>", lambda e: on_leave_btn(e, sign_in_btn))

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

    def _metric_card(self, parent, key: str, title: str, row: int, column: int, color: str) -> None:
        card = ctk.CTkFrame(
            parent,
            fg_color=color,
            corner_radius=26,
            border_width=1,
            border_color=self.palette["line"],
            height=108,
        )
        card.grid(row=row, column=column, sticky="nsew", padx=8, pady=8)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure((0, 1), weight=1)
        ctk.CTkLabel(
            card,
            text=title,
            text_color=self.palette["muted"],
            font=("Segoe UI", 13, "bold"),
        ).grid(row=0, column=0, sticky="ew", padx=20, pady=(12, 2))
        value_label = ctk.CTkLabel(
            card,
            text="0",
            text_color=self.palette["text"],
            font=("Segoe UI", 28, "bold"),
        )
        value_label.grid(row=1, column=0, sticky="ew", padx=20, pady=(2, 12))
        self.metric_targets.setdefault(key, []).append(value_label)

    def _field(self, parent, label: str, variable: ctk.StringVar, row: int, column: int, numeric_only: bool = False) -> ctk.CTkEntry:
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
        if numeric_only:
            vcmd = (self.register(self._validate_numeric), "%P")
            entry.configure(validate="key", validatecommand=vcmd)
        entry.grid(row=row + 1, column=column, sticky="ew", padx=18 if column == 0 else (8, 18), pady=(0, 16))
        return entry

    def _validate_numeric(self, P: str) -> bool:
        return P == "" or P.isdigit()

    def _date_picker_field(
        self,
        parent,
        label: str,
        variable: ctk.StringVar,
        row: int,
        column: int,
    ) -> DatePickerField:
        self._field_label(parent, label, row, column)
        picker = DatePickerField(
            parent,
            variable=variable,
            min_date=date_type.today(),
            get_status_map=self._admin_date_status_map,
            palette={
                "surface": self.palette["surface"],
                "surface_alt": self.palette["surface_alt"],
                "line": self.palette["line"],
                "text": self.palette["text"],
                "muted": self.palette["muted"],
                "brand": self.palette["brand"],
                "brand_dark": self.palette["brand_dark"],
                "available": "#D9EFE3",
                "available_text": self.palette["brand"],
                "reserved": self.palette["status_reserved"],
                "reserved_text": self.palette["status_reserved_text"],
                "in_use": self.palette["status_in_use"],
                "in_use_text": self.palette["status_in_use_text"],
            },
        )
        picker.grid(
            row=row + 1,
            column=column,
            sticky="ew",
            padx=18 if column == 0 else (8, 18),
            pady=(0, 16),
        )
        return picker

    def _multi_destination_selector(self, parent, label: str, row: int, column: int) -> None:
        self._field_label(parent, label, row, column)
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.grid(row=row + 1, column=column, sticky="ew", padx=(8, 18), pady=(0, 16))
        self.destination_checkboxes = {}
        
        # Sort destinations to keep SandBar first (usually the one with 0 rate)
        dest_names = sorted(self.destination_vars.keys(), key=lambda x: self.destination_assets_by_name.get(x, {}).get("base_rate", 0))

        for i, name in enumerate(dest_names):
            var = self.destination_vars[name]
            cb = ctk.CTkCheckBox(
                container,
                text=name,
                variable=var,
                font=("Segoe UI", 12),
                fg_color=self.palette["brand"],
                hover_color=self.palette["brand_dark"],
                border_color=self.palette["line"],
                checkmark_color=self.palette["surface"],
                height=24,
                checkbox_height=20,
                checkbox_width=20
            )
            cb.grid(row=i // 2, column=i % 2, sticky="w", pady=4, padx=(0, 15))
            self.destination_checkboxes[name] = cb
        self._refresh_destination_checkbox_labels()

    def _dropdown(self, parent, label: str, variable: ctk.StringVar, values: tuple[str, ...], row: int, column: int) -> ctk.CTkOptionMenu:
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
        menu.grid(row=row + 1, column=column, sticky="ew", padx=(8, 18), pady=(0, 16))
        return menu

    def _field_label(self, parent: ctk.CTkFrame, label: str, row: int, column: int) -> None:
        ctk.CTkLabel(
            parent,
            text=label,
            text_color=self.palette["muted"],
            font=("Segoe UI", 12, "bold"),
        ).grid(row=row, column=column, sticky="w", padx=18 if column == 0 else (8, 18), pady=(0, 4))

    def _login_field(self, parent, label: str, variable: ctk.StringVar, row: int, password: bool = False) -> ctk.CTkEntry:
        ctk.CTkLabel(
            parent,
            text=label,
            text_color=self.palette["muted"],
            font=("Segoe UI", 13, "bold"),
        ).grid(row=row, column=0, sticky="w", padx=28, pady=(0, 6))

        entry_frame = ctk.CTkFrame(parent, fg_color="transparent")
        entry_frame.grid(row=row + 1, column=0, sticky="ew", padx=28, pady=(0, 10))
        entry_frame.grid_columnconfigure(0, weight=1)

        entry = ctk.CTkEntry(
            entry_frame,
            textvariable=variable,
            height=46,
            corner_radius=14,
            border_width=1,
            border_color=self.palette["line"],
            fg_color=self.palette["page"],
            text_color=self.palette["text"],
            show="*" if password else "",
        )
        entry.grid(row=0, column=0, sticky="ew")

        if password:
            def toggle_show():
                if entry.cget("show") == "*":
                    entry.configure(show="")
                    toggle_btn.configure(text="O")
                else:
                    entry.configure(show="*")
                    toggle_btn.configure(text="Ø")

            toggle_btn = ctk.CTkButton(
                entry_frame,
                text="Ø",
                width=30,
                height=30,
                corner_radius=8,
                fg_color="transparent",
                hover_color=self.palette["surface"],
                text_color=self.palette["muted"],
                font=("Segoe UI", 14, "bold"),
                command=toggle_show,
            )
            toggle_btn.grid(row=0, column=1, padx=(8, 0))

        return entry

    def _action_button(self, parent, text: str, command, fg_color: str, text_color: str) -> ctk.CTkButton:
        # Determine hover color based on button color
        if fg_color == self.palette["accent"]:
            hover_color = self.palette["accent_dark"]
        elif fg_color == self.palette["brand"]:
            hover_color = self.palette["brand_dark"]
        elif fg_color == self.palette["danger"]:
            hover_color = "#A85347"
        else:
            hover_color = "#E8E8E8"
        
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            fg_color=fg_color,
            hover_color=hover_color,
            text_color=text_color,
            corner_radius=16,
            height=46,
            font=("Segoe UI", 14, "bold"),
        )

    def _mini_button(self, parent, text: str, fg_color: str, text_color: str, command) -> ctk.CTkButton:
        # Determine hover color based on button color
        if fg_color == self.palette["accent"]:
            hover_color = self.palette["accent_dark"]
        elif fg_color == self.palette["brand"]:
            hover_color = self.palette["brand_dark"]
        elif fg_color == self.palette["danger"]:
            hover_color = "#A85347"
        else:
            hover_color = "#E8E8E8"
        
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            width=96,
            height=34,
            corner_radius=13,
            fg_color=fg_color,
            hover_color=hover_color,
            text_color=text_color,
            font=("Segoe UI", 12, "bold"),
        )

    def _status_style(self, status: str) -> tuple[str, str]:
        return {
            "Available": (self.palette["status_available"], self.palette["status_available_text"]),
            "Unpaid": (self.palette["status_cancelled"], self.palette["status_cancelled_text"]),
            "Partially Paid": (self.palette["status_reserved"], self.palette["status_reserved_text"]),
            "Paid": (self.palette["status_available"], self.palette["status_available_text"]),
            "Refunded": (self.palette["status_completed"], self.palette["status_completed_text"]),
            "Pending": (self.palette["status_reserved"], self.palette["status_reserved_text"]),
            "Confirmed": (self.palette["status_reserved"], self.palette["status_reserved_text"]),
            "Approved": (self.palette["status_reserved"], self.palette["status_reserved_text"]),
            "Reserved": (self.palette["status_reserved"], self.palette["status_reserved_text"]),
            "On Going": (self.palette["status_in_use"], self.palette["status_in_use_text"]),
            "Completed": (self.palette["status_completed"], self.palette["status_completed_text"]),
            "Cancelled": (self.palette["status_cancelled"], self.palette["status_cancelled_text"]),
        }.get(status, (self.palette["surface_alt"], self.palette["text"]))

    def _show_quick_stats(self) -> None:
        messagebox.showinfo("Dashboard", "Analytics dashboard would go here.")

    def _attempt_login(self) -> None:
        username = self.login_user_var.get().strip()
        password = self.login_password_var.get()
        auth_result = self.auth_controller.login(username, password)
        if auth_result is None:
            self.login_password_var.set("")
            self.login_feedback_var.set("Incorrect username or password. Please try again.")
            if self.login_feedback_label is not None:
                self.login_feedback_label.configure(text_color=self.palette["danger"])
            return

        if auth_result.role == "admin":
            self.login_feedback_var.set("Login successful. Opening dashboard...")
            if self.login_feedback_label is not None:
                self.login_feedback_label.configure(text_color=self.palette["accent_dark"])
            self._set_status(f"Welcome back, {username}.")
            
            # Store the current logged in user for the UI
            self.current_user = auth_result.username
            
            self.after(150, self._hide_login_overlay)
            
            # Forced Setup Check for Admin
            if not auth_result.session_user.get("recovery_question"):
                self.after(500, lambda: RecoverySetupDialog(self, self.auth_controller, self.palette, auth_result.username, "admin"))
            return

        self.login_feedback_var.set("Login successful. Opening user portal...")
        if self.login_feedback_label is not None:
            self.login_feedback_label.configure(text_color=self.palette["accent_dark"])
        self._set_status(f"Opening the guest portal for {auth_result.username}.")
        self.after(150, lambda: self._open_user_portal(auth_result.session_user))
        
        # Forced Setup Check for Guest
        if not auth_result.session_user.get("recovery_question"):
            self.after(1000, lambda: RecoverySetupDialog(self, self.auth_controller, self.palette, auth_result.username, "user"))

    def _open_recovery_dialog(self) -> None:
        """Opens the multi-step recovery window."""
        RecoveryDialog(self, self.auth_controller, self.palette)

    def _open_guest_signup_portal(self) -> None:
        self.login_password_var.set("")
        self.login_feedback_var.set("Opening the guest sign-up page...")
        if self.login_feedback_label is not None:
            self.login_feedback_label.configure(text_color=self.palette["accent_dark"])
        self._set_status("Opening the guest sign-up page.")
        self.after(100, lambda: self._open_user_portal(None, initial_auth_tab="register", auth_mode="register_only"))

    def _load_guest_portal_shell_class(self):
        project_root = Path(__file__).resolve().parents[2]
        guest_root = project_root / "k3_user"
        guest_path = str(guest_root)
        if guest_path not in sys.path:
            sys.path.insert(0, guest_path)
        from k3_user.app import GuestPortalShell

        return GuestPortalShell

    def _open_user_portal(
        self,
        session_user: dict | None = None,
        initial_auth_tab: str = "login",
        auth_mode: str = "full",
    ) -> None:
        try:
            guest_shell_class = self._load_guest_portal_shell_class()
        except Exception as exc:
            self.login_password_var.set("")
            self.login_feedback_var.set(f"Unable to open the user portal: {exc}")
            if self.login_feedback_label is not None:
                self.login_feedback_label.configure(text_color=self.palette["danger"])
            self._set_status(f"User portal launch failed: {exc}", tone="danger")
            return

        self.login_password_var.set("")
        self._hide_login_overlay()
        if self.guest_portal_host is not None:
            self.guest_portal_host.destroy()

        self.guest_portal_host = ctk.CTkFrame(self, fg_color=self.palette["bg"], corner_radius=0)
        self.guest_portal_host.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.guest_portal_host.grid_rowconfigure(0, weight=1)
        self.guest_portal_host.grid_columnconfigure(0, weight=1)

        self.guest_portal_shell = guest_shell_class(
            self.guest_portal_host,
            session_user=session_user,
            initial_auth_tab=initial_auth_tab,
            auth_mode=auth_mode,
            integrated_auth=True,
            logout_callback=self._close_user_portal,
        )
        self.guest_portal_shell.grid(row=0, column=0, sticky="nsew")
        self.guest_portal_host.lift()

    def _close_user_portal(self) -> None:
        if self.guest_portal_host is not None:
            self.guest_portal_host.destroy()
        self.guest_portal_host = None
        self.guest_portal_shell = None
        
        if self.login_overlay is not None:
            self.login_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.login_overlay.lift()
            
        self.login_password_var.set("")
        self.login_feedback_var.set("")
        self._show_login_overlay()
        self._set_status("Guest portal closed. Sign in again to continue.")

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
        self._refresh_profile_identity()

    def _refresh_profile_identity(self) -> None:
        username = getattr(self, "current_user", None) or self.login_settings.username or "Admin"
        avatar_text = username[0].upper() if username else "A"
        if hasattr(self, "profile_avatar"):
            self.profile_avatar.configure(text=avatar_text)
        if hasattr(self, "profile_name_label"):
            self.profile_name_label.configure(text=username)

    def _refresh_login_settings_state(self) -> None:
        self.login_settings = AppLoginSettings.from_env()
        self.login_user_var.set(self.login_settings.username)
        self.login_hint_var.set(
            "Default login: admin / k3admin123"
            if self.login_settings.uses_default_credentials()
            else "Using the custom K3 app account configured in .env."
        )

    def _logout(self) -> None:
        if messagebox.askyesno("Confirm Logout", "Are you sure you want to log out?"):
            self._show_login_overlay()
            self._set_status("Logged out. Sign in again to continue.")



    def _admin_date_status_map(self) -> dict[str, str]:
        try:
            return self.dashboard_controller.get_date_status_map(
                destination=self.destination_var.get().strip() or None,
                cottage_code=(self._selected_cottage_asset() or {}).get("asset_code"),
            )
        except Exception:
            return {}


    def _update_live_reservation_summary(self) -> None:
        try:
            # 1. Price Calculation
            cottage = self._selected_cottage_asset()
            
            # Ensure catalog is loaded
            if not self.destination_assets_by_name:
                self._refresh_destination_catalog()

            try:
                duration_str = self.duration_var.get().strip()
                duration = float(duration_str) if duration_str else 0
            except ValueError:
                duration = 0
                
            if cottage and duration > 0:
                # Prepare data for unified calculation
                selected_destinations = [name for name, var in self.destination_vars.items() if var.get()]
                all_dest_objects = [
                    self.destination_assets_by_name[name]
                    for name in selected_destinations
                    if name in self.destination_assets_by_name
                ]
                
                # Mock times for live calculation (duration-based)
                now = datetime.now()
                end_time = now + timedelta(hours=duration)
                
                # Use the primary destination from the list if available
                primary_dest = all_dest_objects[0] if all_dest_objects else {"id": 0, "base_rate": 0}
                
                total = self.reservation_controller.calculate_total_price(
                    departure_time=now,
                    return_time=end_time,
                    cottage=cottage,
                    destination_asset=primary_dest,
                    additional_destinations=all_dest_objects
                )
                self.live_price_text_var.set(f"Estimated: PHP {total:,.2f}")
            else:
                self.live_price_text_var.set("Estimated: PHP 0.00")
                
            # 2. Capacity Check
            if cottage:
                capacity = int(cottage.get("capacity", 0))
                try:
                    party = int(self.party_size_var.get().strip())
                except ValueError:
                    party = 0
                    
                if party > capacity:
                    self.live_capacity_text_var.set(f"⚠️ Over Capacity: {party}/{capacity}")
                    if hasattr(self, "capacity_label"):
                        self.capacity_label.configure(text_color=self.palette["danger"])
                else:
                    self.live_capacity_text_var.set(f"👥 Capacity: {party}/{capacity}")
                    if hasattr(self, "capacity_label"):
                        self.capacity_label.configure(text_color=self.palette["text"])
            else:
                self.live_capacity_text_var.set("Capacity: --")
                
            # 3. End Time Calculation
            slot = self.departure_slot_var.get().strip()
            if slot and duration > 0:
                try:
                    dep_time = datetime.strptime(slot, "%H:%M")
                    arr_time = dep_time + timedelta(hours=duration)
                    self.live_time_text_var.set(f"🕒 Ends at: {arr_time.strftime('%I:%M %p')}")
                except Exception:
                    self.live_time_text_var.set("Ends at: --")
            else:
                self.live_time_text_var.set("Ends at: --")
                
        except Exception:
            pass

    def preview_availability(self) -> None:
        try:
            result = self.reservation_controller.preview_availability(self._build_schedule_payload())
        except (ApplicationError, ValueError) as exc:
            self._set_status(str(exc), tone="danger")
            messagebox.showerror("Availability", str(exc))
            return

        departure_time = datetime.strptime(self.departure_var.get(), ReservationController.DATETIME_FORMAT)
        return_time = departure_time + timedelta(hours=float(self.duration_var.get().strip()))
        selected_cottage = self._selected_cottage_asset()
        selected_cottage_text = ""
        if selected_cottage is not None:
            selected_cottage_text = (
                f"Selected cottage: {selected_cottage['asset_code']} - {selected_cottage['name']}\n"
            )
        self.availability_var.set(
            f"{departure_time.strftime('%b %d, %Y %I:%M %p')} to {return_time.strftime('%I:%M %p')}\n\n"
            f"{selected_cottage_text}"
            "Matched pairing: "
            f"{result['recommended']['cottage']['asset_code']} / {result['recommended']['destination_asset']['asset_code']}\n"
            f"Cottage: {result['recommended']['cottage']['name']}\n"
            f"Destination: {result['recommended']['destination_asset']['name']}\n"
            f"Available cottages: {len(result['cottages'])} | Available destinations: {len(result['destination_assets'])}"
        )
        self._set_status("Availability checked successfully.")

    def create_reservation(self) -> None:
        try:
            payload = self._build_schedule_payload()
            
            # Selected destinations
            selected_destinations = [name for name, var in self.destination_vars.items() if var.get()]
            dest_summary = ", ".join(selected_destinations) if selected_destinations else "No stops selected"

            payload.update({
                "full_name": self.name_var.get().strip(),
                "contact_number": self.contact_var.get().strip(),
                "email": self.email_var.get().strip(),
                "notes": self.notes_var.get().strip(),
                "destinations": selected_destinations
            })

            # Check availability again to get the assigned assets and price
            avail = self.reservation_controller.preview_availability(payload)
            cottage = avail["recommended"]["cottage"]
            destination_asset = avail["recommended"]["destination_asset"]
            
            departure_time = datetime.strptime(payload["departure_time"], ReservationController.DATETIME_FORMAT)
            return_time = datetime.strptime(payload["return_time"], ReservationController.DATETIME_FORMAT)
            
            # Use the cached destination catalog for consistent pricing
            all_dest_objects = [
                self.destination_assets_by_name[name]
                for name in selected_destinations
                if name in self.destination_assets_by_name
            ]

            price = self.reservation_controller.calculate_total_price(
                departure_time, return_time, cottage, destination_asset, additional_destinations=all_dest_objects
            )
            
            details = [
                ("Guest", payload['full_name'], "👤"),
                ("Cottage", f"{cottage['asset_code']} | {cottage['name']}", "🏠"),
                ("Destinations", dest_summary, "📍"),
                ("Schedule", f"{departure_time.strftime('%b %d, %Y')} • {departure_time.strftime('%I:%M %p')} - {return_time.strftime('%I:%M %p')}", "📅"),
                ("Party Size", f"{payload['party_size']} pax", "👥"),
            ]
            
            self._show_reservation_confirmation(details, price, payload)
            
        except (ApplicationError, ValueError) as exc:
            self._set_status(str(exc), tone="danger")
            messagebox.showerror("Reservation", str(exc))

    def _show_reservation_confirmation(self, details: list[tuple], price: float, payload: dict) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Confirm Reservation")
        dialog.geometry("520x700")
        dialog.configure(fg_color=self.palette["bg"])
        dialog.transient(self)
        dialog.grab_set()

        # Center dialog
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (520 // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (700 // 2)
        dialog.geometry(f"+{x}+{y}")

        shell = ctk.CTkFrame(dialog, fg_color="transparent")
        shell.pack(fill="both", expand=True, padx=24, pady=20)

        ctk.CTkLabel(
            shell, 
            text="Review Reservation", 
            font=("Segoe UI", 28, "bold"), 
            text_color=self.palette["text"]
        ).pack(pady=(0, 4))
        ctk.CTkLabel(
            shell, 
            text="Please verify the booking details below.", 
            font=("Segoe UI", 13), 
            text_color=self.palette["muted"]
        ).pack(pady=(0, 20))

        # Pack buttons at the bottom FIRST
        btn_row = ctk.CTkFrame(shell, fg_color="transparent")
        btn_row.pack(side="bottom", fill="x", pady=(15, 0))
        btn_row.grid_columnconfigure((0, 1), weight=1)

        def on_confirm():
            dialog.destroy()
            self._execute_create_reservation(payload)

        ctk.CTkButton(
            btn_row, 
            text="Back", 
            fg_color=self.palette["surface"], 
            text_color=self.palette["text"], 
            border_width=1,
            border_color=self.palette["line"],
            hover_color=self.palette["hover"],
            command=dialog.destroy, 
            height=46,
            corner_radius=12,
            font=("Segoe UI", 13)
        ).grid(row=0, column=0, padx=(0, 6), sticky="ew")
        
        ctk.CTkButton(
            btn_row, 
            text="Generate Receipt & Confirm", 
            fg_color=self.palette["brand"], 
            hover_color=self.palette["brand_dark"],
            text_color=self.palette["surface"], 
            font=("Segoe UI", 13, "bold"), 
            command=on_confirm, 
            height=46,
            corner_radius=12
        ).grid(row=0, column=1, padx=(6, 0), sticky="ew")
        
        card = ctk.CTkFrame(
            shell, 
            fg_color=self.palette["surface"], 
            corner_radius=24, 
            border_width=1, 
            border_color=self.palette["line"]
        )
        card.pack(fill="both", expand=True, pady=0)
        
        details_inner = ctk.CTkFrame(card, fg_color="transparent")
        details_inner.pack(fill="x", padx=20, pady=15)
        details_inner.grid_columnconfigure(0, weight=1)

        for i, (label, value, icon) in enumerate(details):
            row = ctk.CTkFrame(details_inner, fg_color="transparent")
            row.grid(row=i, column=0, sticky="ew", pady=6)
            row.grid_columnconfigure(1, weight=1)
            
            icon_lbl = ctk.CTkLabel(row, text=icon, font=("Segoe UI", 18), text_color=self.palette["brand"])
            icon_lbl.grid(row=0, column=0, padx=(0, 15))
            
            content = ctk.CTkFrame(row, fg_color="transparent")
            content.grid(row=0, column=1, sticky="w")
            
            ctk.CTkLabel(content, text=label.upper(), font=("Segoe UI", 10, "bold"), text_color=self.palette["muted"], anchor="w").pack(anchor="w")
            ctk.CTkLabel(content, text=value, font=("Segoe UI", 14), text_color=self.palette["text"], anchor="w").pack(anchor="w")

        price_card = ctk.CTkFrame(card, fg_color=self.palette["surface_alt"], corner_radius=18)
        price_card.pack(fill="x", padx=20, pady=(0, 20))
        
        ctk.CTkLabel(
            price_card, 
            text="TOTAL PRICE TO BE PAID", 
            font=("Segoe UI", 10, "bold"), 
            text_color=self.palette["muted"]
        ).pack(pady=(15, 0))
        
        ctk.CTkLabel(
            price_card, 
            text=f"PHP {price:,.2f}", 
            font=("Segoe UI", 24, "bold"), 
            text_color=self.palette["brand"]
        ).pack(pady=(0, 12))


    def _execute_create_reservation(self, payload: dict) -> None:
        try:
            result = self.reservation_controller.create_reservation(payload)
        except ApplicationError as exc:
            self._set_status(str(exc), tone="danger")
            messagebox.showerror("Reservation", str(exc))
            return

        reservation = result["reservation"]
        
        # Generate Receipt PDF
        try:
            from k3_rms.services.receipt_service import ReceiptService
            import subprocess
            import os
            
            receipt_path = ReceiptService.generate_receipt(reservation)
            if receipt_path:
                # Try to open the PDF automatically
                if os.name == 'nt': # Windows
                    os.startfile(receipt_path)
                elif sys.platform == 'darwin': # macOS
                    subprocess.call(['open', receipt_path])
                else: # Linux
                    subprocess.call(['xdg-open', receipt_path])
        except Exception as e:
            print(f"Failed to generate or open receipt: {e}")

        self.action_code_var.set(reservation["reservation_code"])
        self.availability_var.set(f"Reservation {reservation['reservation_code']} created for {reservation['full_name']}.")
        self.refresh_dashboard(status_message=f"Reservation {reservation['reservation_code']} created successfully.")
        self.show_page("operations")
        messagebox.showinfo(
            "Reservation Confirmed",
            (
                f"Reservation Code: {reservation['reservation_code']}\n"
                f"Cottage: {result['auto_assigned']['cottage']['asset_code']} - {result['auto_assigned']['cottage']['name']}\n"
                f"Destination: {result['auto_assigned']['destination_asset']['asset_code']} - {result['auto_assigned']['destination_asset']['name']}\n"
                f"Total Price: PHP {float(reservation['total_price']):,.2f}\n\n"
                f"Receipt generated: {receipt_path}"
            ),
        )

    def _clear_reservation_form(self) -> None:
        default_departure = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
        if datetime.now().hour >= 15:
            default_departure = default_departure + timedelta(days=1)
        
        self.departure_date_var.set(default_departure.strftime("%Y-%m-%d"))
        self.departure_slot_var.set("08:00")
        self.duration_var.set("4")
        self.party_size_var.set("6")
        self.name_var.set("")
        self.contact_var.set("")
        self.email_var.set("")
        self.destination_var.set(self.reservation_controller.destinations()[0])
        self.notes_var.set("")
        self.availability_var.set("Choose a travel date, departure slot, and party size, then click Check Availability.")
        
        self._refresh_cottage_catalog()
        self._set_status("Reservation form cleared.")

    def start_trip(self) -> None:
        self._execute_status_change("start")

    def complete_trip(self) -> None:
        self._execute_status_change("complete")

    def cancel_reservation(self) -> None:
        self._execute_status_change("cancel")

    def _execute_status_change(self, action: str) -> None:
        code = self.action_code_var.get().strip()
        if not code:
            messagebox.showwarning(
                "Reservation Code",
                "Enter a reservation code or use the reservation action buttons first.",
            )
            return

        try:
            if action == "start":
                reservation = self.reservation_controller.start_trip(code)
                message = f"{reservation['reservation_code']} is now on going."
            elif action == "complete":
                reservation = self.reservation_controller.complete_trip(code)
                message = f"{reservation['reservation_code']} has been completed."
            else:
                reservation = self.reservation_controller.cancel_reservation(code, "Cancelled from Operations page.")
                message = f"{reservation['reservation_code']} has been cancelled."
        except ApplicationError as exc:
            self._set_status(str(exc), tone="danger")
            messagebox.showerror("Trip Update", str(exc))
            return

        self.refresh_dashboard(status_message=message)
        self._set_status(message)

    def _build_schedule_payload(self) -> dict:
        selected_cottage = self._selected_cottage_asset()
        if selected_cottage is None:
            raise ValueError("Select a cottage to book.")
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
            
        selected_destinations = [name for name, var in self.destination_vars.items() if var.get()]
        if not selected_destinations:
            raise ValueError("Select at least one destination.")
        primary_destination = selected_destinations[0]
        primary_asset = self.destination_assets_by_name.get(primary_destination)
            
        self.departure_var.set(departure_time.strftime(ReservationController.DATETIME_FORMAT))
        return {
            "cottage_id": selected_cottage["id"],
            "destination": primary_destination,
            "destination_id": primary_asset["id"] if primary_asset else None,
            "destinations": selected_destinations,
            "departure_time": departure_time.strftime(ReservationController.DATETIME_FORMAT),
            "return_time": return_time_value.strftime(ReservationController.DATETIME_FORMAT),
            "party_size": int(party_size),
        }

    def _render_reservations(
        self,
        section,
        reservations: list[dict],
        with_actions: bool,
        preserve_section_header: bool = True,
    ) -> None:
        if preserve_section_header:
            self._clear_section_content(section)
            first_row = 1
        else:
            self._clear_children(section)
            first_row = 0
        if not reservations:
            ctk.CTkLabel(
                section,
                text="No reservations to show right now.",
                text_color=self.palette["muted"],
                font=("Segoe UI", 14),
            ).grid(row=first_row, column=0, sticky="w", padx=18, pady=(0, 18))
            return

        for row_index, reservation in enumerate(reservations, start=first_row):
            card = ctk.CTkFrame(section, fg_color=self.palette["surface"], corner_radius=20, border_width=1, border_color=self.palette["line"])
            card.grid(row=row_index, column=0, sticky="ew", padx=24, pady=(0, 12))
            card.grid_columnconfigure(0, weight=1)

            departure_value = reservation["departure_time"]
            departure_text = departure_value.strftime("%b %d, %Y %I:%M %p") if isinstance(departure_value, datetime) else str(departure_value)

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
                    f"Cottage {reservation['cottage_code']} | Destination {reservation['destination_code']}"
                ),
                text_color=self.palette["muted"],
                font=("Segoe UI", 13),
                justify="left",
                wraplength=700,
            ).grid(row=1, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 12))

            if with_actions:
                status = reservation.get("status")
                if status in ("Completed", "Cancelled"):
                    action_row = ctk.CTkFrame(card, fg_color="transparent")
                    action_row.grid(row=2, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 16))
                    
                    # Show Delete for finished bookings
                    self._mini_button(
                        action_row,
                        "Delete",
                        "#D0757A", # Danger/Red
                        self.palette["surface"],
                        lambda code=reservation["reservation_code"]: self._on_delete_reservation(code),
                    ).grid(row=0, column=0)
                # No other buttons (Cancel/Start/Complete) for active bookings on cards

    def _render_reservations_table(self, reservations: list[dict]) -> None:
        if self.operations_reservations_table_frame is None:
            return
        self._clear_children(self.operations_reservations_table_frame)

        visible_reservations = self._filtered_sorted_reservations(reservations)
        upcoming_count = 0
        past_count = 0
        now = datetime.now()
        for reservation in visible_reservations:
            departure_time = reservation.get("departure_time")
            if isinstance(departure_time, datetime) and departure_time >= now:
                upcoming_count += 1
            else:
                past_count += 1

        self.reservation_summary_var.set(
            f"Showing {len(visible_reservations)} of {len(reservations)} reservations | "
            f"Upcoming and active: {upcoming_count} | Past: {past_count}"
        )

        if not visible_reservations:
            ctk.CTkLabel(
                self.operations_reservations_table_frame,
                text="No reservations matched the current search and filters.",
                text_color=self.palette["muted"],
                font=("Segoe UI", 14),
            ).grid(row=0, column=0, sticky="w", padx=24, pady=(0, 18))
            return

        board = ctk.CTkScrollableFrame(
            self.operations_reservations_table_frame,
            fg_color="transparent",
            height=420,
        )
        board.grid(row=0, column=0, sticky="nsew", padx=18, pady=(0, 18))
        board.grid_columnconfigure(0, weight=1)

        headers = [
            "Reservation ID", "Cottage Name", "Customer Name", "Contact",
            "Date", "Status", "Price", "Created At", "Actions",
        ]

        table_data = [headers]
        reservation_codes = []
        reservation_statuses = []

        for reservation in visible_reservations:
            departure_time = reservation.get("departure_time")
            created_at = reservation.get("created_at")
            departure_text = (
                departure_time.strftime("%b %d, %Y %I:%M %p")
                if isinstance(departure_time, datetime)
                else str(departure_time or "")
            )
            created_text = (
                created_at.strftime("%b %d, %Y %I:%M %p")
                if isinstance(created_at, datetime)
                else str(created_at or "")
            )
            status = str(reservation.get("status") or "")
            if status in {"Completed", "Cancelled"}:
                action_text = "Load | Delete"
            else:
                action_text = "Load | Cancel"

            row_values = [
                str(reservation.get("reservation_code") or ""),
                f"{reservation.get('cottage_code') or ''} | {reservation.get('cottage_name') or ''}",
                str(reservation.get("full_name") or ""),
                str(reservation.get("contact_number") or ""),
                departure_text,
                status,
                f"PHP {float(reservation.get('total_price') or 0):,.2f}",
                created_text,
                action_text,
            ]
            table_data.append(row_values)
            reservation_codes.append(str(reservation.get("reservation_code") or ""))
            reservation_statuses.append(status)

        def on_reservation_table_click(cell_data):
            row_idx = cell_data["row"]
            if row_idx == 0:
                col_key_map = {
                    0: "reservation_code", 1: "cottage_name", 2: "full_name",
                    3: "contact_number", 4: "departure_time", 5: "status",
                    6: "total_price", 7: "created_at",
                }
                col_idx = cell_data["column"]
                sort_key = col_key_map.get(col_idx)
                if sort_key:
                    self._toggle_reservation_sort(sort_key)
                return
            data_index = row_idx - 1
            if data_index < 0 or data_index >= len(reservation_codes):
                return
            code = reservation_codes[data_index]
            col_idx = cell_data["column"]
            if col_idx == 8:
                action_type = cell_data["value"].lower()
                if "delete" in action_type:
                    self._on_delete_reservation(code)
                else:
                    self.action_code_var.set(code)

        table = CTkTable(
            master=board,
            row=len(table_data),
            column=len(headers),
            values=table_data,
            colors=[self.palette["surface"], "#FAFAFA"],
            header_color=self.palette["surface_alt"],
            hover_color="#EDF6F3",
            text_color=self.palette["text"],
            font=("Segoe UI", 11),
            corner_radius=8,
            padx=4,
            pady=4,
            command=on_reservation_table_click,
            wraplength=120,
        )
        table.pack(fill="both", expand=True, padx=8, pady=8)

        for col_idx in range(len(headers)):
            table.edit(0, col_idx, font=("Segoe UI", 11, "bold"), text_color=self.palette["text_secondary"])

        for data_row_idx in range(len(visible_reservations)):
            status = reservation_statuses[data_row_idx]
            table_row = data_row_idx + 1
            if status in {"Completed", "Cancelled"}:
                table.edit(
                    table_row, 8,
                    fg_color=self.palette["surface_alt"],
                    text_color=self.palette["muted"],
                    font=("Segoe UI", 11, "bold"),
                )
            else:
                table.edit(
                    table_row, 8,
                    fg_color=self.palette["brand"],
                    text_color=self.palette["surface"],
                    font=("Segoe UI", 11, "bold"),
                )

    def _render_payments_page(self, reservations: list[dict]) -> None:
        if self.payments_summary_frame is not None:
            self._clear_section_content(self.payments_summary_frame)
            
            # Re-add Revenue Report button (since clear_section_content removes it)
            ctk.CTkButton(
                self.payments_summary_frame,
                text="📈 Detailed Revenue Report",
                command=self._show_revenue_report,
                fg_color=self.palette["brand"],
                hover_color=self.palette["brand_dark"],
                text_color="#FFFFFF",
                font=("Segoe UI", 12, "bold"),
                height=36,
                corner_radius=10,
            ).place(relx=1.0, x=-24, y=32, anchor="ne")

            cards = ctk.CTkFrame(self.payments_summary_frame, fg_color="transparent")
            cards.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
            for column_index in range(4):
                cards.grid_columnconfigure(column_index, weight=1)

            unpaid_count = sum(1 for reservation in reservations if str(reservation.get("payment_status") or "Unpaid") == "Unpaid")
            partial_count = sum(1 for reservation in reservations if str(reservation.get("payment_status") or "") == "Partially Paid")
            paid_count = sum(1 for reservation in reservations if str(reservation.get("payment_status") or "") == "Paid")
            refunded_count = sum(1 for reservation in reservations if str(reservation.get("payment_status") or "") == "Refunded")

            self._summary_stat_card(cards, "Unpaid", str(unpaid_count), "Bookings with no recorded payment yet.", 0, 0, "#FCEBE9")
            self._summary_stat_card(cards, "Partially Paid", str(partial_count), "Reservations with a remaining balance.", 0, 1, "#FDF5E0")
            self._summary_stat_card(cards, "Paid", str(paid_count), "Bookings fully settled by the guest.", 0, 2, "#EAF3EF")
            self._summary_stat_card(cards, "Refunded", str(refunded_count), "Reservations whose payment was reversed.", 0, 3, "#F7F4FA")

        if not hasattr(self, "payments_records_section"):
            return

        visible_reservations = self._filtered_sorted_payments(reservations)
        outstanding_balance = sum(float(reservation.get("balance_due") or 0) for reservation in visible_reservations)
        total_collected = sum(float(reservation.get("amount_paid") or 0) for reservation in visible_reservations)
        
        self.payment_summary_var.set(
            f"Showing {len(visible_reservations)} of {len(reservations)} records | "
            f"Total Collected: PHP {total_collected:,.2f} | "
            f"Outstanding: PHP {outstanding_balance:,.2f}"
        )

        buckets = {
            "Pending": [],
            "Approved": [],
            "On Going": [],
            "Completed": [],
            "Cancelled": [],
        }
        for r in visible_reservations:
            status = r.get("status")
            if status == "Reserved": buckets["Approved"].append(r)
            elif status == "On Going": buckets["On Going"].append(r)
            elif status in buckets: buckets[status].append(r)

        # Update Tab Counts
        for key, btn in self.payment_tab_buttons.items():
            count = len(buckets.get(key, []))
            btn.configure(text=f"{key}  ({count})" if count > 0 else key)

        # Render Active Tab Content
        active_tab = self.payment_active_tab.get()
        active_reservations = buckets.get(active_tab, [])
        
        self._clear_children(self._payment_content_frame)
        if not active_reservations:
            ctk.CTkLabel(
                self._payment_content_frame,
                text=f"No {active_tab.lower()} records match filters.",
                text_color=self.palette["muted"],
                font=("Segoe UI", 13),
            ).grid(row=0, column=0, pady=40)
        else:
            self._render_payments_tab_table(self._payment_content_frame, active_reservations)

    def _render_payments_tab_table(self, container, reservations: list[dict]) -> None:
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)
        board = ctk.CTkFrame(container, fg_color="transparent")
        board.grid(row=0, column=0, sticky="nsew")
        board.grid_columnconfigure(0, weight=1)
        board.grid_rowconfigure(0, weight=1)

        headers = [
            "Ref ID", "Guest", "Travel Date", "Total",
            "Paid", "Balance", "Payment", "Method",
            "Trip", "Actions",
        ]

        table_data = [headers]
        reservation_codes = []

        for reservation in reservations:
            departure_time = reservation.get("departure_time")
            departure_text = (
                departure_time.strftime("%b %d, %H:%M")
                if isinstance(departure_time, datetime)
                else str(departure_time or "")
            )
            p_status = str(reservation.get("payment_status") or "Unpaid")
            t_status = str(reservation.get("status") or "")
            
            # Read-only if Paid or Cancelled
            is_readonly = (p_status == "Paid" or t_status == "Cancelled")
            
            row_values = [
                str(reservation.get("reservation_code") or ""),
                str(reservation.get("full_name") or ""),
                departure_text,
                f"P{float(reservation.get('total_price') or 0):,.0f}",
                f"P{float(reservation.get('amount_paid') or 0):,.0f}",
                f"P{float(reservation.get('balance_due') or 0):,.0f}",
                p_status,
                str(reservation.get("payment_method") or "-"),
                t_status,
                "Details" if is_readonly else "Details | Update",
            ]
            table_data.append(row_values)
            reservation_codes.append(str(reservation.get("reservation_code") or ""))

        def on_click(cell_data):
            row_idx = cell_data["row"]
            if row_idx == 0: return # No header sorting in tab view for now to keep simple
            data_index = row_idx - 1
            if data_index < 0 or data_index >= len(reservation_codes): return
            code = reservation_codes[data_index]
            col_idx = cell_data["column"]
            if col_idx == 9:
                if "Update" in str(cell_data.get("value", "")):
                    self._show_payment_update_modal(code)
                else:
                    self._show_payment_details(code)

        table = CTkTable(
            master=board,
            row=len(table_data),
            column=len(headers),
            values=table_data,
            colors=[self.palette["surface"], "#FAFAFA"],
            header_color=self.palette["surface_alt"],
            hover_color="#EDF6F3",
            text_color=self.palette["text"],
            font=("Segoe UI", 10),
            corner_radius=8,
            padx=4,
            pady=4,
            command=on_click,
        )
        table.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        for col_idx in range(len(headers)):
            table.edit(0, col_idx, font=("Segoe UI", 10, "bold"), text_color=self.palette["text_secondary"])

        for data_row_idx, reservation in enumerate(reservations):
            table_row = data_row_idx + 1
            p_status = str(reservation.get("payment_status") or "Unpaid")
            p_bg, p_text = self._status_style(p_status)
            table.edit(table_row, 6, fg_color=p_bg, text_color=p_text, font=("Segoe UI", 10, "bold"))
            
            t_status = str(reservation.get("status") or "")
            t_bg, t_text = self._status_style(t_status)
            table.edit(table_row, 8, fg_color=t_bg, text_color=t_text, font=("Segoe UI", 10, "bold"))

            if t_status == "Cancelled" or p_status == "Paid":
                table.edit(table_row, 9, fg_color=self.palette["surface_alt"], text_color=self.palette["accent_dark"], font=("Segoe UI", 10, "bold"))
            else:
                table.edit(table_row, 9, fg_color=self.palette["brand"], text_color=self.palette["surface"], font=("Segoe UI", 10, "bold"))

    def _show_revenue_report(self) -> None:
        try:
            report_data = self.dashboard_controller.get_revenue_report_data()
        except Exception as exc:
            self._set_status(f"Failed to fetch report data: {exc}", tone="danger")
            messagebox.showerror("Revenue Report", str(exc))
            return

        if not report_data:
            messagebox.showinfo("Revenue Report", "No financial data available to generate a report.")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Revenue & Collection Analysis")
        dialog.geometry("1000x850")
        dialog.configure(fg_color=self.palette["bg"])
        dialog.transient(self)
        dialog.grab_set()

        # Center
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (1000 // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (850 // 2)
        dialog.geometry(f"+{x}+{y}")

        shell = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        shell.pack(fill="both", expand=True, padx=24, pady=24)

        # Header
        header = ctk.CTkFrame(shell, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            header,
            text="Financial Performance Report",
            font=("Segoe UI", 36, "bold"),
            text_color=self.palette["text"],
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            header,
            text="Detailed breakdown of projected revenue vs. actual collections.",
            font=("Segoe UI", 16),
            text_color=self.palette["muted"],
        ).pack(anchor="w")

        # Summary Row
        summary_row = ctk.CTkFrame(shell, fg_color="transparent")
        summary_row.pack(fill="x", pady=(0, 24))
        for i in range(4): summary_row.grid_columnconfigure(i, weight=1)

        total_rev = sum(float(d["total_revenue"] or 0) for d in report_data)
        total_col = sum(float(d["total_collected"] or 0) for d in report_data)
        total_out = total_rev - total_col
        collection_rate = (total_col / total_rev * 100) if total_rev > 0 else 0

        self._summary_stat_card(summary_row, "Lifetime Revenue", f"PHP {total_rev:,.2f}", "Total value of all non-cancelled bookings.", 0, 0, "#EAF3EF")
        self._summary_stat_card(summary_row, "Lifetime Collected", f"PHP {total_col:,.2f}", "Actual total money received in pocket.", 0, 1, "#EBF5FB")
        self._summary_stat_card(summary_row, "Outstanding Balance", f"PHP {total_out:,.2f}", "Total remaining amount to be collected.", 0, 2, "#FCEBE9")
        self._summary_stat_card(summary_row, "Collection Rate", f"{collection_rate:.1f}%", "Efficiency of your payment collection.", 0, 3, "#F7F4FA")

        # Chart Section
        chart_card = ctk.CTkFrame(shell, fg_color=self.palette["surface"], corner_radius=28, border_width=1, border_color=self.palette["line"])
        chart_card.pack(fill="x", pady=(0, 24))
        
        ctk.CTkLabel(chart_card, text="Monthly Revenue Trend", font=("Segoe UI", 20, "bold"), text_color=self.palette["text"]).pack(anchor="w", padx=30, pady=(24, 10))

        # Prepare data for matplotlib
        # Sort report_data by month ASC for the chart
        sorted_for_chart = sorted(report_data, key=lambda x: x["month"])
        months = [d["month"] for d in sorted_for_chart]
        rev_vals = [float(d["total_revenue"] or 0) for d in sorted_for_chart]
        col_vals = [float(d["total_collected"] or 0) for d in sorted_for_chart]

        fig = Figure(figsize=(9, 4), dpi=100, facecolor=self.palette["surface"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(self.palette["surface"])
        
        x_indices = range(len(months))
        width = 0.35
        
        ax.bar([i - width/2 for i in x_indices], rev_vals, width, label='Projected Revenue', color=self.palette["accent"], alpha=0.7)
        ax.bar([i + width/2 for i in x_indices], col_vals, width, label='Actual Collected', color=self.palette["brand"])
        
        display_months = []
        for m in months:
            try:
                dt = datetime.strptime(m, "%Y-%m")
                display_months.append(dt.strftime("%b %Y"))
            except Exception:
                display_months.append(m)

        ax.set_xticks(x_indices)
        ax.set_xticklabels(display_months, rotation=30, fontsize=9)
        ax.legend(frameon=False, fontsize=10)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='y', linestyle='--', alpha=0.3)
        
        canvas = FigureCanvasTkAgg(fig, master=chart_card)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="x", padx=30, pady=(0, 30))

        # Table Section
        table_card = ctk.CTkFrame(shell, fg_color=self.palette["surface"], corner_radius=28, border_width=1, border_color=self.palette["line"])
        table_card.pack(fill="x")
        
        ctk.CTkLabel(table_card, text="Monthly Breakdown Table", font=("Segoe UI", 20, "bold"), text_color=self.palette["text"]).pack(anchor="w", padx=30, pady=(24, 10))

        headers = ["Month", "Bookings", "Projected Revenue", "Actual Collected", "Outstanding", "Collection %"]
        table_data = [headers]
        for d in report_data:
            rev = float(d["total_revenue"] or 0)
            col = float(d["total_collected"] or 0)
            out = rev - col
            rate = (col / rev * 100) if rev > 0 else 0
            try:
                month_dt = datetime.strptime(d["month"], "%Y-%m")
                month_display = month_dt.strftime("%B %Y")
            except Exception:
                month_display = d["month"]

            table_data.append([
                month_display,
                str(d["total_bookings"]),
                f"PHP {rev:,.2f}",
                f"PHP {col:,.2f}",
                f"PHP {out:,.2f}",
                f"{rate:.1f}%"
            ])

        table = CTkTable(
            master=table_card,
            row=len(table_data),
            column=len(headers),
            values=table_data,
            colors=[self.palette["surface"], "#FAFAFA"],
            header_color=self.palette["surface_alt"],
            hover_color="#EDF6F3",
            text_color=self.palette["text"],
            font=("Segoe UI", 12),
            corner_radius=16,
            padx=10,
            pady=10,
        )
        table.pack(fill="x", padx=30, pady=(0, 30))
        for i in range(len(headers)): 
            table.edit(0, i, font=("Segoe UI", 12, "bold"), text_color=self.palette["text_secondary"])
            
        # Export Notice
        ctk.CTkLabel(
            shell,
            text="Note: This report is generated in real-time based on current reservation and payment logs.",
            font=("Segoe UI", 12, "italic"),
            text_color=self.palette["muted"],
        ).pack(pady=20)

    def _show_payment_details(self, reservation_code: str) -> None:
        try:
            reservation = self.reservation_controller.get_reservation(reservation_code)
            payment_history = self.reservation_controller.get_payment_history(reservation_code, limit=1)
            payment_logs = self.reservation_controller.get_payment_logs(reservation_code, limit=1)
        except (ApplicationError, ValueError) as exc:
            self._set_status(str(exc), tone="danger")
            messagebox.showerror("Payment Details", str(exc))
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Payment Details - {reservation_code}")
        dialog.geometry("560x660")
        dialog.configure(fg_color=self.palette["bg"])
        dialog.transient(self)
        dialog.grab_set()

        shell = ctk.CTkFrame(dialog, fg_color="transparent")
        shell.pack(fill="both", expand=True, padx=14, pady=14)

        card = ctk.CTkFrame(
            shell,
            fg_color=self.palette["surface"],
            corner_radius=20,
            border_width=1,
            border_color=self.palette["line"],
        )
        card.pack(fill="both", expand=True)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            card,
            text="Payment Details",
            text_color=self.palette["text"],
            font=("Segoe UI", 18, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(14, 2))
        ctk.CTkLabel(
            card,
            text="Review reservation and payment details before applying changes.",
            text_color=self.palette["muted"],
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 8))

        latest_payment = payment_history[0] if payment_history else None
        latest_log = payment_logs[0] if payment_logs else None
        latest_payment_text = "No payment transaction recorded yet."
        if latest_payment:
            payment_recorded_at = latest_payment.get("recorded_at")
            payment_recorded_text = (
                payment_recorded_at.strftime("%b %d, %Y %I:%M %p")
                if isinstance(payment_recorded_at, datetime)
                else str(payment_recorded_at or "Unknown time")
            )
            latest_payment_text = (
                f"{latest_payment.get('transaction_type') or 'Payment'} | "
                f"PHP {abs(float(latest_payment.get('payment_amount') or 0)):,.2f} | "
                f"{latest_payment.get('payment_status') or 'Unpaid'} | {payment_recorded_text}"
            )

        latest_log_text = "No payment log recorded yet."
        if latest_log:
            log_created_at = latest_log.get("created_at")
            log_created_text = (
                log_created_at.strftime("%b %d, %Y %I:%M %p")
                if isinstance(log_created_at, datetime)
                else str(log_created_at or "Unknown time")
            )
            latest_log_text = (
                f"{str(latest_log.get('action') or 'status_update').replace('_', ' ').title()} | "
                f"{latest_log.get('old_payment_status') or 'Unpaid'} -> "
                f"{latest_log.get('new_payment_status') or 'Unpaid'} | {log_created_text}"
            )

        detail_rows = [
            ("Reservation Code", reservation.get("reservation_code")),
            ("Guest", reservation.get("full_name")),
            ("Contact Number", reservation.get("contact_number")),
            ("Email", reservation.get("email")),
            ("Cottage", f"{reservation.get('cottage_code') or ''} | {reservation.get('cottage_name') or ''}"),
            ("Destination", reservation.get("destination")),
            ("Travel Date", reservation.get("departure_time").strftime("%b %d, %Y %I:%M %p") if isinstance(reservation.get("departure_time"), datetime) else reservation.get("departure_time")),
            ("Return Time", reservation.get("return_time").strftime("%b %d, %Y %I:%M %p") if isinstance(reservation.get("return_time"), datetime) else reservation.get("return_time")),
            ("Reservation Status", reservation.get("status")),
            ("Payment Status", reservation.get("payment_status") or "Unpaid"),
            ("Total Amount", f"PHP {float(reservation.get('total_price') or 0):,.2f}"),
            ("Amount Paid", f"PHP {float(reservation.get('amount_paid') or 0):,.2f}"),
            ("Balance Due", f"PHP {float(reservation.get('balance_due') or 0):,.2f}"),
            ("Payment Method", reservation.get("payment_method") or "Not set"),
            ("Paid At", reservation.get("paid_at").strftime("%b %d, %Y %I:%M %p") if isinstance(reservation.get("paid_at"), datetime) else "Not recorded"),
            ("Payment Notes", reservation.get("payment_notes") or "No payment notes recorded."),
            ("Latest Payment Entry", latest_payment_text),
            ("Latest Transaction Log", latest_log_text),
        ]

        detail_grid = ctk.CTkFrame(card, fg_color=self.palette["surface_alt"], corner_radius=14)
        detail_grid.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 10))
        detail_grid.grid_columnconfigure(0, weight=1)
        detail_grid.grid_columnconfigure(1, weight=1)
        for index, (label, value) in enumerate(detail_rows):
            ctk.CTkLabel(
                detail_grid,
                text=label,
                text_color=self.palette["muted"],
                font=("Segoe UI", 10, "bold"),
                anchor="w",
            ).grid(row=index, column=0, sticky="w", padx=14, pady=(8 if index == 0 else 4, 0))
            ctk.CTkLabel(
                detail_grid,
                text=str(value or ""),
                text_color=self.palette["text"],
                font=("Segoe UI", 11, "bold") if label in {"Reservation Code", "Guest", "Payment Status", "Balance Due"} else ("Segoe UI", 11),
                anchor="e",
                justify="right",
                wraplength=220,
            ).grid(row=index, column=1, sticky="e", padx=14, pady=(8 if index == 0 else 4, 0))

        is_locked = (reservation.get("status") == "Cancelled" or str(reservation.get("payment_status") or "Unpaid") == "Paid")

        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 14))
        footer.grid_columnconfigure((0, 1), weight=1)
        
        if not is_locked:
            ctk.CTkButton(
                footer,
                text="Update Payment Status",
                command=lambda: (dialog.destroy(), self._show_payment_update_modal(reservation_code)),
                height=38,
                corner_radius=10,
                fg_color=self.palette["brand"],
                hover_color=self.palette["brand_dark"],
                text_color=self.palette["surface"],
                font=("Segoe UI", 12, "bold"),
            ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
            
        ctk.CTkButton(
            footer,
            text="Close",
            command=dialog.destroy,
            height=38,
            corner_radius=10,
            fg_color=self.palette["surface_alt"],
            hover_color=self.palette["hover"],
            text_color=self.palette["text"],
            font=("Segoe UI", 12, "bold"),
        ).grid(
            row=0, 
            column=1 if not is_locked else 0, 
            sticky="ew", 
            columnspan=1 if not is_locked else 2, 
            padx=(6, 0) if not is_locked else 0
        )

    def _show_payment_update_modal(self, reservation_code: str) -> None:
        try:
            reservation = self.reservation_controller.get_reservation(reservation_code)
        except (ApplicationError, ValueError) as exc:
            self._set_status(str(exc), tone="danger")
            messagebox.showerror("Update Payment", str(exc))
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Update Payment - {reservation_code}")
        dialog.geometry("500x540")
        dialog.configure(fg_color=self.palette["bg"])
        dialog.transient(self)
        dialog.grab_set()

        shell = ctk.CTkFrame(dialog, fg_color="transparent")
        shell.pack(fill="both", expand=True, padx=14, pady=14)

        card = ctk.CTkFrame(
            shell,
            fg_color=self.palette["surface"],
            corner_radius=20,
            border_width=1,
            border_color=self.palette["line"],
        )
        card.pack(fill="both", expand=True)
        card.grid_columnconfigure(0, weight=1)

        status_var = ctk.StringVar(value=str(reservation.get("payment_status") or "Unpaid"))
        amount_var = ctk.StringVar(value=f"{float(reservation.get('amount_paid') or 0):.2f}")
        method_var = ctk.StringVar(value=str(reservation.get("payment_method") or ""))

        ctk.CTkLabel(
            card,
            text="Update Payment Status",
            text_color=self.palette["text"],
            font=("Segoe UI", 18, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(16, 2))
        ctk.CTkLabel(
            card,
            text=f"{reservation.get('reservation_code')} | {reservation.get('full_name') or 'Guest'}",
            text_color=self.palette["muted"],
            font=("Segoe UI", 11),
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 10))

        ctk.CTkLabel(
            card,
            text="Payment Status",
            text_color=self.palette["text_secondary"],
            font=("Segoe UI", 12, "bold"),
            anchor="w",
        ).grid(row=2, column=0, sticky="w", padx=20, pady=(0, 3))
        def on_status_change(new_status):
            if new_status == "Paid":
                amount_var.set(f"{float(reservation.get('total_price') or 0):.2f}")
            elif new_status in ("Unpaid", "Refunded"):
                amount_var.set("0.00")

        ctk.CTkOptionMenu(
            card,
            values=list(self.reservation_controller.reservation_model.PAYMENT_STATUS_OPTIONS),
            variable=status_var,
            command=on_status_change,
            height=36,
            corner_radius=10,
            fg_color=self.palette["accent"],
            button_color=self.palette["accent_dark"],
            button_hover_color="#41766E",
            text_color=self.palette["text"],
            dropdown_fg_color=self.palette["surface"],
            dropdown_hover_color="#EDF6F3",
            dropdown_text_color=self.palette["text"],
        ).grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 8))

        ctk.CTkLabel(
            card,
            text="Amount Paid",
            text_color=self.palette["text_secondary"],
            font=("Segoe UI", 12, "bold"),
            anchor="w",
        ).grid(row=4, column=0, sticky="w", padx=20, pady=(0, 3))
        ctk.CTkEntry(
            card,
            textvariable=amount_var,
            height=36,
            corner_radius=10,
            border_width=1,
            border_color=self.palette["line"],
            fg_color=self.palette["surface"],
            text_color=self.palette["text"],
        ).grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 8))

        ctk.CTkLabel(
            card,
            text="Payment Method",
            text_color=self.palette["text_secondary"],
            font=("Segoe UI", 12, "bold"),
            anchor="w",
        ).grid(row=6, column=0, sticky="w", padx=20, pady=(0, 3))
        ctk.CTkOptionMenu(
            card,
            values=list(self.reservation_controller.reservation_model.PAYMENT_METHOD_OPTIONS),
            variable=method_var,
            height=36,
            corner_radius=10,
            fg_color=self.palette["accent"],
            button_color=self.palette["accent_dark"],
            button_hover_color="#41766E",
            text_color=self.palette["text"],
            dropdown_fg_color=self.palette["surface"],
            dropdown_hover_color="#EDF6F3",
            dropdown_text_color=self.palette["text"],
        ).grid(row=7, column=0, sticky="ew", padx=20, pady=(0, 8))

        ctk.CTkLabel(
            card,
            text="Payment Notes",
            text_color=self.palette["text_secondary"],
            font=("Segoe UI", 12, "bold"),
            anchor="w",
        ).grid(row=8, column=0, sticky="w", padx=20, pady=(0, 3))
        notes_box = ctk.CTkTextbox(
            card,
            height=70,
            corner_radius=10,
            border_width=1,
            border_color=self.palette["line"],
            fg_color=self.palette["surface"],
            text_color=self.palette["text"],
            font=("Segoe UI", 12),
        )
        notes_box.grid(row=9, column=0, sticky="ew", padx=20, pady=(0, 8))
        notes_box.insert("1.0", str(reservation.get("payment_notes") or ""))

        ctk.CTkLabel(
            card,
            text="Set Paid to auto-fill the full amount. Set Unpaid or Refunded to clear the paid amount.",
            text_color=self.palette["muted"],
            font=("Segoe UI", 10),
            justify="left",
            wraplength=420,
        ).grid(row=10, column=0, sticky="w", padx=20, pady=(0, 10))

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=11, column=0, sticky="ew", padx=20, pady=(0, 16))
        actions.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(
            actions,
            text="Confirm Changes",
            command=lambda: self._save_payment_update(
                dialog,
                reservation_code,
                status_var,
                amount_var,
                method_var,
                notes_box,
            ),
            height=38,
            corner_radius=10,
            fg_color=self.palette["brand"],
            hover_color=self.palette["brand_dark"],
            text_color=self.palette["surface"],
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(
            actions,
            text="Cancel",
            command=dialog.destroy,
            height=38,
            corner_radius=10,
            fg_color=self.palette["surface_alt"],
            hover_color=self.palette["hover"],
            text_color=self.palette["text"],
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def _save_payment_update(
        self,
        dialog,
        reservation_code: str,
        status_var: ctk.StringVar,
        amount_var: ctk.StringVar,
        method_var: ctk.StringVar,
        notes_box: ctk.CTkTextbox,
    ) -> None:
        amount_text = amount_var.get().strip()
        try:
            amount_paid = None if not amount_text else float(amount_text)
        except ValueError:
            messagebox.showerror("Update Payment", "Amount paid must be a valid number.")
            return

        try:
            updated = self.reservation_controller.update_payment_status(
                reservation_code,
                payment_status=status_var.get().strip(),
                amount_paid=amount_paid,
                payment_method=method_var.get().strip() or None,
                payment_notes=notes_box.get("1.0", "end").strip() or None,
                recorded_by=self._current_admin_username(),
            )
        except (ApplicationError, ValueError) as exc:
            self._set_status(str(exc), tone="danger")
            messagebox.showerror("Update Payment", str(exc))
            return

        dialog.destroy()
        self.refresh_dashboard(
            status_message=f"Payment updated for {updated['reservation_code']} ({updated.get('payment_status') or 'Unpaid'})."
        )

    def _render_assets(self, key: str, assets: list[dict]) -> None:
        frame = self.asset_sections.get(key)
        if not frame:
            return
        self._clear_children(frame)
        visible_assets = self._filtered_sorted_assets(key, assets)
        self.filtered_asset_counts[key] = (len(visible_assets), len(assets))
        if key == "destinations":
            cottages_visible, cottages_total = self.filtered_asset_counts.get("cottages", (0, 0))
            boats_visible, boats_total = self.filtered_asset_counts.get("destinations", (0, 0))
            self.asset_filter_summary_var.set(
                f"{self._selected_asset_reference_date().isoformat()}: showing {cottages_visible}/{cottages_total} cottages and "
                f"{boats_visible}/{boats_total} destinations after applying the current filters."
            )

        if not visible_assets:
            ctk.CTkLabel(
                frame,
                text="No assets matched the selected availability filters.",
                text_color=self.palette["muted"],
                font=("Segoe UI", 14),
            ).grid(row=0, column=0, sticky="w", padx=10, pady=10)
            return

        # Table Header
        sort_state = self.asset_sort_state.get(key, {"key": "status", "descending": False})
        headers = ["Asset Code", "Name", "Capacity", "Base Rate", "Status"]

        table_data = [headers]
        for asset in visible_assets:
            table_data.append([
                str(asset["asset_code"]),
                str(asset["name"]),
                f"{asset['capacity']} pax",
                f"PHP {float(asset['base_rate']):,.2f}",
                str(asset["status"]),
            ])

        header_key_map = {
            0: "asset_code", 1: "name", 2: "capacity",
            3: "base_rate", 4: "status",
        }

        def on_asset_table_click(cell_data):
            row_idx = cell_data["row"]
            if row_idx == 0:
                col_idx = cell_data["column"]
                sort_key = header_key_map.get(col_idx)
                if sort_key:
                    self._toggle_asset_sort(key, sort_key)

        table = CTkTable(
            master=frame,
            row=len(table_data),
            column=len(headers),
            values=table_data,
            colors=[self.palette["surface"], "#FAFAFA"],
            header_color=self.palette["surface_alt"],
            hover_color="#EDF6F3",
            text_color=self.palette["text"],
            font=("Segoe UI", 12),
            corner_radius=8,
            padx=4,
            pady=4,
            command=on_asset_table_click,
            wraplength=150,
        )
        table.grid(row=0, column=0, sticky="ew", padx=8, pady=8)

        for col_idx in range(len(headers)):
            table.edit(0, col_idx, font=("Segoe UI", 12, "bold"), text_color=self.palette["text_secondary"])

        for row_idx, asset in enumerate(visible_assets, start=1):
            status = str(asset.get("status") or "Available")
            bg, text = self._status_style(status)
            table.edit(
                row_idx, 4,
                fg_color=bg,
                text_color=text,
                font=("Segoe UI", 12, "bold"),
            )

    def _render_todays_bookings(self, reservations: list[dict]) -> None:
        self._clear_section_content(self.todays_bookings_frame)
        
        today = datetime.now().date()
        todays_reservations = []
        for r in reservations:
            status = r.get("status")
            dt = r.get("departure_time")
            if status == "On Going":
                todays_reservations.append(r)
            elif status == "Reserved" and isinstance(dt, datetime) and dt.date() == today:
                todays_reservations.append(r)
        
        if not todays_reservations:
            ctk.CTkLabel(
                self.todays_bookings_frame,
                text="No bookings scheduled for today.",
                text_color=self.palette["muted"],
                font=("Segoe UI", 14),
            ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 18))
            return

        for row_index, reservation in enumerate(todays_reservations, start=1):
            card = ctk.CTkFrame(self.todays_bookings_frame, fg_color=self.palette["surface"], corner_radius=16, border_width=1, border_color=self.palette["line"])
            card.grid(row=row_index, column=0, sticky="ew", padx=24, pady=(0, 12))
            card.grid_columnconfigure(0, weight=1)

            departure_value = reservation["departure_time"]
            time_text = departure_value.strftime("%I:%M %p")

            ctk.CTkLabel(
                card,
                text=f"Cottage {reservation.get('cottage_code', 'N/A')}",
                text_color=self.palette["accent_dark"],
                font=("Segoe UI", 18, "bold"),
            ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 4))
            
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
            ).grid(row=0, column=1, sticky="e", padx=18, pady=(16, 4))

            details_text = (
                f"Guest: {reservation.get('full_name', 'Unknown')}\n"
                f"Time: {time_text}   |   Pax: {reservation.get('party_size', 'N/A')}\n"
                f"Destinations: {reservation.get('destination', 'N/A')} "
                f"(Destination: {reservation.get('destination_code', 'Unassigned')})"
            )
            
            ctk.CTkLabel(
                card,
                text=details_text,
                text_color=self.palette["text_secondary"],
                font=("Segoe UI", 14),
                justify="left",
                wraplength=700,
            ).grid(row=1, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 16))

    def _summary_stat_card(
        self,
        parent,
        title: str,
        value: str,
        subtitle: str,
        row: int,
        column: int,
        color: str,
        columnspan: int = 1,
        value_font: tuple | None = None,
        subtitle_wraplength: int = 180,
    ) -> None:
        card = ctk.CTkFrame(
            parent,
            fg_color=color,
            corner_radius=22,
            border_width=1,
            border_color=self.palette["line"],
            height=96,
        )
        card.grid(row=row, column=column, columnspan=columnspan, sticky="nsew", padx=8, pady=8)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card,
            text=title,
            text_color=self.palette["muted"],
            font=("Segoe UI", 12, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 2))
        ctk.CTkLabel(
            card,
            text=value,
            text_color=self.palette["text"],
            font=value_font or ("Segoe UI", 21, "bold"),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 1))
        ctk.CTkLabel(
            card,
            text=subtitle,
            text_color=self.palette["text_secondary"],
            font=("Segoe UI", 10),
            justify="left",
            wraplength=subtitle_wraplength,
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))

    def _dashboard_reservation_feed(self, reservations: list[dict], limit: int = 8) -> list[dict]:
        active_statuses = {"Pending", "Confirmed", "Approved", "Reserved", "On Going"}
        now = datetime.now()
        upcoming: list[dict] = []
        past: list[dict] = []

        for reservation in reservations:
            departure_time = reservation.get("departure_time")
            status = str(reservation.get("status") or "")
            if (
                isinstance(departure_time, datetime)
                and departure_time >= now
                and status in active_statuses
            ):
                upcoming.append(reservation)
            else:
                past.append(reservation)

        upcoming.sort(
            key=lambda reservation: (
                reservation.get("departure_time") or datetime.max,
                reservation.get("created_at") or datetime.min,
            )
        )
        past.sort(
            key=lambda reservation: (
                reservation.get("departure_time") or datetime.min,
                reservation.get("created_at") or datetime.min,
            ),
            reverse=True,
        )
        return (upcoming + past)[:limit]

    def _build_guest_rows(self, reservations: list[dict]) -> list[dict]:
        active_statuses = {"Pending", "Confirmed", "Approved", "Reserved", "On Going"}
        now = datetime.now()
        guest_map: dict[str, dict] = {}

        for reservation in reservations:
            full_name = str(reservation.get("full_name") or "Guest").strip() or "Guest"
            contact_number = str(reservation.get("contact_number") or "").strip()
            email = str(reservation.get("email") or "").strip()
            guest_key = (email.lower() or contact_number or full_name.lower())
            row = guest_map.setdefault(
                guest_key,
                {
                    "full_name": full_name,
                    "contact_number": contact_number,
                    "email": email,
                    "bookings": 0,
                    "completed": 0,
                    "upcoming": 0,
                    "total_spent": 0.0,
                    "next_trip": None,
                    "last_activity": None,
                },
            )
            row["bookings"] += 1

            status = str(reservation.get("status") or "")
            departure_time = reservation.get("departure_time")
            created_at = reservation.get("created_at")
            total_price = float(reservation.get("total_price") or 0)

            if status == "Completed":
                row["completed"] += 1
            if status != "Cancelled":
                row["total_spent"] += total_price
            if (
                isinstance(departure_time, datetime)
                and departure_time >= now
                and status in active_statuses
            ):
                row["upcoming"] += 1
                if row["next_trip"] is None or departure_time < row["next_trip"]:
                    row["next_trip"] = departure_time

            activity_markers = [
                value
                for value in (created_at, departure_time)
                if isinstance(value, datetime)
            ]
            for marker in activity_markers:
                if row["last_activity"] is None or marker > row["last_activity"]:
                    row["last_activity"] = marker

        upcoming_rows = [row for row in guest_map.values() if isinstance(row.get("next_trip"), datetime)]
        past_rows = [row for row in guest_map.values() if not isinstance(row.get("next_trip"), datetime)]
        upcoming_rows.sort(key=lambda row: (row["next_trip"], self._natural_sort_key(row["full_name"])))
        past_rows.sort(
            key=lambda row: (
                row.get("last_activity") or datetime.min,
                row["bookings"],
            ),
            reverse=True,
        )
        return upcoming_rows + past_rows

    def _guest_activity_text(self, guest_row: dict) -> str:
        next_trip = guest_row.get("next_trip")
        if isinstance(next_trip, datetime):
            return next_trip.strftime("%b %d, %Y %I:%M %p")
        last_activity = guest_row.get("last_activity")
        if isinstance(last_activity, datetime):
            return last_activity.strftime("%b %d, %Y %I:%M %p")
        return "No activity"

    def _render_guest_dashboard(self, reservations: list[dict]) -> None:
        guest_rows = self._build_guest_rows(reservations)
        total_guests = len(guest_rows)
        repeat_guests = sum(1 for row in guest_rows if row["bookings"] > 1)
        upcoming_guests = sum(1 for row in guest_rows if row["upcoming"] > 0)
        average_spend = (
            sum(row["total_spent"] for row in guest_rows) / total_guests
            if total_guests
            else 0.0
        )

        if self.dashboard_guest_summary_frame is not None:
            self._clear_section_content(self.dashboard_guest_summary_frame)
            cards = ctk.CTkFrame(self.dashboard_guest_summary_frame, fg_color="transparent")
            cards.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
            for column_index in range(4):
                cards.grid_columnconfigure(column_index, weight=1)
            self._summary_stat_card(
                cards,
                "Total Guests",
                str(total_guests),
                "Unique guests with recorded reservations.",
                0,
                0,
                self.palette["surface"],
            )
            self._summary_stat_card(
                cards,
                "Repeat Guests",
                str(repeat_guests),
                "Guests who booked more than once.",
                0,
                1,
                "#EEF5F2",
            )
            self._summary_stat_card(
                cards,
                "Upcoming Guests",
                str(upcoming_guests),
                "Guests with a future or active booking.",
                0,
                2,
                "#F6F1E8",
            )
            self._summary_stat_card(
                cards,
                "Avg Spend / Guest",
                f"PHP {average_spend:,.2f}",
                "Average non-cancelled spend per guest.",
                0,
                3,
                "#F7F4FA",
            )

        if self.dashboard_guest_table_frame is None:
            return

        self._clear_section_content(self.dashboard_guest_table_frame)
        if not guest_rows:
            ctk.CTkLabel(
                self.dashboard_guest_table_frame,
                text="No guest reservation records are available yet.",
                text_color=self.palette["muted"],
                font=("Segoe UI", 14),
            ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 18))
            return

        board = ctk.CTkScrollableFrame(
            self.dashboard_guest_table_frame,
            fg_color="transparent",
            height=380,
        )
        board.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        board.grid_columnconfigure(0, weight=1)

        headers = [
            "Guest", "Contact", "Email", "Bookings",
            "Upcoming", "Completed", "Total Spend", "Next / Last Activity", "Actions",
        ]

        table_data = [headers]
        self._current_guest_list_data = [] # To store guest identity for clicks
        for guest_row in guest_rows:
            self._current_guest_list_data.append({
                "full_name": guest_row["full_name"],
                "contact": guest_row["contact_number"],
                "email": guest_row["email"]
            })
            table_data.append([
                guest_row["full_name"],
                guest_row["contact_number"] or "--",
                guest_row["email"] or "--",
                str(guest_row["bookings"]),
                str(guest_row["upcoming"]),
                str(guest_row["completed"]),
                f"PHP {guest_row['total_spent']:,.2f}",
                self._guest_activity_text(guest_row),
                "Delete",
            ])

        table = CTkTable(
            master=board,
            row=len(table_data),
            column=len(headers),
            values=table_data,
            colors=[self.palette["surface"], "#FAFAFA"],
            header_color=self.palette["surface_alt"],
            hover_color="#EDF6F3",
            text_color=self.palette["text"],
            font=("Segoe UI", 12),
            corner_radius=8,
            padx=4,
            pady=4,
            command=self._on_guest_table_click,
            wraplength=120,
        )
        table.pack(fill="both", expand=True, padx=8, pady=8)

        for col_idx in range(len(headers)):
            table.edit(0, col_idx, font=("Segoe UI", 12, "bold"), text_color=self.palette["text_secondary"])

    def _render_dashboard_bookings(self, reservations: list[dict]) -> None:
        now = datetime.now()
        active_statuses = {"Pending", "Confirmed", "Approved", "Reserved", "On Going"}
        active_count = sum(
            1
            for reservation in reservations
            if str(reservation.get("status") or "") in active_statuses
            and (
                not isinstance(reservation.get("departure_time"), datetime)
                or reservation["departure_time"] >= now
                or reservation.get("status") == "On Going"
            )
        )
        completed_count = sum(
            1 for reservation in reservations if str(reservation.get("status") or "") == "Completed"
        )
        cancelled_count = sum(
            1 for reservation in reservations if str(reservation.get("status") or "") == "Cancelled"
        )
        booked_revenue = sum(
            float(reservation.get("total_price") or 0)
            for reservation in reservations
            if str(reservation.get("status") or "") != "Cancelled"
        )

        if self.dashboard_bookings_summary_frame is not None:
            self._clear_section_content(self.dashboard_bookings_summary_frame)
            cards = ctk.CTkFrame(self.dashboard_bookings_summary_frame, fg_color="transparent")
            cards.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
            for column_index in range(4):
                cards.grid_columnconfigure(column_index, weight=1)
            self._summary_stat_card(
                cards,
                "Upcoming / Active",
                str(active_count),
                "Bookings that still need attention or service.",
                0,
                0,
                self.palette["good"],
            )
            self._summary_stat_card(
                cards,
                "Completed",
                str(completed_count),
                "Bookings that already finished successfully.",
                0,
                1,
                self.palette["surface"],
            )
            self._summary_stat_card(
                cards,
                "Cancelled",
                str(cancelled_count),
                "Bookings that were called off or voided.",
                0,
                2,
                "#F4DBD6",
            )
            self._summary_stat_card(
                cards,
                "Booked Revenue",
                f"PHP {booked_revenue:,.2f}",
                "All non-cancelled booking value in the system.",
                0,
                3,
                "#EEF5F2",
            )

        if self.dashboard_bookings_frame is not None:
            self._render_reservations(
                self.dashboard_bookings_frame,
                self._dashboard_reservation_feed(reservations, limit=8),
                with_actions=False,
            )



    def _build_asset_summary(self, snapshot: dict) -> str:
        cottages = self._count_statuses(snapshot["cottages"])
        boats = self._count_statuses(snapshot["destinations"])
        return (
            "Cottages\n"
            f"Available: {cottages['Available']} | Reserved: {cottages['Reserved']} | On Going: {cottages['On Going']}\n\n"
            "Destinations\n"
            f"Available: {boats['Available']} | Reserved: {boats['Reserved']} | On Going: {boats['On Going']}"
        )

    def _count_statuses(self, assets: list[dict]) -> dict:
        counts = {"Available": 0, "Reserved": 0, "On Going": 0}
        for asset in assets:
            counts[asset["status"]] = counts.get(asset["status"], 0) + 1
        return counts

    def _load_brand_images(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        for candidate in (
            project_root / "images" / "logo.png",
            project_root / "images" / "k3_logo.jpg",
            project_root / "images" / "inspo_preview.png",
            project_root / "images" / "inspo.avif",
            project_root / "logo.png",
            project_root / "k3_logo.jpg",
            project_root / "inspo_preview.png",
            project_root / "inspo.avif",
        ):
            if not candidate.exists():
                continue
            try:
                image = Image.open(candidate)
                # Preserve transparency for PNGs
                if image.mode == 'RGBA':
                    self.logo_image = ctk.CTkImage(light_image=image, size=(48, 48))
                    self.login_logo_image = ctk.CTkImage(light_image=image, size=(144, 144))
                else:
                    image = image.convert("RGB")
                    self.logo_image = ctk.CTkImage(light_image=image, size=(48, 48))
                    self.login_logo_image = ctk.CTkImage(light_image=image, size=(144, 144))
                if self.brand_logo_label is not None:
                    self.brand_logo_label.configure(image=self.logo_image, text="")
                if self.login_logo_label is not None:
                    self.login_logo_label.configure(image=self.login_logo_image, text="")
                return
            except Exception:
                continue

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

    def _dialog_field(self, parent, label: str, variable: ctk.StringVar, row: int, password: bool = False) -> None:
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

    def _connect_database(self, dialog, host: str, port: str, user: str, password: str, database: str) -> None:
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
        self._refresh_cottage_catalog()
        self._refresh_connection_state()
        self.refresh_dashboard(status_message=self.startup_notice)

    def _current_admin_username(self) -> str:
        return getattr(self, "current_user", None) or self.login_settings.username or "admin"

    def _admin_credentials_storage_text(self) -> str:
        if self.data_mode == "mysql":
            return "Live MySQL admin account with .env sync"
        return "Local app credentials from .env"

    def _save_admin_credentials(
        self,
        dialog,
        current_pass_var: ctk.StringVar,
        new_user_var: ctk.StringVar,
        new_pass_var: ctk.StringVar,
        confirm_pass_var: ctk.StringVar,
        message_var: ctk.StringVar,
        message_label,
    ) -> None:
        current_pass = current_pass_var.get()
        if not current_pass:
            message_var.set("Current password is required.")
            message_label.configure(text_color=self.palette["danger"])
            return

        new_user = new_user_var.get().strip()
        new_pass = new_pass_var.get().strip()
        confirm_pass = confirm_pass_var.get().strip()

        if not new_user and not new_pass:
            message_var.set("Enter a new username or a new password first.")
            message_label.configure(text_color=self.palette["danger"])
            return

        if new_pass and new_pass != confirm_pass:
            message_var.set("New passwords do not match.")
            message_label.configure(text_color=self.palette["danger"])
            return

        if new_pass and len(new_pass) < 6:
            message_var.set("Password must be at least 6 characters.")
            message_label.configure(text_color=self.palette["danger"])
            return

        current_username = self._current_admin_username()
        success, message = self.auth_controller.change_credentials(
            current_username,
            current_pass,
            new_user,
            new_pass,
        )
        if not success:
            message_var.set(message)
            message_label.configure(text_color=self.palette["danger"])
            return

        self.current_user = new_user or current_username
        self._refresh_login_settings_state()
        self._refresh_profile_identity()
        self._set_status(message)

        current_pass_var.set("")
        new_user_var.set("")
        new_pass_var.set("")
        confirm_pass_var.set("")
        message_var.set(message)
        message_label.configure(text_color=self.palette["good"])
        self.after(1600, dialog.destroy)

    def _set_status(self, message: str, tone: str = "info") -> None:
        self.status_var.set(message)
        self.status_label.configure(
            text_color={
                "info": self.palette["text"],
                "warning": self.palette["brand_dark"],
                "danger": self.palette["danger"],
            }.get(tone, self.palette["text"])
        )

    def _clear_section_content(self, section) -> None:
        for child in section.winfo_children()[1:]:
            child.destroy()

    def _clear_children(self, widget) -> None:
        for child in widget.winfo_children():
            child.destroy()

    def _toggle_notifications_panel(self) -> None:
        if self.notifications_visible:
            self._hide_notifications_panel()
        else:
            self._show_notifications_panel()

    def _show_notifications_panel(self) -> None:
        if self.notifications_panel is not None:
            return

        self._refresh_notifications_cache()
        self.notifications_panel = ctk.CTkToplevel(self)
        self.notifications_panel.title("Notifications")
        self.notifications_panel.geometry("380x430")
        self.notifications_panel.resizable(False, False)

        main_x = self.winfo_x()
        main_y = self.winfo_y()
        self.notifications_panel.geometry(f"+{main_x + 1060}+{main_y + 60}")
        self.notifications_panel.configure(fg_color=self.palette["surface"])

        ctk.CTkLabel(
            self.notifications_panel,
            text="Recent Notifications",
            text_color=self.palette["text"],
            font=("Segoe UI", 14, "bold"),
        ).pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(
            self.notifications_panel,
            text="New guest bookings appear here automatically.",
            text_color=self.palette["muted"],
            font=("Segoe UI", 11),
        ).pack(fill="x", padx=16, pady=(0, 12))

        scroll_frame = ctk.CTkScrollableFrame(self.notifications_panel, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        if not self.notification_items:
            ctk.CTkLabel(
                scroll_frame,
                text="No notifications yet.",
                text_color=self.palette["muted"],
                font=("Segoe UI", 12),
            ).pack(anchor="w", padx=8, pady=8)
        else:
            for notif in self.notification_items:
                self._create_notification_item(scroll_frame, notif)

        ctk.CTkButton(
            self.notifications_panel,
            text="Close",
            command=self._hide_notifications_panel,
            height=36,
            corner_radius=8,
            fg_color=self.palette["muted"],
            hover_color=self.palette["accent_dark"],
            text_color=self.palette["surface"],
            font=("Segoe UI", 12, "bold"),
        ).pack(fill="x", padx=16, pady=(0, 12))

        self.notifications_visible = True
        self.notifications_panel.protocol("WM_DELETE_WINDOW", self._hide_notifications_panel)
        self._mark_notifications_seen()

    def _create_notification_item(self, parent, notif: dict) -> None:
        """Create a single notification item."""
        item_frame = ctk.CTkFrame(parent, fg_color=self.palette["page"], corner_radius=8, height=80)
        item_frame.pack(fill="x", pady=(0, 8))
        
        # Icon based on notification type
        icon_map = {"new_reservation": "📋", "checkin": "🚪", "maintenance": "🔧", "checkout": "📤"}
        icon = icon_map.get(notif["type"], "📢")
        
        ctk.CTkLabel(
            item_frame,
            text=icon,
            font=("Arial", 16),
        ).pack(side="left", padx=(8, 12), pady=8)
        
        # Notification content
        content_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        content_frame.pack(side="left", fill="both", expand=True, pady=6, padx=(0, 8))
        
        ctk.CTkLabel(
            content_frame,
            text=notif["title"],
            text_color=self.palette["text"],
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            content_frame,
            text=notif["desc"],
            text_color=self.palette["muted"],
            font=("Segoe UI", 10),
            wraplength=240,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))
        ctk.CTkLabel(
            content_frame,
            text=notif.get("time", ""),
            text_color=self.palette["muted"],
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(4, 0))

    def _hide_notifications_panel(self) -> None:
        """Hide and destroy the notifications panel."""
        if self.notifications_panel is not None:
            self.notifications_panel.destroy()
            self.notifications_panel = None
        self.notifications_visible = False

    def _refresh_notifications_cache(self) -> None:
        previous_ids = {item.get("id") for item in self.notification_items}
        try:
            self.notification_items = self.dashboard_controller.get_recent_notifications(limit=8)
        except Exception:
            self.notification_items = []
        current_ids = {item.get("id") for item in self.notification_items}
        self.unread_notifications_count = sum(
            1 for item in self.notification_items if item.get("id") not in self.seen_notification_ids
        )
        self._update_notification_badge()
        if current_ids - previous_ids:
            self._animate_notification_badge()

    def _mark_notifications_seen(self) -> None:
        self.seen_notification_ids.update(
            item.get("id") for item in self.notification_items if item.get("id")
        )
        self.unread_notifications_count = 0
        self._update_notification_badge()

    def _update_notification_badge(self) -> None:
        if not hasattr(self, "notification_badge"):
            return
        if self.unread_notifications_count > 0:
            badge_text = str(min(self.unread_notifications_count, 9))
            if self.unread_notifications_count > 9:
                badge_text = "9+"
            self.notification_badge.configure(text=badge_text)
            self.notification_badge.place(relx=1.0, rely=0.0, x=-2, y=0, anchor="ne")
        else:
            self.notification_badge.place_forget()

    def _poll_notifications(self) -> None:
        if not self.winfo_exists():
            return
        try:
            self._refresh_notifications_cache()
        finally:
            self.after(15000, self._poll_notifications)

    def _show_admin_settings_modal(self) -> None:
        """Display a structured admin login credentials modal."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Admin Login Credentials")
        dialog.geometry("580x580")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=self.palette["surface"])
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        current_pass_var = ctk.StringVar()
        new_user_var = ctk.StringVar()
        new_pass_var = ctk.StringVar()
        confirm_pass_var = ctk.StringVar()
        message_var = ctk.StringVar()
        current_username = self._current_admin_username()

        header = ctk.CTkFrame(dialog, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 8))

        ctk.CTkLabel(
            header,
            text="Admin Login Credentials",
            text_color=self.palette["text"],
            font=("Segoe UI", 18, "bold"),
        ).pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(
            header,
            text="Update the admin username and password used to sign in.",
            text_color=self.palette["muted"],
            font=("Segoe UI", 11),
            justify="left",
            wraplength=520,
        ).pack(fill="x")

        shell = ctk.CTkScrollableFrame(
            dialog,
            fg_color="transparent",
            scrollbar_button_color=self.palette["sage"],
            scrollbar_button_hover_color=self.palette["accent"],
        )
        shell.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 6))
        shell.grid_columnconfigure(0, weight=1)

        info_card = ctk.CTkFrame(
            shell,
            fg_color=self.palette["page"],
            corner_radius=14,
            border_width=1,
            border_color=self.palette["line"],
        )
        info_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        info_card.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(
            info_card,
            text="Current Admin Username",
            text_color=self.palette["muted"],
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 2))
        ctk.CTkLabel(
            info_card,
            text=current_username,
            text_color=self.palette["text"],
            font=("Segoe UI", 15, "bold"),
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 12))
        ctk.CTkLabel(
            info_card,
            text="Credential Storage",
            text_color=self.palette["muted"],
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=1, sticky="w", padx=14, pady=(12, 2))
        ctk.CTkLabel(
            info_card,
            text=self._admin_credentials_storage_text(),
            text_color=self.palette["text"],
            font=("Segoe UI", 11),
            justify="left",
            wraplength=200,
        ).grid(row=1, column=1, sticky="w", padx=14, pady=(0, 12))

        username_card = ctk.CTkFrame(
            shell,
            fg_color=self.palette["surface"],
            corner_radius=14,
            border_width=1,
            border_color=self.palette["line"],
        )
        username_card.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        ctk.CTkLabel(
            username_card,
            text="Username",
            text_color=self.palette["text"],
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w", padx=14, pady=(12, 2))
        ctk.CTkLabel(
            username_card,
            text="Leave blank to keep the current username.",
            text_color=self.palette["muted"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=14, pady=(0, 6))
        ctk.CTkEntry(
            username_card,
            textvariable=new_user_var,
            height=36,
            corner_radius=10,
            border_width=1,
            border_color=self.palette["line"],
            fg_color=self.palette["page"],
            text_color=self.palette["text"],
            font=("Segoe UI", 12),
            placeholder_text=f"Current: {current_username}",
            placeholder_text_color=self.palette["muted"],
        ).pack(fill="x", padx=14, pady=(0, 12))

        password_card = ctk.CTkFrame(
            shell,
            fg_color=self.palette["surface"],
            corner_radius=14,
            border_width=1,
            border_color=self.palette["line"],
        )
        password_card.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        ctk.CTkLabel(
            password_card,
            text="Password",
            text_color=self.palette["text"],
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w", padx=14, pady=(12, 2))
        ctk.CTkLabel(
            password_card,
            text="Current password is required before changes can be saved.",
            text_color=self.palette["muted"],
            font=("Segoe UI", 10),
            justify="left",
            wraplength=480,
        ).pack(anchor="w", padx=14, pady=(0, 6))

        def credential_entry(parent, label: str, variable: ctk.StringVar, placeholder: str, password: bool = False) -> None:
            ctk.CTkLabel(
                parent,
                text=label,
                text_color=self.palette["text"],
                font=("Segoe UI", 11, "bold"),
            ).pack(anchor="w", padx=14, pady=(0, 4))
            
            entry = ctk.CTkEntry(
                parent,
                textvariable=variable,
                height=36,
                corner_radius=10,
                border_width=1,
                border_color=self.palette["line"],
                fg_color=self.palette["page"],
                text_color=self.palette["text"],
                font=("Segoe UI", 12),
                show="*" if password else "",
                placeholder_text=placeholder,
                placeholder_text_color=self.palette["muted"],
            )
            entry.pack(fill="x", padx=14, pady=(0, 10))

            if password:
                def toggle_show():
                    if entry.cget("show") == "*":
                        entry.configure(show="")
                        toggle_btn.configure(text="O")
                    else:
                        entry.configure(show="*")
                        toggle_btn.configure(text="Ø")

                toggle_btn = ctk.CTkButton(
                    entry,
                    text="Ø",
                    width=28,
                    height=28,
                    corner_radius=6,
                    fg_color="transparent",
                    hover_color=self.palette["surface"],
                    text_color=self.palette["muted"],
                    font=("Segoe UI", 14, "bold"),
                    command=toggle_show,
                )
                toggle_btn.place(relx=1.0, rely=0.5, anchor="e", x=-4)

        credential_entry(password_card, "Current Password", current_pass_var, "Enter current admin password", password=True)
        credential_entry(password_card, "New Password", new_pass_var, "Leave blank to keep current password", password=True)
        credential_entry(password_card, "Confirm New Password", confirm_pass_var, "Repeat the new password", password=True)

        spacer = ctk.CTkFrame(shell, fg_color="transparent", height=4)
        spacer.grid(row=3, column=0, sticky="ew")

        footer = ctk.CTkFrame(dialog, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=24, pady=(4, 18))
        message_label = ctk.CTkLabel(
            footer,
            textvariable=message_var,
            text_color=self.palette["good"],
            font=("Segoe UI", 11),
            justify="center",
            wraplength=520,
        )
        message_label.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            footer,
            text="Click Confirm Changes to save the admin credential update.",
            text_color=self.palette["muted"],
            font=("Segoe UI", 11),
            justify="left",
            wraplength=520,
        ).pack(fill="x", pady=(0, 8))

        button_frame = ctk.CTkFrame(footer, fg_color="transparent")
        button_frame.pack(fill="x")
        button_frame.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(
            button_frame,
            text="Confirm Changes",
            command=lambda: self._save_admin_credentials(
                dialog,
                current_pass_var,
                new_user_var,
                new_pass_var,
                confirm_pass_var,
                message_var,
                message_label,
            ),
            height=42,
            corner_radius=12,
            fg_color=self.palette["accent"],
            hover_color=self.palette["accent_dark"],
            text_color=self.palette["surface"],
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=dialog.destroy,
            height=42,
            corner_radius=12,
            fg_color=self.palette["muted"],
            hover_color=self.palette["brand_dark"],
            text_color=self.palette["surface"],
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        dialog.after(50, dialog.lift)

    def _build_operations_page(self) -> None:
        page = self._create_page("operations")
        page.grid_rowconfigure(0, weight=1)
        page.grid_columnconfigure(0, weight=1)

        container = ctk.CTkFrame(page, fg_color="transparent")
        container.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(3, weight=1)

        # ── Header row ──────────────────────────────────────────────
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Reservation Management",
            text_color=self.palette["text"],
            font=("Segoe UI", 26, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Review, approve, and manage all guest bookings",
            text_color=self.palette["muted"],
            font=("Segoe UI", 13),
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        ctk.CTkButton(
            header,
            text="⟳  Refresh",
            command=lambda: self.refresh_dashboard("Operations refreshed."),
            width=120,
            height=38,
            corner_radius=12,
            fg_color=self.palette["brand"],
            hover_color=self.palette["brand_dark"],
            text_color=self.palette["surface"],
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=1, rowspan=2, sticky="e", padx=(8, 0))

        # ── Tab bar ──────────────────────────────────────────────────
        tab_bar = ctk.CTkFrame(
            container,
            fg_color=self.palette["surface_alt"],
            corner_radius=16,
            height=52,
        )
        tab_bar.grid(row=1, column=0, sticky="new", pady=(0, 0))
        tab_bar.grid_propagate(False)
        for col_idx in range(4):
            tab_bar.grid_columnconfigure(col_idx, weight=1)

        self._ops_active_tab = ctk.StringVar(value="pending")
        self._ops_tab_buttons: dict[str, ctk.CTkButton] = {}

        tab_defs = [
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("ongoing", "On Going"),
            ("cancelled", "Cancelled"),
        ]

        for col_idx, (key, label) in enumerate(tab_defs):
            btn = ctk.CTkButton(
                tab_bar,
                text=label,
                height=38,
                corner_radius=12,
                fg_color=self.palette["brand"] if key == "pending" else "transparent",
                hover_color=self.palette["accent"],
                text_color=self.palette["surface"] if key == "pending" else self.palette["muted"],
                font=("Segoe UI", 13, "bold"),
                command=lambda k=key: self._switch_operations_tab(k),
            )
            btn.grid(row=0, column=col_idx, sticky="ew", padx=4, pady=6)
            self._ops_tab_buttons[key] = btn

        # ── Search bar ───────────────────────────────────────────────
        search_row = ctk.CTkFrame(container, fg_color="transparent")
        search_row.grid(row=2, column=0, sticky="ew", pady=(12, 8))
        search_row.grid_columnconfigure(0, weight=1)

        self._ops_search_var = ctk.StringVar()
        ctk.CTkEntry(
            search_row,
            textvariable=self._ops_search_var,
            placeholder_text="Search by reservation code, guest name, cottage, or destination...",
            height=44,
            corner_radius=14,
            border_width=1,
            border_color=self.palette["line"],
            fg_color=self.palette["surface"],
            text_color=self.palette["text"],
            font=("Segoe UI", 12),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            search_row,
            text="Search",
            width=100,
            height=44,
            corner_radius=14,
            fg_color=self.palette["accent"],
            hover_color=self.palette["accent_dark"],
            text_color=self.palette["text"],
            font=("Segoe UI", 12, "bold"),
            command=lambda: self._render_operations_current_tab(),
        ).grid(row=0, column=1, sticky="e")

        # ── Tab content area ─────────────────────────────────────────
        self._ops_content_frame = ctk.CTkFrame(container, fg_color="transparent")
        self._ops_content_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 0))
        self._ops_content_frame.grid_columnconfigure(0, weight=1)
        self._ops_content_frame.grid_rowconfigure(1, weight=1)

        # Keep old reference alive so refresh_dashboard doesn't crash
        self.operations_reservations_frame = None
        self.operations_reservations_table_frame = None

    # ── Operations Tab Methods ───────────────────────────────────────────────
    def _switch_operations_tab(self, tab_key: str) -> None:
        self._ops_active_tab.set(tab_key)
        for key, btn in self._ops_tab_buttons.items():
            if key == tab_key:
                btn.configure(fg_color=self.palette["brand"], text_color=self.palette["surface"])
            else:
                btn.configure(fg_color="transparent", text_color=self.palette["muted"])
        self._render_operations_current_tab()

    def _render_operations_current_tab(self) -> None:
        if not self.last_dashboard_snapshot:
            return
        reservations = self.last_dashboard_snapshot.get("reservations", [])
        tab = self._ops_active_tab.get()

        status_map = {
            "pending": ("Pending",),
            "approved": ("Reserved",),
            "ongoing": ("On Going",),
            "cancelled": ("Cancelled",),
        }
        allowed = status_map.get(tab, ())
        search_text = self._ops_search_var.get().strip().lower() if hasattr(self, "_ops_search_var") else ""

        filtered: list[dict] = []
        for r in reservations:
            if r.get("status") not in allowed:
                continue
            if search_text:
                blob = " ".join([
                    str(r.get("reservation_code") or ""),
                    str(r.get("full_name") or ""),
                    str(r.get("cottage_code") or ""),
                    str(r.get("cottage_name") or ""),
                    str(r.get("destination") or ""),
                    str(r.get("destination_name") or ""),
                ]).lower()
                if search_text not in blob:
                    continue
            filtered.append(r)

        # Sort: newest first
        filtered.sort(
            key=lambda x: x.get("created_at") or datetime.min,
            reverse=True,
        )

        self._render_operations_cards(filtered, tab)

    def _render_operations_cards(self, reservations: list[dict], tab: str) -> None:
        if not hasattr(self, "_ops_content_frame") or self._ops_content_frame is None:
            return
        self._clear_children(self._ops_content_frame)

        # Count badge update
        if self.last_dashboard_snapshot:
            all_res = self.last_dashboard_snapshot.get("reservations", [])
            counts = {"pending": 0, "approved": 0, "ongoing": 0, "cancelled": 0}
            for r in all_res:
                s = r.get("status")
                if s == "Pending":
                    counts["pending"] += 1
                elif s == "Reserved":
                    counts["approved"] += 1
                elif s == "On Going":
                    counts["ongoing"] += 1
                elif s == "Cancelled":
                    counts["cancelled"] += 1
            tab_labels = {
                "pending": "Pending",
                "approved": "Approved",
                "ongoing": "On Going",
                "cancelled": "Cancelled",
            }
            for key, btn in self._ops_tab_buttons.items():
                c = counts.get(key, 0)
                label = tab_labels.get(key, key)
                btn.configure(text=f"{label}  ({c})" if c > 0 else label)

        # Summary
        ctk.CTkLabel(
            self._ops_content_frame,
            text=f"{len(reservations)} reservation{'s' if len(reservations) != 1 else ''} found",
            text_color=self.palette["muted"],
            font=("Segoe UI", 12),
        ).grid(row=0, column=0, sticky="w", padx=4, pady=(8, 8))

        if not reservations:
            empty_card = ctk.CTkFrame(
                self._ops_content_frame,
                fg_color=self.palette["surface"],
                corner_radius=20,
                border_width=1,
                border_color=self.palette["line"],
                height=120,
            )
            empty_card.grid(row=1, column=0, sticky="ew", pady=(0, 8))
            empty_card.grid_propagate(False)
            ctk.CTkLabel(
                empty_card,
                text="No reservations in this category.",
                text_color=self.palette["muted"],
                font=("Segoe UI", 14),
            ).place(relx=0.5, rely=0.5, anchor="center")
            return

        scroll = ctk.CTkScrollableFrame(
            self._ops_content_frame,
            fg_color="transparent",
            height=480,
            scrollbar_button_color=self.palette.get("sage", self.palette["line"]),
            scrollbar_button_hover_color=self.palette["accent"],
        )
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        for idx, reservation in enumerate(reservations):
            self._ops_reservation_card(scroll, reservation, idx, tab)

    def _ops_reservation_card(self, parent, reservation: dict, idx: int, tab: str) -> None:
        departure_value = reservation.get("departure_time")
        departure_text = (
            departure_value.strftime("%b %d, %Y  •  %I:%M %p")
            if isinstance(departure_value, datetime)
            else str(departure_value or "—")
        )
        return_value = reservation.get("return_time")
        return_text = (
            return_value.strftime("%I:%M %p")
            if isinstance(return_value, datetime)
            else str(return_value or "—")
        )
        created_value = reservation.get("created_at")
        created_text = (
            created_value.strftime("%b %d, %Y %I:%M %p")
            if isinstance(created_value, datetime)
            else str(created_value or "—")
        )

        card = ctk.CTkFrame(
            parent,
            fg_color=self.palette["surface"],
            corner_radius=20,
            border_width=1,
            border_color=self.palette["line"],
            height=1,
        )
        card.grid(row=idx, column=0, sticky="ew", pady=(0, 10))
        card.grid_columnconfigure(0, weight=1)

        # ── Row 1: Code + Guest + Status Badge ─────────────────
        top = ctk.CTkFrame(card, fg_color="transparent", height=1)
        top.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        top.grid_columnconfigure(0, weight=1)

        code = str(reservation.get("reservation_code") or "—")
        guest = str(reservation.get("full_name") or "Guest")
        ctk.CTkLabel(
            top,
            text=f"{code}  •  {guest}",
            text_color=self.palette["text"],
            font=("Segoe UI", 15, "bold"),
        ).grid(row=0, column=0, sticky="w")

        status = str(reservation.get("status") or "")
        badge_bg, badge_text = self._status_style(status)
        ctk.CTkLabel(
            top,
            text=status,
            text_color=badge_text,
            fg_color=badge_bg,
            corner_radius=10,
            padx=14,
            pady=5,
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=1, sticky="e")

        # ── Row 2: Details grid ─────────────────────────────────
        details = ctk.CTkFrame(card, fg_color="transparent", height=1)
        details.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 6))
        for c in range(4):
            details.grid_columnconfigure(c, weight=1)

        detail_items = [
            ("Cottage", f"{reservation.get('cottage_code') or ''} • {reservation.get('cottage_name') or '—'}"),
            ("Destination", str(reservation.get("destination") or reservation.get("destination_name") or "—")),
            ("Schedule", f"{departure_text} — {return_text}"),
            ("Pax", str(reservation.get("party_size") or "—")),
        ]
        for col, (label, value) in enumerate(detail_items):
            ctk.CTkLabel(
                details,
                text=label,
                text_color=self.palette["muted"],
                font=("Segoe UI", 10, "bold"),
                anchor="w",
            ).grid(row=0, column=col, sticky="w", padx=(0, 12))
            ctk.CTkLabel(
                details,
                text=value,
                text_color=self.palette["text"],
                font=("Segoe UI", 12),
                anchor="w",
            ).grid(row=1, column=col, sticky="w", padx=(0, 12))

        # ── Row 3: Price + Created + Actions ────────────────────
        bottom_pady = (6, 16) if tab != "cancelled" else (6, 8)
        bottom = ctk.CTkFrame(card, fg_color="transparent", height=1)
        bottom.grid(row=2, column=0, sticky="ew", padx=20, pady=bottom_pady)
        bottom.grid_columnconfigure(0, weight=1)

        total_price = float(reservation.get("total_price") or 0)
        ctk.CTkLabel(
            bottom,
            text=f"₱ {total_price:,.2f}  •  Booked {created_text}",
            text_color=self.palette["muted"],
            font=("Segoe UI", 11),
        ).grid(row=0, column=0, sticky="w")

        if tab != "cancelled":
            actions = ctk.CTkFrame(bottom, fg_color="transparent")
            actions.grid(row=0, column=1, sticky="e")

            if tab == "pending":
                self._mini_button(
                    actions, "Approve", self.palette["brand"], self.palette["surface"],
                    lambda c=code: self._ops_approve(c),
                ).grid(row=0, column=0, padx=(0, 6))
                self._mini_button(
                    actions, "Reject", self.palette["danger"], self.palette["surface"],
                    lambda c=code: self._ops_reject(c),
                ).grid(row=0, column=1)
            elif tab == "approved":
                self._mini_button(
                    actions, "Cancel", self.palette["danger"], self.palette["surface"],
                    lambda c=code: self._ops_cancel(c),
                ).grid(row=0, column=0)
            elif tab == "ongoing":
                self._mini_button(
                    actions, "Complete", self.palette["brand"], self.palette["surface"],
                    lambda c=code: self._ops_complete(c),
                ).grid(row=0, column=0)

    def _ops_approve(self, reservation_code: str) -> None:
        try:
            result = self.reservation_controller.approve_reservation(reservation_code)
            msg = f"{result['reservation_code']} has been approved."
        except ApplicationError as exc:
            self._set_status(str(exc), tone="danger")
            messagebox.showerror("Approval", str(exc))
            return
        self.refresh_dashboard(status_message=msg)
        self._set_status(msg)

    def _ops_reject(self, reservation_code: str) -> None:
        try:
            result = self.reservation_controller.cancel_reservation(reservation_code, "Rejected by admin.")
            msg = f"{result['reservation_code']} has been rejected."
        except ApplicationError as exc:
            self._set_status(str(exc), tone="danger")
            messagebox.showerror("Rejection", str(exc))
            return
        self.refresh_dashboard(status_message=msg)
        self._set_status(msg)

    def _ops_start(self, reservation_code: str) -> None:
        try:
            result = self.reservation_controller.start_trip(reservation_code)
            msg = f"{result['reservation_code']} is now on going."
        except ApplicationError as exc:
            self._set_status(str(exc), tone="danger")
            messagebox.showerror("Start Trip", str(exc))
            return
        self.refresh_dashboard(status_message=msg)
        self._set_status(msg)

    def _ops_cancel(self, reservation_code: str) -> None:
        try:
            result = self.reservation_controller.cancel_reservation(reservation_code, "Cancelled from Operations.")
            msg = f"{result['reservation_code']} has been cancelled."
        except ApplicationError as exc:
            self._set_status(str(exc), tone="danger")
            messagebox.showerror("Cancel", str(exc))
            return
        self.refresh_dashboard(status_message=msg)
        self._set_status(msg)

    def _ops_complete(self, reservation_code: str) -> None:
        try:
            result = self.reservation_controller.complete_trip(reservation_code)
            msg = f"{result['reservation_code']} has been completed."
        except ApplicationError as exc:
            self._set_status(str(exc), tone="danger")
            messagebox.showerror("Complete", str(exc))
            return
        self.refresh_dashboard(status_message=msg)
        self._set_status(msg)

    def _build_payments_page(self) -> None:
        page = self._create_page("payments")
        page.grid_rowconfigure(0, weight=1)
        page.grid_columnconfigure(0, weight=1)

        scroll_frame = ctk.CTkScrollableFrame(
            page,
            fg_color="transparent",
            scrollbar_button_color=self.palette["sage"],
            scrollbar_button_hover_color=self.palette["accent"],
        )
        scroll_frame.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        scroll_frame.grid_columnconfigure(0, weight=1)

        self.payments_summary_frame = self._section_frame(scroll_frame, "Payment Snapshot")
        self.payments_summary_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 16))

        filters = self._section_frame(scroll_frame, "Payment Filters")
        filters.grid(row=1, column=0, sticky="nsew", pady=(0, 16))
        filters.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(
            filters,
            text="Search Reservation / Guest",
            text_color=self.palette["muted"],
            font=("Segoe UI", 12, "bold"),
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 4))
        ctk.CTkEntry(
            filters,
            textvariable=self.payment_search_var,
            height=44,
            corner_radius=14,
            border_width=1,
            border_color=self.palette["line"],
            fg_color=self.palette["surface"],
            text_color=self.palette["text"],
            placeholder_text="Search reservation code, guest, contact, cottage, or method",
        ).grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 12))

        ctk.CTkLabel(
            filters,
            text="Travel Date",
            text_color=self.palette["muted"],
            font=("Segoe UI", 12, "bold"),
        ).grid(row=1, column=1, sticky="w", padx=8, pady=(0, 4))
        DatePickerField(
            filters,
            variable=self.payment_filter_date_var,
            min_date=date_type(2020, 1, 1),
            get_status_map=lambda: {},
            palette={
                "surface": self.palette["surface"],
                "surface_alt": self.palette["surface_alt"],
                "line": self.palette["line"],
                "text": self.palette["text"],
                "muted": self.palette["muted"],
                "brand": self.palette["brand"],
                "brand_dark": self.palette["brand_dark"],
            },
        ).grid(row=2, column=1, sticky="ew", padx=8, pady=(0, 12))

        ctk.CTkLabel(
            filters,
            text="Payment Status",
            text_color=self.palette["muted"],
            font=("Segoe UI", 12, "bold"),
        ).grid(row=1, column=2, sticky="w", padx=24, pady=(0, 4))
        ctk.CTkOptionMenu(
            filters,
            values=["All", "Unpaid", "Partially Paid", "Paid", "Refunded"],
            variable=self.payment_status_filter_var,
            height=42,
            corner_radius=14,
            fg_color=self.palette["accent"],
            button_color=self.palette["accent_dark"],
            button_hover_color="#41766E",
            text_color=self.palette["text"],
            dropdown_fg_color=self.palette["surface"],
            dropdown_hover_color="#EDF6F3",
            dropdown_text_color=self.palette["text"],
        ).grid(row=2, column=2, sticky="ew", padx=24, pady=(0, 12))

        actions = ctk.CTkFrame(filters, fg_color="transparent")
        actions.grid(row=3, column=0, columnspan=3, sticky="ew", padx=24, pady=(0, 12))
        actions.grid_columnconfigure((0, 1), weight=1)
        self._action_button(actions, "Apply Payment Filters", self._apply_payment_filters, self.palette["brand"], self.palette["surface"]).grid(row=0, column=0, padx=(0, 8), sticky="ew")
        self._action_button(actions, "Reset Payment Filters", self._reset_payment_filters, self.palette["surface"], self.palette["text"]).grid(row=0, column=1, padx=(8, 0), sticky="ew")

        ctk.CTkLabel(
            filters,
            textvariable=self.payment_summary_var,
            text_color=self.palette["muted"],
            font=("Segoe UI", 12),
            justify="left",
        ).grid(row=4, column=0, columnspan=3, sticky="w", padx=24, pady=(0, 16))

        # ── Payment Tab bar ──────────────────────────────────────────
        tab_bar = ctk.CTkFrame(
            scroll_frame,
            fg_color=self.palette["surface_alt"],
            corner_radius=16,
            height=52,
        )
        tab_bar.grid(row=2, column=0, sticky="ew", pady=(0, 16))
        tab_bar.grid_propagate(False)
        for col_idx in range(5):
            tab_bar.grid_columnconfigure(col_idx, weight=1)

        self.payment_active_tab = ctk.StringVar(value="Pending")
        self.payment_tab_buttons: dict[str, ctk.CTkButton] = {}

        tab_defs = [
            ("Pending", "Pending"),
            ("Approved", "Approved"),
            ("On Going", "On Going"),
            ("Completed", "Completed"),
            ("Cancelled", "Cancelled"),
        ]

        for col_idx, (key, label) in enumerate(tab_defs):
            btn = ctk.CTkButton(
                tab_bar,
                text=label,
                height=38,
                corner_radius=12,
                fg_color=self.palette["brand"] if key == "Pending" else "transparent",
                hover_color=self.palette["accent"],
                text_color=self.palette["surface"] if key == "Pending" else self.palette["muted"],
                font=("Segoe UI", 13, "bold"),
                command=lambda k=key: self._switch_payment_tab(k),
            )
            btn.grid(row=0, column=col_idx, sticky="ew", padx=4, pady=6)
            self.payment_tab_buttons[key] = btn

        self.payments_records_section = self._section_frame(scroll_frame, "Payment Records")
        self.payments_records_section.grid(row=3, column=0, sticky="nsew", pady=(0, 0))
        self.payments_records_section.grid_rowconfigure(1, weight=1)

        self._payment_content_frame = ctk.CTkFrame(self.payments_records_section, fg_color="transparent")
        self._payment_content_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)
        self._payment_content_frame.grid_columnconfigure(0, weight=1)
        self._payment_content_frame.grid_rowconfigure(0, weight=1)

    def _switch_payment_tab(self, tab_key: str) -> None:
        self.payment_active_tab.set(tab_key)
        for key, btn in self.payment_tab_buttons.items():
            if key == tab_key:
                btn.configure(fg_color=self.palette["brand"], text_color=self.palette["surface"])
            else:
                btn.configure(fg_color="transparent", text_color=self.palette["muted"])
        self.refresh_dashboard()

    def _build_dashboard_page(self) -> None:
        page = self._create_page("dashboard")
        page.grid_rowconfigure(0, weight=1)
        self.nav_buttons = {}
        page.grid_columnconfigure(0, weight=1)

        main_content = ctk.CTkFrame(page, fg_color="transparent")
        main_content.grid(row=0, column=0, sticky="nsew")
        main_content.grid_rowconfigure(0, weight=1)
        main_content.grid_columnconfigure(0, weight=1)

        dashboard_shell = ctk.CTkFrame(main_content, fg_color="transparent")
        dashboard_shell.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        dashboard_shell.grid_rowconfigure(0, weight=1)
        dashboard_shell.grid_columnconfigure(0, weight=0)
        dashboard_shell.grid_columnconfigure(1, weight=1)

        section_sidebar = ctk.CTkFrame(
            dashboard_shell,
            fg_color=self.palette["surface"],
            border_width=1,
            border_color=self.palette["line"],
            width=230,
            corner_radius=24,
        )
        section_sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 16))
        section_sidebar.grid_propagate(False)
        section_sidebar.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(
            section_sidebar,
            text="Dashboard Sections",
            text_color=self.palette["text"],
            font=("Segoe UI", 18, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(20, 4))
        ctk.CTkLabel(
            section_sidebar,
            text="Review records and operational summaries by category.",
            text_color=self.palette["muted"],
            font=("Segoe UI", 12),
            justify="left",
            wraplength=180,
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 14))

        section_nav = ctk.CTkFrame(section_sidebar, fg_color="transparent")
        section_nav.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))

        section_footer = ctk.CTkFrame(section_sidebar, fg_color="transparent")
        section_footer.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 18))
        ctk.CTkFrame(section_footer, fg_color=self.palette["line"], height=1).pack(fill="x", padx=6, pady=(0, 12))
        ctk.CTkButton(
            section_footer,
            text="Logout",
            font=("Segoe UI", 14, "bold"),
            text_color=self.palette["danger"],
            fg_color="transparent",
            hover_color="#FDE8E8",
            corner_radius=14,
            height=44,
            anchor="w",
            command=self._logout,
        ).pack(fill="x")

        content_host = ctk.CTkFrame(dashboard_shell, fg_color="transparent")
        content_host.grid(row=0, column=1, sticky="nsew")
        content_host.grid_rowconfigure(0, weight=1)
        content_host.grid_columnconfigure(0, weight=1)

        self.metric_targets = {}
        self.dashboard_section_buttons = {}
        self.dashboard_section_frames = {}

        def create_section(name: str, title: str, subtitle: str) -> ctk.CTkScrollableFrame:
            button = ctk.CTkButton(
                section_nav,
                text=title,
                font=("Segoe UI", 14, "bold"),
                text_color=self.palette["text_secondary"],
                fg_color="transparent",
                hover_color=self.palette["hover"],
                corner_radius=14,
                height=44,
                anchor="w",
                command=lambda current_name=name: self._show_dashboard_section(current_name),
            )
            button.pack(fill="x", pady=4)
            self.dashboard_section_buttons[name] = button

            frame = ctk.CTkScrollableFrame(
                content_host,
                fg_color="transparent",
                scrollbar_button_color=self.palette["sage"],
                scrollbar_button_hover_color=self.palette["accent"],
            )
            frame.grid(row=0, column=0, sticky="nsew")
            frame.grid_columnconfigure(0, weight=1)
            frame.grid_remove()
            self.dashboard_section_frames[name] = frame
            ctk.CTkLabel(
                frame,
                text=title,
                text_color=self.palette["text"],
                font=("Segoe UI", 26, "bold"),
            ).grid(row=0, column=0, sticky="w", pady=(0, 8))
            ctk.CTkLabel(
                frame,
                text=subtitle,
                text_color=self.palette["muted"],
                font=("Segoe UI", 13),
                justify="left",
                wraplength=980,
            ).grid(row=1, column=0, sticky="w", pady=(0, 18))
            return frame

        overview_scroll = create_section(
            "overview",
            "Overview",
            "Total booking counts, reservation analytics, and the current session board.",
        )
        self.dashboard_overview_summary_frame = self._section_frame(overview_scroll, "Booking Status")
        self.dashboard_overview_summary_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 16))
        self.dashboard_asset_analytics_frame = self._section_frame(overview_scroll, "Reservation Analytics")
        self.dashboard_asset_analytics_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 16))
        ctk.CTkLabel(
            self.dashboard_asset_analytics_frame,
            text="View analytics and insights for your floating cottage reservations.",
            text_color=self.palette["muted"],
            font=("Segoe UI", 13),
            justify="left",
            wraplength=980,
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 16))
        self.dashboard_asset_analytics_summary_frame = ctk.CTkFrame(
            self.dashboard_asset_analytics_frame,
            fg_color="transparent",
        )
        self.dashboard_asset_analytics_summary_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))
        self.dashboard_asset_analytics_summary_frame.grid_columnconfigure(0, weight=1)
        self.dashboard_asset_analytics_chart_frame = ctk.CTkFrame(
            self.dashboard_asset_analytics_frame,
            fg_color="transparent",
        )
        self.dashboard_asset_analytics_chart_frame.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 18))
        self.dashboard_asset_analytics_chart_frame.grid_columnconfigure(0, weight=1)
        self.dashboard_cottage_period_graph_frame = self._section_frame(overview_scroll, "Top Booked Cottages")
        self.dashboard_cottage_period_graph_frame.grid(row=4, column=0, sticky="nsew", pady=(0, 16))
        self.todays_bookings_frame = self._section_frame(overview_scroll, "Today's Bookings")
        self.todays_bookings_frame.grid(row=5, column=0, sticky="nsew", pady=(0, 0))

        assets_scroll = create_section(
            "assets",
            "Assets",
            "Available and reserved cottages and destinations for the selected date.",
        )
        asset_filters = self._section_frame(assets_scroll, "Availability Filters")
        asset_filters.grid(row=2, column=0, sticky="nsew", pady=(0, 16))
        asset_filters.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(asset_filters, text="Selected Date", text_color=self.palette["muted"], font=("Segoe UI", 12, "bold")).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 4))
        DatePickerField(
            asset_filters,
            variable=self.asset_table_date_var,
            min_date=date_type(2020, 1, 1),
            get_status_map=lambda: {},
            palette={
                "surface": self.palette["surface"],
                "surface_alt": self.palette["surface_alt"],
                "line": self.palette["line"],
                "text": self.palette["text"],
                "muted": self.palette["muted"],
                "brand": self.palette["brand"],
                "brand_dark": self.palette["brand_dark"],
            },
        ).grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 12))
        ctk.CTkLabel(asset_filters, text="Availability", text_color=self.palette["muted"], font=("Segoe UI", 12, "bold")).grid(row=1, column=1, sticky="w", padx=8, pady=(0, 4))
        ctk.CTkOptionMenu(
            asset_filters,
            values=["All", "Available", "Reserved", "On Going"],
            variable=self.asset_availability_filter_var,
            height=42,
            corner_radius=14,
            fg_color=self.palette["accent"],
            button_color=self.palette["accent_dark"],
            button_hover_color="#41766E",
            text_color=self.palette["text"],
            dropdown_fg_color=self.palette["surface"],
            dropdown_hover_color="#EDF6F3",
            dropdown_text_color=self.palette["text"],
        ).grid(row=2, column=1, sticky="ew", padx=8, pady=(0, 12))
        ctk.CTkLabel(asset_filters, text="Cottage", text_color=self.palette["muted"], font=("Segoe UI", 12, "bold")).grid(row=1, column=2, sticky="w", padx=8, pady=(0, 4))
        self.asset_cottage_filter_menu = ctk.CTkOptionMenu(
            asset_filters,
            values=list(self.asset_cottage_filter_values),
            variable=self.asset_cottage_filter_var,
            height=42,
            corner_radius=14,
            fg_color=self.palette["accent"],
            button_color=self.palette["accent_dark"],
            button_hover_color="#41766E",
            text_color=self.palette["text"],
            dropdown_fg_color=self.palette["surface"],
            dropdown_hover_color="#EDF6F3",
            dropdown_text_color=self.palette["text"],
        )
        self.asset_cottage_filter_menu.grid(row=2, column=2, sticky="ew", padx=8, pady=(0, 12))
        ctk.CTkLabel(asset_filters, text="Destination", text_color=self.palette["muted"], font=("Segoe UI", 12, "bold")).grid(row=1, column=3, sticky="w", padx=24, pady=(0, 4))
        self.asset_destination_filter_menu = ctk.CTkOptionMenu(
            asset_filters,
            values=list(self.asset_destination_filter_values),
            variable=self.asset_destination_filter_var,
            height=42,
            corner_radius=14,
            fg_color=self.palette["accent"],
            button_color=self.palette["accent_dark"],
            button_hover_color="#41766E",
            text_color=self.palette["text"],
            dropdown_fg_color=self.palette["surface"],
            dropdown_hover_color="#EDF6F3",
            dropdown_text_color=self.palette["text"],
        )
        self.asset_destination_filter_menu.grid(row=2, column=3, sticky="ew", padx=24, pady=(0, 12))
        asset_actions = ctk.CTkFrame(asset_filters, fg_color="transparent")
        asset_actions.grid(row=3, column=0, columnspan=4, sticky="ew", padx=24, pady=(0, 12))
        asset_actions.grid_columnconfigure(0, weight=1)
        asset_actions.grid_columnconfigure(1, weight=1)
        self._action_button(asset_actions, "Apply Asset Filters", self._apply_asset_filters, self.palette["brand"], self.palette["surface"]).grid(row=0, column=0, padx=(0, 8), sticky="ew")
        self._action_button(asset_actions, "Reset Asset Filters", self._reset_asset_filters, self.palette["surface"], self.palette["text"]).grid(row=0, column=1, padx=(8, 0), sticky="ew")
        ctk.CTkLabel(
            asset_filters,
            textvariable=self.asset_filter_summary_var,
            text_color=self.palette["muted"],
            font=("Segoe UI", 12),
            justify="left",
        ).grid(row=4, column=0, columnspan=4, sticky="w", padx=24, pady=(0, 16))

        cottages_section = self._section_frame(assets_scroll, "Floating Cottages")
        cottages_section.grid(row=3, column=0, sticky="nsew", pady=(0, 16))
        cottages_section.grid_columnconfigure(0, weight=1)
        cottages_scroll = ctk.CTkScrollableFrame(cottages_section, fg_color="transparent")
        cottages_scroll.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        cottages_scroll.grid_columnconfigure(0, weight=1)
        self.asset_sections["cottages"] = cottages_scroll

        destinations_section = self._section_frame(assets_scroll, "Destinations Availability")
        destinations_section.grid(row=4, column=0, sticky="nsew", pady=(0, 16))
        destinations_section.grid_columnconfigure(0, weight=1)
        destinations_scroll = ctk.CTkScrollableFrame(destinations_section, fg_color="transparent")
        destinations_scroll.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        destinations_scroll.grid_columnconfigure(0, weight=1)
        self.asset_sections["destinations"] = destinations_scroll

        asset_tab_shell = ctk.CTkFrame(assets_scroll, fg_color="transparent")
        asset_tab_shell.grid(row=5, column=0, sticky="nsew", pady=(0, 0))
        asset_tab_shell.grid_columnconfigure(0, weight=1)
        asset_tab_shell.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            asset_tab_shell,
            text="Review destination analytics while keeping the availability filters above.",
            text_color=self.palette["muted"],
            font=("Segoe UI", 12),
            justify="left",
            wraplength=980,
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))

        asset_tab_nav = ctk.CTkFrame(asset_tab_shell, fg_color="transparent")
        asset_tab_nav.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        asset_tab_host = ctk.CTkFrame(asset_tab_shell, fg_color="transparent")
        asset_tab_host.grid(row=2, column=0, sticky="nsew")
        asset_tab_host.grid_columnconfigure(0, weight=1)
        asset_tab_host.grid_rowconfigure(0, weight=1)

        self.asset_tab_buttons = {}
        self.asset_tab_frames = {}

        def create_asset_tab(name: str, title: str) -> ctk.CTkFrame:
            button = ctk.CTkButton(
                asset_tab_nav,
                text=title,
                font=("Segoe UI", 13, "bold"),
                text_color=self.palette["text_secondary"],
                fg_color="transparent",
                hover_color=self.palette["hover"],
                corner_radius=14,
                height=40,
                anchor="w",
                command=lambda current_name=name: self._show_assets_tab(current_name),
            )
            button.pack(side="left", padx=(0, 8), pady=4)
            self.asset_tab_buttons[name] = button

            frame = ctk.CTkFrame(asset_tab_host, fg_color="transparent")
            frame.grid(row=0, column=0, sticky="nsew")
            frame.grid_columnconfigure(0, weight=1)
            frame.grid_remove()
            self.asset_tab_frames[name] = frame
            return frame

        destinations_tab = create_asset_tab("destinations", "Most Picked Destinations")

        guests_scroll = create_section(
            "guests",
            "Guests",
            "Total users, repeat guests, and recent booking activity.",
        )
        self.dashboard_guest_summary_frame = self._section_frame(guests_scroll, "Guest Snapshot")
        self.dashboard_guest_summary_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 16))
        self.dashboard_guest_table_frame = self._section_frame(guests_scroll, "Guest Records")
        self.dashboard_guest_table_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 0))

        self.dashboard_destination_popularity_card = DestinationPopularityCard(
            destinations_tab,
            palette=self.palette,
            subject_singular="Destination",
            subject_plural="Destinations",
        )
        self.dashboard_destination_popularity_card.grid(row=0, column=0, sticky="nsew", pady=(0, 16))
        
        self.dashboard_destinations_table_frame = self._section_frame(destinations_tab, "Destination Analytics")
        self.dashboard_destinations_table_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 0))

        bookings_scroll = create_section(
            "bookings",
            "Bookings",
            "Nearest reservations and the bookings that still need admin action.",
        )
        self.dashboard_bookings_summary_frame = self._section_frame(bookings_scroll, "Booking Snapshot")
        self.dashboard_bookings_summary_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 16))
        self.dashboard_bookings_frame = self._section_frame(bookings_scroll, "Bookings by Status")
        self.dashboard_bookings_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 0))

        self._show_assets_tab("destinations")
        self._show_dashboard_section("overview")

    def _show_dashboard_section(self, name: str) -> None:
        previous_section = self.dashboard_current_section
        if previous_section == "overview" and name != "overview":
            self._reset_asset_analytics_for_navigation()
        if previous_section == "assets" and name != "assets":
            self._reset_assets_dashboard_navigation()
            
        self.dashboard_current_section = name
        for section_name, frame in self.dashboard_section_frames.items():
            if section_name == name:
                frame.grid()
            else:
                frame.grid_remove()
        self._set_dashboard_section_state(name)
        if self.last_dashboard_snapshot is not None and self.current_page == "dashboard":
            self._render_visible_snapshot(self.last_dashboard_snapshot, replay_animations=True)

    def _set_dashboard_section_state(self, active_section: str) -> None:
        for section_name, button in self.dashboard_section_buttons.items():
            if section_name == active_section:
                button.configure(
                    fg_color=self.palette["hover"],
                    text_color=self.palette["brand"],
                )
            else:
                button.configure(
                    fg_color="transparent",
                    text_color=self.palette["text_secondary"],
                )

    def _show_assets_tab(self, name: str) -> None:
        previous_tab = self.asset_current_tab
        if previous_tab == "destinations" and name != "destinations":
            self._reset_destination_popularity_for_navigation()
        if previous_tab == "cottages" and name != "cottages":
            self._reset_cottage_popularity_for_navigation()

        self.asset_current_tab = name
        for tab_name, frame in self.asset_tab_frames.items():
            if tab_name == name:
                frame.grid()
            else:
                frame.grid_remove()
        self._set_assets_tab_state(name)
        if (
            self.last_dashboard_snapshot is not None
            and self.current_page == "dashboard"
            and self.dashboard_current_section == "assets"
        ):
            self._render_visible_snapshot(self.last_dashboard_snapshot, replay_animations=True)

    def _set_assets_tab_state(self, active_tab: str) -> None:
        for tab_name, button in self.asset_tab_buttons.items():
            if tab_name == active_tab:
                button.configure(
                    fg_color=self.palette["hover"],
                    text_color=self.palette["brand"],
                )
            else:
                button.configure(
                    fg_color="transparent",
                    text_color=self.palette["text_secondary"],
                )

    def _render_overview_dashboard(self, reservations: list[dict]) -> None:
        if self.dashboard_overview_summary_frame is None:
            return

        total_bookings = len(reservations)
        pending_count = sum(1 for reservation in reservations if str(reservation.get("status") or "") == "Pending")
        reserved_count = sum(1 for reservation in reservations if str(reservation.get("status") or "") == "Reserved")
        in_use_count = sum(1 for reservation in reservations if str(reservation.get("status") or "") == "On Going")
        completed_count = sum(1 for reservation in reservations if str(reservation.get("status") or "") == "Completed")
        cancelled_count = sum(1 for reservation in reservations if str(reservation.get("status") or "") == "Cancelled")

        self._clear_section_content(self.dashboard_overview_summary_frame)
        cards = ctk.CTkFrame(self.dashboard_overview_summary_frame, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
        for column_index in range(3):
            cards.grid_columnconfigure(column_index, weight=1)
        self._summary_stat_card(cards, "Total Bookings", str(total_bookings), "All reservations currently stored.", 0, 0, self.palette["surface"])
        self._summary_stat_card(cards, "Pending", str(pending_count), "Bookings awaiting admin approval.", 0, 1, "#FDF5E0")
        self._summary_stat_card(cards, "Reserved", str(reserved_count), "Approved bookings for their scheduled date.", 0, 2, self.palette["status_reserved"])
        self._summary_stat_card(cards, "On Going", str(in_use_count), "Trips that are currently active right now.", 1, 0, self.palette["status_in_use"])
        self._summary_stat_card(cards, "Completed", str(completed_count), "Finished trips and fulfilled bookings.", 1, 1, "#EEF5F2")
        self._summary_stat_card(cards, "Cancelled", str(cancelled_count), "Reservations that were cancelled or voided.", 1, 2, "#F4DBD6")

    def _render_guest_dashboard(self, reservations: list[dict]) -> None:
        guest_rows = self._build_guest_rows(reservations)
        total_guests = len(guest_rows)
        repeat_guests = sum(1 for row in guest_rows if row["bookings"] > 1)
        recent_cutoff = datetime.now() - timedelta(days=7)
        recent_bookings = sum(
            1
            for reservation in reservations
            if isinstance(reservation.get("created_at"), datetime)
            and reservation["created_at"] >= recent_cutoff
        )
        upcoming_guests = sum(1 for row in guest_rows if row["upcoming"] > 0)

        if self.dashboard_guest_summary_frame is not None:
            self._clear_section_content(self.dashboard_guest_summary_frame)
            cards = ctk.CTkFrame(self.dashboard_guest_summary_frame, fg_color="transparent")
            cards.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
            for column_index in range(4):
                cards.grid_columnconfigure(column_index, weight=1)
            self._summary_stat_card(cards, "Total Users", str(total_guests), "Unique guests with at least one reservation.", 0, 0, self.palette["surface"])
            self._summary_stat_card(cards, "Repeat Guests", str(repeat_guests), "Guests who booked more than once.", 0, 1, "#EEF5F2")
            self._summary_stat_card(cards, "Recent Bookings", str(recent_bookings), "Bookings created in the last 7 days.", 0, 2, "#F6F1E8")
            self._summary_stat_card(cards, "Upcoming Guests", str(upcoming_guests), "Guests with a future or active reservation.", 0, 3, "#F7F4FA")

        if self.dashboard_guest_table_frame is None:
            return

        self._clear_section_content(self.dashboard_guest_table_frame)
        if not guest_rows:
            ctk.CTkLabel(
                self.dashboard_guest_table_frame,
                text="No guest reservation records are available yet.",
                text_color=self.palette["muted"],
                font=("Segoe UI", 14),
            ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 18))
            return

        board = ctk.CTkScrollableFrame(self.dashboard_guest_table_frame, fg_color="transparent", height=360)
        board.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        board.grid_columnconfigure(0, weight=1)

        headers = [
            "Guest", "Contact", "Email", "Bookings",
            "Upcoming", "Completed", "Total Spend", "Next / Last Activity", "Actions",
        ]

        table_data = [headers]
        self._current_guest_list_data = guest_rows
        for guest_row in guest_rows:
            table_data.append([
                guest_row["full_name"],
                guest_row["contact_number"] or "--",
                guest_row["email"] or "--",
                str(guest_row["bookings"]),
                str(guest_row["upcoming"]),
                str(guest_row["completed"]),
                f"PHP {guest_row['total_spent']:,.2f}",
                self._guest_activity_text(guest_row),
                "Delete",
            ])

        table = CTkTable(
            master=board,
            row=len(table_data),
            column=len(headers),
            values=table_data,
            colors=[self.palette["surface"], "#FAFAFA"],
            header_color=self.palette["surface_alt"],
            hover_color="#EDF6F3",
            text_color=self.palette["text"],
            font=("Segoe UI", 12),
            corner_radius=8,
            padx=4,
            pady=4,
            command=self._on_guest_table_click,
            wraplength=120,
        )
        table.pack(fill="both", expand=True, padx=8, pady=8)

        for col_idx in range(len(headers)):
            table.edit(0, col_idx, font=("Segoe UI", 12, "bold"), text_color=self.palette["text_secondary"])

    def _build_monthly_reservation_series(self, reservations: list[dict]) -> list[dict]:
        """Build month/value pairs for the chart.

        This currently falls back to sample data when the current year does not
        have reservation rows yet, which keeps the dashboard presentable during
        demos and early setup. Replacing the fallback later with a database query
        is straightforward because the chart only consumes this normalized list.
        """

        month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        current_year = datetime.now().year
        monthly_totals = [0] * 12
        has_live_data = False

        for reservation in reservations:
            departure_time = reservation.get("departure_time")
            status = str(reservation.get("status") or "")
            if (
                isinstance(departure_time, datetime)
                and departure_time.year == current_year
                and status != "Cancelled"
            ):
                monthly_totals[departure_time.month - 1] += 1
                has_live_data = True

        if not has_live_data:
            monthly_totals = [14, 18, 16, 21, 24, 28, 33, 30, 26, 22, 19, 17]

        return [
            {"month": label, "value": total}
            for label, total in zip(month_labels, monthly_totals)
        ]

    def _destroy_asset_analytics_canvas(self) -> None:
        if self.asset_analytics_visibility_job is not None:
            try:
                self.after_cancel(self.asset_analytics_visibility_job)
            except Exception:
                pass
            self.asset_analytics_visibility_job = None
        if self.anim is not None:
            try:
                self.anim.event_source.stop()
            except Exception:
                pass
            self.anim = None
        if self.asset_analytics_canvas is not None:
            try:
                self.asset_analytics_canvas.get_tk_widget().destroy()
            except Exception:
                pass
            self.asset_analytics_canvas = None
        if self.asset_analytics_figure is not None:
            self.asset_analytics_figure.clear()
            self.asset_analytics_figure = None
        self.asset_analytics_chart_card = None
        self.asset_analytics_canvas_host = None

    def _reset_asset_analytics_for_navigation(self) -> None:
        if self.asset_analytics_visibility_job is not None:
            try:
                self.after_cancel(self.asset_analytics_visibility_job)
            except Exception:
                pass
            self.asset_analytics_visibility_job = None
        if self.anim is not None:
            try:
                self.anim.event_source.stop()
            except Exception:
                pass
            self.anim = None

    def _restore_asset_analytics_for_navigation(self) -> None:
        if (
            self.dashboard_current_section != "overview"
            or self.current_page != "dashboard"
            or self.last_dashboard_snapshot is None
        ):
            return
        reservations = self.last_dashboard_snapshot.get("reservations", [])
        self._render_asset_analytics(reservations, animate=True)

    def _reset_destination_popularity_for_navigation(self) -> None:
        if self.dashboard_destination_popularity_card is None:
            return
        self.dashboard_destination_popularity_card.reset_animation()

    def _restore_destination_popularity_for_navigation(self) -> None:
        if (
            self.dashboard_current_section != "assets"
            or self.asset_current_tab != "destinations"
            or self.current_page != "dashboard"
            or self.dashboard_destination_popularity_card is None
        ):
            return
        self.dashboard_destination_popularity_card.replay_animation_when_visible()

    def _reset_cottage_popularity_for_navigation(self) -> None:
        if self.dashboard_cottage_popularity_card is None:
            return
        self.dashboard_cottage_popularity_card.reset_animation()

    def _restore_cottage_popularity_for_navigation(self) -> None:
        if (
            self.dashboard_current_section != "assets"
            or self.asset_current_tab != "cottages"
            or self.current_page != "dashboard"
            or self.dashboard_cottage_popularity_card is None
        ):
            return
        self.dashboard_cottage_popularity_card.replay_animation_when_visible()

    def _reset_assets_dashboard_navigation(self) -> None:
        self._reset_destination_popularity_for_navigation()
        self._reset_cottage_popularity_for_navigation()

    def _restore_assets_dashboard_navigation(self) -> None:
        if self.asset_current_tab == "destinations":
            self._restore_destination_popularity_for_navigation()
        elif self.asset_current_tab == "cottages":
            self._restore_cottage_popularity_for_navigation()

    def _is_widget_visible_in_window(self, widget) -> bool:
        try:
            if widget is None or not widget.winfo_exists() or not widget.winfo_ismapped():
                return False
            widget_height = max(int(widget.winfo_height()), 1)
            widget_top = widget.winfo_rooty()
            widget_bottom = widget_top + widget_height
            window_top = self.winfo_rooty()
            window_bottom = window_top + max(int(self.winfo_height()), 1)
            visible_height = min(widget_bottom, window_bottom) - max(widget_top, window_top)
            minimum_visible = min(max(widget_height * 0.25, 80), widget_height)
            return visible_height >= minimum_visible
        except Exception:
            return False

    def _start_asset_analytics_animation_when_visible(self, widget, starter) -> None:
        if self.asset_analytics_visibility_job is not None:
            try:
                self.after_cancel(self.asset_analytics_visibility_job)
            except Exception:
                pass
            self.asset_analytics_visibility_job = None

        def try_start() -> None:
            if widget is None or not widget.winfo_exists():
                self.asset_analytics_visibility_job = None
                return
            if self._is_widget_visible_in_window(widget):
                self.asset_analytics_visibility_job = None
                starter()
                return
            self.asset_analytics_visibility_job = self.after(120, try_start)

        self.asset_analytics_visibility_job = self.after(80, try_start)

    def _render_asset_analytics(self, reservations: list[dict], animate: bool = False) -> None:
        if (
            self.dashboard_asset_analytics_summary_frame is None
            or self.dashboard_asset_analytics_chart_frame is None
        ):
            return

        series = self._build_monthly_reservation_series(reservations)
        months = [point["month"] for point in series]
        values = [point["value"] for point in series]
        total_reservations = sum(values)
        peak_index = max(range(len(values)), key=lambda index: values[index])
        peak_month = months[peak_index]
        peak_value = values[peak_index]
        monthly_average = total_reservations / len(values) if values else 0

        self._clear_children(self.dashboard_asset_analytics_summary_frame)
        summary_cards = ctk.CTkFrame(
            self.dashboard_asset_analytics_summary_frame,
            fg_color="transparent",
        )
        summary_cards.grid(row=0, column=0, sticky="ew")
        summary_cards.grid_columnconfigure((0, 1, 2), weight=1)
        self._summary_stat_card(
            summary_cards,
            "Total Reservations",
            str(total_reservations),
            "Bookings tracked across January to December.",
            0,
            0,
            "#FCFEFD",
        )
        self._summary_stat_card(
            summary_cards,
            "Peak Month",
            peak_month,
            f"{peak_value} reservations reached the highest point.",
            0,
            1,
            "#F9F5EE",
        )
        self._summary_stat_card(
            summary_cards,
            "Monthly Average",
            f"{monthly_average:.1f}",
            "Average reservations recorded each month.",
            0,
            2,
            "#F6FBF7",
        )

        if self.asset_analytics_visibility_job is not None:
            try:
                self.after_cancel(self.asset_analytics_visibility_job)
            except Exception:
                pass
            self.asset_analytics_visibility_job = None
        if self.anim is not None:
            try:
                self.anim.event_source.stop()
            except Exception:
                pass
            self.anim = None

        chart_card_missing = (
            self.asset_analytics_chart_card is None
            or not self.asset_analytics_chart_card.winfo_exists()
            or self.asset_analytics_canvas_host is None
            or not self.asset_analytics_canvas_host.winfo_exists()
        )
        if chart_card_missing:
            if self.asset_analytics_canvas is not None or self.asset_analytics_figure is not None:
                self._destroy_asset_analytics_canvas()
            self._clear_children(self.dashboard_asset_analytics_chart_frame)
            self.asset_analytics_chart_card = ctk.CTkFrame(
                self.dashboard_asset_analytics_chart_frame,
                fg_color=self.palette["surface"],
                corner_radius=24,
                border_width=1,
                border_color=self.palette["line"],
            )
            self.asset_analytics_chart_card.grid(row=0, column=0, sticky="nsew")
            self.asset_analytics_chart_card.grid_columnconfigure(0, weight=1)
            self.asset_analytics_chart_card.grid_rowconfigure(2, weight=1)
            ctk.CTkLabel(
                self.asset_analytics_chart_card,
                text="Reservations per Month",
                text_color="#005F61",
                font=("Segoe UI", 20, "bold"),
            ).grid(row=0, column=0, sticky="w", padx=24, pady=(20, 4))
            ctk.CTkLabel(
                self.asset_analytics_chart_card,
                text="Monthly booking activity for the current year",
                text_color="#8FA3A6",
                font=("Segoe UI", 12),
            ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 14))

            self.asset_analytics_canvas_host = ctk.CTkFrame(
                self.asset_analytics_chart_card,
                fg_color=self.palette["surface"],
            )
            self.asset_analytics_canvas_host.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))
            self.asset_analytics_canvas_host.grid_columnconfigure(0, weight=1)
            self.asset_analytics_canvas_host.grid_rowconfigure(0, weight=1)

        width = max(
            int(self.asset_analytics_canvas_host.winfo_width()) if self.asset_analytics_canvas_host is not None else 0,
            840,
        )
        height = max(
            int(self.asset_analytics_canvas_host.winfo_height()) if self.asset_analytics_canvas_host is not None else 0,
            360,
        )

        if self.asset_analytics_figure is None:
            self.asset_analytics_figure = Figure(
                figsize=(width / 100, height / 100),
                dpi=100,
                facecolor=self.palette["surface"],
            )
        else:
            self.asset_analytics_figure.clear()
            self.asset_analytics_figure.set_size_inches(width / 100, height / 100, forward=True)

        if self.asset_analytics_canvas is None and self.asset_analytics_canvas_host is not None:
            self.asset_analytics_canvas = FigureCanvasTkAgg(
                self.asset_analytics_figure,
                master=self.asset_analytics_canvas_host,
            )
            self.asset_analytics_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        figure = self.asset_analytics_figure
        axis = figure.add_subplot(111)
        axis.set_facecolor(self.palette["surface"])

        x_values = list(range(len(months)))
        line_color = "#7ED6D1"
        baseline_values = [0] * len(values)
        max_value = max(values) if values else 0
        line, = axis.plot(
            x_values,
            baseline_values,
            color=line_color,
            linewidth=3,
            marker="o",
            markersize=7,
            markerfacecolor=self.palette["surface"],
            markeredgecolor=line_color,
            markeredgewidth=2,
            zorder=3,
        )
        fill = axis.fill_between(x_values, baseline_values, color=line_color, alpha=0.18, zorder=1)
        peak_marker = axis.scatter(
            [peak_index],
            [peak_value],
            s=95,
            color="#E9A09A",
            edgecolor=self.palette["surface"],
            linewidth=1.8,
            zorder=4,
            visible=False,
        )
        peak_annotation = axis.annotate(
            f"{peak_month}: {peak_value}",
            (peak_index, peak_value),
            xytext=(0, 18),
            textcoords="offset points",
            ha="center",
            color="#005F61",
            fontsize=10,
            fontweight="bold",
            bbox={
                "boxstyle": "round,pad=0.35",
                "facecolor": "#FFF7F6",
                "edgecolor": "#E5DDD6",
                "linewidth": 1,
            },
            zorder=5,
        )
        peak_annotation.set_visible(False)

        axis.set_xticks(x_values)
        axis.set_xticklabels(months, color="#8FA3A6", fontsize=10)
        axis.tick_params(axis="y", colors="#8FA3A6", labelsize=10)
        axis.yaxis.set_major_locator(MaxNLocator(integer=True))
        axis.grid(axis="y", color="#E5DDD6", linewidth=0.9, alpha=0.9)
        axis.grid(axis="x", visible=False)
        axis.set_ylabel("Reservations", color="#005F61", fontsize=11, labelpad=10)
        axis.set_xlabel("Month", color="#005F61", fontsize=11, labelpad=10)

        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        axis.spines["left"].set_color("#E5DDD6")
        axis.spines["bottom"].set_color("#E5DDD6")
        axis.margins(x=0.03)
        axis.set_ylim(0, max(max_value * 1.2, 1))
        figure.tight_layout(pad=2.0)

        self.asset_analytics_canvas.draw()

        frame_count = 90

        def update(frame_index: int):
            nonlocal fill
            progress = frame_index / (frame_count - 1)
            eased_progress = 1 - ((1 - progress) ** 3)
            animated_values = [value * eased_progress for value in values]
            line.set_ydata(animated_values)

            try:
                fill.remove()
            except Exception:
                pass
            fill = axis.fill_between(x_values, animated_values, color=line_color, alpha=0.18, zorder=1)

            is_final_frame = frame_index >= frame_count - 1
            peak_marker.set_visible(is_final_frame)
            peak_annotation.set_visible(is_final_frame)
            return line, fill, peak_marker, peak_annotation

        self.asset_analytics_canvas.draw_idle()
        canvas_widget = self.asset_analytics_canvas.get_tk_widget()

        def start_animation() -> None:
            if self.anim is not None:
                try:
                    self.anim.event_source.stop()
                except Exception:
                    pass
            self.anim = FuncAnimation(
                figure,
                update,
                frames=frame_count,
                interval=16,
                blit=False,
                repeat=False,
            )
            self.asset_analytics_canvas.draw_idle()

        if not animate:
            update(frame_count - 1)
            self.asset_analytics_canvas.draw_idle()
            return

        self._start_asset_analytics_animation_when_visible(canvas_widget, start_animation)

    def _build_destination_rows(self, reservations: list[dict], assets: list[dict]) -> list[dict]:
        now = datetime.now()
        active_statuses = {"Pending", "Confirmed", "Approved", "Reserved", "On Going"}
        known_destinations = {
            str(asset.get("name") or "").strip()
            for asset in assets
            if str(asset.get("name") or "").strip()
        }
        rows: dict[str, dict] = {
            str(asset.get("name") or ""): {
                "name": str(asset.get("name") or ""),
                "total_bookings": 0,
                "upcoming_bookings": 0,
                "guest_load": 0,
                "next_trip": None,
            }
            for asset in assets
            if asset.get("name")
        }

        for reservation in reservations:
            destination_names = self._reservation_destination_names(reservation, known_destinations)
            if not destination_names:
                continue
            departure_time = reservation.get("departure_time")
            status = str(reservation.get("status") or "")
            party_size = int(reservation.get("party_size") or 0)
            is_upcoming = (
                isinstance(departure_time, datetime)
                and departure_time >= now
                and status in active_statuses
            )

            for destination_name in destination_names:
                row = rows.setdefault(
                    destination_name,
                    {
                        "name": destination_name,
                        "total_bookings": 0,
                        "upcoming_bookings": 0,
                        "guest_load": 0,
                        "next_trip": None,
                    },
                )
                row["total_bookings"] += 1
                if is_upcoming:
                    row["upcoming_bookings"] += 1
                    row["guest_load"] += party_size
                    if row["next_trip"] is None or departure_time < row["next_trip"]:
                        row["next_trip"] = departure_time

        return sorted(
            rows.values(),
            key=lambda row: (
                -row["total_bookings"],
                -row["upcoming_bookings"],
                row["next_trip"] or datetime.max,
                self._natural_sort_key(row["name"]),
            ),
        )

    def _asset_booking_label(self, code: str | None, name: str | None, fallback: str) -> str:
        code_value = str(code or "").strip()
        name_value = str(name or "").strip()
        if code_value and name_value:
            return f"{code_value} | {name_value}"
        if name_value:
            return name_value
        if code_value:
            return code_value
        return fallback

    def _reservation_destination_names(
        self,
        reservation: dict,
        known_destinations: set[str] | None = None,
    ) -> list[str]:
        raw_destination = str(reservation.get("destination") or "").strip()
        if not raw_destination:
            return []
        if known_destinations and raw_destination in known_destinations:
            return [raw_destination]

        destination_names = [
            part.strip()
            for part in re.split(r"\s*,\s*", raw_destination)
            if part.strip()
        ]
        if known_destinations:
            matched_names = [name for name in destination_names if name in known_destinations]
            if matched_names:
                destination_names = matched_names

        unique_names = list(dict.fromkeys(destination_names))
        return unique_names or [raw_destination]

    def _build_cottage_rows(self, reservations: list[dict], assets: list[dict]) -> list[dict]:
        now = datetime.now()
        active_statuses = {"Pending", "Confirmed", "Approved", "Reserved", "On Going"}
        rows: dict[str, dict] = {}

        for asset in assets:
            label = self._asset_booking_label(
                asset.get("asset_code"),
                asset.get("name"),
                "Floating Cottage",
            )
            rows[label] = {
                "name": label,
                "total_bookings": 0,
                "upcoming_bookings": 0,
                "guest_load": 0,
                "next_trip": None,
            }

        for reservation in reservations:
            label = self._asset_booking_label(
                reservation.get("cottage_code"),
                reservation.get("cottage_name"),
                "Floating Cottage",
            )
            row = rows.setdefault(
                label,
                {
                    "name": label,
                    "total_bookings": 0,
                    "upcoming_bookings": 0,
                    "guest_load": 0,
                    "next_trip": None,
                },
            )
            row["total_bookings"] += 1
            departure_time = reservation.get("departure_time")
            status = str(reservation.get("status") or "")
            if (
                isinstance(departure_time, datetime)
                and departure_time >= now
                and status in active_statuses
            ):
                row["upcoming_bookings"] += 1
                row["guest_load"] += int(reservation.get("party_size") or 0)
                if row["next_trip"] is None or departure_time < row["next_trip"]:
                    row["next_trip"] = departure_time

        return sorted(
            rows.values(),
            key=lambda row: (
                -row["total_bookings"],
                -row["upcoming_bookings"],
                row["next_trip"] or datetime.max,
                self._natural_sort_key(row["name"]),
            ),
        )

    def _destination_activity_text(self, row: dict) -> str:
        if isinstance(row.get("next_trip"), datetime):
            return row["next_trip"].strftime("%b %d, %Y %I:%M %p")
        return "No upcoming trip"

    def _render_destination_dashboard(
        self,
        reservations: list[dict],
        assets: list[dict],
        animate: bool = False,
    ) -> None:
        rows = self._build_destination_rows(reservations, assets)
        if self.dashboard_destination_popularity_card is not None:
            popularity_data = {
                row_data["name"]: int(row_data.get("total_bookings") or 0)
                for row_data in rows
                if row_data.get("name")
            }
            self.dashboard_destination_popularity_card.set_data(popularity_data, animate=animate)

        if self.dashboard_destinations_table_frame is None:
            return

        self._clear_section_content(self.dashboard_destinations_table_frame)
        if not rows:
            ctk.CTkLabel(
                self.dashboard_destinations_table_frame,
                text="No destination booking records are available yet.",
                text_color=self.palette["muted"],
                font=("Segoe UI", 14),
            ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 18))
            return

        board = ctk.CTkScrollableFrame(self.dashboard_destinations_table_frame, fg_color="transparent", height=360)
        board.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        board.grid_columnconfigure(0, weight=1)

        headers = ["Destination", "Total Bookings", "Upcoming Trips", "Guest Load", "Next Trip"]

        table_data = [headers]
        for row_data in rows:
            table_data.append([
                row_data["name"],
                str(row_data["total_bookings"]),
                str(row_data["upcoming_bookings"]),
                str(row_data["guest_load"]),
                self._destination_activity_text(row_data),
            ])

        table = CTkTable(
            master=board,
            row=len(table_data),
            column=len(headers),
            values=table_data,
            colors=[self.palette["surface"], "#FAFAFA"],
            header_color=self.palette["surface_alt"],
            hover_color="#EDF6F3",
            text_color=self.palette["text"],
            font=("Segoe UI", 12),
            corner_radius=8,
            padx=4,
            pady=4,
            wraplength=140,
        )
        table.pack(fill="both", expand=True, padx=8, pady=8)

        for col_idx in range(len(headers)):
            table.edit(0, col_idx, font=("Segoe UI", 12, "bold"), text_color=self.palette["text_secondary"])

    def _render_cottage_dashboard(
        self,
        reservations: list[dict],
        assets: list[dict],
        animate: bool = False,
    ) -> None:
        rows = self._build_cottage_rows(reservations, assets)
        if self.dashboard_cottage_popularity_card is not None:
            popularity_data = {
                row_data["name"]: int(row_data.get("total_bookings") or 0)
                for row_data in rows
                if row_data.get("name")
            }
            self.dashboard_cottage_popularity_card.set_data(popularity_data, animate=animate)

        if self.dashboard_cottages_table_frame is None:
            return

        self._clear_section_content(self.dashboard_cottages_table_frame)
        if not rows:
            ctk.CTkLabel(
                self.dashboard_cottages_table_frame,
                text="No floating cottage booking records are available yet.",
                text_color=self.palette["muted"],
                font=("Segoe UI", 14),
            ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 18))
            return

        board = ctk.CTkScrollableFrame(self.dashboard_cottages_table_frame, fg_color="transparent", height=360)
        board.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        board.grid_columnconfigure(0, weight=1)

        headers = ["Floating Cottage", "Total Bookings", "Upcoming Trips", "Guest Load", "Next Trip"]

        table_data = [headers]
        for row_data in rows:
            table_data.append([
                row_data["name"],
                str(row_data["total_bookings"]),
                str(row_data["upcoming_bookings"]),
                str(row_data["guest_load"]),
                self._destination_activity_text(row_data),
            ])

        table = CTkTable(
            master=board,
            row=len(table_data),
            column=len(headers),
            values=table_data,
            colors=[self.palette["surface"], "#FAFAFA"],
            header_color=self.palette["surface_alt"],
            hover_color="#EDF6F3",
            text_color=self.palette["text"],
            font=("Segoe UI", 12),
            corner_radius=8,
            padx=4,
            pady=4,
            wraplength=140,
        )
        table.pack(fill="both", expand=True, padx=8, pady=8)

        for col_idx in range(len(headers)):
            table.edit(0, col_idx, font=("Segoe UI", 12, "bold"), text_color=self.palette["text_secondary"])

    def _top_cottage_from_counts(self, counts: dict[str, int]) -> tuple[str, int]:
        if not counts:
            return "--", 0
        return sorted(
            counts.items(),
            key=lambda item: (-item[1], self._natural_sort_key(item[0])),
        )[0]

    def _build_cottage_leader_rows(self, reservations: list[dict], assets: list[dict]) -> dict:
        month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        now = datetime.now()
        valid_statuses = {"Pending", "Confirmed", "Approved", "Reserved", "On Going", "Completed"}
        cottage_labels = {
            int(asset.get("id")): self._asset_booking_label(
                asset.get("asset_code"),
                asset.get("name"),
                "Floating Cottage",
            )
            for asset in assets
            if asset.get("id") is not None
        }
        month_counts: dict[tuple[int, int], dict[str, int]] = {}
        week_counts: dict[tuple[int, int], dict[str, int]] = {}
        year_counts: dict[int, dict[str, int]] = {}
        all_cottage_totals: dict[str, dict[str, int]] = {
            label: {"current_month": 0, "current_year": 0, "all_time": 0}
            for label in cottage_labels.values()
        }

        for reservation in reservations:
            departure_time = reservation.get("departure_time")
            status = str(reservation.get("status") or "")
            if not isinstance(departure_time, datetime) or status not in valid_statuses:
                continue

            cottage_id = reservation.get("cottage_id")
            try:
                cottage_id = int(cottage_id) if cottage_id is not None else None
            except (TypeError, ValueError):
                cottage_id = None
            label = cottage_labels.get(cottage_id) or self._asset_booking_label(
                reservation.get("cottage_code"),
                reservation.get("cottage_name"),
                "Floating Cottage",
            )

            month_key = (departure_time.year, departure_time.month)
            month_counts.setdefault(month_key, {})
            month_counts[month_key][label] = month_counts[month_key].get(label, 0) + 1

            iso_year, iso_week, _ = departure_time.isocalendar()
            week_key = (iso_year, iso_week)
            week_counts.setdefault(week_key, {})
            week_counts[week_key][label] = week_counts[week_key].get(label, 0) + 1

            year_counts.setdefault(departure_time.year, {})
            year_counts[departure_time.year][label] = year_counts[departure_time.year].get(label, 0) + 1

            totals = all_cottage_totals.setdefault(
                label,
                {"current_month": 0, "current_year": 0, "all_time": 0},
            )
            totals["all_time"] += 1
            if departure_time.year == now.year:
                totals["current_year"] += 1
                if departure_time.month == now.month:
                    totals["current_month"] += 1

        monthly_rows = []
        for month_number, month_label in enumerate(month_labels, start=1):
            counts = month_counts.get((now.year, month_number), {})
            top_cottage, booking_count = self._top_cottage_from_counts(counts)
            monthly_rows.append(
                {
                    "period": f"{month_label} {now.year}",
                    "top_cottage": top_cottage,
                    "booking_count": booking_count,
                    "total_bookings": sum(counts.values()),
                }
            )

        current_iso_year, current_iso_week, _ = now.isocalendar()
        weekly_rows = []
        for week_number in range(1, current_iso_week + 1):
            counts = week_counts.get((current_iso_year, week_number), {})
            top_cottage, booking_count = self._top_cottage_from_counts(counts)
            weekly_rows.append(
                {
                    "period": f"Week {week_number}, {current_iso_year}",
                    "top_cottage": top_cottage,
                    "booking_count": booking_count,
                    "total_bookings": sum(counts.values()),
                }
            )

        yearly_rows = []
        for year in sorted(year_counts, reverse=True):
            counts = year_counts[year]
            top_cottage, booking_count = self._top_cottage_from_counts(counts)
            yearly_rows.append(
                {
                    "period": str(year),
                    "top_cottage": top_cottage,
                    "booking_count": booking_count,
                    "total_bookings": sum(counts.values()),
            }
        )

        current_week_counts = week_counts.get((current_iso_year, current_iso_week), {})
        current_month_counts = month_counts.get((now.year, now.month), {})
        current_year_counts = year_counts.get(now.year, {})
        current_week_top = self._top_cottage_from_counts(current_week_counts)
        current_month_top = self._top_cottage_from_counts(current_month_counts)
        current_year_top = self._top_cottage_from_counts(current_year_counts)
        all_time_top = self._top_cottage_from_counts(
            {
                cottage: sum(counts.get(cottage, 0) for counts in year_counts.values())
                for counts in year_counts.values()
                for cottage in counts
            }
        )

        all_cottage_rows = []
        for rank, (cottage_name, totals) in enumerate(
            sorted(
                all_cottage_totals.items(),
                key=lambda item: (
                    -item[1]["all_time"],
                    -item[1]["current_year"],
                    -item[1]["current_month"],
                    self._natural_sort_key(item[0]),
                ),
            ),
            start=1,
        ):
            all_cottage_rows.append(
                {
                    "rank": rank,
                    "cottage": cottage_name,
                    "current_month": totals["current_month"],
                    "current_year": totals["current_year"],
                    "all_time": totals["all_time"],
                }
            )

        return {
            "all_cottage_rows": all_cottage_rows,
            "weekly_rows": weekly_rows,
            "monthly_rows": monthly_rows,
            "yearly_rows": yearly_rows,
            "current_week_top": current_week_top,
            "current_month_top": current_month_top,
            "current_year_top": current_year_top,
            "all_time_top": all_time_top,
            "period_graph_rows": [
                {
                    "period": "This Week",
                    "top_cottage": current_week_top[0],
                    "booking_count": current_week_top[1],
                    "total_bookings": sum(current_week_counts.values()),
                },
                {
                    "period": "This Month",
                    "top_cottage": current_month_top[0],
                    "booking_count": current_month_top[1],
                    "total_bookings": sum(current_month_counts.values()),
                },
                {
                    "period": "This Year",
                    "top_cottage": current_year_top[0],
                    "booking_count": current_year_top[1],
                    "total_bookings": sum(current_year_counts.values()),
                },
            ],
            "total_bookings": sum(sum(counts.values()) for counts in year_counts.values()),
        }

    def _render_cottage_leader_table(self, parent, rows: list[dict], empty_message: str) -> None:
        self._clear_section_content(parent)
        if not rows:
            ctk.CTkLabel(
                parent,
                text=empty_message,
                text_color=self.palette["muted"],
                font=("Segoe UI", 14),
            ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 18))
            return

        board = ctk.CTkScrollableFrame(parent, fg_color="transparent", height=360)
        board.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        board.grid_columnconfigure(0, weight=1)

        headers = ["Period", "Top Cottage", "Winning Bookings", "Total Bookings"]
        table_data = [headers]
        for row_data in rows:
            table_data.append([
                row_data["period"],
                row_data["top_cottage"],
                str(row_data["booking_count"]),
                str(row_data["total_bookings"]),
            ])

        table = CTkTable(
            master=board,
            row=len(table_data),
            column=len(headers),
            values=table_data,
            colors=[self.palette["surface"], "#FAFAFA"],
            header_color=self.palette["surface_alt"],
            hover_color="#EDF6F3",
            text_color=self.palette["text"],
            font=("Segoe UI", 12),
            corner_radius=8,
            padx=4,
            pady=4,
            wraplength=160,
        )
        table.pack(fill="both", expand=True, padx=8, pady=8)

        for col_idx in range(len(headers)):
            table.edit(0, col_idx, font=("Segoe UI", 12, "bold"), text_color=self.palette["text_secondary"])

    def _render_all_cottages_performance_table(self, parent, rows: list[dict]) -> None:
        self._clear_section_content(parent)
        if not rows:
            ctk.CTkLabel(
                parent,
                text="No cottage assets are available yet.",
                text_color=self.palette["muted"],
                font=("Segoe UI", 14),
            ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 18))
            return

        board = ctk.CTkScrollableFrame(parent, fg_color="transparent", height=360)
        board.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        board.grid_columnconfigure(0, weight=1)

        headers = ["Rank", "Floating Cottage", "This Month", "This Year", "All-Time"]
        table_data = [headers]
        for row_data in rows:
            table_data.append([
                str(row_data["rank"]),
                row_data["cottage"],
                str(row_data["current_month"]),
                str(row_data["current_year"]),
                str(row_data["all_time"]),
            ])

        table = CTkTable(
            master=board,
            row=len(table_data),
            column=len(headers),
            values=table_data,
            colors=[self.palette["surface"], "#FAFAFA"],
            header_color=self.palette["surface_alt"],
            hover_color="#EDF6F3",
            text_color=self.palette["text"],
            font=("Segoe UI", 12),
            corner_radius=8,
            padx=4,
            pady=4,
            wraplength=150,
        )
        table.pack(fill="both", expand=True, padx=8, pady=8)

        for col_idx in range(len(headers)):
            table.edit(0, col_idx, font=("Segoe UI", 12, "bold"), text_color=self.palette["text_secondary"])

    def _render_cottage_period_graph(self, parent, leader_data: dict) -> None:
        if self.cottage_leader_anim is not None:
            try:
                self.cottage_leader_anim.event_source.stop()
            except Exception:
                pass
            self.cottage_leader_anim = None
        self._clear_section_content(parent)

        graph_shell = ctk.CTkFrame(
            parent,
            fg_color=self.palette["surface"],
            corner_radius=24,
            border_width=1,
            border_color=self.palette["line"],
        )
        graph_shell.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        graph_shell.grid_columnconfigure(0, weight=1)
        graph_shell.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            graph_shell,
            text="Most Booked Floating Cottage",
            text_color=self.palette["text"],
            font=("Segoe UI", 20, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(18, 4))
        ctk.CTkLabel(
            graph_shell,
            text="Weekly, monthly, and yearly leaders based on non-cancelled reservations.",
            text_color=self.palette["muted"],
            font=("Segoe UI", 12),
        ).grid(row=1, column=0, sticky="w", padx=22, pady=(0, 12))

        chart_host = ctk.CTkFrame(graph_shell, fg_color=self.palette["surface"], height=560)
        chart_host.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        chart_host.grid_columnconfigure(0, weight=1)
        chart_host.grid_rowconfigure(0, weight=1)

        chart_groups = [
            ("Weekly Leaders", leader_data.get("weekly_rows", []), "#7ED6D1", 8),
            ("Monthly Leaders", leader_data.get("monthly_rows", []), "#E9A09A", 12),
            ("Yearly Leaders", leader_data.get("yearly_rows", []), "#AFC7A3", 8),
        ]

        figure = Figure(figsize=(10, 8.4), dpi=100, facecolor=self.palette["surface"])
        axes = figure.subplots(len(chart_groups), 1)
        if len(chart_groups) == 1:
            axes = [axes]

        animated_items = []
        for axis, (title, rows, color, limit) in zip(axes, chart_groups):
            plotted_rows = [
                row
                for row in rows
                if int(row.get("booking_count") or 0) > 0
            ]
            plotted_rows = plotted_rows[-limit:] if title != "Yearly Leaders" else plotted_rows[:limit]
            if not plotted_rows:
                plotted_rows = list(rows[:1]) or [{"period": "--", "top_cottage": "--", "booking_count": 0}]

            labels = [str(row.get("period") or "--") for row in plotted_rows]
            values = [int(row.get("booking_count") or 0) for row in plotted_rows]
            winners = [str(row.get("top_cottage") or "--") for row in plotted_rows]
            y_positions = list(range(len(labels)))
            max_value = max(max(values or [0]), 1)

            axis.set_facecolor(self.palette["surface"])
            bars = axis.barh(y_positions, [0] * len(values), color=color, height=0.56, zorder=3)
            value_labels = []
            for y_position, winner, value in zip(y_positions, winners, values):
                label = winner if len(winner) <= 34 else f"{winner[:31]}..."
                value_label = axis.text(
                    max_value * 0.03,
                    y_position,
                    f"{label}  |  0",
                    va="center",
                    ha="left",
                    color=self.palette["text"],
                    fontsize=8.5,
                    fontweight="bold",
                    zorder=4,
                )
                value_labels.append((value_label, label, value))
            animated_items.append((bars, value_labels, values, max_value))

            axis.set_title(title, color=self.palette["text"], fontsize=12, fontweight="bold", loc="left")
            axis.set_yticks(y_positions)
            axis.set_yticklabels(labels, color=self.palette["text_secondary"], fontsize=8.5)
            axis.invert_yaxis()
            axis.xaxis.set_major_locator(MaxNLocator(integer=True))
            axis.set_xlim(0, max(max_value * 1.55, 1.5))
            axis.tick_params(axis="x", colors=self.palette["muted"], labelsize=8)
            axis.tick_params(axis="y", length=0)
            axis.grid(axis="x", color="#E5DDD6", linewidth=0.8, alpha=0.8, zorder=1)
            axis.grid(axis="y", visible=False)
            axis.spines["top"].set_visible(False)
            axis.spines["right"].set_visible(False)
            axis.spines["left"].set_color("#E5DDD6")
            axis.spines["bottom"].set_color("#E5DDD6")

        figure.tight_layout(pad=2.2)

        canvas = FigureCanvasTkAgg(figure, master=chart_host)
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        canvas.draw()

        frame_count = 70

        def update(frame_index: int):
            progress = frame_index / (frame_count - 1)
            eased_progress = 1 - ((1 - progress) ** 3)
            artists = []
            for bars, value_labels, values, max_value in animated_items:
                for bar, value, (value_label, label, final_value) in zip(bars, values, value_labels):
                    animated_value = value * eased_progress
                    bar.set_width(animated_value)
                    value_label.set_x(animated_value + max_value * 0.03)
                    value_label.set_text(f"{label}  |  {int(round(final_value * eased_progress))}")
                    artists.extend([bar, value_label])
            return artists

        self.cottage_leader_anim = FuncAnimation(
            figure,
            update,
            frames=frame_count,
            interval=18,
            blit=False,
            repeat=False,
        )
        canvas.draw_idle()

    def _render_cottage_performance_dashboard(self, reservations: list[dict], assets: list[dict]) -> None:
        leader_data = self._build_cottage_leader_rows(reservations, assets)

        if self.dashboard_cottage_performance_summary_frame is not None:
            self._clear_section_content(self.dashboard_cottage_performance_summary_frame)
            cards = ctk.CTkFrame(self.dashboard_cottage_performance_summary_frame, fg_color="transparent")
            cards.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
            for column_index in range(4):
                cards.grid_columnconfigure(column_index, weight=1)

            month_name = datetime.now().strftime("%B")
            week_top, week_count = leader_data["current_week_top"]
            month_top, month_count = leader_data["current_month_top"]
            year_top, year_count = leader_data["current_year_top"]
            self._summary_stat_card(cards, "Top This Week", week_top, f"{week_count} booking(s) this week.", 0, 0, self.palette["surface"], subtitle_wraplength=210)
            self._summary_stat_card(cards, f"Top in {month_name}", month_top, f"{month_count} booking(s) this month.", 0, 1, "#EEF5F2", subtitle_wraplength=210)
            self._summary_stat_card(cards, f"Top in {datetime.now().year}", year_top, f"{year_count} booking(s) this year.", 0, 2, "#F6F1E8", subtitle_wraplength=210)
            self._summary_stat_card(cards, "Tracked Bookings", str(leader_data["total_bookings"]), "Non-cancelled cottage reservations.", 0, 3, "#F7F4FA", subtitle_wraplength=210)

        if self.dashboard_cottage_period_graph_frame is not None:
            self._render_cottage_period_graph(
                self.dashboard_cottage_period_graph_frame,
                leader_data,
            )

        if self.dashboard_all_cottages_performance_frame is not None:
            self._render_all_cottages_performance_table(
                self.dashboard_all_cottages_performance_frame,
                leader_data["all_cottage_rows"],
            )

        if self.dashboard_cottage_weekly_leaders_frame is not None:
            self._render_cottage_leader_table(
                self.dashboard_cottage_weekly_leaders_frame,
                leader_data["weekly_rows"],
                "No weekly cottage booking records are available for the current year yet.",
            )

        if self.dashboard_cottage_monthly_leaders_frame is not None:
            self._render_cottage_leader_table(
                self.dashboard_cottage_monthly_leaders_frame,
                leader_data["monthly_rows"],
                "No monthly cottage booking records are available for the current year yet.",
            )

        if self.dashboard_cottage_yearly_leaders_frame is not None:
            self._render_cottage_leader_table(
                self.dashboard_cottage_yearly_leaders_frame,
                leader_data["yearly_rows"],
                "No yearly cottage booking records are available yet.",
            )

    def _dashboard_booking_tab_definitions(self) -> list[tuple[str, str]]:
        return [
            ("pending", "Pending"),
            ("reserved", "Reserved"),
            ("ongoing", "On Going"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ]

    def _dashboard_booking_status_map(self) -> dict[str, tuple[str, ...]]:
        return {
            "pending": ("Pending",),
            "reserved": ("Confirmed", "Approved", "Reserved"),
            "ongoing": ("On Going",),
            "completed": ("Completed",),
            "cancelled": ("Cancelled",),
        }

    def _booking_display_label(self, reservation: dict) -> str:
        cottage_name = str(reservation.get("cottage_name") or "").strip()
        cottage_code = str(reservation.get("cottage_code") or "").strip()
        if cottage_name:
            return cottage_name
        if cottage_code:
            return cottage_code
        return "Floating Cottage"

    def _nearest_dashboard_reservation(self, reservations: list[dict]) -> dict | None:
        now = datetime.now()
        reserved_upcoming = [
            reservation
            for reservation in reservations
            if str(reservation.get("status") or "") == "Reserved"
            and isinstance(reservation.get("departure_time"), datetime)
            and reservation["departure_time"] >= now
        ]
        reserved_upcoming.sort(
            key=lambda reservation: (
                reservation.get("departure_time") or datetime.max,
                reservation.get("created_at") or datetime.min,
            )
        )
        if reserved_upcoming:
            return reserved_upcoming[0]

        reserved_fallback = [
            reservation
            for reservation in reservations
            if str(reservation.get("status") or "") == "Reserved"
        ]
        reserved_fallback.sort(
            key=lambda reservation: (
                reservation.get("departure_time")
                if isinstance(reservation.get("departure_time"), datetime)
                else reservation.get("created_at")
                if isinstance(reservation.get("created_at"), datetime)
                else datetime.min,
                reservation.get("created_at") or datetime.min,
            ),
        )
        return reserved_fallback[0] if reserved_fallback else None

    def _nearest_dashboard_reservation_summary(self, reservation: dict | None) -> tuple[str, str]:
        if reservation is None:
            return "--", "No reserved booking is available right now."

        departure_time = reservation.get("departure_time")
        departure_text = (
            departure_time.strftime("%b %d, %Y %I:%M %p")
            if isinstance(departure_time, datetime)
            else "Schedule unavailable"
        )
        status = str(reservation.get("status") or "").strip() or "Unknown"
        guest = str(reservation.get("full_name") or "Guest").strip() or "Guest"
        destination = (
            str(reservation.get("destination") or reservation.get("destination_name") or "").strip()
            or "Destination unavailable"
        )
        cottage_code = str(reservation.get("cottage_code") or "").strip()

        primary_line = " | ".join(part for part in (cottage_code, guest) if part)
        detail_line = " | ".join(part for part in (destination, departure_text, status) if part)
        subtitle = "\n".join(line for line in (primary_line, detail_line) if line)
        return self._booking_display_label(reservation), subtitle or "Reservation details unavailable."

    def _dashboard_bookings_for_tab(self, reservations: list[dict], tab_key: str) -> list[dict]:
        allowed_statuses = set(self._dashboard_booking_status_map().get(tab_key, ()))
        filtered = [
            reservation
            for reservation in reservations
            if str(reservation.get("status") or "") in allowed_statuses
        ]

        if tab_key in {"pending", "reserved"}:
            filtered.sort(
                key=lambda reservation: (
                    reservation.get("departure_time")
                    if isinstance(reservation.get("departure_time"), datetime)
                    else datetime.max,
                    reservation.get("created_at")
                    if isinstance(reservation.get("created_at"), datetime)
                    else datetime.min,
                )
            )
            return filtered

        if tab_key == "ongoing":
            filtered.sort(
                key=lambda reservation: (
                    reservation.get("return_time")
                    if isinstance(reservation.get("return_time"), datetime)
                    else reservation.get("departure_time")
                    if isinstance(reservation.get("departure_time"), datetime)
                    else datetime.max,
                    reservation.get("departure_time")
                    if isinstance(reservation.get("departure_time"), datetime)
                    else datetime.max,
                )
            )
            return filtered

        filtered.sort(
            key=lambda reservation: (
                reservation.get("return_time")
                if isinstance(reservation.get("return_time"), datetime)
                else reservation.get("departure_time")
                if isinstance(reservation.get("departure_time"), datetime)
                else reservation.get("created_at")
                if isinstance(reservation.get("created_at"), datetime)
                else datetime.min,
                reservation.get("created_at")
                if isinstance(reservation.get("created_at"), datetime)
                else datetime.min,
            ),
            reverse=True,
        )
        return filtered

    def _switch_dashboard_bookings_tab(self, tab_key: str) -> None:
        self.dashboard_bookings_current_tab = tab_key
        if not self.last_dashboard_snapshot:
            return
        self._render_dashboard_bookings(self.last_dashboard_snapshot.get("reservations", []))

    def _render_dashboard_bookings_tabs(self, reservations: list[dict]) -> None:
        if self.dashboard_bookings_frame is None:
            return

        tab_defs = self._dashboard_booking_tab_definitions()
        tab_counts = {
            key: len(self._dashboard_bookings_for_tab(reservations, key))
            for key, _label in tab_defs
        }
        if self.dashboard_bookings_current_tab not in dict(tab_defs):
            self.dashboard_bookings_current_tab = tab_defs[0][0]

        tab_bar = ctk.CTkFrame(
            self.dashboard_bookings_frame,
            fg_color=self.palette["surface_alt"],
            corner_radius=16,
            height=52,
        )
        tab_bar.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 14))
        tab_bar.grid_propagate(False)
        for column_index in range(len(tab_defs)):
            tab_bar.grid_columnconfigure(column_index, weight=1)

        for column_index, (key, label) in enumerate(tab_defs):
            count = tab_counts.get(key, 0)
            is_active = key == self.dashboard_bookings_current_tab
            ctk.CTkButton(
                tab_bar,
                text=f"{label} ({count})",
                height=38,
                corner_radius=12,
                fg_color=self.palette["brand"] if is_active else "transparent",
                hover_color=self.palette["accent"],
                text_color=self.palette["surface"] if is_active else self.palette["muted"],
                font=("Segoe UI", 12, "bold"),
                command=lambda current_key=key: self._switch_dashboard_bookings_tab(current_key),
            ).grid(row=0, column=column_index, sticky="ew", padx=4, pady=6)

        ctk.CTkLabel(
            self.dashboard_bookings_frame,
            text="Each list is ordered from the nearest booking to the farthest one for that status.",
            text_color=self.palette["muted"],
            font=("Segoe UI", 12),
            justify="left",
        ).grid(row=2, column=0, sticky="w", padx=18, pady=(0, 12))

        list_host = ctk.CTkFrame(self.dashboard_bookings_frame, fg_color="transparent")
        list_host.grid(row=3, column=0, sticky="nsew", padx=0, pady=(0, 0))
        list_host.grid_columnconfigure(0, weight=1)

        self._render_reservations(
            list_host,
            self._dashboard_bookings_for_tab(reservations, self.dashboard_bookings_current_tab),
            with_actions=True,
            preserve_section_header=False,
        )

    def _render_dashboard_bookings(self, reservations: list[dict]) -> None:
        now = datetime.now()
        pending_count = sum(
            1 for reservation in reservations if str(reservation.get("status") or "") == "Pending"
        )
        in_use_count = sum(1 for reservation in reservations if str(reservation.get("status") or "") == "On Going")
        next_seven_days = sum(
            1
            for reservation in reservations
            if isinstance(reservation.get("departure_time"), datetime)
            and now <= reservation["departure_time"] <= now + timedelta(days=7)
        )
        nearest = self._nearest_dashboard_reservation(reservations)
        nearest_title, nearest_subtitle = self._nearest_dashboard_reservation_summary(nearest)

        if self.dashboard_bookings_summary_frame is not None:
            self._clear_section_content(self.dashboard_bookings_summary_frame)
            cards = ctk.CTkFrame(self.dashboard_bookings_summary_frame, fg_color="transparent")
            cards.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
            for column_index in range(5):
                cards.grid_columnconfigure(column_index, weight=1)
            self._summary_stat_card(
                cards,
                "Need Action",
                str(pending_count),
                "Pending bookings that still need admin review.",
                0,
                0,
                "#F6F1E8",
            )
            self._summary_stat_card(
                cards,
                "Nearest Reservation",
                nearest_title,
                nearest_subtitle,
                0,
                1,
                self.palette["surface"],
                columnspan=2,
                value_font=("Segoe UI", 18, "bold"),
                subtitle_wraplength=360,
            )
            self._summary_stat_card(
                cards,
                "Next 7 Days",
                str(next_seven_days),
                "Reservations scheduled within the next week.",
                0,
                3,
                "#EEF5F2",
            )
            self._summary_stat_card(
                cards,
                "On Going",
                str(in_use_count),
                "Trips currently active right now.",
                0,
                4,
                "#F7F4FA",
            )

        if self.dashboard_bookings_frame is not None:
            self._clear_section_content(self.dashboard_bookings_frame)
            self._render_dashboard_bookings_tabs(reservations)

    def show_page(self, name: str) -> None:
        previous_page = self.current_page
        if previous_page == "dashboard" and name != "dashboard" and self.dashboard_current_section == "overview":
            self._reset_asset_analytics_for_navigation()
        if previous_page == "dashboard" and name != "dashboard" and self.dashboard_current_section == "assets":
            self._reset_assets_dashboard_navigation()
        self.current_page = name

        if self.profile_dropdown_visible:
            self._hide_profile_dropdown()
        if self.notifications_visible:
            self._hide_notifications_panel()

        page_display_names = {
            "home": "K3's Floating Cottage",
            "reservations": "Reservations",
            "operations": "Operations",
            "payments": "Payments",
            "dashboard": "Dashboard",
        }
        if self.current_page_label:
            self.current_page_label.configure(text=page_display_names.get(name, "K3's Floating Cottage"))

        if hasattr(self, "action_icon_label") and hasattr(self, "action_text_label"):
            if name == "home":
                self._action_button_mode = "logout"
                self.action_icon_label.configure(text="")
                self.action_text_label.configure(text="Logout")
            else:
                self._action_button_mode = "back"
                self.action_icon_label.configure(text="")
                self.action_text_label.configure(text="Back")
            self.action_frame.configure(fg_color="transparent")
            self.action_icon_label.configure(text_color=self.palette["text"])
            self.action_text_label.configure(text_color=self.palette["text"])

        if name in self.nav_buttons:
            self._set_dashboard_navigation_state(name)

        if hasattr(self, "header") and self.header is not None:
            self.header.grid()

        self.page_frames[name].tkraise()
        if self.last_dashboard_snapshot is not None:
            self._render_visible_snapshot(
                self.last_dashboard_snapshot,
                replay_animations=(name == "dashboard"),
            )

    def refresh_dashboard(self, status_message: str | None = None) -> None:
        self._queue_dashboard_refresh(
            self._selected_asset_reference_date(),
            status_message,
        )


    def _on_delete_reservation(self, code: str) -> None:
        print(f"DEBUG: Delete clicked for reservation {code}")
        # Use after(0) to ensure the messagebox doesn't hang the UI thread in some environments
        def confirm():
            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete reservation {code}?\n\nThis will move the record to the trash bin table."):
                try:
                    self.reservation_controller.delete_reservation(code)
                    messagebox.showinfo("Deleted", f"Reservation {code} has been moved to the trash bin.")
                    self.refresh_dashboard()
                except Exception as e:
                    messagebox.showerror("Error", str(e))
        self.after(0, confirm)

    def _on_guest_table_click(self, cell_data: dict) -> None:
        row_idx = cell_data["row"]
        if row_idx == 0:
             return
        
        col_idx = cell_data["column"]
        if col_idx != 8: # Actions column
            return
            
        data_idx = row_idx - 1
        if not hasattr(self, "_current_guest_list_data") or data_idx < 0 or data_idx >= len(self._current_guest_list_data):
            return
            
        guest = self._current_guest_list_data[data_idx]
        guest_name = guest["full_name"]
        contact = guest["contact_number"]
        email = guest["email"]
        
        print(f"DEBUG: Delete clicked for guest {guest_name}")

        def confirm():
            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete guest '{guest_name}'?\n\nThis will also delete all their booking records and move everything to the trash bin table."):
                try:
                    success = self.dashboard_controller.delete_guest(email, contact, guest_name)
                    if success:
                        messagebox.showinfo("Deleted", f"Guest '{guest_name}' and their records have been moved to the trash bin.")
                        self.refresh_dashboard()
                    else:
                        messagebox.showerror("Error", "Could not find guest record to delete.")
                except Exception as e:
                    messagebox.showerror("Error", str(e))
        self.after(0, confirm)


class RecoveryDialog(ctk.CTkToplevel):
    """Multi-step dialog for password recovery via security question."""
    def __init__(self, parent, auth_controller, palette):
        super().__init__(parent)
        self.auth_controller = auth_controller
        self.palette = palette
        self.title("Recover Password")
        self.geometry("440x480")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=palette["page"])
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.username = None
        self.role = None
        self.question = None
        
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=0, column=0, sticky="nsew", padx=30, pady=30)
        self.container.grid_columnconfigure(0, weight=1)
        
        self._show_step_1()

    def _clear(self):
        for child in self.container.winfo_children():
            child.destroy()

    def _show_step_1(self):
        self._clear()
        ctk.CTkLabel(self.container, text="Account Recovery", font=("Segoe UI", 24, "bold"), text_color=self.palette["text"]).pack(pady=(0, 10), anchor="w")
        ctk.CTkLabel(self.container, text="Enter your username to start recovery.", font=("Segoe UI", 13), text_color=self.palette["text_secondary"]).pack(pady=(0, 20), anchor="w")
        
        user_var = ctk.StringVar()
        entry = ctk.CTkEntry(self.container, placeholder_text="Username", height=45, corner_radius=12, textvariable=user_var)
        entry.pack(fill="x", pady=(0, 20))
        entry.focus_set()
        
        def on_next():
            username = user_var.get().strip()
            if not username: return
            info = self.auth_controller.get_recovery_info(username)
            if not info:
                messagebox.showerror("Recovery", "Username not found or recovery not enabled.")
                return
            self.username = username
            self.question = info["question"]
            self.role = info["role"]
            self._show_step_2()

        ctk.CTkButton(self.container, text="Next Step", command=on_next, height=40, corner_radius=10, fg_color=self.palette["brand"], hover_color=self.palette["brand_dark"]).pack(fill="x")

    def _show_step_2(self):
        self._clear()
        ctk.CTkLabel(self.container, text="Security Check", font=("Segoe UI", 24, "bold"), text_color=self.palette["text"]).pack(pady=(0, 10), anchor="w")
        ctk.CTkLabel(self.container, text=f"Answer your security question for {self.username}:", font=("Segoe UI", 13), text_color=self.palette["text_secondary"]).pack(pady=(0, 20), anchor="w")
        
        q_card = ctk.CTkFrame(self.container, fg_color=self.palette["surface_alt"], corner_radius=12)
        q_card.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(q_card, text=self.question or "No question set.", font=("Segoe UI", 13, "italic"), text_color=self.palette["text"], wraplength=340).pack(padx=15, pady=15)
        
        ans_var = ctk.StringVar()
        entry = ctk.CTkEntry(self.container, placeholder_text="Your Answer", height=45, corner_radius=12, textvariable=ans_var)
        entry.pack(fill="x", pady=(0, 20))
        entry.focus_set()
        
        def on_next():
            self.answer = ans_var.get().strip()
            if not self.answer: return
            self._show_step_3()

        ctk.CTkButton(self.container, text="Verify Answer", command=on_next, height=40, corner_radius=10, fg_color=self.palette["brand"], hover_color=self.palette["brand_dark"]).pack(fill="x")

    def _show_step_3(self):
        self._clear()
        ctk.CTkLabel(self.container, text="Reset Password", font=("Segoe UI", 24, "bold"), text_color=self.palette["text"]).pack(pady=(0, 10), anchor="w")
        ctk.CTkLabel(self.container, text="Create a new secure password.", font=("Segoe UI", 13), text_color=self.palette["text_secondary"]).pack(pady=(0, 20), anchor="w")
        
        # Feedback Label
        status_var = ctk.StringVar()
        status_lbl = ctk.CTkLabel(self.container, textvariable=status_var, font=("Segoe UI", 12), text_color=self.palette["danger"], wraplength=340)
        status_lbl.pack(pady=(0, 10))

        ctk.CTkLabel(self.container, text="New Password", font=("Segoe UI", 12, "bold"), text_color=self.palette["text"]).pack(anchor="w", pady=(0, 5))
        pw_var = ctk.StringVar()
        ctk.CTkEntry(self.container, placeholder_text="Minimum 6 characters", show="•", height=45, corner_radius=12, textvariable=pw_var).pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(self.container, text="Confirm Password", font=("Segoe UI", 12, "bold"), text_color=self.palette["text"]).pack(anchor="w", pady=(0, 5))
        conf_var = ctk.StringVar()
        ctk.CTkEntry(self.container, placeholder_text="Repeat new password", show="•", height=45, corner_radius=12, textvariable=conf_var).pack(fill="x", pady=(0, 25))
        
        def on_reset():
            status_var.set("")
            ok, msg = self.auth_controller.reset_password(self.username, self.role, self.answer, pw_var.get(), conf_var.get())
            if not ok:
                status_var.set(msg)
                return
            messagebox.showinfo("Success", "Password reset successfully! You can now log in.")
            self.destroy()

        ctk.CTkButton(self.container, text="Change Password", command=on_reset, height=44, corner_radius=12, font=("Segoe UI", 13, "bold"), fg_color=self.palette["brand"], hover_color=self.palette["brand_dark"]).pack(fill="x")




class RecoverySetupDialog(ctk.CTkToplevel):
    """Dialog for mandatory security question setup."""
    def __init__(self, parent, auth_controller, palette, username, role):
        super().__init__(parent)
        self.auth_controller = auth_controller
        self.palette = palette
        self.username = username
        self.role = role
        
        self.title("Secure Your Account")
        self.geometry("460x420")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", lambda: None) # Prevent closing
        self.configure(fg_color=palette["page"])
        
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=40, pady=40)
        
        ctk.CTkLabel(container, text="One-Time Setup", font=("Segoe UI", 26, "bold"), text_color=palette["text"]).pack(pady=(0, 10), anchor="w")
        ctk.CTkLabel(container, text="Please set a security question to help you recover your account if you forget your password.", font=("Segoe UI", 13), text_color=palette["text_secondary"], wraplength=380, justify="left").pack(pady=(0, 24), anchor="w")
        
        questions = [
            "What was the name of your first pet?",
            "What was your childhood nickname?",
            "In what city were you born?",
            "What is your mother's maiden name?",
            "What was the name of your first school?",
            "What is your favorite book?"
        ]
        q_var = ctk.StringVar(value=questions[0])
        ctk.CTkOptionMenu(container, values=questions, variable=q_var, height=45, corner_radius=12, fg_color=palette["surface"], button_color=palette["brand"], text_color=palette["text"], dropdown_fg_color=palette["surface"]).pack(fill="x", pady=(0, 15))
        
        ans_var = ctk.StringVar()
        entry = ctk.CTkEntry(container, placeholder_text="Answer to your question", height=45, corner_radius=12, textvariable=ans_var)
        entry.pack(fill="x", pady=(0, 24))
        
        def on_save():
            ans = ans_var.get().strip()
            if not ans: return
            self.auth_controller.update_recovery_info(self.username, self.role, q_var.get(), ans)
            messagebox.showinfo("Security", "Recovery information saved successfully!")
            self.destroy()

        ctk.CTkButton(container, text="Save & Continue", command=on_save, height=46, corner_radius=12, font=("Segoe UI", 14, "bold"), fg_color=palette["brand"], hover_color=palette["brand_dark"]).pack(fill="x")
