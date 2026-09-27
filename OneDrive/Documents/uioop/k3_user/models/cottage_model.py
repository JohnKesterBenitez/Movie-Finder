"""
models/cottage_model.py - Cottage and destination asset data.
"""

from datetime import date as date_type, datetime, time, timedelta
import re

from k3_user.db import get_database
from k3_rms.cottage_media import COTTAGE_IMAGE_MAP

try:
    from k3_rms.config import DESTINATIONS as CONFIG_DESTINATIONS
except Exception:  # pragma: no cover - standalone fallback
    CONFIG_DESTINATIONS = (
        "SandBar Area",
        "Snorkeling Area",
        "Starfish Area",
        "Little Boracay",
    )

DESTINATION_GUIDES = {
    "SandBar Area": {
        "summary": "A bright sandbar stop with calm shallows and open shoreline views.",
        "highlights": ("Shallow water", "Sunrise photos", "Relaxed shoreline stop"),
        "image": "images/sandbar_area.jpg",
    },
    "Snorkeling Area": {
        "summary": "A clear-water stop best known for reef viewing and easy snorkeling sessions.",
        "highlights": ("Reef views", "Snorkeling stop", "Clear water"),
        "image": "images/snorkeling_area.jpg",
    },
    "Starfish Area": {
        "summary": "A scenic shallow zone where guests usually slow down for photos and wading.",
        "highlights": ("Starfish sightings", "Photo spot", "Gentle shallow zone"),
        "image": "images/starfish_area.jpg",
    },
    "Little Boracay": {
        "summary": "A soft white-sand destination with the most resort-like beach atmosphere in the route.",
        "highlights": ("White sand", "Swimming stop", "Island-style view"),
        "image": "images/little_boracay_area.jpg",
    },
    "Wave Runner": {
        "summary": "An exciting wave runner experience across open waters for thrill-seeking guests.",
        "highlights": ("Wave runner ride", "Open water", "Adventure activity"),
        "image": "images/wave_runner.jpg",
    },
}

DESTINATIONS = tuple(CONFIG_DESTINATIONS)
SLOTS = ["06:00", "07:00", "08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00"]
DURATIONS = [str(hour) for hour in range(1, 9)]
PARTY_SIZES = [str(size) for size in range(1, 21)]


def _normalize_selected_date(selected_date: str | date_type | None) -> date_type:
    if isinstance(selected_date, date_type):
        return selected_date
    if isinstance(selected_date, str) and selected_date.strip():
        try:
            return datetime.strptime(selected_date.strip(), "%Y-%m-%d").date()
        except ValueError:
            pass
    return date_type.today()


def _destination_slug(name: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower())
    return cleaned.strip("_") or "destination"


def _destination_metadata(name: str) -> dict:
    guide = DESTINATION_GUIDES.get(name, {})
    image_path = guide.get("image") or f"images/{_destination_slug(name)}.jpg"
    return {
        "summary": guide.get(
            "summary",
            "A featured stop in the floating cottage route, shared here for guest reference.",
        ),
        "highlights": tuple(
            guide.get(
                "highlights",
                ("Island view", "Photo stop", "Resort route guide"),
            )
        ),
        "image": image_path,
        "image_hint": f"Upload a destination photo later to {image_path}",
        "booking_note": "Select multiple destinations during booking. Some spots have additional rates.",
    }


def _fetch_assets(
    table_name: str,
    asset_type: str,
    selected_date: str | date_type | None = None,
) -> list[dict]:
    database = get_database()
    target_date = _normalize_selected_date(selected_date)
    day_start = datetime.combine(target_date, time.min)
    day_end = day_start + timedelta(days=1)
    now = datetime.now()
    is_today = 1 if target_date == date_type.today() else 0
    with database.session() as (_, cursor):
        base_query = f"""
            SELECT
                id,
                asset_code,
                name,
                capacity,
                base_rate,
                CASE
                    WHEN %s = 1
                         AND EXISTS (
                             SELECT 1
                             FROM reservations r
                             WHERE r.{"cottage_id" if asset_type == "cottage" else "destination_id"} = {table_name}.id
                               AND r.status = 'On Going'
                               AND r.departure_time <= %s
                               AND r.return_time > %s
                         ) THEN 'On Going'
                    WHEN EXISTS (
                        SELECT 1
                        FROM reservations r
                        WHERE r.{"cottage_id" if asset_type == "cottage" else "destination_id"} = {table_name}.id
                          AND r.status IN ('Reserved', 'On Going')
                          AND r.departure_time < %s
                          AND r.return_time > %s
                    ) THEN 'Reserved'
                    ELSE 'Available'
                END AS status
            FROM {table_name}
        """
        params: list[object] = [is_today, now, now, day_end, day_start]
        cursor.execute(
            f"{base_query} ORDER BY id ASC",
            tuple(params),
        )
        rows = cursor.fetchall()
    assets = []
    for row in rows:
        asset = {
            "db_id": row["id"],
            "id": row["asset_code"],
            "name": row["name"],
            "capacity": int(row["capacity"]),
            "rate": float(row["base_rate"]),
            "status": row["status"],
            "type": asset_type,
        }
        if asset_type == "cottage":
            asset["image"] = COTTAGE_IMAGE_MAP.get(row["asset_code"])
        else:
            asset.update(_destination_metadata(row["name"]))
        assets.append(asset)
    return assets


class CottageModel:
    @staticmethod
    def get_all(selected_date: str | date_type | None = None) -> list[dict]:
        return _fetch_assets("cottages", "cottage", selected_date)

    @staticmethod
    def get_by_id(cid: str, selected_date: str | date_type | None = None) -> dict | None:
        for cottage in CottageModel.get_all(selected_date):
            if cottage["id"] == cid:
                return cottage
        return None

    @staticmethod
    def calculate_total(cottage: dict, hours: int) -> float:
        return float(cottage["rate"]) * hours


class BoatModel:
    @staticmethod
    def get_all(selected_date: str | date_type | None = None) -> list[dict]:
        return _fetch_assets("destinations", "boat", selected_date)

    @staticmethod
    def get_guides() -> list[dict]:
        return [dict(item) for item in BoatModel.get_all()]

    @staticmethod
    def get_by_id(bid: str, selected_date: str | date_type | None = None) -> dict | None:
        for destination in BoatModel.get_all(selected_date):
            if destination["id"] == bid:
                return destination
        return None

    @staticmethod
    def calculate_total(boat: dict, hours: int) -> float:
        return float(boat["rate"]) * hours
