"""Reservation persistence."""

from datetime import date as date_type, datetime, time, timedelta

from k3_user.db import get_database
from k3_rms.config import PENDING_APPROVAL_DEADLINE_HOURS

try:
    from models.user_model import UserModel
except ImportError:  # pragma: no cover - package import fallback
    from k3_user.models.user_model import UserModel

DATETIME_FORMAT = "%Y-%m-%d %H:%M"
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


def _gen_ref() -> str:
    import random
    import string
    characters = string.ascii_uppercase + string.digits
    database = get_database()
    while True:
        code = "K3-" + "".join(random.choices(characters, k=5))
        # Check uniqueness
        with database.session() as (_, cursor):
            cursor.execute("SELECT 1 FROM reservations WHERE reservation_code = %s LIMIT 1", (code,))
            if not cursor.fetchone():
                return code


def _format_reservation(row: dict) -> dict:
    departure_time = row["departure_time"]
    return_time = row["return_time"]
    hours = max(int((return_time - departure_time).total_seconds() // 3600), 1)
    return {
        "ref": row["reservation_code"],
        "username": row.get("username") or "",
        "name": row.get("full_name") or "",
        "contact": row.get("contact_number") or "",
        "email": row.get("email") or "",
        "type": "cottage",
        "cottage_id": row["cottage_code"],
        "cottage_name": row["cottage_name"],
        "destination": row["destination"],
        "date": departure_time.strftime("%Y-%m-%d"),
        "slot": departure_time.strftime("%H:%M"),
        "hours": hours,
        "party": row["party_size"],
        "notes": row.get("notes") or "",
        "total": float(row["total_price"]),
        "status": row["status"],
        "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else row["created_at"],
    }


def _normalize_destination_names(destinations: list[str] | None, fallback_summary: str | None = None) -> list[str]:
    candidates = list(destinations or [])
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


def _auto_expire_pending_reservations(
    database,
    deadline_hours: int = PENDING_APPROVAL_DEADLINE_HOURS,
) -> None:
    deadline_hours = max(int(deadline_hours), 0)
    now = datetime.now()
    cutoff = now + timedelta(hours=deadline_hours)
    reason = (
        "System: Auto-expired because the booking was still pending "
        f"within {deadline_hours} hour(s) of departure."
    )
    with database.session() as (_, cursor):
        # Auto-expire pending
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
        
        # Auto-start reserved
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
        
        # Auto-complete past reservations
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


class ReservationModel:
    ACTIVE_STATUSES = {"Confirmed", "Reserved", "On Going"}

    @staticmethod
    def create(
        username: str,
        guest_info: dict,
        cottage: dict,
        destinations: list[str],
        date: str,
        slot: str,
        hours: int,
        party: int,
        notes: str,
        booking_type: str = "cottage",
    ) -> dict:
        del guest_info, booking_type
        database = get_database()
        user = UserModel.get_user(username)
        customer = UserModel.get_customer_record(username)
        if user is None or customer is None or user.get("id") is None or customer.get("id") is None:
            raise ValueError("Missing database-backed user profile.")

        departure_time = datetime.strptime(f"{date.strip()} {slot.strip()}", DATETIME_FORMAT)
        return_time = departure_time + timedelta(hours=hours)
        reservation_code = _gen_ref()
        destinations = _normalize_destination_names(destinations)
        if not destinations:
            raise ValueError("Select at least one destination.")

        with database.session() as (_, cursor):
            cursor.execute(
                """
                SELECT id, asset_code, name, base_rate
                FROM cottages
                WHERE asset_code = %s
                LIMIT 1
                """,
                (cottage["id"],),
            )
            cottage_row = cursor.fetchone()

            # Fetch all destination objects for pricing
            placeholders = ", ".join(["%s"] * len(destinations))
            cursor.execute(
                f"SELECT id, name, base_rate FROM destinations WHERE name IN ({placeholders})",
                tuple(destinations)
            )
            dest_rows = cursor.fetchall()

            if cottage_row is None or not dest_rows:
                raise ValueError("Selected cottage or destinations were not found in the database.")

            cursor.execute(
                """
                SELECT r.reservation_code
                FROM reservations r
                WHERE r.status IN ('Reserved', 'On Going')
                  AND NOT (r.return_time <= %s OR r.departure_time >= %s)
                  AND r.cottage_id = %s
                LIMIT 1
                """,
                (
                    departure_time,
                    return_time,
                    cottage_row["id"],
                ),
            )
            conflict = cursor.fetchone()
            if conflict is not None:
                raise ValueError("That cottage is already reserved for the selected date and time.")

            total_dest_rate = sum(float(row["base_rate"]) for row in dest_rows)
            total = round((float(cottage_row["base_rate"]) + total_dest_rate) * hours, 2)
            
            # Primary destination ID and summary
            primary_dest_id = dest_rows[0]["id"]

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
                    reservation_code,
                    user["id"],
                    customer["id"],
                    cottage_row["id"],
                    primary_dest_id,
                    party,
                    departure_time,
                    return_time,
                    total,
                    "Pending",
                    notes,
                ),
            )
            reservation_id = cursor.lastrowid
            _replace_reservation_destinations(
                cursor,
                reservation_id=reservation_id,
                primary_destination_id=int(primary_dest_id),
                destination_names=destinations,
            )
        return ReservationModel.get_by_code(reservation_code)

    @staticmethod
    def get_by_code(code: str) -> dict:
        database = get_database()
        _auto_expire_pending_reservations(database)
        with database.session() as (_, cursor):
            cursor.execute(
                f"""
                SELECT
                    r.reservation_code,
                    COALESCE(NULLIF(rds.destination_summary, ''), d.name) AS destination,
                    r.party_size,
                    r.departure_time,
                    r.return_time,
                    r.total_price,
                    r.status,
                    r.notes,
                    r.created_at,
                    u.username,
                    c.full_name,
                    c.contact_number,
                    c.email,
                    fc.asset_code AS cottage_code,
                    fc.name AS cottage_name
                FROM reservations r
                {DESTINATION_SUMMARY_JOIN}
                INNER JOIN users u ON u.id = r.user_id
                INNER JOIN customers c ON c.id = r.customer_id
                INNER JOIN cottages fc ON fc.id = r.cottage_id
                LEFT JOIN destinations d ON d.id = r.destination_id
                WHERE r.reservation_code = %s
                LIMIT 1
                """,
                (code,),
            )
            row = cursor.fetchone()
        if row is None:
            raise ValueError("Reservation was created but could not be reloaded.")
        return _format_reservation(row)

    @staticmethod
    def get_by_username(username: str) -> list[dict]:
        normalized = username.strip().lower()
        database = get_database()
        _auto_expire_pending_reservations(database)
        with database.session() as (_, cursor):
            cursor.execute(
                f"""
                SELECT
                    r.reservation_code,
                    COALESCE(NULLIF(rds.destination_summary, ''), d.name) AS destination,
                    r.party_size,
                    r.departure_time,
                    r.return_time,
                    r.total_price,
                    r.status,
                    r.notes,
                    r.created_at,
                    u.username,
                    c.full_name,
                    c.contact_number,
                    c.email,
                    fc.asset_code AS cottage_code,
                    fc.name AS cottage_name
                FROM reservations r
                {DESTINATION_SUMMARY_JOIN}
                INNER JOIN users u ON u.id = r.user_id
                INNER JOIN customers c ON c.id = r.customer_id
                INNER JOIN cottages fc ON fc.id = r.cottage_id
                LEFT JOIN destinations d ON d.id = r.destination_id
                WHERE u.username = %s
                ORDER BY r.created_at ASC
                """,
                (normalized,),
            )
            return [_format_reservation(row) for row in cursor.fetchall()]

    @staticmethod
    def get_payment_history_by_username(username: str) -> list[dict]:
        normalized = username.strip().lower()
        database = get_database()
        _auto_expire_pending_reservations(database)
        with database.session() as (_, cursor):
            cursor.execute(
                """
                SELECT 
                    p.*,
                    r.reservation_code,
                    r.total_price,
                    COALESCE(t.total_paid, 0) AS total_paid,
                    GREATEST(r.total_price - COALESCE(t.total_paid, 0), 0) AS balance_due
                FROM payments p
                INNER JOIN reservations r ON r.id = p.reservation_id
                INNER JOIN users u ON u.id = r.user_id
                LEFT JOIN (
                    SELECT reservation_id, SUM(payment_amount) AS total_paid
                    FROM payments
                    GROUP BY reservation_id
                ) t ON t.reservation_id = r.id
                WHERE u.username = %s
                ORDER BY p.recorded_at DESC
                """,
                (normalized,),
            )
            return cursor.fetchall()

    @staticmethod
    def get_all() -> list[dict]:
        database = get_database()
        _auto_expire_pending_reservations(database)
        with database.session() as (_, cursor):
            cursor.execute(
                f"""
                SELECT
                    r.reservation_code,
                    COALESCE(NULLIF(rds.destination_summary, ''), d.name) AS destination,
                    r.party_size,
                    r.departure_time,
                    r.return_time,
                    r.total_price,
                    r.status,
                    r.notes,
                    r.created_at,
                    u.username,
                    c.full_name,
                    c.contact_number,
                    c.email,
                    fc.asset_code AS cottage_code,
                    fc.name AS cottage_name
                FROM reservations r
                {DESTINATION_SUMMARY_JOIN}
                LEFT JOIN users u ON u.id = r.user_id
                INNER JOIN customers c ON c.id = r.customer_id
                INNER JOIN cottages fc ON fc.id = r.cottage_id
                LEFT JOIN destinations d ON d.id = r.destination_id
                ORDER BY r.created_at ASC
                """
            )
            return [_format_reservation(row) for row in cursor.fetchall()]

    @staticmethod
    def is_slot_available(
        cottage_id: str,
        destination: str,
        travel_date: str,
        slot: str,
        hours: int,
    ) -> bool:
        del destination
        departure_time = datetime.strptime(f"{travel_date.strip()} {slot.strip()}", DATETIME_FORMAT)
        return_time = departure_time + timedelta(hours=max(hours, 1))
        database = get_database()
        with database.session() as (_, cursor):
            cursor.execute(
                """
                SELECT 1
                FROM reservations r
                INNER JOIN cottages fc ON fc.id = r.cottage_id
                WHERE r.status IN ('Reserved', 'On Going')
                  AND NOT (r.return_time <= %s OR r.departure_time >= %s)
                  AND fc.asset_code = %s
                LIMIT 1
                """,
                (
                    departure_time,
                    return_time,
                    cottage_id,
                ),
            )
            return cursor.fetchone() is None

    @staticmethod
    def get_date_status_map(
        cottage_id: str | None = None,
        destination: str | None = None,
        days_ahead: int = 120,
    ) -> dict[str, str]:
        status_map: dict[str, str] = {}
        today = date_type.today()
        window_start = datetime.combine(today, time.min)
        window_end = datetime.combine(today + timedelta(days=days_ahead + 1), time.min)

        database = get_database()
        query = """
            SELECT r.departure_time, r.return_time, r.status
            FROM reservations r
            INNER JOIN cottages fc ON fc.id = r.cottage_id
            WHERE r.status IN ('Reserved', 'On Going')
              AND r.departure_time < %s
              AND r.return_time >= %s
        """
        params: list[object] = [window_end, window_start]
        if cottage_id:
            query += " AND fc.asset_code = %s"
            params.append(cottage_id)
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

        with database.session() as (_, cursor):
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

        for row in rows:
            ReservationModel._mark_status_dates(
                status_map,
                row["departure_time"],
                row["return_time"],
                row["status"],
            )
        return status_map

    @staticmethod
    def _mark_status_dates(
        status_map: dict[str, str],
        departure_time: datetime,
        return_time: datetime,
        status: str,
    ) -> None:
        current_day = departure_time.date()
        last_day = return_time.date()
        mapped_status = "On Going" if status == "On Going" else "Reserved"
        while current_day <= last_day:
            key = current_day.isoformat()
            if mapped_status == "On Going" or key not in status_map:
                status_map[key] = mapped_status
            current_day += timedelta(days=1)
