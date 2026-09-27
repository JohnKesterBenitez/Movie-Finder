import bcrypt

from k3_rms.config import (
    AppLoginSettings,
    DEFAULT_COTTAGES,
    DEFAULT_DESTINATION_ASSETS,
    PENDING_APPROVAL_DEADLINE_HOURS,
)
from k3_rms.database.connection import DatabaseManager


class SchemaManager:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database
        self.warnings: list[str] = []

    def initialize(self) -> list[str]:
        self.database.connect()
        self._drop_derived_objects()
        self._ensure_admin_users_table()
        self._ensure_cottages_table()
        self._ensure_destinations_table()
        self._ensure_users_table()
        self._ensure_customers_table()
        self._ensure_reservations_table()
        self._ensure_trash_bin_table()
        self._migrate_pending_status()
        for table_name in ("admin_users", "users", "destinations"):
            self._normalize_table_collation(table_name)
        self._seed_assets("cottages", DEFAULT_COTTAGES)
        self._seed_assets("destinations", DEFAULT_DESTINATION_ASSETS)
        self._migrate_reservations_to_destinations()
        self._seed_admin()
        self._sync_user_customer_profiles()
        self._finalize_reservations_table()
        self._ensure_reservation_destinations_table()
        self._ensure_payments_table()
        self._backfill_payments_from_reservations()
        self._ensure_payment_logs_table()
        self._normalize_payment_methods()
        self._ensure_audit_logs_table()
        self._cleanup_redundant_columns()
        routines_enabled = self._create_functions()
        self._create_procedures(routines_enabled=routines_enabled)
        self._create_triggers(routines_enabled=routines_enabled)
        self._create_events(routines_enabled=routines_enabled)
        self._create_views(routines_enabled=routines_enabled)
        return list(self.warnings)

    def _drop_derived_objects(self) -> None:
        with self.database.session() as (_, cursor):
            cursor.execute("DROP VIEW IF EXISTS vw_active_reservations")

    def _ensure_admin_users_table(self) -> None:
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS admin_users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    full_name VARCHAR(120) NOT NULL DEFAULT 'Administrator',
                    contact_number VARCHAR(30) NULL,
                    email VARCHAR(120) NULL,
                    role ENUM('admin') NOT NULL DEFAULT 'admin',
                    recovery_question VARCHAR(255) NULL,
                    recovery_answer VARCHAR(255) NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )
        self._add_column_if_missing(
            "admin_users",
            "full_name",
            "ALTER TABLE admin_users ADD COLUMN full_name VARCHAR(120) NOT NULL DEFAULT 'Administrator' AFTER password",
        )
        self._add_column_if_missing(
            "admin_users",
            "contact_number",
            "ALTER TABLE admin_users ADD COLUMN contact_number VARCHAR(30) NULL AFTER full_name",
        )
        self._add_column_if_missing(
            "admin_users",
            "email",
            "ALTER TABLE admin_users ADD COLUMN email VARCHAR(120) NULL AFTER contact_number",
        )
        self._add_column_if_missing(
            "admin_users",
            "role",
            "ALTER TABLE admin_users ADD COLUMN role ENUM('admin') NOT NULL DEFAULT 'admin' AFTER email",
        )
        self._add_column_if_missing(
            "admin_users",
            "updated_at",
            "ALTER TABLE admin_users ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at",
        )
        self._add_column_if_missing(
            "admin_users",
            "recovery_question",
            "ALTER TABLE admin_users ADD COLUMN recovery_question VARCHAR(255) NULL AFTER role",
        )
        self._add_column_if_missing(
            "admin_users",
            "recovery_answer",
            "ALTER TABLE admin_users ADD COLUMN recovery_answer VARCHAR(255) NULL AFTER recovery_question",
        )

    def _ensure_users_table(self) -> None:
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    password_scheme ENUM('bcrypt', 'sha256') NOT NULL DEFAULT 'bcrypt',
                    full_name VARCHAR(120) NOT NULL,
                    contact_number VARCHAR(30) NULL UNIQUE,
                    email VARCHAR(120) NULL UNIQUE,
                    status ENUM('active', 'inactive') NOT NULL DEFAULT 'active',
                    recovery_question VARCHAR(255) NULL,
                    recovery_answer VARCHAR(255) NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )
        self._add_column_if_missing(
            "users",
            "recovery_question",
            "ALTER TABLE users ADD COLUMN recovery_question VARCHAR(255) NULL AFTER status",
        )
        self._add_column_if_missing(
            "users",
            "recovery_answer",
            "ALTER TABLE users ADD COLUMN recovery_answer VARCHAR(255) NULL AFTER recovery_question",
        )

    def _ensure_cottages_table(self) -> None:
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS cottages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    asset_code VARCHAR(20) NOT NULL UNIQUE,
                    name VARCHAR(100) NOT NULL,
                    capacity INT NOT NULL,
                    base_rate DECIMAL(10, 2) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        self._drop_column_if_exists("cottages", "status")

    def _ensure_destinations_table(self) -> None:
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS destinations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    asset_code VARCHAR(20) NOT NULL UNIQUE,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    capacity INT NOT NULL,
                    base_rate DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )
        self._drop_column_if_exists("destinations", "status")

    def _ensure_customers_table(self) -> None:
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS customers (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NULL UNIQUE,
                    full_name VARCHAR(120) NOT NULL,
                    contact_number VARCHAR(30) NULL UNIQUE,
                    email VARCHAR(120) NULL UNIQUE,
                    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
                """
            )
        self._add_column_if_missing(
            "customers",
            "user_id",
            "ALTER TABLE customers ADD COLUMN user_id INT NULL UNIQUE FIRST",
        )
        self._add_column_if_missing(
            "customers",
            "is_deleted",
            "ALTER TABLE customers ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0 AFTER email",
        )
        self._create_foreign_key_if_missing(
            "customers",
            "fk_customers_user",
            """
            ALTER TABLE customers
            ADD CONSTRAINT fk_customers_user
            FOREIGN KEY (user_id) REFERENCES users (id)
            """,
        )

    def _ensure_reservations_table(self) -> None:
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS reservations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    reservation_code VARCHAR(30) NOT NULL UNIQUE,
                    user_id INT NULL,
                    customer_id INT NOT NULL,
                    cottage_id INT NOT NULL,
                    destination_id INT NULL,
                    party_size INT NOT NULL,
                    departure_time DATETIME NOT NULL,
                    return_time DATETIME NOT NULL,
                    total_price DECIMAL(10, 2) NOT NULL,
                    status ENUM('Pending', 'Reserved', 'On Going', 'Completed', 'Cancelled') NOT NULL DEFAULT 'Pending',
                    notes TEXT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    completed_at DATETIME NULL,
                    cancelled_at DATETIME NULL,
                    is_deleted TINYINT(1) NOT NULL DEFAULT 0
                )
                """
            )
        self._add_column_if_missing(
            "reservations",
            "user_id",
            "ALTER TABLE reservations ADD COLUMN user_id INT NULL AFTER reservation_code",
        )
        self._add_column_if_missing(
            "reservations",
            "destination_id",
            "ALTER TABLE reservations ADD COLUMN destination_id INT NULL AFTER cottage_id",
        )
        self._add_column_if_missing(
            "reservations",
            "is_deleted",
            "ALTER TABLE reservations ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0",
        )
        self._add_column_if_missing(
            "reservations",
            "is_deleted",
            "ALTER TABLE reservations ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0",
        )
        self._create_index_if_missing(
            "reservations",
            "idx_reservations_status_schedule",
            "ALTER TABLE reservations ADD INDEX idx_reservations_status_schedule (status, departure_time, return_time)",
        )
        if self._column_exists("reservations", "billing_status") and self._column_exists("reservations", "payment_status"):
            with self.database.session() as (_, cursor):
                cursor.execute(
                    """
                    UPDATE reservations
                    SET payment_status = billing_status
                    WHERE COALESCE(payment_status, 'Unpaid') <> COALESCE(billing_status, 'Unpaid')
                    """
                )

    def _migrate_reservations_to_destinations(self) -> None:
        if not self._table_exists("reservations"):
            return

        # self._seed_destinations_from_reservation_names()

        if self._column_exists("reservations", "destination"):
            with self.database.session() as (_, cursor):
                cursor.execute(
                    """
                    UPDATE reservations r
                    INNER JOIN destinations d
                        ON d.name COLLATE utf8mb4_unicode_ci = r.destination COLLATE utf8mb4_unicode_ci
                    SET r.destination_id = d.id
                    WHERE r.destination_id IS NULL
                    """
                )

        if self._column_exists("reservations", "motorboat_id") and self._table_exists("motorboats"):
            self._seed_destinations_from_legacy_motorboats()
            with self.database.session() as (_, cursor):
                cursor.execute(
                    """
                    UPDATE reservations r
                    INNER JOIN motorboats m ON m.id = r.motorboat_id
                    LEFT JOIN destinations d
                        ON d.name COLLATE utf8mb4_general_ci = m.name COLLATE utf8mb4_general_ci
                    SET r.destination_id = COALESCE(r.destination_id, d.id)
                    WHERE r.destination_id IS NULL
                    """
                )

        # self._seed_destinations_from_reservation_names()
        if self._column_exists("reservations", "destination"):
            with self.database.session() as (_, cursor):
                cursor.execute(
                    """
                    UPDATE reservations r
                    INNER JOIN destinations d
                        ON d.name COLLATE utf8mb4_unicode_ci = r.destination COLLATE utf8mb4_unicode_ci
                    SET r.destination_id = d.id
                    WHERE r.destination_id IS NULL
                    """
                )

    def _seed_destinations_from_reservation_names(self) -> None:
        if not self._table_exists("reservations") or not self._column_exists("reservations", "destination"):
            return
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                SELECT DISTINCT destination
                FROM reservations
                WHERE destination IS NOT NULL AND TRIM(destination) <> ''
                """
            )
            destination_names = [row["destination"] for row in cursor.fetchall()]
        for name in destination_names:
            self._ensure_destination_record(name)

    def _seed_destinations_from_legacy_motorboats(self) -> None:
        if not self._table_exists("motorboats"):
            return
        with self.database.session() as (_, cursor):
            cursor.execute("SELECT name FROM motorboats ORDER BY id ASC")
            for row in cursor.fetchall():
                self._ensure_destination_record(row["name"])

    def _seed_admin(self) -> None:
        settings = AppLoginSettings.from_env()
        with self.database.session() as (_, cursor):
            cursor.execute(
                "SELECT id FROM admin_users WHERE username = %s LIMIT 1",
                (settings.username,),
            )
            existing = cursor.fetchone()
            if existing:
                cursor.execute(
                    """
                    UPDATE admin_users
                    SET full_name = COALESCE(NULLIF(full_name, ''), 'Administrator'),
                        role = 'admin'
                    WHERE id = %s
                    """,
                    (existing["id"],),
                )
                return
            cursor.execute(
                """
                INSERT INTO admin_users (username, password, full_name, role)
                VALUES (%s, %s, %s, 'admin')
                """,
                (
                    settings.username,
                    bcrypt.hashpw(settings.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
                    "Administrator",
                ),
            )

    def _sync_user_customer_profiles(self) -> None:
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                SELECT id, full_name, contact_number, email
                FROM users
                WHERE status = 'active'
                ORDER BY id ASC
                """
            )
            users = cursor.fetchall()

        for user in users:
            with self.database.session() as (_, cursor):
                cursor.execute(
                    """
                    SELECT id
                         , full_name
                         , contact_number
                         , email
                    FROM customers
                    WHERE user_id = %s
                       OR (%s IS NOT NULL AND email = %s)
                       OR (%s IS NOT NULL AND contact_number = %s)
                    ORDER BY CASE WHEN user_id = %s THEN 0 ELSE 1 END, id ASC
                    LIMIT 1
                    """,
                    (
                        user["id"],
                        user["email"],
                        user["email"],
                        user["contact_number"],
                        user["contact_number"],
                        user["id"],
                    ),
                )
                existing = cursor.fetchone()
                if existing:
                    resolved_name = existing["full_name"] or user["full_name"]
                    resolved_contact = existing["contact_number"] or user["contact_number"]
                    resolved_email = existing["email"] or user["email"]
                    cursor.execute(
                        """
                        UPDATE customers
                        SET user_id = %s,
                            full_name = %s,
                            contact_number = %s,
                            email = %s
                        WHERE id = %s
                        """,
                        (
                            user["id"],
                            resolved_name,
                            resolved_contact,
                            resolved_email,
                            existing["id"],
                        ),
                    )
                    cursor.execute(
                        """
                        UPDATE users
                        SET full_name = %s,
                            contact_number = %s,
                            email = %s
                        WHERE id = %s
                        """,
                        (
                            resolved_name,
                            resolved_contact,
                            resolved_email,
                            user["id"],
                        ),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO customers (user_id, full_name, contact_number, email)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            user["id"],
                            user["full_name"],
                            user["contact_number"],
                            user["email"],
                        ),
                    )

    def _migrate_pending_status(self) -> None:
        """Add 'Pending' to the status ENUM for existing databases that don't have it yet."""
        try:
            with self.database.session() as (_, cursor):
                cursor.execute(
                    """
                    ALTER TABLE reservations
                    MODIFY COLUMN status
                    ENUM('Pending', 'Reserved', 'On Going', 'Completed', 'Cancelled')
                    NOT NULL DEFAULT 'Pending'
                    """
                )
        except Exception:
            pass  # Already migrated or column doesn't exist yet

    def _finalize_reservations_table(self) -> None:
        if self._column_exists("reservations", "destination_id"):
            with self.database.session() as (_, cursor):
                cursor.execute("SELECT COUNT(*) AS missing_count FROM reservations WHERE destination_id IS NULL")
                missing_count = (cursor.fetchone() or {}).get("missing_count") or 0
            if missing_count == 0:
                with self.database.session() as (_, cursor):
                    cursor.execute(
                        """
                        ALTER TABLE reservations
                        MODIFY COLUMN destination_id INT NOT NULL
                        """
                    )

        if self._column_exists("reservations", "motorboat_id"):
            self._drop_foreign_key_if_exists("reservations", "fk_reservations_motorboat")
            with self.database.session() as (_, cursor):
                cursor.execute("ALTER TABLE reservations DROP COLUMN motorboat_id")

        self._create_foreign_key_if_missing(
            "reservations",
            "fk_reservations_user",
            """
            ALTER TABLE reservations
            ADD CONSTRAINT fk_reservations_user
            FOREIGN KEY (user_id) REFERENCES users (id)
            """,
        )
        self._create_foreign_key_if_missing(
            "reservations",
            "fk_reservations_customer",
            """
            ALTER TABLE reservations
            ADD CONSTRAINT fk_reservations_customer
            FOREIGN KEY (customer_id) REFERENCES customers (id)
            """,
        )
        self._create_foreign_key_if_missing(
            "reservations",
            "fk_reservations_cottage",
            """
            ALTER TABLE reservations
            ADD CONSTRAINT fk_reservations_cottage
            FOREIGN KEY (cottage_id) REFERENCES cottages (id)
            """,
        )
        self._create_foreign_key_if_missing(
            "reservations",
            "fk_reservations_destination",
            """
            ALTER TABLE reservations
            ADD CONSTRAINT fk_reservations_destination
            FOREIGN KEY (destination_id) REFERENCES destinations (id)
            """,
        )

    def _ensure_reservation_destinations_table(self) -> None:
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS reservation_destinations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    reservation_id INT NOT NULL,
                    destination_id INT NOT NULL,
                    sort_order INT NOT NULL DEFAULT 1,
                    is_primary TINYINT(1) NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )
        self._add_column_if_missing(
            "reservation_destinations",
            "sort_order",
            "ALTER TABLE reservation_destinations ADD COLUMN sort_order INT NOT NULL DEFAULT 1 AFTER destination_id",
        )
        self._add_column_if_missing(
            "reservation_destinations",
            "is_primary",
            "ALTER TABLE reservation_destinations ADD COLUMN is_primary TINYINT(1) NOT NULL DEFAULT 0 AFTER sort_order",
        )
        self._add_column_if_missing(
            "reservation_destinations",
            "created_at",
            "ALTER TABLE reservation_destinations ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP AFTER is_primary",
        )
        self._create_foreign_key_if_missing(
            "reservation_destinations",
            "fk_reservation_destinations_reservation",
            """
            ALTER TABLE reservation_destinations
            ADD CONSTRAINT fk_reservation_destinations_reservation
            FOREIGN KEY (reservation_id) REFERENCES reservations (id)
            """,
        )
        self._create_foreign_key_if_missing(
            "reservation_destinations",
            "fk_reservation_destinations_destination",
            """
            ALTER TABLE reservation_destinations
            ADD CONSTRAINT fk_reservation_destinations_destination
            FOREIGN KEY (destination_id) REFERENCES destinations (id)
            """,
        )
        self._create_index_if_missing(
            "reservation_destinations",
            "idx_reservation_destinations_reservation",
            """
            ALTER TABLE reservation_destinations
            ADD INDEX idx_reservation_destinations_reservation (reservation_id)
            """,
        )
        self._create_index_if_missing(
            "reservation_destinations",
            "idx_reservation_destinations_destination",
            """
            ALTER TABLE reservation_destinations
            ADD INDEX idx_reservation_destinations_destination (destination_id)
            """,
        )
        self._create_index_if_missing(
            "reservation_destinations",
            "uq_reservation_destinations_reservation_destination",
            """
            ALTER TABLE reservation_destinations
            ADD UNIQUE INDEX uq_reservation_destinations_reservation_destination (reservation_id, destination_id)
            """,
        )
        self._create_index_if_missing(
            "reservation_destinations",
            "uq_reservation_destinations_reservation_sort",
            """
            ALTER TABLE reservation_destinations
            ADD UNIQUE INDEX uq_reservation_destinations_reservation_sort (reservation_id, sort_order)
            """,
        )
        self._backfill_reservation_destinations()

    @staticmethod
    def _split_destination_names(raw_value: str | None) -> list[str]:
        parts = [
            part.strip()
            for part in str(raw_value or "").split(",")
            if part and part.strip()
        ]
        unique_names: list[str] = []
        seen_names: set[str] = set()
        for part in parts:
            normalized = part.lower()
            if normalized in seen_names:
                continue
            seen_names.add(normalized)
            unique_names.append(part)
        return unique_names

    def _backfill_reservation_destinations(self) -> None:
        if not self._table_exists("reservations"):
            return
        has_legacy_destination = self._column_exists("reservations", "destination")
        with self.database.session() as (_, cursor):
            if has_legacy_destination:
                cursor.execute(
                    """
                    SELECT id, destination_id, destination
                    FROM reservations
                    ORDER BY id ASC
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT id, destination_id
                    FROM reservations
                    ORDER BY id ASC
                    """
                )
            reservations = cursor.fetchall()
            cursor.execute("SELECT id, name FROM destinations ORDER BY id ASC")
            destination_rows = cursor.fetchall()
            cursor.execute("SELECT DISTINCT reservation_id FROM reservation_destinations")
            existing_rows = cursor.fetchall()

        existing_reservation_ids = {
            int(row["reservation_id"])
            for row in existing_rows
            if row.get("reservation_id") is not None
        }
        destinations_by_name = {
            str(row["name"]).strip().lower(): row
            for row in destination_rows
            if str(row.get("name") or "").strip()
        }
        destinations_by_id = {
            int(row["id"]): row
            for row in destination_rows
            if row.get("id") is not None
        }

        for reservation in reservations:
            reservation_id = int(reservation["id"])
            if reservation_id in existing_reservation_ids:
                continue

            raw_primary_destination_id = reservation.get("destination_id")
            primary_destination_id = int(raw_primary_destination_id) if raw_primary_destination_id is not None else None
            primary_destination = destinations_by_id.get(primary_destination_id) if primary_destination_id is not None else None
            ordered_destinations: list[dict] = []
            seen_destination_ids: set[int] = set()

            for name in self._split_destination_names(reservation.get("destination")):
                match = destinations_by_name.get(name.lower())
                if not match:
                    continue
                destination_id = int(match["id"])
                if destination_id in seen_destination_ids:
                    continue
                ordered_destinations.append(match)
                seen_destination_ids.add(destination_id)

            if primary_destination and int(primary_destination["id"]) not in seen_destination_ids:
                ordered_destinations.insert(0, primary_destination)
                seen_destination_ids.add(int(primary_destination["id"]))

            if not ordered_destinations and primary_destination:
                ordered_destinations.append(primary_destination)

            if not ordered_destinations:
                continue

            primary_destination_id = int(primary_destination["id"]) if primary_destination else None
            normalized_summary = ", ".join(str(row["name"]).strip() for row in ordered_destinations)
            primary_written = False

            with self.database.session() as (_, cursor):
                for sort_order, destination_row in enumerate(ordered_destinations, start=1):
                    destination_id = int(destination_row["id"])
                    is_primary = int(
                        primary_destination_id is not None
                        and destination_id == primary_destination_id
                        and not primary_written
                    )
                    if is_primary:
                        primary_written = True
                    cursor.execute(
                        """
                        INSERT INTO reservation_destinations (
                            reservation_id,
                            destination_id,
                            sort_order,
                            is_primary
                        )
                        VALUES (%s, %s, %s, %s)
                        """,
                        (reservation_id, destination_id, sort_order, is_primary),
                    )

                if not primary_written:
                    cursor.execute(
                        """
                        UPDATE reservation_destinations
                        SET is_primary = 1
                        WHERE reservation_id = %s AND sort_order = 1
                        """,
                        (reservation_id,),
                    )

                if has_legacy_destination:
                    cursor.execute(
                        """
                        UPDATE reservations
                        SET destination = %s
                        WHERE id = %s
                        """,
                        (normalized_summary, reservation_id),
                    )

    def _ensure_payments_table(self) -> None:
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS payments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    reservation_id INT NOT NULL,
                    transaction_type VARCHAR(30) NOT NULL DEFAULT 'Payment',
                    payment_status VARCHAR(30) NOT NULL DEFAULT 'Unpaid',
                    payment_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                    payment_method VARCHAR(50) NULL,
                    payment_notes TEXT NULL,
                    recorded_by VARCHAR(255) NULL,
                    recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )
        self._create_foreign_key_if_missing(
            "payments",
            "fk_payments_reservation",
            """
            ALTER TABLE payments
            ADD CONSTRAINT fk_payments_reservation
            FOREIGN KEY (reservation_id) REFERENCES reservations (id)
            """,
        )
        self._create_index_if_missing(
            "payments",
            "idx_payments_reservation_recorded",
            "ALTER TABLE payments ADD INDEX idx_payments_reservation_recorded (reservation_id, recorded_at)",
        )
        self._create_index_if_missing(
            "payments",
            "idx_payments_status",
            "ALTER TABLE payments ADD INDEX idx_payments_status (payment_status)",
        )

    def _backfill_payments_from_reservations(self) -> None:
        if not self._table_exists("reservations") or not self._column_exists("reservations", "amount_paid"):
            return
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                SELECT 
                    r.id,
                    r.total_price,
                    r.payment_status,
                    COALESCE(r.amount_paid, 0) AS amount_paid,
                    r.payment_method,
                    r.payment_notes,
                    r.paid_at,
                    r.created_at
                FROM reservations r
                LEFT JOIN payments p ON p.reservation_id = r.id
                WHERE p.id IS NULL
                  AND (
                      COALESCE(r.amount_paid, 0) <> 0
                      OR COALESCE(r.payment_status, 'Unpaid') <> 'Unpaid'
                      OR r.payment_method IS NOT NULL
                      OR r.payment_notes IS NOT NULL
                      OR r.paid_at IS NOT NULL
                  )
                ORDER BY r.id ASC
                """
            )
            rows = cursor.fetchall()

        for row in rows:
            total_price = float(row.get("total_price") or 0)
            amount_paid = float(row.get("amount_paid") or 0)
            balance_due = round(max(total_price - amount_paid, 0.0), 2)
            recorded_at = row.get("paid_at") or row.get("created_at")
            with self.database.session() as (_, cursor):
                cursor.execute(
                    """
                    INSERT INTO payments (
                        reservation_id,
                        transaction_type,
                        payment_status,
                        payment_amount,
                        payment_method,
                        payment_notes,
                        recorded_by,
                        recorded_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        row["id"],
                        "Migration",
                        row["payment_status"],
                        amount_paid,
                        row.get("payment_method"),
                        row.get("payment_notes"),
                        "schema_migration",
                        recorded_at,
                    ),
                )

    def _ensure_payment_logs_table(self) -> None:
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS payment_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    reservation_id INT NOT NULL,
                    payment_id INT NULL,
                    action VARCHAR(40) NOT NULL DEFAULT 'status_update',
                    old_payment_status VARCHAR(30) NULL,
                    new_payment_status VARCHAR(30) NOT NULL,
                    old_amount_paid DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                    new_amount_paid DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                    payment_method VARCHAR(50) NULL,
                    notes TEXT NULL,
                    recorded_by VARCHAR(255) NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )
        self._create_foreign_key_if_missing(
            "payment_logs",
            "fk_payment_logs_reservation",
            """
            ALTER TABLE payment_logs
            ADD CONSTRAINT fk_payment_logs_reservation
            FOREIGN KEY (reservation_id) REFERENCES reservations (id)
            """,
        )
        self._create_foreign_key_if_missing(
            "payment_logs",
            "fk_payment_logs_payment",
            """
            ALTER TABLE payment_logs
            ADD CONSTRAINT fk_payment_logs_payment
            FOREIGN KEY (payment_id) REFERENCES payments (id)
            """,
        )
        self._create_index_if_missing(
            "payment_logs",
            "idx_payment_logs_reservation_created",
            "ALTER TABLE payment_logs ADD INDEX idx_payment_logs_reservation_created (reservation_id, created_at)",
        )

    def _normalize_payment_methods(self) -> None:
        replacements = {
            "G-Cash": "GCash",
            "Others": "Other",
            "Bank Transfer": "Other",
        }
        targets = (
            ("payments", "payment_method"),
            ("payment_logs", "payment_method"),
            ("reservations", "payment_method"),
        )
        for table_name, column_name in targets:
            if not self._table_exists(table_name) or not self._column_exists(table_name, column_name):
                continue
            with self.database.session() as (_, cursor):
                for source_value, target_value in replacements.items():
                    cursor.execute(
                        f"""
                        UPDATE {table_name}
                        SET {column_name} = %s
                        WHERE TRIM(COALESCE({column_name}, '')) = %s
                        """,
                        (target_value, source_value),
                    )

    def _ensure_audit_logs_table(self) -> None:
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    table_name VARCHAR(50) NOT NULL,
                    record_id INT NOT NULL,
                    action ENUM('INSERT', 'UPDATE', 'DELETE') NOT NULL,
                    old_values JSON NULL,
                    new_values JSON NULL,
                    changed_by VARCHAR(255) NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )
        self._create_index_if_missing(
            "audit_logs",
            "idx_audit_logs_table_record",
            "ALTER TABLE audit_logs ADD INDEX idx_audit_logs_table_record (table_name, record_id)",
        )
        self._create_index_if_missing(
            "audit_logs",
            "idx_audit_logs_created",
            "ALTER TABLE audit_logs ADD INDEX idx_audit_logs_created (created_at)",
        )

    def _seed_assets(self, table_name: str, assets: tuple[dict, ...]) -> None:
        insert_sql = (
            f"INSERT INTO {table_name} (asset_code, name, capacity, base_rate) "
            "VALUES (%s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE "
            "name = VALUES(name), "
            "capacity = VALUES(capacity), "
            "base_rate = VALUES(base_rate)"
        )
        with self.database.session() as (_, cursor):
            for asset in assets:
                cursor.execute(
                    insert_sql,
                    (
                        asset["asset_code"],
                        asset["name"],
                        asset["capacity"],
                        asset["base_rate"],
                    ),
                )

    def _create_functions(self) -> bool:
        function_statements = (
            "DROP FUNCTION IF EXISTS fn_format_customer_name",
            """
            CREATE FUNCTION fn_format_customer_name(p_full_name VARCHAR(120))
            RETURNS VARCHAR(120)
            DETERMINISTIC
            NO SQL
            BEGIN
                DECLARE cleaned_name VARCHAR(120);
                SET cleaned_name = TRIM(COALESCE(p_full_name, ''));
                IF cleaned_name = '' THEN
                    RETURN 'Guest';
                END IF;
                RETURN CONCAT(
                    UPPER(LEFT(cleaned_name, 1)),
                    LOWER(SUBSTRING(cleaned_name, 2))
                );
            END
            """,
            "DROP FUNCTION IF EXISTS fn_remaining_session_minutes",
            """
            CREATE FUNCTION fn_remaining_session_minutes(p_return_time DATETIME)
            RETURNS INT
            NOT DETERMINISTIC
            NO SQL
            BEGIN
                RETURN GREATEST(TIMESTAMPDIFF(MINUTE, NOW(), p_return_time), 0);
            END
            """,
            "DROP FUNCTION IF EXISTS fn_slot_has_available_assets",
            """
            CREATE FUNCTION fn_slot_has_available_assets(
                p_departure_time DATETIME,
                p_return_time DATETIME,
                p_party_size INT
            )
            RETURNS TINYINT(1)
            READS SQL DATA
            BEGIN
                DECLARE available_cottages INT DEFAULT 0;
                DECLARE available_destinations INT DEFAULT 0;

                SELECT COUNT(*)
                INTO available_cottages
                FROM cottages c
                WHERE c.capacity >= p_party_size
                  AND NOT EXISTS (
                      SELECT 1
                      FROM reservations r
                      WHERE r.cottage_id = c.id
                        AND r.status IN ('Reserved', 'On Going')
                        AND NOT (
                            r.return_time <= p_departure_time
                            OR r.departure_time >= p_return_time
                        )
                  );

                SELECT COUNT(*)
                INTO available_destinations
                FROM destinations d
                WHERE d.capacity >= p_party_size
                  AND NOT EXISTS (
                      SELECT 1
                      FROM reservations r
                      WHERE r.destination_id = d.id
                        AND r.status IN ('Reserved', 'On Going')
                        AND NOT (
                            r.return_time <= p_departure_time
                            OR r.departure_time >= p_return_time
                        )
                  );

                RETURN (available_cottages > 0 AND available_destinations > 0);
            END
            """,
        )
        try:
            with self.database.session() as (_, cursor):
                for statement in function_statements:
                    cursor.execute(statement)
            return True
        except Exception as exc:
            self.warnings.append(
                "Stored MySQL routines were skipped because this MariaDB/XAMPP installation "
                f"reported: {exc}"
            )
            return False

    def _create_procedures(self, routines_enabled: bool) -> None:
        if not routines_enabled:
            return
        procedure_statements = (
            "DROP PROCEDURE IF EXISTS sp_cancel_reservation",
            """
            CREATE PROCEDURE sp_cancel_reservation(
                IN p_reservation_id INT,
                IN p_reason TEXT
            )
            BEGIN
                UPDATE reservations
                SET status = 'Cancelled',
                    cancelled_at = NOW(),
                    notes = CONCAT(COALESCE(notes, ''), '\nCancellation Reason: ', COALESCE(p_reason, 'No reason provided'))
                WHERE id = p_reservation_id;
            END
            """,
            "DROP PROCEDURE IF EXISTS sp_process_payment",
            """
            CREATE PROCEDURE sp_process_payment(
                IN p_reservation_id INT,
                IN p_amount DECIMAL(10, 2),
                IN p_method VARCHAR(50),
                IN p_notes TEXT,
                IN p_recorded_by VARCHAR(255)
            )
            BEGIN
                DECLARE v_old_paid DECIMAL(10,2) DEFAULT 0.00;
                DECLARE v_new_paid DECIMAL(10,2) DEFAULT 0.00;
                DECLARE v_total_price DECIMAL(10,2) DEFAULT 0.00;
                DECLARE v_old_status VARCHAR(30) DEFAULT 'Unpaid';
                DECLARE v_new_status VARCHAR(30) DEFAULT 'Unpaid';
                DECLARE v_payment_id INT;
                
                -- Get current totals and status
                SELECT total_price INTO v_total_price
                FROM reservations WHERE id = p_reservation_id;
                
                SELECT COALESCE(SUM(payment_amount), 0) INTO v_old_paid
                FROM payments WHERE reservation_id = p_reservation_id;
                
                SELECT COALESCE(payment_status, 'Unpaid') INTO v_old_status
                FROM payments 
                WHERE reservation_id = p_reservation_id 
                ORDER BY recorded_at DESC, id DESC LIMIT 1;
                
                -- Calculate new values
                SET v_new_paid = v_old_paid + p_amount;
                IF v_new_paid >= v_total_price THEN
                    SET v_new_status = 'Paid';
                ELSEIF v_new_paid > 0 THEN
                    SET v_new_status = 'Partially Paid';
                ELSE
                    SET v_new_status = 'Unpaid';
                END IF;

                -- Insert Payment
                INSERT INTO payments (
                    reservation_id, transaction_type, payment_status, 
                    payment_amount, payment_method, payment_notes, recorded_by
                )
                VALUES (
                    p_reservation_id, 'Payment', v_new_status, 
                    p_amount, p_method, p_notes, p_recorded_by
                );
                
                SET v_payment_id = LAST_INSERT_ID();
                
                -- Insert Log
                INSERT INTO payment_logs (
                    reservation_id, payment_id, action,
                    old_payment_status, new_payment_status,
                    old_amount_paid, new_amount_paid,
                    payment_method, notes, recorded_by
                )
                VALUES (
                    p_reservation_id, v_payment_id, 'payment',
                    v_old_status, v_new_status,
                    v_old_paid, v_new_paid,
                    p_method, p_notes, p_recorded_by
                );
                
                UPDATE reservations
                SET updated_at = NOW()
                WHERE id = p_reservation_id;
            END
            """,
            "DROP PROCEDURE IF EXISTS sp_GenerateMonthlyRevenueReport",
            """
            CREATE PROCEDURE sp_GenerateMonthlyRevenueReport(
                IN p_start_date DATE,
                IN p_end_date DATE
            )
            BEGIN
                -- Result Set 1: Overall Summary
                SELECT 
                    COUNT(r.id) AS total_bookings,
                    COALESCE(SUM(r.total_price), 0) AS total_expected_revenue,
                    COALESCE(SUM(ps.total_paid), 0) AS total_collected,
                    COALESCE(SUM(GREATEST(r.total_price - COALESCE(ps.total_paid, 0), 0)), 0) AS total_outstanding
                FROM reservations r
                LEFT JOIN (
                    SELECT reservation_id, SUM(payment_amount) AS total_paid
                    FROM payments
                    GROUP BY reservation_id
                ) ps ON ps.reservation_id = r.id
                WHERE r.status <> 'Cancelled' AND r.is_deleted = 0
                  AND DATE(r.created_at) >= p_start_date 
                  AND DATE(r.created_at) <= p_end_date;

                -- Result Set 2: Breakdown by Payment Method
                SELECT 
                    COALESCE(p.payment_method, 'Unpaid') AS payment_method,
                    SUM(p.payment_amount) AS total_collected
                FROM payments p
                INNER JOIN reservations r ON r.id = p.reservation_id
                WHERE r.status <> 'Cancelled' AND r.is_deleted = 0
                  AND DATE(r.created_at) >= p_start_date 
                  AND DATE(r.created_at) <= p_end_date
                GROUP BY COALESCE(p.payment_method, 'Unpaid');
            END
            """,
        )
        try:
            with self.database.session() as (_, cursor):
                for statement in procedure_statements:
                    cursor.execute(statement)
        except Exception as exc:
            self.warnings.append(f"Stored procedures were skipped: {exc}")

    def _create_triggers(self, routines_enabled: bool) -> None:
        if not routines_enabled:
            return
        trigger_statements = (
            "DROP TRIGGER IF EXISTS trg_reservations_after_update",
            """
            CREATE TRIGGER trg_reservations_after_update
            AFTER UPDATE ON reservations
            FOR EACH ROW
            BEGIN
                IF OLD.status <> NEW.status OR OLD.total_price <> NEW.total_price THEN
                    INSERT INTO audit_logs (table_name, record_id, action, old_values, new_values)
                    VALUES (
                        'reservations',
                        NEW.id,
                        'UPDATE',
                        JSON_OBJECT('status', OLD.status, 'total_price', OLD.total_price),
                        JSON_OBJECT('status', NEW.status, 'total_price', NEW.total_price)
                    );
                END IF;
            END
            """,
            "DROP TRIGGER IF EXISTS trg_reservations_after_delete",
            """
            CREATE TRIGGER trg_reservations_after_delete
            AFTER DELETE ON reservations
            FOR EACH ROW
            BEGIN
                INSERT INTO audit_logs (table_name, record_id, action, old_values)
                VALUES (
                    'reservations',
                    OLD.id,
                    'DELETE',
                    JSON_OBJECT('reservation_code', OLD.reservation_code, 'status', OLD.status)
                );
            END
            """,
        )
        try:
            with self.database.session() as (_, cursor):
                for statement in trigger_statements:
                    cursor.execute(statement)
        except Exception as exc:
            self.warnings.append(f"Triggers were skipped: {exc}")

    def _create_events(self, routines_enabled: bool) -> None:
        del routines_enabled
        
        try:
            with self.database.session() as (_, cursor):
                cursor.execute("SET GLOBAL event_scheduler = ON")
        except Exception:
            pass

        event_statements = (
            "DROP EVENT IF EXISTS evt_complete_expired_trips",
            """
            CREATE EVENT evt_complete_expired_trips
            ON SCHEDULE EVERY 1 HOUR
            DO
            BEGIN
                UPDATE reservations
                SET status = 'Completed',
                    completed_at = NOW()
                WHERE status = 'On Going' AND return_time <= NOW();
            END
            """,
            "DROP EVENT IF EXISTS evt_expire_unapproved_bookings",
            f"""
            CREATE EVENT evt_expire_unapproved_bookings
            ON SCHEDULE EVERY 30 MINUTE
            DO
            BEGIN
                UPDATE reservations
                SET status = 'Cancelled',
                    notes = CASE
                        WHEN TRIM(COALESCE(notes, '')) = '' THEN 'System: Auto-expired because the booking was still pending within {PENDING_APPROVAL_DEADLINE_HOURS} hour(s) of departure.'
                        ELSE CONCAT(COALESCE(notes, ''), '\\nSystem: Auto-expired because the booking was still pending within {PENDING_APPROVAL_DEADLINE_HOURS} hour(s) of departure.')
                    END,
                    cancelled_at = NOW()
                WHERE status = 'Pending'
                  AND departure_time <= DATE_ADD(NOW(), INTERVAL {PENDING_APPROVAL_DEADLINE_HOURS} HOUR);
            END
            """,
        )
        try:
            with self.database.session() as (_, cursor):
                for statement in event_statements:
                    cursor.execute(statement)
        except Exception as exc:
            self.warnings.append(f"Events were skipped: {exc}")

    def _create_views(self, routines_enabled: bool) -> None:
        del routines_enabled
        view_statements = (
            "DROP VIEW IF EXISTS vw_active_reservations",
            """
            CREATE VIEW vw_active_reservations AS
            SELECT
                r.id,
                r.reservation_code,
                r.user_id,
                r.customer_id,
                CASE
                    WHEN TRIM(COALESCE(c.full_name, '')) = '' THEN 'Guest'
                    ELSE CONCAT(UPPER(LEFT(TRIM(c.full_name), 1)), LOWER(SUBSTRING(TRIM(c.full_name), 2)))
                END AS customer_name,
                c.contact_number,
                c.email,
                r.cottage_id,
                fc.asset_code AS cottage_code,
                fc.name AS cottage_name,
                CASE
                    WHEN r.status IN ('Reserved', 'On Going')
                         AND r.departure_time <= NOW()
                         AND r.return_time > NOW() THEN 'On Going'
                    ELSE 'Reserved'
                END AS cottage_status,
                r.destination_id,
                d.asset_code AS destination_code,
                d.name AS destination_name,
                CASE
                    WHEN r.status IN ('Reserved', 'On Going')
                         AND r.departure_time <= NOW()
                         AND r.return_time > NOW() THEN 'On Going'
                    ELSE 'Reserved'
                END AS destination_status,
                COALESCE(NULLIF(rds.destination_summary, ''), d.name) AS destination,
                r.party_size,
                r.departure_time,
                r.return_time,
                CASE
                    WHEN r.status = 'Reserved'
                         AND r.departure_time <= NOW()
                         AND r.return_time > NOW() THEN 'On Going'
                    ELSE r.status
                END AS status,
                r.total_price,
                GREATEST(TIMESTAMPDIFF(MINUTE, NOW(), r.return_time), 0) AS remaining_session_minutes
            FROM reservations r
            INNER JOIN customers c ON c.id = r.customer_id
            INNER JOIN cottages fc ON fc.id = r.cottage_id
            INNER JOIN destinations d ON d.id = r.destination_id
            LEFT JOIN (
                SELECT
                    rd.reservation_id,
                    GROUP_CONCAT(dest.name ORDER BY rd.sort_order SEPARATOR ', ') AS destination_summary
                FROM reservation_destinations rd
                INNER JOIN destinations dest ON dest.id = rd.destination_id
                GROUP BY rd.reservation_id
            ) rds ON rds.reservation_id = r.id
            WHERE r.status IN ('Pending', 'Reserved', 'On Going')
              AND r.is_deleted = 0
            """,
            "DROP VIEW IF EXISTS vw_financial_summary",
            """
            CREATE VIEW vw_financial_summary AS
            SELECT 
                DATE(r.created_at) AS report_date,
                COUNT(*) AS total_bookings,
                SUM(r.total_price) AS total_revenue,
                SUM(COALESCE(ps.total_paid, 0)) AS total_collected,
                SUM(GREATEST(r.total_price - COALESCE(ps.total_paid, 0), 0)) AS total_outstanding
            FROM reservations r
            LEFT JOIN (
                SELECT
                    p.reservation_id,
                    SUM(p.payment_amount) AS total_paid
                FROM payments p
                GROUP BY p.reservation_id
            ) ps ON ps.reservation_id = r.id
            WHERE r.status <> 'Cancelled' AND r.is_deleted = 0
            GROUP BY DATE(r.created_at)
            """,
            "DROP VIEW IF EXISTS vw_cottage_popularity",
            """
            CREATE VIEW vw_cottage_popularity AS
            SELECT 
                c.name AS cottage_name,
                COUNT(r.id) AS booking_count,
                SUM(r.total_price) AS revenue_generated
            FROM cottages c
            LEFT JOIN reservations r ON c.id = r.cottage_id AND r.is_deleted = 0
            GROUP BY c.id, c.name
            """,
        )
        with self.database.session() as (_, cursor):
            for statement in view_statements:
                cursor.execute(statement)

    def _ensure_destination_record(self, name: str) -> int:
        normalized_name = name.strip()
        with self.database.session() as (_, cursor):
            cursor.execute(
                "SELECT id FROM destinations WHERE name = %s LIMIT 1",
                (normalized_name,),
            )
            row = cursor.fetchone()
            if row:
                return row["id"]

            cursor.execute(
                """
                SELECT COALESCE(MAX(id), 0) + 1 AS next_id
                FROM destinations
                """
            )
            next_id = (cursor.fetchone() or {}).get("next_id") or 1
            asset_code = f"DST-{next_id:02d}"
            cursor.execute(
                """
                INSERT INTO destinations (asset_code, name, capacity, base_rate)
                VALUES (%s, %s, 20, 0.00)
                """,
                (asset_code, normalized_name),
            )
            return cursor.lastrowid

    def _table_exists(self, table_name: str) -> bool:
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = DATABASE() AND table_name = %s
                LIMIT 1
                """,
                (table_name,),
            )
            return cursor.fetchone() is not None

    def _column_exists(self, table_name: str, column_name: str) -> bool:
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = DATABASE()
                  AND table_name = %s
                  AND column_name = %s
                LIMIT 1
                """,
                (table_name, column_name),
            )
            return cursor.fetchone() is not None

    def _constraint_exists(self, table_name: str, constraint_name: str) -> bool:
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                SELECT 1
                FROM information_schema.table_constraints
                WHERE table_schema = DATABASE()
                  AND table_name = %s
                  AND constraint_name = %s
                LIMIT 1
                """,
                (table_name, constraint_name),
            )
            return cursor.fetchone() is not None

    def _index_exists(self, table_name: str, index_name: str) -> bool:
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                SELECT 1
                FROM information_schema.statistics
                WHERE table_schema = DATABASE()
                  AND table_name = %s
                  AND index_name = %s
                LIMIT 1
                """,
                (table_name, index_name),
            )
            return cursor.fetchone() is not None

    def _add_column_if_missing(self, table_name: str, column_name: str, ddl: str) -> None:
        if self._column_exists(table_name, column_name):
            return
        with self.database.session() as (_, cursor):
            cursor.execute(ddl)

    def _create_foreign_key_if_missing(self, table_name: str, constraint_name: str, ddl: str) -> None:
        if self._constraint_exists(table_name, constraint_name):
            return
        with self.database.session() as (_, cursor):
            cursor.execute(ddl)

    def _create_index_if_missing(self, table_name: str, index_name: str, ddl: str) -> None:
        if self._index_exists(table_name, index_name):
            return
        with self.database.session() as (_, cursor):
            cursor.execute(ddl)

    def _drop_column_if_exists(self, table_name: str, column_name: str) -> None:
        if not self._column_exists(table_name, column_name):
            return
        with self.database.session() as (_, cursor):
            cursor.execute(f"ALTER TABLE {table_name} DROP COLUMN {column_name}")

    def _normalize_table_collation(self, table_name: str) -> None:
        if not self._table_exists(table_name):
            return
        with self.database.session() as (_, cursor):
            cursor.execute(
                f"ALTER TABLE {table_name} CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )

    def _drop_foreign_key_if_exists(self, table_name: str, constraint_name: str) -> None:
        if not self._constraint_exists(table_name, constraint_name):
            return
        with self.database.session() as (_, cursor):
            cursor.execute(f"ALTER TABLE {table_name} DROP FOREIGN KEY {constraint_name}")

    def _cleanup_redundant_columns(self) -> None:
        """Removes columns that are no longer needed after normalization."""
        # Clean up Reservations table
        for col in ["destination", "payment_status", "amount_paid", "payment_method", "paid_at", "payment_notes"]:
            self._drop_column_if_exists("reservations", col)
        
        # Clean up Payments table
        for col in ["total_amount_paid", "balance_due"]:
            self._drop_column_if_exists("payments", col)
    def _ensure_trash_bin_table(self) -> None:
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS trash_bin (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    record_type VARCHAR(50) NOT NULL,
                    record_id INT NOT NULL,
                    record_ref VARCHAR(100),
                    original_data JSON,
                    deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB;
                """
            )
