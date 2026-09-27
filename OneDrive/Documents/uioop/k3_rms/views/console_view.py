from datetime import datetime, timedelta

from k3_rms.controllers.dashboard_controller import DashboardController
from k3_rms.controllers.reservation_controller import ReservationController
from k3_rms.exceptions import ApplicationError


class ConsoleView:
    def __init__(
        self,
        reservation_controller: ReservationController,
        dashboard_controller: DashboardController,
    ) -> None:
        self.reservation_controller = reservation_controller
        self.dashboard_controller = dashboard_controller

    def run(self) -> None:
        self._print_header("K3's Floating Cottage RMS")
        while True:
            self.render_dashboard()
            print("\nMenu")
            print("1. Create reservation")
            print("2. Complete trip")
            print("3. Cancel reservation")
            print("4. Check availability")
            print("0. Exit")
            choice = input("\nChoose an action: ").strip()
            try:
                if choice == "1":
                    self.handle_create_reservation()
                elif choice == "2":
                    self.handle_status_change("complete")
                elif choice == "3":
                    self.handle_status_change("cancel")
                elif choice == "4":
                    self.handle_preview_availability()
                elif choice == "0":
                    print("Goodbye.")
                    return
                else:
                    print("Please choose a valid option.")
            except ApplicationError as exc:
                print(f"\nAction failed: {exc}")
            except (ValueError, IndexError):
                print("\nAction failed: Please review your input and try again.")

    def render_dashboard(self) -> None:
        snapshot = self.dashboard_controller.get_dashboard_snapshot()
        metrics = snapshot["metrics"]
        print("\n" + "=" * 72)
        print("Transaction Summary Dashboard")
        print("=" * 72)
        print(
            "Active: {active} | Completed: {completed} | Cancelled: {cancelled} | "
            "Today: {daily} | This Week: {weekly}".format(
                active=metrics["active_reservations"],
                completed=metrics["completed_trips"],
                cancelled=metrics["cancellations"],
                daily=metrics["daily_bookings"],
                weekly=metrics["weekly_bookings"],
            )
        )
        self._print_asset_summary("Floating Cottages", snapshot["cottages"])
        self._print_asset_summary("Destinations", snapshot["motorboats"])
        print("\nActive Reservations")
        self._print_table(
            snapshot["active_reservations"],
            (
                ("reservation_code", "Code"),
                ("full_name", "Guest"),
                ("destination", "Destination"),
                ("departure_time", "Departure"),
                ("status", "Status"),
                ("cottage_code", "Cottage"),
                ("destination_code", "Destination"),
            ),
        )

    def handle_create_reservation(self) -> None:
        print("\nCreate Reservation")
        contact_number = self._optional_input("Contact number")
        email = self._optional_input("Email")
        known_customer = self.reservation_controller.lookup_customer(email, contact_number)

        if known_customer:
            print("Known customer found. Press Enter to keep the stored values.")
        full_name_default = known_customer["full_name"] if known_customer else ""
        contact_default = known_customer["contact_number"] if known_customer else contact_number
        email_default = known_customer["email"] if known_customer else email

        full_name = self._prompt_with_default("Full name", full_name_default)
        contact_number = self._prompt_with_default("Contact number", contact_default)
        email = self._prompt_with_default("Email", email_default)

        destinations = self.reservation_controller.destinations()
        for index, destination in enumerate(destinations, start=1):
            print(f"{index}. {destination}")
        destination_choice = int(input("Destination number: ").strip())
        destination = destinations[destination_choice - 1]

        default_departure = (datetime.now() + timedelta(hours=2)).replace(
            minute=0,
            second=0,
            microsecond=0,
        )
        departure_time = self._prompt_with_default(
            "Departure (YYYY-MM-DD HH:MM)",
            default_departure.strftime(ReservationController.DATETIME_FORMAT),
        )
        duration_hours = float(self._prompt_with_default("Trip duration in hours", "4"))
        return_time = (
            datetime.strptime(departure_time, ReservationController.DATETIME_FORMAT)
            + timedelta(hours=duration_hours)
        ).strftime(ReservationController.DATETIME_FORMAT)
        party_size = self._prompt_with_default("Party size", "6")
        notes = self._optional_input("Notes")

        result = self.reservation_controller.create_reservation(
            {
                "full_name": full_name,
                "contact_number": contact_number,
                "email": email,
                "destination": destination,
                "departure_time": departure_time,
                "return_time": return_time,
                "party_size": party_size,
                "notes": notes,
            }
        )
        reservation = result["reservation"]
        assigned = result["auto_assigned"]
        print("\nReservation confirmed.")
        print(f"Reservation code: {reservation['reservation_code']}")
        print(f"Guest: {reservation['full_name']}")
        print(f"Destination: {reservation['destination']}")
        print(f"Cottage: {assigned['cottage']['asset_code']} - {assigned['cottage']['name']}")
        print(f"Motorboat: {assigned['motorboat']['asset_code']} - {assigned['motorboat']['name']}")
        print(f"Total price: PHP {float(reservation['total_price']):,.2f}")

    def handle_status_change(self, action: str) -> None:
        reservation_code = input("Reservation code: ").strip()
        if action == "start":
            reservation = self.reservation_controller.start_trip(reservation_code)
            print(f"Trip started for {reservation['reservation_code']}.")
        elif action == "complete":
            reservation = self.reservation_controller.complete_trip(reservation_code)
            print(f"Trip completed for {reservation['reservation_code']}.")
        else:
            reason = self._optional_input("Cancellation reason")
            reservation = self.reservation_controller.cancel_reservation(reservation_code, reason)
            print(f"Reservation {reservation['reservation_code']} cancelled.")

    def handle_preview_availability(self) -> None:
        print("\nAvailability Check")
        destinations = self.reservation_controller.destinations()
        for index, destination in enumerate(destinations, start=1):
            print(f"{index}. {destination}")
        destination_choice = int(input("Destination number: ").strip())
        departure_time = input("Departure (YYYY-MM-DD HH:MM): ").strip()
        duration_hours = float(input("Trip duration in hours: ").strip())
        return_time = (
            datetime.strptime(departure_time, ReservationController.DATETIME_FORMAT)
            + timedelta(hours=duration_hours)
        ).strftime(ReservationController.DATETIME_FORMAT)
        party_size = input("Party size: ").strip()
        result = self.reservation_controller.preview_availability(
            {
                "destination": destinations[destination_choice - 1],
                "departure_time": departure_time,
                "return_time": return_time,
                "party_size": party_size,
            }
        )
        print("\nRecommended Assignment")
        print(
            f"Cottage: {result['recommended']['cottage']['asset_code']} - "
            f"{result['recommended']['cottage']['name']}"
        )
        print(
            f"Motorboat: {result['recommended']['motorboat']['asset_code']} - "
            f"{result['recommended']['motorboat']['name']}"
        )
        print("\nAvailable Cottages")
        self._print_table(
            result["cottages"],
            (
                ("asset_code", "Code"),
                ("name", "Name"),
                ("capacity", "Capacity"),
                ("status", "Status"),
                ("base_rate", "Rate"),
            ),
        )
        print("\nAvailable Destinations")
        self._print_table(
            result["motorboats"],
            (
                ("asset_code", "Code"),
                ("name", "Name"),
                ("capacity", "Capacity"),
                ("status", "Status"),
                ("base_rate", "Rate"),
            ),
        )

    def _optional_input(self, label: str) -> str | None:
        value = input(f"{label}: ").strip()
        return value or None

    def _prompt_with_default(self, label: str, default: str | None) -> str:
        if default:
            value = input(f"{label} [{default}]: ").strip()
            return value or default
        return input(f"{label}: ").strip()

    def _print_header(self, title: str) -> None:
        print("=" * len(title))
        print(title)
        print("=" * len(title))

    def _print_asset_summary(self, label: str, assets: list[dict]) -> None:
        if not assets:
            print(f"\n{label}: no records found.")
            return
        available = sum(1 for asset in assets if asset["status"] == "Available")
        reserved = sum(1 for asset in assets if asset["status"] == "Reserved")
        in_use = sum(1 for asset in assets if asset["status"] == "On Going")
        print(f"\n{label}: Available={available}, Reserved={reserved}, On Going={in_use}")

    def _print_table(self, rows: list[dict], columns: tuple[tuple[str, str], ...]) -> None:
        if not rows:
            print("No records found.")
            return
        headers = [label for _, label in columns]
        table = [headers]
        for row in rows:
            formatted = []
            for key, _ in columns:
                value = row.get(key, "")
                if isinstance(value, datetime):
                    value = value.strftime("%Y-%m-%d %H:%M")
                elif isinstance(value, float):
                    value = f"{value:,.2f}"
                formatted.append(str(value))
            table.append(formatted)
        widths = [max(len(line[index]) for line in table) for index in range(len(headers))]
        for row_index, row in enumerate(table):
            line = " | ".join(value.ljust(widths[index]) for index, value in enumerate(row))
            print(line)
            if row_index == 0:
                print("-+-".join("-" * width for width in widths))
