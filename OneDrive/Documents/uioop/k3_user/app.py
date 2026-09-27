"""Root application window and page router."""

from __future__ import annotations

import customtkinter as ctk

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

from k3_rms.ui_scaling import apply_customtkinter_scaling
from views.booking_view import BookingView
from views.browse_view import BrowseView
from views.confirm_view import ConfirmView
from views.dashboard_view import DashboardView
from views.home_view import HomeView
from views.login_view import LoginView
from views.my_bookings_view import MyBookingsView
from views.notifications_view import NotificationsView
from views.profile_view import ProfileView
from views.about_view import AboutView


class GuestPortalShell(ctk.CTkFrame):
    """Embeddable guest portal shell used by both the standalone app and RMS."""

    def __init__(
        self,
        parent,
        session_user: dict | None = None,
        initial_auth_tab: str = "login",
        auth_mode: str = "full",
        integrated_auth: bool = False,
        logout_callback=None,
    ):
        from utils.theme import BG

        super().__init__(parent, fg_color=BG)
        self.integrated_auth = integrated_auth
        self.logout_callback = logout_callback
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        if session_user is not None:
            self.session_user = dict(session_user)
        else:
            self.session_user = None
        self.initial_auth_tab = "register" if initial_auth_tab == "register" else "login"
        self.auth_mode = "register_only" if auth_mode == "register_only" else "full"

        self._current_frame = None
        self._sidebar_buttons: dict[str, ctk.CTkButton] = {}
        self._sidebar_title_label = None
        self._sidebar_avatar_label = None
        self._sidebar_name_label = None
        self._sidebar_email_label = None

        self.sidebar = self._build_sidebar()
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        self.main_container = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.main_container.grid(row=0, column=1, sticky="nsew")
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        if self.session_user is not None:
            self.navigate(BrowseView)
        else:
            self.navigate(LoginView, initial_tab=self.initial_auth_tab, auth_mode=self.auth_mode)

    def _build_sidebar(self):
        from utils.theme import (
            BG,
            CARD,
            DANGER,
            DANGER_SOFT,
            DIVIDER,
            SUBTEXT,
            TEAL_DARK,
            TEAL_LIGHT,
            TEXT,
            make_button,
            make_label,
        )

        sidebar = ctk.CTkFrame(self, fg_color=CARD, width=220, corner_radius=0)
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(4, weight=1)
        sidebar.grid_columnconfigure(0, weight=1)

        title_card = ctk.CTkFrame(sidebar, fg_color=TEAL_DARK, corner_radius=10, height=44)
        title_card.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 18))
        title_card.grid_propagate(False)
        self._sidebar_title_label = make_label(title_card, "Guest Portal", 12, "bold", color=CARD)
        self._sidebar_title_label.place(relx=0.05, rely=0.5, anchor="w")

        profile_card = ctk.CTkFrame(sidebar, fg_color="transparent")
        profile_card.grid(row=1, column=0, sticky="ew", padx=14)
        profile_card.grid_columnconfigure(0, weight=1)

        avatar = ctk.CTkFrame(
            profile_card,
            fg_color=TEAL_DARK,
            width=56,
            height=56,
            corner_radius=28,
        )
        avatar.grid(row=0, column=0, pady=(4, 12))
        avatar.grid_propagate(False)
        self._sidebar_avatar_label = make_label(avatar, "G", 22, "bold", color=CARD)
        self._sidebar_avatar_label.place(relx=0.5, rely=0.5, anchor="center")

        self._sidebar_name_label = make_label(profile_card, "Guest User", 14, "bold", color=TEXT)
        self._sidebar_name_label.grid(row=1, column=0, sticky="w")
        self._sidebar_email_label = make_label(profile_card, "Sign in to continue", 11, color=SUBTEXT)
        self._sidebar_email_label.grid(row=2, column=0, sticky="w", pady=(2, 12))

        ctk.CTkFrame(sidebar, height=1, fg_color=DIVIDER).grid(
            row=2,
            column=0,
            sticky="ew",
            padx=14,
            pady=(0, 18),
        )

        nav = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav.grid(row=3, column=0, sticky="ew", padx=8)
        nav.grid_columnconfigure(0, weight=1)

        nav_items = [
            ("profile", "My Profile", ProfileView),
            ("notifications", "Notifications", NotificationsView),
            ("bookings", "My Bookings", MyBookingsView),
            ("about", "About Us", AboutView),
            ("browse", "Make a Reservation", BrowseView),
        ]
        for row, (key, label, view_cls) in enumerate(nav_items):
            if key == "browse":
                button = make_button(
                    nav,
                    f"+  {label}",
                    lambda cls=view_cls: self.navigate(cls),
                    color=TEAL_DARK,
                    hover="#257E79",
                    fg=CARD,
                    height=40,
                    anchor="w",
                    font=("Segoe UI", 12, "bold"),
                )
            else:
                button = make_button(
                    nav,
                    label,
                    lambda cls=view_cls: self.navigate(cls),
                    color="transparent",
                    hover=BG,
                    fg=TEXT,
                    height=38,
                    anchor="w",
                    font=("Segoe UI", 12, "bold"),
                )
            button.grid(row=row, column=0, sticky="ew", padx=6, pady=4)
            self._sidebar_buttons[key] = button

        footer = ctk.CTkFrame(sidebar, fg_color="transparent")
        footer.grid(row=5, column=0, sticky="ew", padx=8, pady=(12, 18))
        footer.grid_columnconfigure(0, weight=1)
        make_button(
            footer,
            "Log Out",
            self._logout,
            color=DANGER_SOFT,
            hover="#F8D9D7",
            fg=DANGER,
            height=38,
            anchor="w",
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="ew", padx=6)

        self._refresh_sidebar_profile()
        return sidebar

    def _refresh_sidebar_profile(self) -> None:
        user = self.session_user or {}
        name = user.get("name") or "Guest User"
        email = user.get("email") or "Sign in to continue"
        avatar = name[:1].upper() if name else "G"

        if self._sidebar_avatar_label is not None:
            self._sidebar_avatar_label.configure(text=avatar)
        if self._sidebar_name_label is not None:
            self._sidebar_name_label.configure(text=name)
        if self._sidebar_email_label is not None:
            self._sidebar_email_label.configure(text=email)

    def _configure_shell(self, title: str, active_key: str | None, show_sidebar: bool) -> None:
        from utils.theme import BG, CARD, SUBTEXT, TEAL_DARK, TEAL_LIGHT, TEXT

        if self._sidebar_title_label is not None:
            self._sidebar_title_label.configure(text=title or "Guest Portal")

        if show_sidebar:
            self.sidebar.grid(row=0, column=0, sticky="nsew")
            self.main_container.grid(row=0, column=1, sticky="nsew")
        else:
            self.sidebar.grid_remove()
            self.main_container.grid(row=0, column=0, columnspan=2, sticky="nsew")

        for key, button in self._sidebar_buttons.items():
            if key == "browse":
                button.configure(
                    fg_color=TEAL_DARK,
                    hover_color="#257E79",
                    text_color=CARD,
                )
                continue
            if key == active_key:
                button.configure(
                    fg_color=TEAL_LIGHT,
                    hover_color=TEAL_LIGHT,
                    text_color=TEAL_DARK,
                )
            else:
                button.configure(
                    fg_color="transparent",
                    hover_color=BG,
                    text_color=TEXT if self.session_user else SUBTEXT,
                )

    def _logout(self) -> None:
        from tkinter import messagebox
        if messagebox.askyesno("Confirm Logout", "Are you sure you want to log out?"):
            self.logout()

    def logout(self) -> None:
        self.session_user = None
        self._refresh_sidebar_profile()
        if self.logout_callback is not None:
            self.after(0, self.logout_callback)
            return
        if self.integrated_auth:
            self.winfo_toplevel().after(0, self.winfo_toplevel().destroy)
            return
        self.navigate(LoginView)

    def navigate(self, view_cls, **kwargs):
        if self._current_frame is not None:
            self._current_frame.destroy()

        self._refresh_sidebar_profile()
        self._current_frame = view_cls(self.main_container, app=self, **kwargs)
        self._current_frame.grid(row=0, column=0, sticky="nsew")

        show_sidebar = getattr(view_cls, "SHOW_SIDEBAR", self.session_user is not None)
        title = getattr(view_cls, "SHELL_TITLE", "Guest Portal")
        active_key = getattr(view_cls, "SIDEBAR_ACTIVE", None)
        self._configure_shell(title, active_key, show_sidebar)


