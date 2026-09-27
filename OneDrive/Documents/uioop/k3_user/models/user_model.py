"""User / guest account auth and profile persistence."""

import hashlib

import bcrypt

from k3_user.db import get_database


def _legacy_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _serialize_user(row: dict) -> dict:
    return {
        "id": row["id"],
        "username": row["username"],
        "name": row.get("full_name") or "",
        "contact": row.get("contact_number") or "",
        "email": row.get("email") or "",
        "recovery_question": row.get("recovery_question"),
    }


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, stored_hash: str, scheme: str) -> bool:
    if scheme == "sha256":
        return _legacy_hash(password) == stored_hash
    return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))


def _fetch_user(username: str) -> dict | None:
    database = get_database()
    with database.session() as (_, cursor):
        cursor.execute(
            """
            SELECT
                u.id,
                u.username,
                u.password,
                u.password_scheme,
                COALESCE(c.full_name, u.full_name) AS full_name,
                COALESCE(c.contact_number, u.contact_number) AS contact_number,
                COALESCE(c.email, u.email) AS email,
                u.status,
                u.recovery_question,
                u.recovery_answer,
                c.id AS customer_id
            FROM users u
            LEFT JOIN customers c
                ON c.user_id = u.id
               AND c.is_deleted = 0
            WHERE u.username = %s
            LIMIT 1
            """,
            (username,),
        )
        return cursor.fetchone()


def _upgrade_legacy_password(user_id: int, password: str) -> None:
    database = get_database()
    with database.session() as (_, cursor):
        cursor.execute(
            """
            UPDATE users
            SET password = %s, password_scheme = 'bcrypt'
            WHERE id = %s
            """,
            (_hash_password(password), user_id),
        )


def _find_conflict(username: str, email: str | None, contact: str | None, exclude_user_id: int | None = None) -> tuple[bool, str]:
    clauses = ["username = %s"]
    params: list[object] = [username]
    if email:
        clauses.append("email = %s")
        params.append(email)
    if contact:
        clauses.append("contact_number = %s")
        params.append(contact)
    query = (
        "SELECT id, username, email, contact_number FROM users WHERE ("
        + " OR ".join(clauses)
        + ")"
    )
    if exclude_user_id is not None:
        query += " AND id <> %s"
        params.append(exclude_user_id)
    database = get_database()
    with database.session() as (_, cursor):
        cursor.execute(query, tuple(params))
        for row in cursor.fetchall():
            if row["username"] == username:
                return True, "Username already exists."
            if email and row.get("email") == email:
                return True, "Email address is already in use."
            if contact and row.get("contact_number") == contact:
                return True, "Contact number is already in use."
    return False, ""


def _upsert_customer_profile(user_id: int, full_name: str, contact: str | None, email: str | None) -> None:
    database = get_database()
    clauses = ["user_id = %s"]
    values: list[object] = [user_id]
    if email:
        clauses.append("email = %s")
        values.append(email)
    if contact:
        clauses.append("contact_number = %s")
        values.append(contact)

    with database.session() as (_, cursor):
        cursor.execute(
            """
            SELECT id, full_name, contact_number, email
            FROM customers
            WHERE """
            + " OR ".join(clauses)
            + """
            ORDER BY CASE WHEN user_id = %s THEN 0 ELSE 1 END, id ASC
            LIMIT 1
            """,
            tuple(values + [user_id]),
        )
        existing = cursor.fetchone()
        if existing:
            cursor.execute(
                """
                UPDATE customers
                SET user_id = %s,
                    full_name = %s,
                    contact_number = %s,
                    email = %s
                WHERE id = %s
                """,
                (user_id, full_name, contact, email, existing["id"]),
            )
            return

        cursor.execute(
            """
            INSERT INTO customers (user_id, full_name, contact_number, email)
            VALUES (%s, %s, %s, %s)
            """,
            (user_id, full_name, contact, email),
        )


