import sys
import os
from pathlib import Path

# Add the project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from k3_rms.database.connection import DatabaseManager
from k3_rms.config import DatabaseSettings

def fix_asset_code():
    try:
        settings = DatabaseSettings.from_env()
        db = DatabaseManager(settings)
        db.connect()
        with db.session() as (_, cursor):
            # Update Wave Runner to DST-05
            cursor.execute("UPDATE destinations SET asset_code = 'DST-05' WHERE name = 'Wave Runner'")
            print("Successfully updated 'Wave Runner' to 'DST-05'")
        db.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_asset_code()