class K3App(ctk.CTk):
    """Standalone guest portal window."""

    def __init__(
        self,
        session_user: dict | None = None,
        integrated_auth: bool = False,
        logout_callback=None,
    ):
        super().__init__()
        self.screen_profile = apply_customtkinter_scaling(
            self.winfo_screenwidth(),
            self.winfo_screenheight(),
        )
        screen_width = self.screen_profile.screen_width
        screen_height = self.screen_profile.screen_height
        initial_width = min(1280, max(900, screen_width - 80))
        initial_height = min(800, max(640, screen_height - 80))
        min_width = min(1120, initial_width)
        min_height = min(720, initial_height)
        self.title("K3's Floating Cottage - Guest Portal")
        self.geometry(f"{initial_width}x{initial_height}")
        self.minsize(min_width, min_height)

        from utils.theme import BG

        self.configure(fg_color=BG)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.shell = GuestPortalShell(
            self,
            session_user=session_user,
            integrated_auth=integrated_auth,
            logout_callback=logout_callback,
        )
        self.shell.grid(row=0, column=0, sticky="nsew")
        self.after(0, self._maximize_window)

    def _maximize_window(self) -> None:
        try:
            self.state("zoomed")
        except Exception:
            try:
                self.attributes("-fullscreen", True)
            except Exception:
                pass

    @property
    def session_user(self):
        return self.shell.session_user

    def navigate(self, view_cls, **kwargs):
        return self.shell.navigate(view_cls, **kwargs)

    def logout(self) -> None:
        self.shell.logout()

    def _refresh_sidebar_profile(self) -> None:
        self.shell._refresh_sidebar_profile()
