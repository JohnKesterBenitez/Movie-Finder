from datetime import date, datetime, time, timedelta

from k3_rms.models.asset_model import AssetModel
from k3_rms.models.customer_model import CustomerModel
from k3_rms.models.reservation_model import ReservationModel
from k3_rms.services.availability_service import AvailabilityService


class DashboardController:
    def __init__(
        self,
        reservation_model: ReservationModel,
        customer_model: CustomerModel,
        asset_model: AssetModel,
        availability_service: AvailabilityService,
    ) -> None:
        self.reservation_model = reservation_model
        self.customer_model = customer_model
        self.asset_model = asset_model
        self.availability_service = availability_service

    def get_dashboard_snapshot(self, asset_reference_date: date | None = None) -> dict:
        today = date.today()
        reference_date = asset_reference_date or today
        reference_time = (
            datetime.now()
            if reference_date == today
            else datetime.combine(reference_date, time.min)
        )
        self.reservation_model.auto_expire_pending_reservations()
        self.reservation_model.auto_start_reservations()
        self.reservation_model.auto_complete_reservations()
        return {
            "metrics": self.reservation_model.get_dashboard_metrics(),
            "active_reservations": self.reservation_model.list_active_reservations(),
            "reservations": self.reservation_model.list_reservations(),
            "session_assignments": self.reservation_model.list_session_assignments(reference_time),
            "cottages": self.asset_model.list_cottages(reference_date, reference_time),
            "destinations": self.asset_model.list_destinations(reference_date, reference_time),
        }

    def get_revenue_report_data(self) -> list[dict]:
        return self.reservation_model.get_revenue_report_data()

    def get_date_status_map(
        self,
        destination: str | None = None,
        cottage_code: str | None = None,
        days_ahead: int = 120,
    ) -> dict[str, str]:
        return self.reservation_model.get_date_status_map(destination, cottage_code, days_ahead)

    def get_recent_notifications(self, limit: int = 8) -> list[dict]:
        notifications: list[dict] = []

        for reservation in self.reservation_model.list_recent_reservations(limit):
            notification = self._notification_from_reservation(
                reservation_code=reservation["reservation_code"],
                guest_name=reservation.get("full_name") or "Guest",
                cottage_label=reservation.get("cottage_code") or "Cottage",
                destination=reservation.get("destination") or reservation.get("motorboat_name") or "Destination",
                departure_time=reservation.get("departure_time"),
                created_at=reservation.get("created_at"),
            )
            notifications.append(notification)

        notifications.sort(
            key=lambda item: item.get("created_at") or datetime.min,
            reverse=True,
        )
        return notifications[:limit]

    def _notification_from_reservation(
        self,
        reservation_code: str,
        guest_name: str,
        cottage_label: str,
        destination: str,
        departure_time: datetime | None,
        created_at: datetime | None,
    ) -> dict:
        departure_label = (
            departure_time.strftime("%b %d, %Y %I:%M %p")
            if isinstance(departure_time, datetime)
            else "a scheduled date"
        )
        return {
            "id": reservation_code,
            "type": "new_reservation",
            "title": "New booking received",
            "desc": f"{guest_name} booked {cottage_label} to {destination} for {departure_label}.",
            "time": self._format_relative_time(created_at),
            "created_at": created_at,
        }

    def _format_relative_time(self, value: datetime | None) -> str:
        if not isinstance(value, datetime):
            return "Unknown time"
        delta = datetime.now() - value
        if delta < timedelta(minutes=1):
            return "Just now"
        if delta < timedelta(hours=1):
            minutes = max(int(delta.total_seconds() // 60), 1)
            return f"{minutes} min ago"
        if delta < timedelta(days=1):
            hours = max(int(delta.total_seconds() // 3600), 1)
            return f"{hours} hr ago"
        if delta < timedelta(days=7):
            days = max(delta.days, 1)
            return f"{days} day ago" if days == 1 else f"{days} days ago"
        return value.strftime("%b %d, %Y")

    def delete_guest(self, email: str | None, contact_number: str | None, full_name: str) -> bool:
        """Soft-delete a guest and all their reservations."""
        # 1. Try to find by email/contact
        guest = self.customer_model.find_known_customer(email, contact_number)
        
        # 2. Fallback: Find by name if first lookup failed
        if not guest:
            with self.customer_model.database.session() as (_, cursor):
                cursor.execute(
                    "SELECT id, user_id FROM customers WHERE full_name = %s AND is_deleted = 0 LIMIT 1",
                    (full_name,)
                )
                guest = cursor.fetchone()
                
        if not guest:
            return False
        
        guest_id = guest["id"]
        
        # 1. Soft-delete all their reservations
        with self.reservation_model.database.session() as (_, cursor):
            cursor.execute(
                "UPDATE reservations SET is_deleted = 1 WHERE customer_id = %s",
                (guest_id,),
            )
        
        # 2. Soft-delete the guest
        success = self.customer_model.delete_customer(guest_id)
        
        # 3. Disable the linked user account if it exists
        if success and guest.get("user_id"):
            with self.customer_model.database.session() as (_, cursor):
                cursor.execute(
                    "UPDATE users SET status = 'inactive' WHERE id = %s",
                    (guest["user_id"],)
                )
        
        return success
