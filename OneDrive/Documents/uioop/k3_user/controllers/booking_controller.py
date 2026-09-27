"""
controllers/booking_controller.py — Validates and creates reservations.
"""

from datetime import datetime, date as date_type
from models.reservation_model import ReservationModel
from models.cottage_model      import CottageModel, BoatModel


class BookingController:

    def __init__(self, app):
        self.app = app

    def calculate_total(self, cottage: dict, destinations: list[dict], hours: int) -> float:
        total_rate = float(cottage["rate"])
        for dest in destinations:
            total_rate += float(dest.get("rate", 0))
        return round(total_rate * hours, 2)

    def prepare_booking(
        self,
        cottage: dict,
        destinations: list[str],
        travel_date: str,
        slot: str,
        hours: int,
        party: int,
        notes: str,
        booking_type: str = "cottage",
    ) -> tuple[bool, str, dict | None]:
        try:
            td = datetime.strptime(travel_date.strip(), "%Y-%m-%d").date()
        except ValueError:
            return False, "Select a valid travel date from the calendar.", None

        if td < date_type.today():
            return False, "Travel date must be today or in the future.", None

        if hours <= 0:
            return False, "Duration must be at least 1 hour.", None

        if party <= 0:
            return False, "Party size must be at least 1 guest.", None

        # Check availability for the first destination for boat assignment purposes
        primary_dest = destinations[0] if destinations else ""
        if not ReservationModel.is_slot_available(cottage["id"], primary_dest, travel_date, slot, hours):
            return False, "That cottage is already reserved for the selected date and time.", None

        # Fetch destination objects for pricing
        all_boats = BoatModel.get_all()
        selected_boat_assets = [b for b in all_boats if b["name"] in destinations]

        user = self.app.session_user
        draft = {
            "username": user["username"],
            "guest_info": {
                "name": user.get("name", ""),
                "contact": user.get("contact", ""),
                "email": user.get("email", ""),
            },
            "cottage": cottage,
            "destinations": destinations,
            "travel_date": travel_date.strip(),
            "slot": slot,
            "hours": hours,
            "party": party,
            "notes": notes,
            "booking_type": booking_type,
            "total": self.calculate_total(cottage, selected_boat_assets, hours),
        }
        return True, "Review your reservation details before final confirmation.", draft

    def submit_booking(self, draft: dict) -> tuple[bool, str, dict | None]:
        try:
            reservation = ReservationModel.create(
                username=draft["username"],
                guest_info=draft["guest_info"],
                cottage=draft["cottage"],
                destinations=draft["destinations"],
                date=draft["travel_date"],
                slot=draft["slot"],
                hours=int(draft["hours"]),
                party=int(draft["party"]),
                notes=draft["notes"],
                booking_type=draft.get("booking_type", "cottage"),
            )
        except ValueError as exc:
            return False, str(exc), None
        except Exception as exc:
            return False, f"System error: {str(exc)}", None
        return True, "Reservation confirmed!", reservation

    def get_my_reservations(self) -> list[dict]:
        user = self.app.session_user
        if not user:
            return []
        return ReservationModel.get_by_username(user["username"])

    def get_my_payments(self) -> list[dict]:
        user = self.app.session_user
        if not user:
            return []
        return ReservationModel.get_payment_history_by_username(user["username"])
