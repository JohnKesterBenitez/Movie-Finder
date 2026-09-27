"""Guest login and signup screen."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running this file directly for testing by adding the k3_user folder to sys.path
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import customtkinter as ctk

from controllers.login_controller import LoginController
from utils.theme import (
    BG,
    CARD,
    DANGER,
    DIVIDER,
    SUBTEXT,
    SUCCESS_TEXT,
    TEAL,
    TEAL_DARK,
    TEAL_LIGHT,
    TEXT,
    WHITE,
    make_button,
    make_card,
    make_entry,
    make_label,
)


class LoginView(ctk.CTkFrame):
    SHELL_TITLE = "Guest Access"
    SHOW_SIDEBAR = False

    def __init__(self, parent, app, initial_tab: str = "login", auth_mode: str = "full"):
        super().__init__(parent, fg_color=BG)
        self.app = app
        self.ctrl = LoginController(app)
        self.initial_tab = "register" if initial_tab == "register" else "login"
        self.auth_mode = "register_only" if auth_mode == "register_only" else "full"
        self.register_only = self.auth_mode == "register_only"
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        ctk.CTkFrame(
            self,
            width=320,
            height=320,
            corner_radius=160,
            fg_color="#F5ECD7",
        ).place(x=-100, y=70)
        ctk.CTkFrame(
            self,
            width=260,
            height=260,
            corner_radius=130,
            fg_color=TEAL_LIGHT,
        ).place(relx=1.0, rely=1.0, x=-160, y=-150)

        # Use a scrollable outer shell so the card is always fully reachable
        shell = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=DIVIDER,
            scrollbar_button_hover_color=TEAL_LIGHT,
        )
        shell.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        shell.grid_columnconfigure(0, weight=1)

        # Back button — outside the card, upper-left
        self._back_btn = make_button(
            shell,
            "←  Back to Login",
            self._go_back_to_login,
            color="transparent",
            hover=TEAL_LIGHT,
            fg=TEAL_DARK,
            height=34,
            font=("Segoe UI", 12, "bold"),
            anchor="w",
            cursor="hand2",
        )
        self._back_btn.grid(row=0, column=0, sticky="w", pady=(0, 8))

        card = make_card(shell, width=580, radius=26)
        card.grid(row=1, column=0, sticky="n", pady=(0, 8))
        card.grid_columnconfigure(0, weight=1)

        hero = ctk.CTkFrame(card, fg_color="transparent")
        hero.grid(row=0, column=0, sticky="ew", padx=36, pady=(28, 12))
        hero.grid_columnconfigure(0, weight=1)

        guest_chip = ctk.CTkLabel(
            hero,
            text="Guest Accounts Only",
            fg_color=TEAL_LIGHT,
            text_color=TEAL_DARK,
            corner_radius=10,
            font=("Segoe UI", 11, "bold"),
            padx=12,
            pady=6,
        )
        guest_chip.grid(row=0, column=0, sticky="w")
        make_label(hero, "K3's Floating Cottage", 24, "bold", color=TEAL_DARK).grid(
            row=1,
            column=0,
            sticky="w",
            pady=(14, 2),
        )
        make_label(hero, "Guest Reservation Portal", 13, color=SUBTEXT).grid(
            row=2,
            column=0,
            sticky="w",
            pady=(0, 10),
        )
        make_label(
            hero,
            "Create a guest account to reserve cottages, manage bookings, and sign back in anytime.",
            12,
            color=TEXT,
            wraplength=470,
            justify="left",
        ).grid(row=3, column=0, sticky="w")

        self._tab = ctk.StringVar(value="login")
        if self.register_only:
            # In register-only mode, skip the tab row entirely
            self._btn_login = None
            self._btn_reg = None  # No tab button needed
        else:
            tab_row = ctk.CTkFrame(card, fg_color=TEAL_LIGHT, corner_radius=12, height=42)
            tab_row.grid(row=1, column=0, sticky="ew", padx=36, pady=(2, 0))
            tab_row.grid_propagate(False)
            tab_row.grid_columnconfigure((0, 1), weight=1)
            self._btn_login = ctk.CTkButton(
                tab_row,
                text="Sign In",
                corner_radius=10,
                fg_color=TEAL,
                hover_color=TEAL_DARK,
                text_color=WHITE,
                font=("Segoe UI", 12, "bold"),
                height=32,
                command=lambda: self._switch_tab("login"),
            )
            self._btn_login.grid(row=0, column=0, padx=4, pady=4, sticky="ew")
            self._btn_reg = ctk.CTkButton(
                tab_row,
                text="Sign Up",
                corner_radius=10,
                fg_color="transparent",
                hover_color=TEAL_LIGHT,
                text_color=SUBTEXT,
                font=("Segoe UI", 12),
                height=32,
                command=lambda: self._switch_tab("register"),
            )
            self._btn_reg.grid(row=0, column=1, padx=4, pady=4, sticky="ew")

        self._panels = ctk.CTkFrame(card, fg_color="transparent")
        self._panels.grid(row=2, column=0, sticky="ew", padx=36, pady=(12, 0))
        self._panels.grid_columnconfigure(0, weight=1)

        self._build_login_panel()
        self._build_register_panel()
        self._switch_tab(self.initial_tab)

        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=36, pady=(14, 24))
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkFrame(footer, fg_color=DIVIDER, height=1).grid(row=0, column=0, sticky="ew", pady=(0, 10))
        make_label(
            footer,
            "New guest accounts are saved to the reservation database."
            if self.register_only
            else "New guest accounts are saved to the reservation database and can be used to sign in after registration.",
            11,
            color=SUBTEXT,
            wraplength=470,
            justify="left",
        ).grid(row=1, column=0, sticky="w")

    def _build_login_panel(self) -> None:
        panel = ctk.CTkFrame(self._panels, fg_color="transparent")
        panel.grid_columnconfigure(0, weight=1)

        make_label(panel, "Username", 12, "bold").grid(row=0, column=0, sticky="w", pady=(12, 4))
        self.e_username = make_entry(panel, "Enter your username")
        self.e_username.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        make_label(panel, "Password", 12, "bold").grid(row=2, column=0, sticky="w", pady=(0, 4))
        self.e_password = make_entry(panel, "Enter your password", show="*")
        self.e_password.grid(row=3, column=0, sticky="ew", pady=(0, 12))

        self.lbl_login_status = make_label(panel, "", 11, color=DANGER, wraplength=440, justify="left")
        self.lbl_login_status.grid(row=4, column=0, sticky="w", pady=(0, 10))

        make_button(panel, "Sign In", self._do_login, height=44).grid(
            row=5,
            column=0,
            sticky="ew",
            pady=(0, 4),
        )
        
        # Forgot Password Link
        make_button(
            panel, 
            "Forgot password?", 
            self._open_recovery_dialog, 
            height=24, 
            color="transparent", 
            fg=TEAL_DARK,
            font=("Segoe UI", 12, "bold")
        ).grid(row=6, column=0, sticky="e", pady=(0, 8))
        make_label(
            panel,
            "Guest sign-in only. Admin accounts use the RMS login screen.",
            11,
            color=SUBTEXT,
            wraplength=440,
            justify="left",
        ).grid(row=7, column=0, sticky="w", pady=(0, 10))

        self._login_panel = panel

    def _build_register_panel(self) -> None:
        panel = ctk.CTkFrame(self._panels, fg_color="transparent")
        panel.grid_columnconfigure((0, 1), weight=1)

        fields = [
            ("Full Name", "Juan Dela Cruz", "e_r_name", 0, 0, 2, False),
            ("Username", "juandelacruz", "e_r_user", 1, 0, 1, False),
            ("Contact Number", "09XXXXXXXXX", "e_r_contact", 1, 1, 1, False),
            ("Email Address", "you@email.com", "e_r_email", 2, 0, 2, False),
            ("Password", "Create a password", "e_r_pass", 3, 0, 1, True),
            ("Confirm Password", "Repeat your password", "e_r_confirm", 3, 1, 1, True),
        ]

        for label, placeholder, attr, row, column, span, is_password in fields:
            padx = (0, 8) if column == 0 and span == 1 else ((8, 0) if column == 1 else (0, 0))
            make_label(panel, label, 12, "bold").grid(
                row=row * 2,
                column=column,
                columnspan=span,
                sticky="w",
                pady=(12, 4),
                padx=padx,
            )
            entry_kwargs = {"show": "*"} if is_password else {}
            entry = make_entry(panel, placeholder, **entry_kwargs)
            entry.grid(
                row=row * 2 + 1,
                column=column,
                columnspan=span,
                sticky="ew",
                padx=padx,
                pady=(0, 6),
            )
            setattr(self, attr, entry)

        # Recovery Question Section
        make_label(panel, "Security Question", 12, "bold").grid(row=8, column=0, columnspan=2, sticky="w", pady=(12, 4))
        self.recovery_questions = [
            "What was the name of your first pet?",
            "What was your childhood nickname?",
            "In what city were you born?",
            "What is your mother's maiden name?",
            "What was the name of your first school?",
            "What is your favorite book?"
        ]
        self.e_r_question_var = ctk.StringVar(value=self.recovery_questions[0])
        self.e_r_question = ctk.CTkOptionMenu(
            panel,
            values=self.recovery_questions,
            variable=self.e_r_question_var,
            height=40,
            corner_radius=12,
            fg_color=WHITE,
            button_color=TEAL_LIGHT,
            button_hover_color="#EDF6F3",
            text_color=TEXT,
            dropdown_fg_color=WHITE,
            dropdown_hover_color=TEAL_LIGHT,
            dropdown_text_color=TEXT,
            font=("Segoe UI", 12),
        )
        self.e_r_question.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        make_label(panel, "Security Answer", 12, "bold").grid(row=10, column=0, columnspan=2, sticky="w", pady=(12, 4))
        self.e_r_answer = make_entry(panel, "Enter your secret answer")
        self.e_r_answer.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        self.lbl_reg_status = make_label(panel, "", 11, color=DANGER, wraplength=440, justify="left")
        self.lbl_reg_status.grid(row=12, column=0, columnspan=2, sticky="w", pady=(8, 10))

        make_button(panel, "Sign Up", self._do_register, height=44).grid(
            row=13,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(0, 8),
        )
        make_label(
            panel,
            "This sign-up page is for guest accounts only. Your details will be stored in the booking database.",
            11,
            color=SUBTEXT,
            wraplength=440,
            justify="left",
        ).grid(row=14, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self._register_panel = panel

    def _switch_tab(self, tab: str) -> None:
        if self.register_only:
            tab = "register"
        self._tab.set(tab)
        self._clear_statuses()

        # Show back button only on the register tab
        if hasattr(self, "_back_btn"):
            if tab == "register":
                self._back_btn.grid()
            else:
                self._back_btn.grid_remove()

        if tab == "login":
            self._register_panel.grid_remove()
            self._login_panel.grid(row=0, column=0, sticky="ew")
            if self._btn_login is not None:
                self._btn_login.configure(fg_color=TEAL, text_color=WHITE, font=("Segoe UI", 12, "bold"))
            if self._btn_reg is not None:
                self._btn_reg.configure(fg_color="transparent", text_color=SUBTEXT, font=("Segoe UI", 12))
            self.after(40, self.e_username.focus_set)
            return

        self._login_panel.grid_remove()
        self._register_panel.grid(row=0, column=0, sticky="ew")
        if self._btn_reg is not None:
            self._btn_reg.configure(fg_color=TEAL, text_color=WHITE, font=("Segoe UI", 12, "bold"))
        if self._btn_login is not None:
            self._btn_login.configure(fg_color="transparent", text_color=SUBTEXT, font=("Segoe UI", 12))
        self.after(40, self.e_r_name.focus_set)

    def _go_back_to_login(self) -> None:
        """Navigate back to the login page."""
        if self.register_only:
            # In register-only mode (RMS integrated), close the portal
            self.app.logout()
        else:
            # In full mode, just switch to the login tab
            self._switch_tab("login")

    def _clear_statuses(self) -> None:
        self.lbl_login_status.configure(text="", text_color=DANGER)
        self.lbl_reg_status.configure(text="", text_color=DANGER)

    def _set_login_status(self, message: str, success: bool = False) -> None:
        self.lbl_login_status.configure(text=message, text_color=SUCCESS_TEXT if success else DANGER)

    def _set_register_status(self, message: str, success: bool = False) -> None:
        self.lbl_reg_status.configure(text=message, text_color=SUCCESS_TEXT if success else DANGER)

    def _do_login(self) -> None:
        self._set_login_status("")
        ok, msg = self.ctrl.login(self.e_username.get(), self.e_password.get())
        if not ok:
            self._set_login_status(msg)
            return
        from views.browse_view import BrowseView

        self._set_login_status(msg, success=True)
        self.app.navigate(BrowseView)

    def _do_register(self) -> None:
        self._set_register_status("")
        username = self.e_r_user.get().strip().lower()
        password = self.e_r_pass.get()
        ok, msg = self.ctrl.register(
            username,
            password,
            self.e_r_confirm.get(),
            self.e_r_name.get(),
            self.e_r_contact.get(),
            self.e_r_email.get(),
            self.e_r_question_var.get(),
            self.e_r_answer.get().strip()
        )
        if not ok:
            self._set_register_status(msg)
            return

        login_ok, login_msg = self.ctrl.login(username, password)
        if not login_ok:
            self._set_register_status(
                "Guest account was created, but automatic sign in failed. Please sign in manually.",
                success=False,
            )
            if not self.register_only:
                self.e_username.delete(0, "end")
                self.e_username.insert(0, username)
                self.e_password.delete(0, "end")
                self._switch_tab("login")
                self._set_login_status(login_msg)
            return

        for field in (
            self.e_r_name,
            self.e_r_user,
            self.e_r_contact,
            self.e_r_email,
            self.e_r_pass,
            self.e_r_confirm,
            self.e_r_answer,
        ):
            field.delete(0, "end")
        self._set_register_status("Guest account created successfully. Opening your portal...", success=True)
        from views.browse_view import BrowseView

        self.after(120, lambda: self.app.navigate(BrowseView))

    def _open_recovery_dialog(self) -> None:
        # We will implement this in RMS as well, so I'll create a reusable one or 
        # just show a notice for now and implement it in the next step.
        from tkinter import messagebox
        messagebox.showinfo("Forgot Password", "Password recovery is being handled by the main application dashboard.")

if __name__ == "__main__":
    class MockApp(ctk.CTk):
        def __init__(self):
            super().__init__()
            self.title("Login View Preview")
            self.geometry("800x600")
            
            # Use real app logic if possible, otherwise use dummy
            try:
                from k3_user.app import GuestPortalShell
                self.shell = GuestPortalShell(self)
                self.shell.pack(fill="both", expand=True)
            except Exception:
                # Fallback to direct view
                self.view = LoginView(self, self, auth_mode="full")
                self.view.pack(fill="both", expand=True)

        def navigate(self, *args, **kwargs):
            print(f"Navigation requested to: {args}")

    app = MockApp()
    app.mainloop()
