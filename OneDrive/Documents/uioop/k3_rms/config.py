from dataclasses import dataclass
from getpass import getpass
import os
from pathlib import Path
import sys

from k3_rms.exceptions import DatabaseConfigurationError

DEFAULT_APP_USERNAME = "admin"
DEFAULT_APP_PASSWORD = "k3admin123"


DEFAULT_COTTAGES = (
    {"asset_code": "FC-01", "name": "Azure Breeze", "capacity": 20, "base_rate": 2800.00},
    {"asset_code": "FC-02", "name": "Sea Haven", "capacity": 20, "base_rate": 3400.00},
    {"asset_code": "FC-03", "name": "Driftwood Lounge", "capacity": 20, "base_rate": 4200.00},
)

DEFAULT_DESTINATION_ASSETS = (
    {"asset_code": "DST-01", "name": "SandBar Area", "capacity": 20, "base_rate": 0.00},
    {"asset_code": "DST-02", "name": "Snorkeling Area", "capacity": 20, "base_rate": 300.00},
    {"asset_code": "DST-03", "name": "Starfish Area", "capacity": 20, "base_rate": 300.00},
    {"asset_code": "DST-04", "name": "Little Boracay", "capacity": 20, "base_rate": 500.00},
    {"asset_code": "DST-05", "name": "Wave Runner", "capacity": 20, "base_rate": 500.00},
)

DESTINATIONS = tuple(asset["name"] for asset in DEFAULT_DESTINATION_ASSETS)
DEFAULT_MOTORBOATS = DEFAULT_DESTINATION_ASSETS
PENDING_APPROVAL_DEADLINE_HOURS = 24

TOUR_HEADLINE = "CALATAGAN LITTLE BORACAY DAY TOUR"
TOUR_HIGHLIGHTS = (
    "No entrance fee.",
    "No corkage fee.",
    "Day tour only from 6:00 AM to 4:00 PM.",
    "3 to 4 hours travel from Manila to Calatagan, Batangas.",
    "100% safe for kids, seniors, and PWD guests.",
    "First downpayment first serve to secure your floating cottage slot.",
    "Maximum capacity is 20 pax per floating cottage.",
    "Pet friendly.",
    "Accommodating tour guide.",
)
OTHER_INCLUSIONS = (
    "Free use of griller.",
    "Dressing room.",
    "Medicine kit.",
    "Life vest.",
    "Life guard.",
    "Boat man.",
    "Motor boat.",
    "Body board.",
    "Foam on request.",
)
FOOD_OPTIONS = (
    "Boodle fight packages for 10 pax.",
    "Boodle fight packages for 15 pax.",
)
TRANSIENT_OPTIONS = (
    "Transient house near the docking area for 5 to 10 pax.",
    "Transient house near the docking area for 15 to 20 pax.",
)
DISCLAIMER_TEXT = (
    "Little Boracay is not beachfront. This is an island-hopping setup where a motorboat "
    "pulls the floating cottage across the four destinations."
)
CONTACT_NAME = "Katelyn Carmina Delos Santos"
CONTACT_PHONE = "09615560030"


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    user: str
    password: str
    database: str

    @classmethod
    def from_env(cls) -> "DatabaseSettings":
        _load_dotenv_file()
        host = os.getenv("K3_DB_HOST", "localhost")
        port = int(os.getenv("K3_DB_PORT", "3306"))
        user = os.getenv("K3_DB_USER", "root")
        password = _resolve_password()
        database = os.getenv("K3_DB_NAME", "k3_floating_cottage")
        if password is None:
            raise DatabaseConfigurationError(
                "Set K3_DB_PASSWORD, add it to a local .env file, or run the app in a terminal "
                "so it can prompt for the MySQL password."
            )
        return cls(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
        )


@dataclass(frozen=True)
class AppLoginSettings:
    username: str
    password: str

    @classmethod
    def from_env(cls) -> "AppLoginSettings":
        _load_dotenv_file()
        return cls(
            username=os.getenv("K3_APP_USERNAME", DEFAULT_APP_USERNAME),
            password=os.getenv("K3_APP_PASSWORD", DEFAULT_APP_PASSWORD),
        )

    def uses_default_credentials(self) -> bool:
        return self.username == DEFAULT_APP_USERNAME and self.password == DEFAULT_APP_PASSWORD

    @classmethod
    def persist(cls, username: str, password: str) -> "AppLoginSettings":
        normalized_username = username.strip()
        if not normalized_username:
            raise ValueError("Username cannot be empty.")
        if not password:
            raise ValueError("Password cannot be empty.")

        _persist_env_values(
            {
                "K3_APP_USERNAME": normalized_username,
                "K3_APP_PASSWORD": password,
            }
        )
        return cls(username=normalized_username, password=password)


def _load_dotenv_file() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _persist_env_values(updates: dict[str, str | int]) -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    existing_lines: list[str] = []
    replaced_keys: set[str] = set()

    if env_path.exists():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = raw_line.strip()
            if stripped and not stripped.startswith("#") and "=" in raw_line:
                key, _ = raw_line.split("=", 1)
                normalized_key = key.strip()
                if normalized_key in updates:
                    if normalized_key not in replaced_keys:
                        existing_lines.append(f"{normalized_key}={_format_env_value(updates[normalized_key])}")
                        replaced_keys.add(normalized_key)
                    continue
            existing_lines.append(raw_line)

    for key, value in updates.items():
        if key not in replaced_keys:
            existing_lines.append(f"{key}={_format_env_value(value)}")

    env_path.write_text("\n".join(existing_lines).rstrip() + "\n", encoding="utf-8")
    for key, value in updates.items():
        os.environ[str(key)] = str(value)


def _format_env_value(value: str | int) -> str:
    text = str(value)
    needs_quotes = (
        text == ""
        or any(character.isspace() for character in text)
        or "#" in text
        or '"' in text
        or "'" in text
    )
    if needs_quotes:
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def _resolve_password() -> str | None:
    if "K3_DB_PASSWORD" in os.environ:
        return os.environ.get("K3_DB_PASSWORD", "")
    if sys.stdin is not None and sys.stdin.isatty():
        try:
            return getpass("Enter MySQL password for K3 RMS: ")
        except (EOFError, KeyboardInterrupt):
            return None
    return None
