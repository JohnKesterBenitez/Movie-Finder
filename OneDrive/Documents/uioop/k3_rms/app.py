from dataclasses import dataclass
from k3_rms.config import AppLoginSettings, DatabaseSettings, _persist_env_values
from k3_rms.controllers.auth_controller import AuthController
from k3_rms.controllers.dashboard_controller import DashboardController
from k3_rms.controllers.reservation_controller import ReservationController
from k3_rms.database.connection import DatabaseManager
from k3_rms.database.schema import SchemaManager
from k3_rms.exceptions import ApplicationError
from k3_rms.models.asset_model import AssetModel
from k3_rms.models.customer_model import CustomerModel
from k3_rms.models.reservation_model import ReservationModel
from k3_rms.services.availability_service import AvailabilityService
from k3_rms.services.auth_service import AuthService
from k3_rms.views.desktop_view import DesktopView


@dataclass
class ApplicationContext:
    reservation_controller: ReservationController
    dashboard_controller: DashboardController
    auth_controller: AuthController
    data_mode: str
    startup_notice: str


def build_context_from_env() -> ApplicationContext:
    try:
        settings = DatabaseSettings.from_env()
    except Exception as exc:
        raise ApplicationError(
            "Database access is required for this build. Update the MySQL settings in `.env` "
            f"and make sure the server is reachable. Details: {exc}"
        )
    return build_mysql_context(settings, startup_notice="Connected to MySQL live data.")


def build_mysql_context(
    settings: DatabaseSettings,
    startup_notice: str | None = None,
) -> ApplicationContext:
    database = DatabaseManager(settings)
    schema_manager = SchemaManager(database)
    warnings = schema_manager.initialize()

    customer_model = CustomerModel(database)
    asset_model = AssetModel(database)
    reservation_model = ReservationModel(database)
    availability_service = AvailabilityService(asset_model, reservation_model)

    reservation_controller = ReservationController(
        customer_model=customer_model,
        asset_model=asset_model,
        reservation_model=reservation_model,
        availability_service=availability_service,
    )
    dashboard_controller = DashboardController(
        reservation_model=reservation_model,
        customer_model=customer_model,
        asset_model=asset_model,
        availability_service=availability_service,
    )
    auth_service = AuthService(database)
    auth_controller = AuthController(auth_service)
    return ApplicationContext(
        reservation_controller=reservation_controller,
        dashboard_controller=dashboard_controller,
        auth_controller=auth_controller,
        data_mode="mysql",
        startup_notice=startup_notice or (
            "Connected to MySQL live data."
            + (f" {warnings[0]}" if warnings else "")
        ),
    )


def connect_database_and_persist(
    host: str,
    port: str | int,
    user: str,
    password: str,
    database: str,
) -> ApplicationContext:
    settings = DatabaseSettings(
        host=(host or "localhost").strip(),
        port=int(port or 3306),
        user=(user or "root").strip(),
        password=password,
        database=(database or "k3_floating_cottage").strip(),
    )
    context = build_mysql_context(
        settings,
        startup_notice="Connected to MySQL live data. New reservations will now save to the database.",
    )
    _write_env_file(settings)
    return context


def _write_env_file(settings: DatabaseSettings) -> None:
    login_settings = AppLoginSettings.from_env()
    _persist_env_values(
        {
            "K3_DB_HOST": settings.host,
            "K3_DB_PORT": settings.port,
            "K3_DB_USER": settings.user,
            "K3_DB_PASSWORD": settings.password,
            "K3_DB_NAME": settings.database,
            "K3_APP_USERNAME": login_settings.username,
            "K3_APP_PASSWORD": login_settings.password,
        }
    )


def build_application() -> DesktopView:
    context = build_context_from_env()
    return DesktopView(
        reservation_controller=context.reservation_controller,
        dashboard_controller=context.dashboard_controller,
        auth_controller=context.auth_controller,
        data_mode=context.data_mode,
        startup_notice=context.startup_notice,
        connect_database_callback=connect_database_and_persist,
        login_settings=AppLoginSettings.from_env(),
    )


def run() -> None:
    try:
        build_application().run()
    except ApplicationError as exc:
        print(f"Startup failed: {exc}")
    except Exception as exc:  # pragma: no cover - runtime guard for CLI use
        print(f"Unexpected error: {exc}")
