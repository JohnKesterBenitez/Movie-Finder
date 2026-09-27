import json
from datetime import date, datetime, time, timedelta

from k3_rms.config import PENDING_APPROVAL_DEADLINE_HOURS
from k3_rms.database.connection import DatabaseManager
from k3_rms.exceptions import ReservationValidationError

DESTINATION_SUMMARY_JOIN = """
    LEFT JOIN (
        SELECT
            rd.reservation_id,
            GROUP_CONCAT(d.name ORDER BY rd.sort_order SEPARATOR ', ') AS destination_summary
        FROM reservation_destinations rd
        INNER JOIN destinations d ON d.id = rd.destination_id
        GROUP BY rd.reservation_id
    ) rds ON rds.reservation_id = r.id
"""
PAYMENT_SUMMARY_JOIN = """
    LEFT JOIN (
        SELECT 
            r_stats.reservation_id,
            latest_p.payment_status AS effective_payment_status,
            r_stats.total_paid AS effective_amount_paid,
            latest_p.payment_method AS effective_payment_method,
            latest_p.payment_notes AS effective_payment_notes,
            latest_p.recorded_at AS effective_paid_at
        FROM (
            SELECT reservation_id, SUM(payment_amount) as total_paid, MAX(id) as max_id
            FROM payments
            GROUP BY reservation_id
        ) r_stats
        INNER JOIN payments latest_p ON latest_p.id = r_stats.max_id
    ) ps ON ps.reservation_id = r.id
"""


