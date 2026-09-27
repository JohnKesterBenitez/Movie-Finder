from datetime import date, datetime, time, timedelta

from k3_rms.config import DEFAULT_COTTAGES, DEFAULT_MOTORBOATS
from k3_rms.exceptions import ReservationValidationError


class InMemoryCustomerModel:
    def __init__(self) -> None:
        self._customers: list[dict] = []
        self._next_id = 1
        for full_name, contact_number, email in (
            ("Jamie Cruz", "09171234567", "jamie@k3demo.local"),
            ("Mika Santos", "09179876543", "mika@k3demo.local"),
            ("John Kester", "09123456789", "john.kester@k3demo.local"),
            ("Carla Dominguez", "09181234001", "carla.dominguez@k3demo.local"),
            ("Paul Reyes", "09181234002", "paul.reyes@k3demo.local"),
            ("Trisha Mendoza", "09181234003", "trisha.mendoza@k3demo.local"),
            ("Denise Garcia", "09181234004", "denise.garcia@k3demo.local"),
        ):
            self.upsert_customer(full_name, contact_number, email)

    def find_known_customer(self, email: str | None, contact_number: str | None) -> dict | None:
        for customer in self._customers:
            if email and customer["email"] == email:
                return dict(customer)
            if contact_number and customer["contact_number"] == contact_number:
                return dict(customer)
        return None

    def upsert_customer(self, full_name: str, contact_number: str | None, email: str | None) -> dict:
        existing = self.find_known_customer(email, contact_number)
        now = datetime.now()
        if existing:
            record = self._get_customer_by_id(existing["id"])
            record["full_name"] = full_name or record["full_name"]
            record["contact_number"] = contact_number or record["contact_number"]
            record["email"] = email or record["email"]
            record["updated_at"] = now
            return dict(record)

        record = {
            "id": self._next_id,
            "full_name": full_name,
            "contact_number": contact_number,
            "email": email,
            "created_at": now,
            "updated_at": now,
        }
        self._next_id += 1
        self._customers.append(record)
        return dict(record)

    def get_by_id(self, customer_id: int) -> dict | None:
        record = self._get_customer_by_id(customer_id)
        return dict(record) if record else None

    def _get_customer_by_id(self, customer_id: int) -> dict | None:
        for customer in self._customers:
            if customer["id"] == customer_id:
                return customer
        return None


