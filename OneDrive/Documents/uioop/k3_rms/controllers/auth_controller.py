from dataclasses import dataclass

from k3_rms.config import AppLoginSettings
from k3_user.models.user_model import UserModel
from k3_rms.services.auth_service import AuthService


@dataclass(frozen=True)
class AuthResult:
    role: str
    username: str
    session_user: dict


class AuthController:
    def __init__(self, auth_service: AuthService | None = None) -> None:
        self.auth_service = auth_service

    def login(self, username: str, plain_password: str) -> AuthResult | None:
        normalized_username = username.strip()
        admin_user = self._admin_login_info(normalized_username, plain_password)
        if admin_user:
            return AuthResult(
                role="admin",
                username=normalized_username,
                session_user={**admin_user, "role": "admin"},
            )

        user = UserModel.login(normalized_username, plain_password)
        if user is None:
            return None

        return AuthResult(
            role="user",
            username=user["username"],
            session_user={**user, "role": "user"},
        )

    def _admin_login_info(self, username: str, plain_password: str) -> dict | None:
        if self.auth_service is None:
            settings = AppLoginSettings.from_env()
            if username == settings.username and plain_password == settings.password:
                return {"username": username, "recovery_question": None}
            return None
        return self.auth_service.login(username, plain_password)

    def change_credentials(
        self,
        current_username: str,
        current_password: str,
        new_username: str,
        new_password: str,
    ) -> tuple[bool, str]:
        normalized_current = current_username.strip()
        desired_username = new_username.strip() or normalized_current
        desired_password = new_password or current_password

        if not desired_username:
            return False, "Username cannot be empty."
        if new_password and len(new_password) < 6:
            return False, "New password must be at least 6 characters long."

        if self.auth_service is None:
            settings = AppLoginSettings.from_env()
            if normalized_current != settings.username or current_password != settings.password:
                return False, "Incorrect current password. Cannot change credentials."
            AppLoginSettings.persist(desired_username, desired_password)
            return True, "Admin credentials updated successfully!"

        success, message = self.auth_service.change_credentials(
            normalized_current,
            current_password,
            new_username,
            new_password,
        )
        if success:
            AppLoginSettings.persist(desired_username, desired_password)
        return success, message

    def change_username(self, current_username: str, current_password: str, new_username: str) -> tuple[bool, str]:
        return self.change_credentials(current_username, current_password, new_username, "")

    def change_password(self, username: str, old_password: str, new_password: str) -> tuple[bool, str]:
        return self.change_credentials(username, old_password, "", new_password)

    def get_recovery_info(self, username: str) -> dict | None:
        """Proxies to the appropriate model based on username presence."""
        # Try Admin first
        if self.auth_service:
            info = self.auth_service.get_recovery_info(username)
            if info:
                return {"question": info.get("recovery_question"), "role": "admin"}
        
        # Then try Guest
        user = UserModel.get_user(username)
        if user:
            return {"question": user.get("recovery_question"), "role": "user"}
        
        return None

    def reset_password(self, username: str, role: str, answer: str, new_password: str, confirm: str) -> tuple[bool, str]:
        """Resets password after role-specific verification and confirmation check."""
        if not new_password or new_password != confirm:
            return False, "Passwords do not match."
        if len(new_password) < 6:
            return False, "Password must be at least 6 characters."

        if role == "admin":
            if not self.auth_service:
                return False, "Database connection required for admin reset."
            return self.auth_service.verify_and_reset_password(username, answer, new_password)
        
        return UserModel.verify_and_reset_password(username, answer, new_password)

    def update_recovery_info(self, username: str, role: str, question: str, answer: str) -> bool:
        """Updates recovery info for the logged in user."""
        if role == "admin":
            if self.auth_service:
                return self.auth_service.update_recovery_info(username, question, answer)
            return False
        
        return UserModel.update(username, recovery_question=question, recovery_answer=answer)
