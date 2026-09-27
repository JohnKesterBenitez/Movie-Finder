import bcrypt
from k3_rms.database.connection import DatabaseManager


class AuthService:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def login(self, username: str, plain_password: str) -> dict | None:
        """Authenticates an admin user using bcrypt. Returns user dict or None."""
        query = "SELECT id, username, password, recovery_question FROM admin_users WHERE username = %s"
        with self.database.session() as (_, cursor):
            cursor.execute(query, (username,))
            user = cursor.fetchone()
            
            if user:
                stored_hash = user['password'].encode('utf-8')
                if bcrypt.checkpw(plain_password.encode('utf-8'), stored_hash):
                    return user
        return None

    def change_username(self, current_username: str, current_password: str, new_username: str) -> tuple[bool, str]:
        """Changes the username after verifying the current password."""
        if not new_username or len(new_username.strip()) == 0:
            return False, "Username cannot be empty."

        with self.database.session() as (_, cursor):
            # Verify current password
            cursor.execute("SELECT id, password FROM admin_users WHERE username = %s", (current_username,))
            user = cursor.fetchone()
            
            if not user or not bcrypt.checkpw(current_password.encode('utf-8'), user['password'].encode('utf-8')):
                return False, "Incorrect current password. Cannot change username."
                
            # Check if new username already exists
            cursor.execute("SELECT id FROM admin_users WHERE username = %s", (new_username,))
            if cursor.fetchone():
                return False, f"The username '{new_username}' is already taken."
                
            # Update to the new username
            update_query = "UPDATE admin_users SET username = %s WHERE id = %s"
            cursor.execute(update_query, (new_username, user['id']))
            return True, "Username updated successfully!"

    def change_password(self, username: str, old_password: str, new_password: str) -> tuple[bool, str]:
        """Changes the password after verifying the old password."""
        if not new_password or len(new_password) < 6:
            return False, "New password must be at least 6 characters long."

        with self.database.session() as (_, cursor):
            # Verify old password
            cursor.execute("SELECT id, password FROM admin_users WHERE username = %s", (username,))
            user = cursor.fetchone()
            
            if not user or not bcrypt.checkpw(old_password.encode('utf-8'), user['password'].encode('utf-8')):
                return False, "Incorrect old password. Cannot change password."
                
            # Hash the new password securely
            new_hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            
            # Update the database
            update_query = "UPDATE admin_users SET password = %s WHERE id = %s"
            cursor.execute(update_query, (new_hashed_password.decode('utf-8'), user['id']))
            return True, "Password updated successfully!"

    def change_credentials(
        self,
        current_username: str,
        current_password: str,
        new_username: str,
        new_password: str,
    ) -> tuple[bool, str]:
        """Changes admin credentials in one verified update."""
        normalized_current = current_username.strip()
        next_username = new_username.strip() or normalized_current

        if not next_username:
            return False, "Username cannot be empty."
        if new_password and len(new_password) < 6:
            return False, "New password must be at least 6 characters long."

        with self.database.session() as (_, cursor):
            cursor.execute(
                "SELECT id, password FROM admin_users WHERE username = %s",
                (normalized_current,),
            )
            user = cursor.fetchone()

            if not user or not bcrypt.checkpw(current_password.encode("utf-8"), user["password"].encode("utf-8")):
                return False, "Incorrect current password. Cannot change credentials."

            if next_username != normalized_current:
                cursor.execute("SELECT id FROM admin_users WHERE username = %s", (next_username,))
                existing = cursor.fetchone()
                if existing and existing["id"] != user["id"]:
                    return False, f"The username '{next_username}' is already taken."

            next_password_hash = user["password"]
            if new_password:
                next_password_hash = bcrypt.hashpw(
                    new_password.encode("utf-8"),
                    bcrypt.gensalt(),
                ).decode("utf-8")

            cursor.execute(
                "UPDATE admin_users SET username = %s, password = %s WHERE id = %s",
                (next_username, next_password_hash, user["id"]),
            )
            return True, "Admin credentials updated successfully!"

    def get_recovery_info(self, username: str) -> dict | None:
        """Fetches recovery question for an admin user."""
        query = "SELECT recovery_question, recovery_answer FROM admin_users WHERE username = %s"
        with self.database.session() as (_, cursor):
            cursor.execute(query, (username,))
            return cursor.fetchone()

    def update_recovery_info(self, username: str, question: str, answer: str) -> bool:
        """Updates recovery question and hashed answer for an admin user."""
        hashed_answer = bcrypt.hashpw(answer.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        query = "UPDATE admin_users SET recovery_question = %s, recovery_answer = %s WHERE username = %s"
        with self.database.session() as (_, cursor):
            cursor.execute(query, (question, hashed_answer, username))
            return True

    def verify_and_reset_password(self, username: str, answer: str, new_password: str) -> tuple[bool, str]:
        """Verifies recovery answer and resets admin password."""
        info = self.get_recovery_info(username)
        if not info or not info.get('recovery_answer'):
            return False, "Recovery information not set for this admin account."
            
        if not bcrypt.checkpw(answer.encode('utf-8'), info['recovery_answer'].encode('utf-8')):
            return False, "Incorrect recovery answer."
            
        new_hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        query = "UPDATE admin_users SET password = %s WHERE username = %s"
        with self.database.session() as (_, cursor):
            cursor.execute(query, (new_hashed_password, username))
            return True, "Admin password reset successfully."