class InMemoryAssetModel:
    TABLE_MAP = {
        "cottage": ("cottages", "cottage_id"),
        "destination": ("destinations", "destination_id"),
        "motorboat": ("motorboats", "motorboat_id"),
    }

    def __init__(self) -> None:
        self._assets = {
            "cottage": self._seed_assets(DEFAULT_COTTAGES),
            "motorboat": self._seed_assets(DEFAULT_MOTORBOATS),
        }
        self.reservation_model = None

    def attach_reservation_model(self, reservation_model) -> None:
        self.reservation_model = reservation_model

    def list_cottages(
        self,
        reference_date: date | None = None,
        reference_time: datetime | None = None,
    ) -> list[dict]:
        return self._list_assets("cottage", reference_date, reference_time)

    def list_motorboats(
        self,
        reference_date: date | None = None,
        reference_time: datetime | None = None,
    ) -> list[dict]:
        return self._list_assets("motorboat", reference_date, reference_time)

    def find_available_assets(
        self,
        asset_type: str,
        departure_time,
        return_time,
        party_size: int,
    ) -> list[dict]:
        normalized_asset_type = self._normalize_asset_type(asset_type)
        _, foreign_key = self.TABLE_MAP[asset_type]
        reservations = self.reservation_model.raw_reservations() if self.reservation_model else []
        available = []
        for asset in self._assets[normalized_asset_type]:
            if asset["capacity"] < party_size:
                continue
            conflict = any(
                reservation[foreign_key] == asset["id"]
                and reservation["status"] in ("Reserved", "On Going")
                and not (
                    reservation["return_time"] <= departure_time
                    or reservation["departure_time"] >= return_time
                )
                for reservation in reservations
            )
            if not conflict:
                row = dict(asset)
                row["status"] = "Available"
                available.append(row)
        return available

    def get_asset(self, asset_type: str, asset_id: int) -> dict | None:
        for asset in self._assets[self._normalize_asset_type(asset_type)]:
            if asset["id"] == asset_id:
                return dict(asset)
        return None

    def update_status(self, asset_type: str, asset_id: int, status: str) -> None:
        del asset_type, asset_id, status

    def _normalize_asset_type(self, asset_type: str) -> str:
        return "motorboat" if asset_type == "destination" else asset_type

    def _list_assets(
        self,
        asset_type: str,
        reference_date: date | None = None,
        reference_time: datetime | None = None,
    ) -> list[dict]:
        normalized_asset_type = self._normalize_asset_type(asset_type)
        foreign_key = "cottage_id" if normalized_asset_type == "cottage" else "destination_id"
        target_date = reference_date or (reference_time.date() if reference_time else date.today())
        reference_point = reference_time or datetime.combine(target_date, time.min)
        day_start = datetime.combine(target_date, time.min)
        day_end = day_start + timedelta(days=1)
        reservations = self.reservation_model.raw_reservations() if self.reservation_model else []

        rows: list[dict] = []
        for asset in self._assets[normalized_asset_type]:
            status = "Available"
            if any(
                reservation[foreign_key] == asset["id"]
                and reservation["status"] in ("Reserved", "On Going")
                and reservation["departure_time"] <= reference_point < reservation["return_time"]
                for reservation in reservations
            ):
                status = "On Going"
            elif any(
                reservation[foreign_key] == asset["id"]
                and reservation["status"] in ("Reserved", "On Going")
                and not (
                    reservation["return_time"] <= day_start
                    or reservation["departure_time"] >= day_end
                )
                for reservation in reservations
            ):
                status = "Reserved"
            row = dict(asset)
            row["status"] = status
            rows.append(row)
        return rows

    def _seed_assets(self, assets: tuple[dict, ...]) -> list[dict]:
        seeded = []
        for index, asset in enumerate(assets, start=1):
            seeded.append(
                {
                    "id": index,
                    "asset_code": asset["asset_code"],
                    "name": asset["name"],
                    "capacity": asset["capacity"],
                    "base_rate": asset["base_rate"],
                    "created_at": datetime.now(),
                }
            )
        return seeded


