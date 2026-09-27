from datetime import date, datetime, time, timedelta

from k3_rms.config import DESTINATIONS
from k3_rms.database.connection import DatabaseManager


class AssetModel:
    TABLE_MAP = {
        "cottage": ("cottages", "cottage_id"),
        "destination": ("destinations", "destination_id"),
        "motorboat": ("destinations", "destination_id"),
    }

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def list_cottages(
        self,
        reference_date: date | None = None,
        reference_time: datetime | None = None,
    ) -> list[dict]:
        return self._list_assets("cottages", "cottage_id", reference_date, reference_time)

    def list_motorboats(
        self,
        reference_date: date | None = None,
        reference_time: datetime | None = None,
    ) -> list[dict]:
        return self._list_assets("destinations", "destination_id", reference_date, reference_time)

    def list_destinations(
        self,
        reference_date: date | None = None,
        reference_time: datetime | None = None,
    ) -> list[dict]:
        return self._list_assets("destinations", "destination_id", reference_date, reference_time)

    def find_available_assets(
        self,
        asset_type: str,
        departure_time,
        return_time,
        party_size: int,
    ) -> list[dict]:
        table_name, foreign_key = self.TABLE_MAP[asset_type]
        destination_filter = ""
        params: list[object] = [party_size]
        if table_name == "destinations":
            placeholders = ", ".join(["%s"] * len(DESTINATIONS))
            destination_filter = f" AND a.name IN ({placeholders})"
            params.extend(DESTINATIONS)

        exclusion_clause = ""
        if asset_type == "cottage":
            exclusion_clause = f"""
                AND a.id NOT IN (
                    SELECT r.{foreign_key}
                    FROM reservations r
                    WHERE r.status IN ('Reserved', 'On Going')
                      AND NOT (r.return_time <= %s OR r.departure_time >= %s)
                )
            """
            params.extend([departure_time, return_time])

        query = f"""
            SELECT
                a.id,
                a.asset_code,
                a.name,
                a.capacity,
                a.base_rate,
                a.created_at,
                'Available' AS status
            FROM {table_name} a
            WHERE a.capacity >= %s
              {destination_filter}
              {exclusion_clause}
            ORDER BY a.capacity ASC, a.id ASC
        """
        with self.database.session() as (_, cursor):
            cursor.execute(query, tuple(params))
            return cursor.fetchall()

    def get_asset(self, asset_type: str, asset_id: int) -> dict | None:
        table_name, _ = self.TABLE_MAP[asset_type]
        with self.database.session() as (_, cursor):
            cursor.execute(
                f"""
                SELECT id, asset_code, name, capacity, base_rate, created_at
                FROM {table_name}
                WHERE id = %s
                """,
                (asset_id,),
            )
            return cursor.fetchone()

    def update_status(self, asset_type: str, asset_id: int, status: str) -> None:
        del asset_type, asset_id, status

    def _list_assets(
        self,
        table_name: str,
        foreign_key: str,
        reference_date: date | None = None,
        reference_time: datetime | None = None,
    ) -> list[dict]:
        target_date = reference_date or (reference_time.date() if reference_time else date.today())
        reference_point = reference_time or datetime.combine(target_date, time.min)
        day_start = datetime.combine(target_date, time.min)
        day_end = day_start + timedelta(days=1)
        with self.database.session() as (_, cursor):
            base_query = f"""
                SELECT
                    a.id,
                    a.asset_code,
                    a.name,
                    a.capacity,
                    a.base_rate,
                    a.created_at,
                    CASE
                        WHEN '{table_name}' = 'cottages' AND EXISTS (
                            SELECT 1
                            FROM reservations r
                            WHERE r.cottage_id = a.id
                              AND r.status IN ('Reserved', 'On Going')
                              AND r.departure_time <= %s
                              AND r.return_time > %s
                        ) THEN 'On Going'
                        WHEN '{table_name}' = 'cottages' AND EXISTS (
                            SELECT 1
                            FROM reservations r
                            WHERE r.cottage_id = a.id
                              AND r.status IN ('Reserved', 'On Going')
                              AND r.departure_time < %s
                              AND r.return_time > %s
                        ) THEN 'Reserved'
                        ELSE 'Available'
                    END AS status
                FROM {table_name} a
            """
            params: list[object] = [reference_point, reference_point, day_end, day_start]
            if table_name == "destinations":
                placeholders = ", ".join(["%s"] * len(DESTINATIONS))
                cursor.execute(
                    f"{base_query} WHERE a.name IN ({placeholders}) ORDER BY a.id ASC",
                    tuple(params + list(DESTINATIONS)),
                )
            else:
                cursor.execute(f"{base_query} ORDER BY a.id ASC", tuple(params))
            return cursor.fetchall()
