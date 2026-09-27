from datetime import datetime

from k3_rms.config import DESTINATIONS
from k3_rms.exceptions import ReservationValidationError
from k3_rms.models.asset_model import AssetModel
from k3_rms.models.reservation_model import ReservationModel


class AvailabilityService:
    def __init__(self, asset_model: AssetModel, reservation_model: ReservationModel) -> None:
        self.asset_model = asset_model
        self.reservation_model = reservation_model

    def validate_and_assign(
        self,
        departure_time: datetime,
        return_time: datetime,
        party_size: int,
        destination: str,
        cottage_id: int | None = None,
        destination_id: int | None = None,
    ) -> dict:
        if destination not in DESTINATIONS:
            raise ReservationValidationError(
                f"Destination must be one of: {', '.join(DESTINATIONS)}."
            )
        if party_size <= 0:
            raise ReservationValidationError("Party size must be greater than zero.")
        if departure_time >= return_time:
            raise ReservationValidationError("Return time must be later than departure time.")
        if departure_time < datetime.now():
            raise ReservationValidationError("Reservations cannot start in the past.")
        if hasattr(self.reservation_model, "check_slot_has_availability"):
            slot_available = self.reservation_model.check_slot_has_availability(
                departure_time=departure_time,
                return_time=return_time,
                party_size=party_size,
            )
            if not slot_available:
                raise ReservationValidationError(
                    "No cottage and destination pair is available for the selected schedule."
                )

        available_cottages = self.asset_model.find_available_assets(
            "cottage", departure_time, return_time, party_size
        )
        available_destinations = self.asset_model.find_available_assets(
            "destination", departure_time, return_time, party_size
        )
        if not available_cottages:
            raise ReservationValidationError(
                "No floating cottage is available for the selected schedule and party size."
            )
        if not available_destinations:
            raise ReservationValidationError(
                "No destination is available for the selected schedule and party size."
            )

        cottage = self._pick_asset("cottage", available_cottages, cottage_id)
        destination_asset = self._pick_destination(destination, available_destinations, destination_id)
        return {"cottage": cottage, "destination_asset": destination_asset}

    def sync_asset_statuses(self, reference_time: datetime | None = None) -> None:
        del reference_time
        # Availability is derived from reservations at read time.
        # Asset records are no longer mutated with Reserved/On Going flags.
        return

    def _pick_asset(self, asset_type: str, available_assets: list[dict], requested_id: int | None) -> dict:
        if requested_id is None:
            return available_assets[0]
        for asset in available_assets:
            if asset["id"] == requested_id:
                return asset
        label = "cottage" if asset_type == "cottage" else "destination"
        raise ReservationValidationError(
            f"Selected {label} is not available for the requested schedule."
        )

    def _pick_destination(
        self,
        destination_name: str,
        available_destinations: list[dict],
        requested_id: int | None,
    ) -> dict:
        if requested_id is not None:
            return self._pick_asset("destination", available_destinations, requested_id)
        for destination in available_destinations:
            if destination["name"].strip().lower() == destination_name.strip().lower():
                return destination
        raise ReservationValidationError(
            f"The selected destination '{destination_name}' is not available for the requested schedule."
        )
