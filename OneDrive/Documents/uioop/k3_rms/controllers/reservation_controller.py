from datetime import date, datetime

from k3_rms.config import DESTINATIONS
from k3_rms.exceptions import ReservationValidationError
from k3_rms.models.asset_model import AssetModel
from k3_rms.models.customer_model import CustomerModel
from k3_rms.models.reservation_model import ReservationModel
from k3_rms.services.availability_service import AvailabilityService


class ReservationController:
    DATETIME_FORMAT = "%Y-%m-%d %H:%M"

    def __init__(
        self,
        customer_model: CustomerModel,
        asset_model: AssetModel,
        reservation_model: ReservationModel,
        availability_service: AvailabilityService,
    ) -> None:
        self.customer_model = customer_model
        self.asset_model = asset_model
        self.reservation_model = reservation_model
        self.availability_service = availability_service

    def destinations(self) -> tuple[str, ...]:
        try:
            destinations = self.asset_model.list_destinations()
            if destinations:
                return tuple(destination["name"] for destination in destinations)
        except Exception:
            pass
        return DESTINATIONS

    def cottages(self, reference_date: date | None = None) -> list[dict]:
        try:
            today = datetime.now().date()
            reference_time = datetime.now() if reference_date in (None, today) else None
            return self.asset_model.list_cottages(reference_date, reference_time)
        except Exception:
            return []

    def lookup_customer(self, email: str | None, contact_number: str | None) -> dict | None:
        return self.customer_model.find_known_customer(email, contact_number)

    def create_reservation(self, payload: dict) -> dict:
        full_name = payload["full_name"].strip()
        contact_number = payload.get("contact_number") or None
        email = payload.get("email") or None
        if not full_name:
            raise ReservationValidationError("Customer full name is required.")
        if not contact_number and not email:
            raise ReservationValidationError("Provide at least a contact number or an email address.")

        departure_time = self._parse_datetime(payload["departure_time"])
        return_time = self._parse_datetime(payload["return_time"])
        party_size = int(payload["party_size"])
        selected_assets = self.availability_service.validate_and_assign(
            departure_time=departure_time,
            return_time=return_time,
            party_size=party_size,
            destination=payload["destination"],
            cottage_id=payload.get("cottage_id"),
            destination_id=payload.get("destination_id") or payload.get("destination_asset_id"),
        )

        customer = self.customer_model.upsert_customer(
            full_name,
            contact_number,
            email,
            user_id=payload.get("user_id"),
        )
        reservation_code = self._generate_reservation_code()
        
        # Fetch all selected destination assets to calculate the cumulative price
        destination_names = payload.get("destinations") or [payload["destination"]]
        additional_assets = []
        with self.asset_model.database.session() as (_, cursor):
            placeholders = ", ".join(["%s"] * len(destination_names))
            cursor.execute(
                f"SELECT id, name, base_rate FROM destinations WHERE name IN ({placeholders})",
                tuple(destination_names)
            )
            additional_assets = cursor.fetchall()

        total_price = self.calculate_total_price(
            departure_time=departure_time,
            return_time=return_time,
            cottage=selected_assets["cottage"],
            destination_asset=selected_assets["destination_asset"],
            additional_destinations=additional_assets
        )
        
        # Save comma-separated destinations for the record
        destination_summary = ", ".join(destination_names)

        self.reservation_model.create(
            {
                "reservation_code": reservation_code,
                "user_id": payload.get("user_id"),
                "customer_id": customer["id"],
                "cottage_id": selected_assets["cottage"]["id"],
                "destination_id": selected_assets["destination_asset"]["id"],
                "destination": destination_summary,
                "destinations": destination_names,
                "party_size": party_size,
                "departure_time": departure_time,
                "return_time": return_time,
                "total_price": total_price,
                "status": "Pending" if payload.get("user_id") else "Reserved",
                "notes": payload.get("notes"),
            }
        )
        reservation = self.reservation_model.find_by_code(reservation_code)
        return {
            "customer": customer,
            "reservation": reservation,
            "auto_assigned": {
                "cottage": selected_assets["cottage"],
                "destination_asset": selected_assets["destination_asset"],
            },
        }

    def approve_reservation(self, reservation_code: str) -> dict:
        reservation = self._require_reservation(reservation_code)
        if reservation["status"] != "Pending":
            raise ReservationValidationError("Only pending bookings can be approved.")
        self.reservation_model.update_status(reservation_code, "Reserved")
        return self._require_reservation(reservation_code)

    def start_trip(self, reservation_code: str) -> dict:
        reservation = self._require_reservation(reservation_code)
        if reservation["status"] not in ("Pending", "Reserved"):
            raise ReservationValidationError("Only pending or reserved bookings can be started.")
        self.reservation_model.update_status(reservation_code, "On Going")
        return self._require_reservation(reservation_code)

    def complete_trip(self, reservation_code: str) -> dict:
        reservation = self._require_reservation(reservation_code)
        if reservation["status"] not in ("Reserved", "On Going"):
            raise ReservationValidationError("Only active bookings can be completed.")
        self.reservation_model.update_status(reservation_code, "Completed")
        return self._require_reservation(reservation_code)

    def cancel_reservation(self, reservation_code: str, reason: str | None = None) -> dict:
        reservation = self._require_reservation(reservation_code)
        if reservation["status"] == "Completed":
            raise ReservationValidationError("Completed trips can no longer be cancelled.")
        if reservation["status"] == "Cancelled":
            raise ReservationValidationError("This reservation is already cancelled.")
        self.reservation_model.update_status(reservation_code, "Cancelled", notes=reason)
        return self._require_reservation(reservation_code)

    def preview_availability(self, payload: dict) -> dict:
        departure_time = self._parse_datetime(payload["departure_time"])
        return_time = self._parse_datetime(payload["return_time"])
        party_size = int(payload["party_size"])
        chosen_assets = self.availability_service.validate_and_assign(
            departure_time=departure_time,
            return_time=return_time,
            party_size=party_size,
            destination=payload["destination"],
            cottage_id=payload.get("cottage_id"),
            destination_id=payload.get("destination_id") or payload.get("destination_asset_id"),
        )
        return {
            "cottages": self.asset_model.find_available_assets(
                "cottage", departure_time, return_time, party_size
            ),
            "destination_assets": self.asset_model.find_available_assets(
                "destination", departure_time, return_time, party_size
            ),
            "recommended": chosen_assets,
        }

    def _generate_reservation_code(self) -> str:
        import random
        import string
        characters = string.ascii_uppercase + string.digits
        while True:
            code = "K3-" + "".join(random.choices(characters, k=5))
            if not self.reservation_model.find_by_code(code):
                return code

    def _parse_datetime(self, value: str) -> datetime:
        try:
            return datetime.strptime(value, self.DATETIME_FORMAT)
        except ValueError as exc:
            raise ReservationValidationError(
                f"Use the datetime format {self.DATETIME_FORMAT}."
            ) from exc

    def calculate_total_price(
        self,
        departure_time: datetime,
        return_time: datetime,
        cottage: dict,
        destination_asset: dict,
        additional_destinations: list[dict] | None = None,
    ) -> float:
        duration_hours = max((return_time - departure_time).total_seconds() / 3600, 1)
        hourly_rate = float(cottage["base_rate"]) + float(destination_asset["base_rate"])
        
        if additional_destinations:
            # Sum up rates of all other destinations, avoiding double counting the primary destination_asset
            for asset in additional_destinations:
                if str(asset["id"]) != str(destination_asset["id"]):
                    hourly_rate += float(asset.get("base_rate", 0))
                    
        return round(hourly_rate * duration_hours, 2)

    def get_reservation(self, reservation_code: str) -> dict:
        return self._require_reservation(reservation_code)

    def update_payment_status(
        self,
        reservation_code: str,
        payment_status: str,
        amount_paid: float | None = None,
        payment_method: str | None = None,
        payment_notes: str | None = None,
        recorded_by: str | None = None,
    ) -> dict:
        reservation = self._require_reservation(reservation_code)
        updated = self.reservation_model.update_payment(
            reservation["reservation_code"],
            payment_status=payment_status,
            amount_paid=amount_paid,
            payment_method=payment_method,
            payment_notes=payment_notes,
            recorded_by=recorded_by,
        )
        if not updated:
            raise ReservationValidationError("Reservation code was not found.")
        return updated

    def get_payment_history(self, reservation_code: str, limit: int = 10) -> list[dict]:
        self._require_reservation(reservation_code)
        return self.reservation_model.list_payment_history(reservation_code, limit=limit)

    def get_payment_logs(self, reservation_code: str, limit: int = 10) -> list[dict]:
        self._require_reservation(reservation_code)
        return self.reservation_model.list_payment_logs(reservation_code, limit=limit)

    def _require_reservation(self, reservation_code: str) -> dict:
        reservation = self.reservation_model.find_by_code(reservation_code)
        if not reservation:
            raise ReservationValidationError("Reservation code was not found.")
        return reservation

    def delete_reservation(self, reservation_code: str) -> bool:
        """Soft-delete a reservation if it's completed or cancelled."""
        reservation = self._require_reservation(reservation_code)
        # We allow deleting only Completed or Cancelled to prevent logic errors in active trips
        if reservation["status"] not in ("Completed", "Cancelled"):
             raise ReservationValidationError(f"Only completed or cancelled bookings can be deleted. Current status: {reservation['status']}")
        
        return self.reservation_model.delete_reservation(reservation_code)