class ReservationModel:
    STATUS_OPTIONS = ("Pending", "Reserved", "On Going", "Completed", "Cancelled")
    PAYMENT_STATUS_OPTIONS = ("Unpaid", "Partially Paid", "Paid", "Refunded")
    PAYMENT_METHOD_OPTIONS = (
        "Cash",
        "Check",
        "GCash",
        "PayMaya",
        "Credit Card",
        "Other",
    )
    PAYMENT_METHOD_ALIASES = {
        "g-cash": "GCash",
        "others": "Other",
        "bank transfer": "Other",
    }

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    @staticmethod
    def _effective_status(
        status: str | None,
        departure_time: datetime | None,
        return_time: datetime | None,
        reference_time: datetime | None = None,
    ) -> str:
        current_status = str(status or "")
        point_in_time = reference_time or datetime.now()
        if (
            current_status == "Reserved"
            and isinstance(departure_time, datetime)
            and isinstance(return_time, datetime)
            and departure_time <= point_in_time < return_time
        ):
            return "On Going"
        return current_status

    @classmethod
    def normalize_payment_method(cls, value: str | None) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        return cls.PAYMENT_METHOD_ALIASES.get(cleaned.casefold(), cleaned)

    def _with_effective_status(
        self,
        row: dict | None,
        reference_time: datetime | None = None,
    ) -> dict | None:
        if not row:
            return row
        hydrated = dict(row)
        for source_key, target_key in (
            ("effective_payment_status", "payment_status"),
            ("effective_amount_paid", "amount_paid"),
            ("effective_balance_due", "balance_due"),
            ("effective_payment_method", "payment_method"),
            ("effective_payment_notes", "payment_notes"),
            ("effective_paid_at", "paid_at"),
        ):
            if source_key in hydrated and hydrated.get(source_key) is not None:
                hydrated[target_key] = hydrated.get(source_key)
        normalized_payment_method = self.normalize_payment_method(hydrated.get("payment_method"))
        if normalized_payment_method is not None:
            hydrated["payment_method"] = normalized_payment_method
        destination_summary = str(hydrated.get("destination_summary") or "").strip()
        if destination_summary:
            hydrated["destination"] = destination_summary
        elif not str(hydrated.get("destination") or "").strip():
            destination_name = str(hydrated.get("destination_name") or "").strip()
            if destination_name:
                hydrated["destination"] = destination_name
        effective_status = self._effective_status(
            hydrated.get("status"),
            hydrated.get("departure_time"),
            hydrated.get("return_time"),
            reference_time=reference_time,
        )
        hydrated["status"] = effective_status
        if "reservation_status" in hydrated:
            hydrated["reservation_status"] = effective_status
        if hydrated.get("reservation_code"):
            if "cottage_status" in hydrated:
                hydrated["cottage_status"] = "On Going" if effective_status == "On Going" else "Reserved"
            if "destination_status" in hydrated:
                hydrated["destination_status"] = "On Going" if effective_status == "On Going" else "Reserved"
        return hydrated

    def create(self, reservation: dict) -> None:
        if self.has_conflict(
            cottage_id=reservation["cottage_id"],
            destination_id=reservation["destination_id"],
            departure_time=reservation["departure_time"],
            return_time=reservation["return_time"],
        ):
            raise ReservationValidationError(
                "That cottage or destination is already reserved for the selected date and time."
            )
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                INSERT INTO reservations (
                    reservation_code,
                    user_id,
                    customer_id,
                    cottage_id,
                    destination_id,
                    party_size,
                    departure_time,
                    return_time,
                    total_price,
                    status,
                    notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    reservation["reservation_code"],
                    reservation.get("user_id"),
                    reservation["customer_id"],
                    reservation["cottage_id"],
                    reservation["destination_id"],
                    reservation["party_size"],
                    reservation["departure_time"],
                    reservation["return_time"],
                    reservation["total_price"],
                    reservation["status"],
                    reservation["notes"],
                ),
            )
            reservation_id = cursor.lastrowid
            self._replace_reservation_destinations(
                cursor,
                reservation_id=reservation_id,
                primary_destination_id=int(reservation["destination_id"]),
                destination_names=self._normalize_destination_names(
                    reservation.get("destinations"),
                    fallback_summary=reservation.get("destination"),
                ),
            )

    @staticmethod
    def _normalize_destination_names(
        destination_names: list[str] | None,
        fallback_summary: str | None = None,
    ) -> list[str]:
        candidates = list(destination_names or [])
        if not candidates and fallback_summary:
            candidates = [
                part.strip()
                for part in str(fallback_summary).split(",")
                if part and part.strip()
            ]
        normalized_names: list[str] = []
        seen_names: set[str] = set()
        for candidate in candidates:
            name = str(candidate or "").strip()
            if not name:
                continue
            key = name.lower()
            if key in seen_names:
                continue
            seen_names.add(key)
            normalized_names.append(name)
        return normalized_names

    def _replace_reservation_destinations(
        self,
        cursor,
        reservation_id: int,
        primary_destination_id: int,
        destination_names: list[str],
    ) -> None:
        destination_ids: list[int] = []
        if destination_names:
            placeholders = ", ".join(["%s"] * len(destination_names))
            cursor.execute(
                f"""
                SELECT id, name
                FROM destinations
                WHERE name IN ({placeholders})
                """,
                tuple(destination_names),
            )
            destination_rows = cursor.fetchall()
            destination_ids_by_name = {
                str(row["name"]).strip().lower(): int(row["id"])
                for row in destination_rows
                if row.get("id") is not None
            }
            for name in destination_names:
                destination_id = destination_ids_by_name.get(name.lower())
                if destination_id is None or destination_id in destination_ids:
                    continue
                destination_ids.append(destination_id)
        if primary_destination_id not in destination_ids:
            destination_ids.insert(0, primary_destination_id)
        if not destination_ids:
            destination_ids = [primary_destination_id]

        cursor.execute(
            "DELETE FROM reservation_destinations WHERE reservation_id = %s",
            (reservation_id,),
        )
        primary_written = False
        for sort_order, destination_id in enumerate(destination_ids, start=1):
            is_primary = int(destination_id == primary_destination_id and not primary_written)
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
        if not primary_written and destination_ids:
            cursor.execute(
                """
                UPDATE reservation_destinations
                SET is_primary = 1
                WHERE reservation_id = %s AND sort_order = 1
                """,
                (reservation_id,),
            )

    def has_conflict(
        self,
        cottage_id: int,
        destination_id: int,
        departure_time: datetime,
        return_time: datetime,
        exclude_reservation_code: str | None = None,
    ) -> bool:
        query = """
            SELECT 1
            FROM reservations r
            WHERE r.status IN ('Reserved', 'On Going')
              AND NOT (r.return_time <= %s OR r.departure_time >= %s)
              AND r.cottage_id = %s
        """
        params: list[object] = [departure_time, return_time, cottage_id]
        if exclude_reservation_code:
            query += " AND r.reservation_code <> %s"
            params.append(exclude_reservation_code)
        query += " LIMIT 1"
        with self.database.session() as (_, cursor):
            cursor.execute(query, tuple(params))
            return cursor.fetchone() is not None

    def find_by_code(self, reservation_code: str) -> dict | None:
        with self.database.session() as (_, cursor):
            cursor.execute(
                f"""
                SELECT
                    r.*,
                    rds.destination_summary,
                    CASE
                        WHEN TRIM(COALESCE(c.full_name, '')) = '' THEN 'Guest'
                        ELSE CONCAT(UPPER(LEFT(TRIM(c.full_name), 1)), LOWER(SUBSTRING(TRIM(c.full_name), 2)))
                    END AS full_name,
                    c.contact_number,
                    c.email,
                    fc.asset_code AS cottage_code,
                    fc.name AS cottage_name,
                    d.asset_code AS destination_code,
                    d.name AS destination_name,
                    COALESCE(ps.effective_payment_status, 'Unpaid') AS effective_payment_status,
                    COALESCE(ps.effective_amount_paid, 0) AS effective_amount_paid,
                    GREATEST(r.total_price - COALESCE(ps.effective_amount_paid, 0), 0) AS effective_balance_due,
                    ps.effective_payment_method,
                    ps.effective_payment_notes,
                    ps.effective_paid_at,
                    GREATEST(TIMESTAMPDIFF(MINUTE, NOW(), r.return_time), 0) AS remaining_session_minutes
                FROM reservations r
                {DESTINATION_SUMMARY_JOIN}
                {PAYMENT_SUMMARY_JOIN}
                INNER JOIN customers c ON c.id = r.customer_id
                INNER JOIN cottages fc ON fc.id = r.cottage_id
                INNER JOIN destinations d ON d.id = r.destination_id
                WHERE r.reservation_code = %s AND r.is_deleted = 0
                LIMIT 1
                """,
                (reservation_code,),
            )
            row = cursor.fetchone()
        return self._with_effective_status(row)

    @staticmethod
    def _payment_transaction_type(
        old_status: str,
        new_status: str,
        amount_delta: float,
    ) -> tuple[str, str]:
        if new_status == "Refunded":
            return "Refund", "refund"
        if amount_delta > 0:
            return "Payment", "payment"
        if amount_delta < 0:
            return "Adjustment", "adjustment"
        if old_status != new_status:
            return "Status Update", "status_update"
        return "Payment", "payment"

    def _load_payment_update_context(self, cursor, reservation_code: str) -> dict | None:
        cursor.execute(
            """
            SELECT id, total_price
            FROM reservations
            WHERE reservation_code = %s AND is_deleted = 0
            LIMIT 1
            FOR UPDATE
            """,
            (reservation_code,),
        )
        reservation_row = cursor.fetchone()
        if reservation_row is None:
            return None

        reservation_id = int(reservation_row["id"])

        cursor.execute(
            """
            SELECT COALESCE(SUM(payment_amount), 0) AS current_paid
            FROM payments
            WHERE reservation_id = %s
            """,
            (reservation_id,),
        )
        payment_totals = cursor.fetchone() or {}

        cursor.execute(
            """
            SELECT payment_status, payment_method, payment_notes
            FROM payments
            WHERE reservation_id = %s
            ORDER BY recorded_at DESC, id DESC
            LIMIT 1
            """,
            (reservation_id,),
        )
        latest_payment = cursor.fetchone() or {}

        return {
            "reservation_id": reservation_id,
            "total_price": float(reservation_row.get("total_price") or 0),
            "current_paid": float(payment_totals.get("current_paid") or 0),
            "payment_status": str(latest_payment.get("payment_status") or "Unpaid"),
            "payment_method": latest_payment.get("payment_method"),
            "payment_notes": latest_payment.get("payment_notes"),
        }

    def update_payment(
        self,
        reservation_code: str,
        payment_status: str,
        amount_paid: float | None = None,
        payment_method: str | None = None,
        payment_notes: str | None = None,
        recorded_by: str | None = None,
    ) -> dict | None:
        if payment_status not in self.PAYMENT_STATUS_OPTIONS:
            raise ValueError(f"Unsupported payment status: {payment_status}")

        with self.database.session() as (_, cursor):
            payment_context = self._load_payment_update_context(cursor, reservation_code)
            if payment_context is None:
                return None

            reservation_id = payment_context["reservation_id"]
            total_price = float(payment_context.get("total_price") or 0)
            current_paid = float(payment_context.get("current_paid") or 0)
            next_amount_paid = current_paid if amount_paid is None else max(float(amount_paid), 0.0)

            if payment_status == "Paid":
                next_amount_paid = total_price
            elif payment_status in {"Unpaid", "Refunded"}:
                next_amount_paid = 0.0
            elif not 0 < next_amount_paid < total_price:
                raise ValueError("Partial payment must be greater than 0 and lower than the total amount.")

            next_paid_at = datetime.now() if payment_status in {"Partially Paid", "Paid"} else None
            method_value = self.normalize_payment_method(payment_method)
            notes_value = payment_notes.strip() if isinstance(payment_notes, str) else None
            old_status = str(payment_context.get("payment_status") or "Unpaid")
            amount_delta = round(next_amount_paid - current_paid, 2)
            transaction_type, log_action = self._payment_transaction_type(old_status, payment_status, amount_delta)
            fallback_method = self.normalize_payment_method(payment_context.get("payment_method"))
            fallback_notes = payment_context.get("payment_notes")

            cursor.execute(
                """
                UPDATE reservations
                SET updated_at = CURRENT_TIMESTAMP
                WHERE reservation_code = %s
                """,
                (reservation_code,),
            )
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
                    reservation_id,
                    transaction_type,
                    payment_status,
                    amount_delta,
                    method_value or fallback_method,
                    notes_value or fallback_notes,
                    recorded_by,
                    next_paid_at or datetime.now(),
                ),
            )
            payment_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO payment_logs (
                    reservation_id,
                    payment_id,
                    action,
                    old_payment_status,
                    new_payment_status,
                    old_amount_paid,
                    new_amount_paid,
                    payment_method,
                    notes,
                    recorded_by
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    reservation_id,
                    payment_id,
                    log_action,
                    old_status,
                    payment_status,
                    current_paid,
                    next_amount_paid,
                    method_value or fallback_method,
                    notes_value or fallback_notes,
                    recorded_by,
                ),
            )
        return self.find_by_code(reservation_code)

    def auto_start_reservations(self) -> int:
        """
        Automatically updates 'Reserved' bookings to 'On Going' if their 
        departure time has passed and they haven't ended yet.
        """
        now = datetime.now()
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                UPDATE reservations
                SET status = 'On Going'
                WHERE status = 'Reserved'
                  AND departure_time <= %s
                  AND return_time > %s
                  AND is_deleted = 0
                """,
                (now, now),
            )
            return cursor.rowcount

    def auto_complete_reservations(self) -> int:
        """
        Automatically updates 'Reserved' or 'On Going' bookings to 'Completed' if their 
        return time has passed.
        """
        now = datetime.now()
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                UPDATE reservations
                SET status = 'Completed',
                    completed_at = COALESCE(completed_at, %s)
                WHERE status IN ('Reserved', 'On Going')
                  AND return_time <= %s
                  AND is_deleted = 0
                """,
                (now, now),
            )
            return cursor.rowcount

    def auto_expire_pending_reservations(
        self,
        deadline_hours: int = PENDING_APPROVAL_DEADLINE_HOURS,
    ) -> int:
        deadline_hours = max(int(deadline_hours), 0)
        now = datetime.now()
        cutoff = now + timedelta(hours=deadline_hours)
        reason = (
            "System: Auto-expired because the booking was still pending "
            f"within {deadline_hours} hour(s) of departure."
        )
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                UPDATE reservations
                SET status = 'Cancelled',
                    notes = CASE
                        WHEN TRIM(COALESCE(notes, '')) = '' THEN %s
                        ELSE CONCAT(notes, %s)
                    END,
                    cancelled_at = COALESCE(cancelled_at, %s)
                WHERE status = 'Pending'
                  AND departure_time <= %s
                  AND is_deleted = 0
                """,
                (reason, "\n" + reason, now, cutoff),
            )
            return cursor.rowcount

    def update_status(self, reservation_code: str, status: str, notes: str | None = None) -> None:
        if status not in self.STATUS_OPTIONS:
            raise ValueError(f"Unsupported reservation status: {status}")
        completed_at = datetime.now() if status == "Completed" else None
        cancelled_at = datetime.now() if status == "Cancelled" else None
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                UPDATE reservations
                SET status = %s,
                    notes = COALESCE(%s, notes),
                    completed_at = COALESCE(%s, completed_at),
                    cancelled_at = COALESCE(%s, cancelled_at)
                WHERE reservation_code = %s AND is_deleted = 0
                """,
                (status, notes, completed_at, cancelled_at, reservation_code),
            )

    def list_active_reservations(self) -> list[dict]:
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                SELECT
                    r.reservation_code,
                    r.customer_name AS full_name,
                    r.contact_number,
                    r.email,
                    r.destination,
                    r.departure_time,
                    r.return_time,
                    r.status,
                    r.cottage_code,
                    r.cottage_name,
                    r.destination_code,
                    r.destination_name,
                    r.remaining_session_minutes
                FROM vw_active_reservations r
                ORDER BY r.departure_time ASC
                LIMIT 10
                """
            )
            rows = cursor.fetchall()
        return [self._with_effective_status(row) for row in rows]

    def list_recent_reservations(self, limit: int = 8) -> list[dict]:
        with self.database.session() as (_, cursor):
            cursor.execute(
                f"""
                SELECT
                    r.reservation_code,
                    COALESCE(NULLIF(rds.destination_summary, ''), d.name) AS destination,
                    r.party_size,
                    r.departure_time,
                    r.return_time,
                    r.status,
                    r.created_at,
                    CASE
                        WHEN TRIM(COALESCE(c.full_name, '')) = '' THEN 'Guest'
                        ELSE CONCAT(UPPER(LEFT(TRIM(c.full_name), 1)), LOWER(SUBSTRING(TRIM(c.full_name), 2)))
                    END AS full_name,
                    fc.asset_code AS cottage_code,
                    fc.name AS cottage_name,
                    d.asset_code AS destination_code,
                    d.name AS destination_name
                FROM reservations r
                {DESTINATION_SUMMARY_JOIN}
                INNER JOIN customers c ON c.id = r.customer_id
                INNER JOIN cottages fc ON fc.id = r.cottage_id
                INNER JOIN destinations d ON d.id = r.destination_id
                WHERE r.is_deleted = 0
                ORDER BY r.created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cursor.fetchall()
        return [self._with_effective_status(row) for row in rows]

    def list_reservations(self, limit: int | None = None) -> list[dict]:
        query = f"""
            SELECT
                r.reservation_code,
                COALESCE(NULLIF(rds.destination_summary, ''), d.name) AS destination,
                r.party_size,
                r.departure_time,
                r.return_time,
                r.total_price,
                r.status,
                COALESCE(ps.effective_payment_status, 'Unpaid') AS effective_payment_status,
                COALESCE(ps.effective_amount_paid, 0) AS effective_amount_paid,
                GREATEST(r.total_price - COALESCE(ps.effective_amount_paid, 0), 0) AS effective_balance_due,
                ps.effective_payment_method,
                ps.effective_payment_notes,
                ps.effective_paid_at,
                r.notes,
                r.created_at,
                CASE
                    WHEN TRIM(COALESCE(c.full_name, '')) = '' THEN 'Guest'
                    ELSE CONCAT(UPPER(LEFT(TRIM(c.full_name), 1)), LOWER(SUBSTRING(TRIM(c.full_name), 2)))
                END AS full_name,
                c.contact_number,
                c.email,
                fc.asset_code AS cottage_code,
                fc.name AS cottage_name,
                fc.capacity AS cottage_capacity,
                d.asset_code AS destination_code,
                d.name AS destination_name
            FROM reservations r
            {DESTINATION_SUMMARY_JOIN}
            {PAYMENT_SUMMARY_JOIN}
            INNER JOIN customers c ON c.id = r.customer_id
            INNER JOIN cottages fc ON fc.id = r.cottage_id
            INNER JOIN destinations d ON d.id = r.destination_id
            WHERE r.is_deleted = 0
            ORDER BY r.departure_time ASC, r.created_at DESC
        """
        params: tuple[object, ...] = ()
        if isinstance(limit, int):
            query += " LIMIT %s"
            params = (limit,)
        with self.database.session() as (_, cursor):
            cursor.execute(query, params)
            rows = cursor.fetchall()
        return [self._with_effective_status(row) for row in rows]

    def list_payment_history(self, reservation_code: str, limit: int = 10) -> list[dict]:
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                SELECT
                    p.id,
                    p.transaction_type,
                    p.payment_status,
                    p.payment_amount,
                    p.payment_method,
                    p.payment_notes,
                    p.recorded_by,
                    p.recorded_at
                FROM payments p
                INNER JOIN reservations r ON r.id = p.reservation_id
                WHERE r.reservation_code = %s
                ORDER BY p.recorded_at DESC, p.id DESC
                LIMIT %s
                """,
                (reservation_code, limit),
            )
            return cursor.fetchall()

    def list_payment_logs(self, reservation_code: str, limit: int = 10) -> list[dict]:
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                SELECT
                    pl.id,
                    pl.action,
                    pl.old_payment_status,
                    pl.new_payment_status,
                    pl.old_amount_paid,
                    pl.new_amount_paid,
                    pl.payment_method,
                    pl.notes,
                    pl.recorded_by,
                    pl.created_at
                FROM payment_logs pl
                INNER JOIN reservations r ON r.id = pl.reservation_id
                WHERE r.reservation_code = %s
                ORDER BY pl.created_at DESC, pl.id DESC
                LIMIT %s
                """,
                (reservation_code, limit),
            )
            return cursor.fetchall()

    def get_revenue_report_data(self) -> list[dict]:
        with self.database.session() as (_, cursor):
            cursor.execute(
                f"""
                SELECT 
                    DATE_FORMAT(r.departure_time, '%Y-%m') AS month,
                    SUM(r.total_price) AS total_revenue,
                    SUM(COALESCE(ps.effective_amount_paid, 0)) AS total_collected,
                    COUNT(*) AS total_bookings
                FROM reservations r
                {PAYMENT_SUMMARY_JOIN}
                WHERE r.status <> 'Cancelled' AND r.is_deleted = 0
                GROUP BY month
                ORDER BY month DESC
                """
            )
            return cursor.fetchall()

    def get_dashboard_metrics(self) -> dict:
        today = date.today()
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                SELECT
                    COUNT(CASE WHEN status IN ('Reserved', 'On Going') THEN 1 END) AS active_reservations,
                    SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed_trips,
                    SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) AS cancellations,
                    COUNT(CASE WHEN DATE(created_at) = %s THEN 1 END) AS daily_bookings,
                    SUM(CASE WHEN YEARWEEK(created_at, 1) = YEARWEEK(%s, 1) THEN 1 ELSE 0 END) AS weekly_bookings,
                    COALESCE(SUM(CASE WHEN DATE(created_at) = %s THEN total_price ELSE 0 END), 0) AS daily_revenue,
                    COALESCE(SUM(CASE WHEN YEARWEEK(created_at, 1) = YEARWEEK(%s, 1) THEN total_price ELSE 0 END), 0) AS weekly_revenue
                FROM reservations
                WHERE is_deleted = 0
                """,
                (today, today, today, today),
            )
            row = cursor.fetchone() or {}
        return {
            "active_reservations": row.get("active_reservations") or 0,
            "completed_trips": row.get("completed_trips") or 0,
            "cancellations": row.get("cancellations") or 0,
            "daily_bookings": row.get("daily_bookings") or 0,
            "weekly_bookings": row.get("weekly_bookings") or 0,
            "daily_revenue": float(row.get("daily_revenue") or 0),
            "weekly_revenue": float(row.get("weekly_revenue") or 0),
        }

    def check_slot_has_availability(
        self,
        departure_time: datetime,
        return_time: datetime,
        party_size: int,
    ) -> bool:
        try:
            with self.database.session() as (_, cursor):
                cursor.execute(
                    """
                    SELECT fn_slot_has_available_assets(%s, %s, %s) AS slot_available
                    """,
                    (departure_time, return_time, party_size),
                )
                row = cursor.fetchone() or {}
            return bool(row.get("slot_available"))
        except Exception:
            with self.database.session() as (_, cursor):
                cursor.execute(
                    """
                    SELECT
                        (
                            EXISTS (
                                SELECT 1
                                FROM cottages c
                                WHERE c.capacity >= %s
                                  AND NOT EXISTS (
                                      SELECT 1
                                      FROM reservations r
                                      WHERE r.cottage_id = c.id
                                        AND r.status IN ('Reserved', 'On Going')
                                        AND NOT (
                                            r.return_time <= %s
                                            OR r.departure_time >= %s
                                        )
                                  )
                            )
                            AND
                            EXISTS (
                                SELECT 1
                                FROM destinations d
                                WHERE d.capacity >= %s
                                  AND NOT EXISTS (
                                      SELECT 1
                                      FROM reservations r
                                      WHERE r.destination_id = d.id
                                        AND r.status IN ('Reserved', 'On Going')
                                        AND NOT (
                                            r.return_time <= %s
                                            OR r.departure_time >= %s
                                        )
                                  )
                            )
                        ) AS slot_available
                    """,
                    (
                        party_size,
                        departure_time,
                        return_time,
                        party_size,
                        departure_time,
                        return_time,
                    ),
                )
                row = cursor.fetchone() or {}
            return bool(row.get("slot_available"))

    def list_session_assignments(self, reference_time: datetime | None = None) -> list[dict]:
        reference_time = reference_time or datetime.now()
        with self.database.session() as (_, cursor):
            cursor.execute(
                """
                SELECT
                    fc.asset_code AS cottage_code,
                    fc.name AS cottage_name,
                    CASE
                        WHEN r.reservation_code IS NULL THEN 'Available'
                        WHEN r.status IN ('Reserved', 'On Going')
                             AND r.departure_time <= %s
                             AND r.return_time > %s THEN 'On Going'
                        ELSE 'Reserved'
                    END AS cottage_status,
                    r.reservation_code,
                    CASE
                        WHEN c.id IS NULL THEN 'Available for booking'
                        WHEN TRIM(COALESCE(c.full_name, '')) = '' THEN 'Guest'
                        ELSE CONCAT(UPPER(LEFT(TRIM(c.full_name), 1)), LOWER(SUBSTRING(TRIM(c.full_name), 2)))
                    END AS customer_name,
                    COALESCE(NULLIF(rds.destination_summary, ''), d.name) AS destination,
                    r.departure_time,
                    r.return_time,
                    r.status AS reservation_status,
                    d.asset_code AS destination_code,
                    d.name AS destination_name,
                    CASE
                        WHEN d.id IS NULL THEN NULL
                        WHEN r.status IN ('Reserved', 'On Going')
                             AND r.departure_time <= %s
                             AND r.return_time > %s THEN 'On Going'
                        ELSE 'Reserved'
                    END AS destination_status
                FROM cottages fc
                LEFT JOIN reservations r
                    ON r.cottage_id = fc.id
                   AND r.status IN ('Reserved', 'On Going')
                   AND r.return_time >= %s
                   AND r.is_deleted = 0
                LEFT JOIN (
                    SELECT
                        rd.reservation_id,
                        GROUP_CONCAT(dest.name ORDER BY rd.sort_order SEPARATOR ', ') AS destination_summary
                    FROM reservation_destinations rd
                    INNER JOIN destinations dest ON dest.id = rd.destination_id
                    GROUP BY rd.reservation_id
                ) rds ON rds.reservation_id = r.id
                LEFT JOIN customers c ON c.id = r.customer_id
                LEFT JOIN destinations d ON d.id = r.destination_id
                ORDER BY fc.id ASC, r.departure_time ASC
                """,
                (reference_time, reference_time, reference_time, reference_time, reference_time),
            )
            rows = cursor.fetchall()
        return [self._with_effective_status(row, reference_time=reference_time) for row in rows]

    def get_asset_status_map(self, asset_type: str, reference_time: datetime) -> list[dict]:
        day_start = datetime.combine(reference_time.date(), time.min)
        day_end = day_start + timedelta(days=1)
        if asset_type == "cottage":
            table_name = "cottages"
            foreign_key = "cottage_id"
        else:
            table_name = "destinations"
            foreign_key = "destination_id"
        query = f"""
            SELECT
                a.id,
                CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM reservations r
                        WHERE r.{foreign_key} = a.id
                          AND r.status IN ('Reserved', 'On Going')
                          AND r.is_deleted = 0
                          AND r.departure_time <= %s
                          AND r.return_time > %s
                    ) THEN 'On Going'
                    WHEN EXISTS (
                        SELECT 1
                        FROM reservations r
                        WHERE r.{foreign_key} = a.id
                          AND r.status IN ('Reserved', 'On Going')
                          AND r.departure_time < %s
                          AND r.return_time > %s
                    ) THEN 'Reserved'
                    ELSE 'Available'
                END AS computed_status
            FROM {table_name} a
            ORDER BY a.id ASC
        """
        with self.database.session() as (_, cursor):
            cursor.execute(query, (reference_time, reference_time, day_end, day_start))
            return cursor.fetchall()

    def get_date_status_map(
        self,
        destination: str | None = None,
        cottage_code: str | None = None,
        days_ahead: int = 120,
    ) -> dict[str, str]:
        today = date.today()
        window_start = datetime.combine(today, time.min)
        window_end = datetime.combine(today + timedelta(days=days_ahead + 1), time.min)
        query = """
            SELECT r.departure_time, r.return_time, r.status
            FROM reservations r
            INNER JOIN cottages c ON c.id = r.cottage_id
            WHERE r.status IN ('Reserved', 'On Going')
              AND r.departure_time < %s
              AND r.return_time >= %s
              AND r.is_deleted = 0
        """
        params: list[object] = [window_end, window_start]
        if cottage_code:
            query += " AND c.asset_code = %s"
            params.append(cottage_code)
        if destination:
            query += """
                AND EXISTS (
                    SELECT 1
                    FROM reservation_destinations rd
                    INNER JOIN destinations d ON d.id = rd.destination_id
                    WHERE rd.reservation_id = r.id
                      AND d.name = %s
                )
            """
            params.append(destination)
        query += " ORDER BY r.departure_time ASC"

        with self.database.session() as (_, cursor):
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

        status_map: dict[str, str] = {}
        for row in rows:
            current_day = row["departure_time"].date()
            last_day = row["return_time"].date()
            mapped_status = self._effective_status(
                row.get("status"),
                row.get("departure_time"),
                row.get("return_time"),
            )
            while current_day <= last_day:
                key = current_day.isoformat()
                if mapped_status == "On Going" or key not in status_map:
                    status_map[key] = mapped_status
                current_day += timedelta(days=1)
        return status_map

    def delete_reservation(self, reservation_code: str) -> bool:
        """Soft-delete a reservation and log to trash_bin."""
        reservation = self.find_by_code(reservation_code)
        if not reservation:
            return False

        with self.database.session() as (_, cursor):
            # 1. Update the record
            cursor.execute(
                "UPDATE reservations SET is_deleted = 1 WHERE reservation_code = %s",
                (reservation_code,),
            )
            # 2. Log to trash bin table
            record_ref = f"{reservation_code} | {reservation.get('full_name', 'Unknown')}"
            cursor.execute(
                "INSERT INTO trash_bin (record_type, record_id, record_ref, original_data) VALUES (%s, %s, %s, %s)",
                (
                    "reservation",
                    reservation["id"],
                    record_ref,
                    json.dumps(reservation, default=str),
                ),
            )
            return cursor.rowcount > 0
