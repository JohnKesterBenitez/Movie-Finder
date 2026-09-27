"""
controllers/login_controller.py — Handles login and registration logic.
"""

from models.user_model import UserModel


class LoginController:

    def __init__(self, app):
        self.app = app
        self.session_user = None   # set after successful login

    # ── Login ─────────────────────────────────────────────────────────────────
    def login(self, username: str, password: str) -> tuple[bool, str]:
        user = UserModel.login(username, password)
        if user is None:
            return False, "Invalid username or password."
        self.app.session_user = user          # store in app for all pages
        return True, "Login successful."

    # ── Register ──────────────────────────────────────────────────────────────
    def register(self, username: str, password: str, confirm: str,
                 name: str, contact: str, email: str,
                 recovery_question: str = None, recovery_answer: str = None) -> tuple[bool, str]:
        if password != confirm:
            return False, "Passwords do not match."
        if len(password) < 6:
            return False, "Password must be at least 6 characters."
        if not name.strip():
            return False, "Full name is required."
        if not contact.strip():
            return False, "Contact number is required."
        if not recovery_question or not recovery_answer:
            return False, "Security question and answer are required."
        return UserModel.register(username, password, name, contact, email, recovery_question, recovery_answer)

    # ── Recovery ──────────────────────────────────────────────────────────────
    def reset_password(self, username: str, answer: str, new_password: str, confirm: str) -> tuple[bool, str]:
        if not username or not answer or not new_password:
            return False, "All fields are required."
        if new_password != confirm:
            return False, "Passwords do not match."
        if len(new_password) < 6:
            return False, "Password must be at least 6 characters."
        return UserModel.verify_and_reset_password(username, answer, new_password)

    # ── Update ────────────────────────────────────────────────────────────────
    def update_profile(self, username: str, **kwargs) -> tuple[bool, str]:
        # Validate password if provided
        confirm = kwargs.pop("confirm_password", None)
        pw = kwargs.get("password")
        if pw:
            if pw != confirm:
                return False, "Passwords do not match."
            if len(pw) < 6:
                return False, "Password must be at least 6 characters."
        
        # Remove empty password if not being changed
        if "password" in kwargs and not kwargs["password"]:
            kwargs.pop("password")

        ok = UserModel.update(username, **kwargs)
        if ok:
            # Refresh session user
            updated = UserModel.get_user(username)
            if updated:
                self.app.session_user = {"username": username, **{k: v for k, v in updated.items() if k != "password"}}
            return True, "Profile updated successfully."
        return False, "Failed to update profile."