class UserModel:
    """All user/auth operations."""

    @staticmethod
    def login(username: str, password: str) -> dict | None:
        normalized = username.strip().lower()
        if not normalized:
            return None
        row = _fetch_user(normalized)
        if row is None or row.get("status") != "active":
            return None
        scheme = row.get("password_scheme") or "bcrypt"
        if not _verify_password(password, row["password"], scheme):
            return None
        if scheme == "sha256":
            _upgrade_legacy_password(row["id"], password)
            row["password_scheme"] = "bcrypt"
        return _serialize_user(row)

    @staticmethod
    def register(username: str, password: str, name: str, contact: str, email: str, 
                 recovery_question: str = None, recovery_answer: str = None) -> tuple[bool, str]:
        normalized = username.strip().lower()
        if not normalized or not password:
            return False, "Username and password are required."
        full_name = name.strip()
        contact_number = contact.strip() or None
        email_address = email.strip() or None

        has_conflict, message = _find_conflict(normalized, email_address, contact_number)
        if has_conflict:
            return False, message

        # Hash recovery answer if provided
        hashed_answer = _hash_password(recovery_answer) if recovery_answer else None

        database = get_database()
        with database.session() as (_, cursor):
            cursor.execute(
                """
                INSERT INTO users (
                    username,
                    password,
                    password_scheme,
                    full_name,
                    contact_number,
                    email,
                    status,
                    recovery_question,
                    recovery_answer
                )
                VALUES (%s, %s, 'bcrypt', %s, %s, %s, 'active', %s, %s)
                """,
                (normalized, _hash_password(password), full_name, contact_number, email_address, recovery_question, hashed_answer),
            )
            user_id = cursor.lastrowid
        _upsert_customer_profile(user_id, full_name, contact_number, email_address)
        return True, "Account created successfully."

    @staticmethod
    def get_user(username: str) -> dict | None:
        normalized = username.strip().lower()
        row = _fetch_user(normalized)
        if row is None:
            return None
        return {
            "id": row["id"],
            "username": row["username"],
            "password": row["password"],
            "full_name": row.get("full_name") or "",
            "name": row.get("full_name") or "",
            "contact_number": row.get("contact_number") or "",
            "contact": row.get("contact_number") or "",
            "email": row.get("email") or "",
            "status": row.get("status") or "active",
            "password_scheme": row.get("password_scheme") or "bcrypt",
            "recovery_question": row.get("recovery_question"),
            "recovery_answer": row.get("recovery_answer"),
        }

    @staticmethod
    def update(username: str, **kwargs) -> bool:
        normalized = username.strip().lower()
        row = _fetch_user(normalized)
        if row is None:
            return False

        full_name = (kwargs.get("name") or row.get("full_name") or "").strip()
        contact_number = (kwargs.get("contact") if "contact" in kwargs else row.get("contact_number")) or None
        email_address = (kwargs.get("email") if "email" in kwargs else row.get("email")) or None
        password = kwargs.get("password")
        
        recovery_question = kwargs.get("recovery_question") or row.get("recovery_question")
        recovery_answer = kwargs.get("recovery_answer")
        if recovery_answer:
            recovery_answer = _hash_password(recovery_answer)
        else:
            recovery_answer = row.get("recovery_answer")

        has_conflict, _ = _find_conflict(normalized, email_address, contact_number, exclude_user_id=row["id"])
        if has_conflict:
            return False

        database = get_database()
        with database.session() as (_, cursor):
            if password:
                cursor.execute(
                    """
                    UPDATE users
                    SET full_name = %s,
                        contact_number = %s,
                        email = %s,
                        password = %s,
                        password_scheme = 'bcrypt',
                        recovery_question = %s,
                        recovery_answer = %s
                    WHERE id = %s
                    """,
                    (full_name, contact_number, email_address, _hash_password(password), recovery_question, recovery_answer, row["id"]),
                )
            else:
                cursor.execute(
                    """
                    UPDATE users
                    SET full_name = %s,
                        contact_number = %s,
                        email = %s,
                        recovery_question = %s,
                        recovery_answer = %s
                    WHERE id = %s
                    """,
                    (full_name, contact_number, email_address, recovery_question, recovery_answer, row["id"]),
                )
        _upsert_customer_profile(row["id"], full_name, contact_number, email_address)
        return True

    @staticmethod
    def verify_and_reset_password(username: str, answer: str, new_password: str) -> tuple[bool, str]:
        normalized = username.strip().lower()
        row = _fetch_user(normalized)
        if not row:
            return False, "User not found."
        
        if not row.get("recovery_answer"):
            return False, "Recovery information not set for this account. Please contact Admin."
            
        if not _verify_password(answer, row["recovery_answer"], "bcrypt"):
            return False, "Incorrect recovery answer."
            
        database = get_database()
        with database.session() as (_, cursor):
            cursor.execute(
                "UPDATE users SET password = %s, password_scheme = 'bcrypt' WHERE id = %s",
                (_hash_password(new_password), row["id"])
            )
        return True, "Password reset successfully."

    @staticmethod
    def get_customer_record(username: str) -> dict | None:
        normalized = username.strip().lower()
        row = _fetch_user(normalized)
        if row is None:
            return None
        database = get_database()
        with database.session() as (_, cursor):
            cursor.execute(
                """
                SELECT id, user_id, full_name, contact_number, email
                FROM customers
                WHERE user_id = %s
                LIMIT 1
                """,
                (row["id"],),
            )
            customer = cursor.fetchone()
        if customer is not None:
            return customer
        _upsert_customer_profile(
            row["id"],
            row.get("full_name") or "",
            row.get("contact_number") or None,
            row.get("email") or None,
        )
        with database.session() as (_, cursor):
            cursor.execute(
                """
                SELECT id, user_id, full_name, contact_number, email
                FROM customers
                WHERE user_id = %s
                LIMIT 1
                """,
                (row["id"],),
            )
            return cursor.fetchone()