class InMemoryReservationModel:
    STATUS_OPTIONS = ("Reserved", "On Going", "Completed", "Cancelled")

    def __init__(self, customer_model: InMemoryCustomerModel, asset_model: InMemoryAssetModel) -> None:
        self.customer_model = customer_model
        self.asset_model = asset_model
        self._reservations: list[dict] = []
        self._next_id = 1
        self._seed_demo_data()

    def raw_reservations(self) -> list[dict]:
        return self._reservations

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

    def create(self, reservation: dict) -> None:
        if self.has_conflict(
            cottage_id=reservation["cottage_id"],
            destination_id=reservation.get("destination_id") or reservation.get("motorboat_id"),
            departure_time=reservation["departure_time"],
            return_time=reservation["return_time"],
        ):
            raise ReservationValidationError(
                "That cottage or destination is already reserved for the selected date and time."
            )
        now = datetime.now()
        record = {
            "id": self._next_id,
            "reservation_code": reservation["reservation_code"],
            "user_id": reservation.get("user_id"),
            "customer_id": reservation["customer_id"],
            "cottage_id": reservation["cottage_id"],
            "destination_id": reservation.get("destination_id") or reservation.get("motorboat_id"),
            "destination": reservation["destination"],
            "party_size": reservation["party_size"],
            "departure_time": reservation["departure_time"],
            "return_time": reservation["return_time"],
            "total_price": reservation["total_price"],
            "status": reservation["status"],
            "notes": reservation.get("notes"),
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
            "cancelled_at": None,
        }
        self._next_id += 1
        self._reservations.append(record)

    def has_conflict(
        self,
        cottage_id: int,
        destination_id: int,
        departure_time: datetime,
        return_time: datetime,
        exclude_reservation_code: str | None = None,
    ) -> bool:
        for reservation in self._reservations:
            if reservation["status"] not in ("Reserved", "On Going"):
                continue
            if exclude_reservation_code and reservation["reservation_code"] == exclude_reservation_code:
                continue
            if reservation["cottage_id"] != cottage_id and reservation["destination_id"] != destination_id:
                continue
            if not (
                reservation["return_time"] <= departure_time
                or reservation["departure_time"] >= return_time
            ):
                return True
        return False

    def find_by_code(self, reservation_code: str) -> dict | None:
        record = self._find_record(reservation_code)
        return self._expand_record(record) if record else None

    def update_status(self, reservation_code: str, status: str, notes: str | None = None) -> None:
        record = self._find_record(reservation_code)
        if record is None:
            return
        now = datetime.now()
        record["status"] = status
        record["updated_at"] = now
        if notes:
            record["notes"] = notes
        if status == "Completed":
            record["completed_at"] = now
        if status == "Cancelled":
            record["cancelled_at"] = now

    def list_active_reservations(self) -> list[dict]:
        active = [
            self._expand_record(record)
            for record in self._reservations
            if record["status"] in ("Reserved", "On Going")
        ]
        active.sort(key=lambda reservation: reservation["departure_time"])
        return active[:10]

    def list_recent_reservations(self, limit: int = 8) -> list[dict]:
        recent = [self._expand_record(record) for record in self._reservations]
        recent.sort(key=lambda reservation: reservation["created_at"], reverse=True)
        return recent[:limit]

    def list_reservations(self, limit: int | None = None) -> list[dict]:
        reservations = [self._expand_record(record) for record in self._reservations]
        reservations.sort(key=lambda reservation: (reservation["departure_time"], reservation["created_at"]))
        if isinstance(limit, int):
            return reservations[:limit]
        return reservations

    def get_dashboard_metrics(self) -> dict:
        today = date.today()
        current_week = today.isocalendar()[:2]
        return {
            "active_reservations": sum(
                1 for reservation in self._reservations if reservation["status"] in ("Reserved", "On Going")
            ),
            "completed_trips": sum(
                1 for reservation in self._reservations if reservation["status"] == "Completed"
            ),
            "cancellations": sum(
                1 for reservation in self._reservations if reservation["status"] == "Cancelled"
            ),
            "daily_bookings": sum(
                1 for reservation in self._reservations if reservation["created_at"].date() == today
            ),
            "weekly_bookings": sum(
                1
                for reservation in self._reservations
                if reservation["created_at"].date().isocalendar()[:2] == current_week
            ),
            "daily_revenue": float(
                sum(
                    reservation["total_price"]
                    for reservation in self._reservations
                    if reservation["created_at"].date() == today
                )
            ),
            "weekly_revenue": float(
                sum(
                    reservation["total_price"]
                    for reservation in self._reservations
                    if reservation["created_at"].date().isocalendar()[:2] == current_week
                )
            ),
        }

    def check_slot_has_availability(
        self,
        departure_time: datetime,
        return_time: datetime,
        party_size: int,
    ) -> bool:
        available_cottages = self.asset_model.find_available_assets(
            "cottage",
            departure_time,
            return_time,
            party_size,
        )
        available_motorboats = self.asset_model.find_available_assets(
            "destination",
            departure_time,
            return_time,
            party_size,
        )
        return bool(available_cottages and available_motorboats)

    def list_session_assignments(self, reference_time: datetime | None = None) -> list[dict]:
        reference_time = reference_time or datetime.now()
        cottage_statuses = {
            cottage["id"]: cottage["status"]
            for cottage in self.asset_model.list_cottages(reference_time.date(), reference_time)
        }
        destination_statuses = {
            destination["id"]: destination["status"]
            for destination in self.asset_model.list_motorboats(reference_time.date(), reference_time)
        }
        rows = []
        for cottage in self.asset_model.list_cottages(reference_time.date(), reference_time):
            related = [
                reservation
                for reservation in self._reservations
                if reservation["cottage_id"] == cottage["id"]
                and reservation["status"] in ("Reserved", "On Going")
                and reservation["return_time"] >= reference_time
            ]
            if not related:
                rows.append(
                    {
                        "cottage_code": cottage["asset_code"],
                        "cottage_name": cottage["name"],
                        "cottage_status": cottage_statuses.get(cottage["id"], "Available"),
                        "reservation_code": None,
                        "customer_name": "Available for booking",
                        "destination": None,
                        "departure_time": None,
                        "return_time": None,
                        "reservation_status": None,
                        "destination_code": None,
                        "destination_name": None,
                        "destination_status": None,
                    }
                )
                continue

            for reservation in sorted(related, key=lambda item: item["departure_time"]):
                expanded = self._expand_record(reservation)
                rows.append(
                    {
                        "cottage_code": expanded["cottage_code"],
                        "cottage_name": expanded["cottage_name"],
                        "cottage_status": cottage_statuses.get(cottage["id"], "Available"),
                        "reservation_code": expanded["reservation_code"],
                        "customer_name": expanded["full_name"],
                        "destination": expanded["destination"],
                        "departure_time": expanded["departure_time"],
                        "return_time": expanded["return_time"],
                        "reservation_status": expanded["status"],
                        "destination_code": expanded["destination_code"],
                        "destination_name": expanded["destination_name"],
                        "destination_status": destination_statuses.get(expanded["destination_id"]),
                    }
                )
        return rows

    def get_asset_status_map(self, asset_type: str, reference_time: datetime) -> list[dict]:
        if asset_type == "cottage":
            assets = self.asset_model.list_cottages(reference_time.date(), reference_time)
        else:
            assets = self.asset_model.list_motorboats(reference_time.date(), reference_time)

        status_map = []
        for asset in assets:
            status_map.append({"id": asset["id"], "computed_status": asset["status"]})
        return status_map

    def get_date_status_map(
        self,
        destination: str | None = None,
        cottage_code: str | None = None,
        days_ahead: int = 120,
    ) -> dict[str, str]:
        status_map: dict[str, str] = {}
        end_date = date.today() + timedelta(days=days_ahead)
        for reservation in self._reservations:
            if reservation["status"] not in ("Reserved", "On Going"):
                continue
            if cottage_code:
                cottage = self.asset_model.get_asset("cottage", reservation["cottage_id"]) or {}
                if cottage.get("asset_code") != cottage_code:
                    continue
            if destination and reservation["destination"] != destination:
                continue
            current_day = reservation["departure_time"].date()
            last_day = reservation["return_time"].date()
            mapped_status = self._effective_status(
                reservation.get("status"),
                reservation.get("departure_time"),
                reservation.get("return_time"),
            )
            while current_day <= last_day:
                if current_day > end_date:
                    break
                key = current_day.isoformat()
                if mapped_status == "On Going" or key not in status_map:
                    status_map[key] = mapped_status
                current_day += timedelta(days=1)
        return status_map

    def _expand_record(self, record: dict) -> dict:
        customer = self.customer_model.get_by_id(record["customer_id"]) or {}
        cottage = self.asset_model.get_asset("cottage", record["cottage_id"]) or {}
        motorboat = self.asset_model.get_asset("destination", record["destination_id"]) or {}
        expanded = dict(record)
        expanded.update(
            {
                "full_name": self._format_customer_name(customer.get("full_name")),
                "contact_number": customer.get("contact_number"),
                "email": customer.get("email"),
                "cottage_code": cottage.get("asset_code"),
                "cottage_name": cottage.get("name"),
                "destination_code": motorboat.get("asset_code"),
                "destination_name": motorboat.get("name"),
                "remaining_session_minutes": self._remaining_session_minutes(record["return_time"]),
                "status": self._effective_status(
                    record.get("status"),
                    record.get("departure_time"),
                    record.get("return_time"),
                ),
            }
        )
        return expanded

    def _find_record(self, reservation_code: str) -> dict | None:
        for reservation in self._reservations:
            if reservation["reservation_code"] == reservation_code:
                return reservation
        return None

    def _format_customer_name(self, full_name: str | None) -> str:
        if not full_name:
            return "Guest"
        cleaned = full_name.strip()
        return cleaned[:1].upper() + cleaned[1:].lower()

    def _remaining_session_minutes(self, return_time: datetime) -> int:
        return max(int((return_time - datetime.now()).total_seconds() // 60), 0)

    def _seed_demo_data(self) -> None:
        base_day = datetime.now().replace(hour=7, minute=0, second=0, microsecond=0)
        jamie = self.customer_model.find_known_customer("jamie@k3demo.local", None)
        mika = self.customer_model.find_known_customer("mika@k3demo.local", None)
        john = self.customer_model.find_known_customer("john.kester@k3demo.local", None)
        carla = self.customer_model.find_known_customer("carla.dominguez@k3demo.local", None)
        paul = self.customer_model.find_known_customer("paul.reyes@k3demo.local", None)
        trisha = self.customer_model.find_known_customer("trisha.mendoza@k3demo.local", None)
        denise = self.customer_model.find_known_customer("denise.garcia@k3demo.local", None)
        if not all((jamie, mika, john, carla, paul, trisha, denise)):
            return
        self._append_seed_reservation(
            reservation_code="K3-DEMO-1001",
            customer_id=john["id"],
            cottage_id=2,
            destination_id=1,
            destination="SandBar Area",
            party_size=8,
            departure_time=base_day - timedelta(days=75) + timedelta(hours=2),
            return_time=base_day - timedelta(days=75) + timedelta(hours=7),
            total_price=17000.0,
            status="Completed",
            created_at=base_day - timedelta(days=92),
            completed_at=base_day - timedelta(days=75) + timedelta(hours=7),
        )
        self._append_seed_reservation(
            reservation_code="K3-DEMO-1002",
            customer_id=mika["id"],
            cottage_id=3,
            destination_id=2,
            destination="Snorkeling Area",
            party_size=12,
            departure_time=base_day - timedelta(days=42) + timedelta(hours=3),
            return_time=base_day - timedelta(days=42) + timedelta(hours=9),
            total_price=25200.0,
            status="Completed",
            created_at=base_day - timedelta(days=60),
            completed_at=base_day - timedelta(days=42) + timedelta(hours=9),
        )
        self._append_seed_reservation(
            reservation_code="K3-DEMO-1003",
            customer_id=jamie["id"],
            cottage_id=1,
            destination_id=4,
            destination="Little Boracay",
            party_size=6,
            departure_time=base_day - timedelta(days=15) + timedelta(hours=4),
            return_time=base_day - timedelta(days=15) + timedelta(hours=8),
            total_price=11200.0,
            status="Completed",
            created_at=base_day - timedelta(days=34),
            completed_at=base_day - timedelta(days=15) + timedelta(hours=8),
        )
        self._append_seed_reservation(
            reservation_code="K3-DEMO-1004",
            customer_id=carla["id"],
            cottage_id=1,
            destination_id=1,
            destination="SandBar Area",
            party_size=9,
            departure_time=base_day + timedelta(days=10, hours=1),
            return_time=base_day + timedelta(days=10, hours=6),
            total_price=14000.0,
            status="Reserved",
            created_at=base_day - timedelta(days=2, hours=4),
        )
        self._append_seed_reservation(
            reservation_code="K3-DEMO-1005",
            customer_id=paul["id"],
            cottage_id=3,
            destination_id=4,
            destination="Little Boracay",
            party_size=15,
            departure_time=base_day + timedelta(days=32, hours=2),
            return_time=base_day + timedelta(days=32, hours=9),
            total_price=29400.0,
            status="Reserved",
            created_at=base_day - timedelta(days=1, hours=3),
        )
        self._append_seed_reservation(
            reservation_code="K3-DEMO-1006",
            customer_id=trisha["id"],
            cottage_id=1,
            destination_id=2,
            destination="Snorkeling Area",
            party_size=5,
            departure_time=base_day + timedelta(days=78, hours=3),
            return_time=base_day + timedelta(days=78, hours=6),
            total_price=8400.0,
            status="Reserved",
            created_at=base_day - timedelta(hours=6),
        )
        self._append_seed_reservation(
            reservation_code="K3-DEMO-1007",
            customer_id=denise["id"],
            cottage_id=2,
            destination_id=3,
            destination="Starfish Area",
            party_size=7,
            departure_time=base_day + timedelta(days=18, hours=5),
            return_time=base_day + timedelta(days=18, hours=9),
            total_price=13600.0,
            status="Cancelled",
            created_at=base_day - timedelta(days=8),
            cancelled_at=base_day - timedelta(days=7),
        )

    def _append_seed_reservation(
        self,
        reservation_code: str,
        customer_id: int,
        cottage_id: int,
        destination_id: int,
        destination: str,
        party_size: int,
        departure_time: datetime,
        return_time: datetime,
        total_price: float,
        status: str,
        created_at: datetime,
        completed_at: datetime | None = None,
        cancelled_at: datetime | None = None,
    ) -> None:
        record = {
            "id": self._next_id,
            "reservation_code": reservation_code,
            "customer_id": customer_id,
            "cottage_id": cottage_id,
            "destination_id": destination_id,
            "destination": destination,
            "party_size": party_size,
            "departure_time": departure_time,
            "return_time": return_time,
            "total_price": total_price,
            "status": status,
            "notes": None,
            "created_at": created_at,
            "updated_at": created_at,
            "completed_at": completed_at,
            "cancelled_at": cancelled_at,
        }
        self._next_id += 1
        self._reservations.append(record)
