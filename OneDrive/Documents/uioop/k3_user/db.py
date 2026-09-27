from functools import lru_cache
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from k3_rms.config import DatabaseSettings
from k3_rms.database.connection import DatabaseManager
from k3_rms.database.schema import SchemaManager


@lru_cache(maxsize=1)
def get_database() -> DatabaseManager:
    database = DatabaseManager(DatabaseSettings.from_env())
    SchemaManager(database).initialize()
    return database
