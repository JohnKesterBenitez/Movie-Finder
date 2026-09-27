import json
from k3_rms.database.connection import DatabaseManager


class CustomerModel:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def find_by_id(self, customer_id: int) -> dict | None:
        with self.database.session() as (_, cursor):
            cursor.execute(
                "SELECT id, full_name, contact_number, email, created_at FROM customers WHERE id = %s",
                (customer_id,),
            )
            return cursor.fetchone()

    def find_by_user_id(self, user_id: int) -> dict | None:
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                SELECT id, user_id, full_name, contact_number, email, created_at, updated_at
                FROM customers
                WHERE user_id = %s AND is_deleted = 0
                LIMIT 1
                """,
                (user_id,),
            )
            return cursor.fetchone()

    def find_known_customer(self, email: str | None, contact_number: str | None) -> dict | None:
        clauses = []
        values = []
        if email:
            clauses.append("email = %s")
            values.append(email)
        if contact_number:
            clauses.append("contact_number = %s")
            values.append(contact_number)
        if not clauses:
            return None
        query = (
            "SELECT id, full_name, contact_number, email, created_at, updated_at "
            "FROM customers WHERE (" + " OR ".join(clauses) + ") AND is_deleted = 0 LIMIT 1"
        )
        with self.database.session() as (_, cursor):
            cursor.execute(query, tuple(values))
            return cursor.fetchone()

    def upsert_customer(
        self,
        full_name: str,
        contact_number: str | None,
        email: str | None,
        user_id: int | None = None,
    ) -> dict:
        if user_id is not None:
            existing_by_user = self.find_by_user_id(user_id)
            if existing_by_user:
                merged_name = full_name or existing_by_user["full_name"]
                merged_contact = contact_number or existing_by_user["contact_number"]
                merged_email = email or existing_by_user["email"]
                with self.database.session() as (_, cursor):
                    cursor.execute(
                        """
                        UPDATE customers
                        SET full_name = %s,
                            contact_number = %s,
                            email = %s
                        WHERE id = %s
                        """,
                        (merged_name, merged_contact, merged_email, existing_by_user["id"]),
                    )
                return self.find_by_user_id(user_id)

        existing = self.find_known_customer(email, contact_number)
        if existing:
            merged_name = full_name or existing["full_name"]
            merged_contact = contact_number or existing["contact_number"]
            merged_email = email or existing["email"]
            with self.database.session() as (_, cursor):
                cursor.execute(
                    """
                    UPDATE customers
                    SET user_id = COALESCE(%s, user_id),
                        full_name = %s,
                        contact_number = %s,
                        email = %s
                    WHERE id = %s
                    """,
                    (user_id, merged_name, merged_contact, merged_email, existing["id"]),
                )
            if user_id is not None:
                return self.find_by_user_id(user_id)
            return self.find_known_customer(merged_email, merged_contact)
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                INSERT INTO customers (user_id, full_name, contact_number, email)
                VALUES (%s, %s, %s, %s)
                """,
                (user_id, full_name, contact_number, email),
            )
        if user_id is not None:
            return self.find_by_user_id(user_id)
        return self.find_known_customer(email, contact_number)

    def delete_customer(self, customer_id: int) -> bool:
        """Soft-delete a customer and log to trash_bin."""
        customer = self.find_by_id(customer_id)
        if not customer:
            return False

        with self.database.session() as (_, cursor):
            # 1. Update flag
            cursor.execute(
                "UPDATE customers SET is_deleted = 1 WHERE id = %s",
                (customer_id,),
            )
            # 2. Log to trash bin
            cursor.execute(
                "INSERT INTO trash_bin (record_type, record_id, record_ref, original_data) VALUES (%s, %s, %s, %s)",
                (
                    "customer",
                    customer_id,
                    customer["full_name"],
                    json.dumps(customer, default=str),
                ),
            )
            return cursor.rowcount > 0
